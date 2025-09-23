from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timedelta
from keybords.keybord_client import kb_client
import re
import sqlite3
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database.engine import async_session_factory
from database.requests import save_submitted_record, get_top_records, get_russia_record, get_user_records, get_user_submitted_records
from database.models import User, UserTeams

from records.record_kb import (
    get_record_main_menu, get_record_submission_menu, get_date_input_keyboard,
    get_score_input_keyboard, get_video_upload_keyboard, get_admin_record_review_keyboard,
    get_record_status_keyboard, remove_keyboard, get_cancel_keyboard, get_confirmation_keyboard
)

router = Router()

def check_user_registration_simple(user_id: int) -> bool:
    """Простая проверка регистрации пользователя в системе"""
    try:
        conn = sqlite3.connect('mydatabase.db')
        cursor = conn.cursor()
        
        # Проверяем, есть ли пользователь в таблице users и привязан ли он к команде
        cursor.execute("""
            SELECT u.tg_id, u.team_id 
            FROM users u 
            WHERE u.tg_id = ? AND u.team_id IS NOT NULL
        """, (user_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        return result is not None
    except Exception:
        return False

def is_video_url(text: str) -> bool:
    """Проверяет, является ли текст ссылкой на видео"""
    import re
    
    # Паттерны для популярных видеохостингов
    video_patterns = [
        r'https?://(?:www\.)?youtube\.com/watch\?v=[\w-]+',
        r'https?://(?:www\.)?youtu\.be/[\w-]+',
        r'https?://(?:www\.)?vimeo\.com/\d+',
        r'https?://(?:www\.)?dailymotion\.com/video/[\w-]+',
        r'https?://(?:www\.)?rutube\.ru/video/[\w-]+',
        r'https?://(?:www\.)?vk\.com/video-?\d+_\d+',
        r'https?://(?:www\.)?ok\.ru/video/\d+',
        r'https?://(?:www\.)?mail\.ru/video/[\w-]+',
        r'https?://(?:www\.)?twitch\.tv/[\w-]+',
        r'https?://(?:www\.)?tiktok\.com/@[\w-]+/video/\d+'
    ]
    
    for pattern in video_patterns:
        if re.match(pattern, text, re.IGNORECASE):
            return True
    
    return False

def get_video_platform(url: str) -> str:
    """Определяет платформу видео по ссылке"""
    import re
    
    if re.search(r'youtube\.com|youtu\.be', url, re.IGNORECASE):
        return "YouTube"
    elif re.search(r'vimeo\.com', url, re.IGNORECASE):
        return "Vimeo"
    elif re.search(r'dailymotion\.com', url, re.IGNORECASE):
        return "Dailymotion"
    elif re.search(r'rutube\.ru', url, re.IGNORECASE):
        return "Rutube"
    elif re.search(r'vk\.com', url, re.IGNORECASE):
        return "VK"
    elif re.search(r'ok\.ru', url, re.IGNORECASE):
        return "OK.ru"
    elif re.search(r'mail\.ru', url, re.IGNORECASE):
        return "Mail.ru"
    elif re.search(r'twitch\.tv', url, re.IGNORECASE):
        return "Twitch"
    elif re.search(r'tiktok\.com', url, re.IGNORECASE):
        return "TikTok"
    else:
        return "Другая платформа"

class RecordSubmissionStates(StatesGroup):
    waiting_for_date = State()
    waiting_for_score = State()
    waiting_for_video = State()
    confirming_submission = State()

# Временное хранилище данных о рекорде (в реальном проекте лучше использовать Redis или базу данных)
user_record_data = {}
submitted_records = []  # Список отправленных рекордов


def _split_text(text: str, limit: int = 4000) -> list[str]:
    """Разбивает текст на части, безопасные для Telegram (лимит ~4096)."""
    if not text:
        return [""]
    return [text[i:i + limit] for i in range(0, len(text), limit)]


async def _send_message_chunked(bot, chat_id: int, text: str):
    """Отправляет длинный текст несколькими сообщениями чтобы избежать MESSAGE_TOO_LONG."""
    for chunk in _split_text(text):
        await bot.send_message(chat_id=chat_id, text=chunk)

@router.callback_query(F.data == "records")
async def show_records_menu(callback: CallbackQuery):
    """Показать главное меню рекордов"""
    user_id = callback.from_user.id
    
    # Проверяем регистрацию пользователя
    if not check_user_registration_simple(user_id):
        await callback.message.edit_text(
            "🏆 Меню рекордов Лиги Решений\n\n"
            "❌ Доступ ограничен\n\n"
            "Для работы с рекордами необходимо:\n"
            "✅ Зарегистрироваться в системе\n"
            "После регистрации вы сможете:\n"
            "• Посмотреть актуальный рекорд России\n"
            "• Отправить свой рекорд на проверку\n"
            "• Просмотреть свои достижения\n"
            "• Сравнить результаты с другими командами\n\n"
            "Пожалуйста, сначала пройдите регистрацию.",
            reply_markup=get_record_main_menu()
        )
        return
    
    await callback.message.edit_text(
        "🏆 Меню рекордов Лиги Решений\n\n"
        "Добро пожаловать в систему рекордов Лиги Решений!\n"
        "Здесь вы можете:\n"
        "• Посмотреть актуальный рекорд России\n"
        "• Отправить свой рекорд на проверку\n"
        "• Просмотреть свои достижения\n"
        "• Сравнить результаты с другими командами\n\n"
        "Выберите нужный раздел:",
        reply_markup=get_record_main_menu()
    )

@router.callback_query(F.data == "submit_record")
async def start_record_submission(callback: CallbackQuery, state: FSMContext):
    """Начать процесс отправки рекорда"""
    user_id = callback.from_user.id
    
    # Проверяем регистрацию пользователя
    if not check_user_registration_simple(user_id):
        await callback.answer(
            "❌ Для отправки рекорда необходимо зарегистрироваться в системе!", 
            show_alert=True
        )
        await callback.message.edit_text(
            "❌ Доступ запрещен\n\n"
            "Для отправки рекорда необходимо:\n"
            "✅ Зарегистрироваться в системе\n"
            "Пожалуйста, сначала пройдите регистрацию.",
            reply_markup=get_record_main_menu()
        )
        return
    
    # Инициализируем данные пользователя
    if user_id not in user_record_data:
        user_record_data[user_id] = {}

    # Запускаем пошаговый сценарий с запроса даты
    await state.set_state(RecordSubmissionStates.waiting_for_date)
    await callback.message.edit_text(
        "📤 ОТПРАВКА РЕКОРДА НА ПРОВЕРКУ\n\n"
        "Шаг 1 из 3 — укажите дату установки рекорда.\n\n"
        "Выберите один из вариантов ниже или введите дату в формате ДД.ММ.ГГГГ.\n"
        "⚠️ Дата не может быть в будущем.")
    await callback.message.answer(
        "Выберите дату:",
        reply_markup=get_date_input_keyboard()
    )

@router.callback_query(F.data == "set_record_date")
async def set_record_date(callback: CallbackQuery, state: FSMContext):
    """Установить дату рекорда"""
    await state.set_state(RecordSubmissionStates.waiting_for_date)
    
    await callback.message.edit_text(
        "📅 Укажите дату установки рекорда\n\n"
        "Выберите один из вариантов или введите дату в формате ДД.ММ.ГГГГ\n\n"
        "⚠️ Дата не может быть в будущем"
    )
    
    await callback.message.answer(
        "Выберите дату:",
        reply_markup=get_date_input_keyboard()
    )

@router.message(RecordSubmissionStates.waiting_for_date)
async def process_date_input(message: Message, state: FSMContext):
    """Обработать ввод даты"""
    user_id = message.from_user.id
    text = message.text
    
    try:
        if text == "📅 Сегодня":
            record_date = datetime.now().strftime("%d.%m.%Y")
        elif text == "📅 Вчера":
            record_date = (datetime.now() - timedelta(days=1)).strftime("%d.%m.%Y")
        elif text == "🔙 Отмена":
            await state.clear()
            await message.answer(
                "Отправка рекорда отменена.",
                reply_markup=remove_keyboard()
            )
            await message.answer(
                "🏆 Меню рекордов",
                reply_markup=get_record_main_menu()
            )
            return
        elif text == "✏️ Ввести дату вручную":
            await message.answer(
                "Введите дату в формате ДД.ММ.ГГГГ (например: 15.03.2024):",
                reply_markup=get_cancel_keyboard()
            )
            return
        else:
            # Проверяем формат даты
            if re.match(r'^\d{2}\.\d{2}\.\d{4}$', text):
                # Проверяем валидность даты
                date_obj = datetime.strptime(text, "%d.%m.%Y")
                # Проверяем, что дата не в будущем
                if date_obj > datetime.now():
                    await message.answer(
                        "❌ Дата не может быть в будущем.",
                        reply_markup=get_date_input_keyboard()
                    )
                    return
                record_date = text
            else:
                await message.answer(
                    "❌ Неверный формат даты. Используйте формат ДД.ММ.ГГГГ",
                    reply_markup=get_date_input_keyboard()
                )
                return
        
        # Сохраняем дату
        user_record_data[user_id]['date'] = record_date
        
        # Переходим к следующему шагу — очки
        await state.set_state(RecordSubmissionStates.waiting_for_score)
        await message.answer(
            f"✅ Дата установлена: {record_date}",
            reply_markup=remove_keyboard()
        )
        await message.answer(
            "🎯 Шаг 2 из 3 — укажите количество набранных очков.\n\n"
            "Введите число от 0 до 700.",
            reply_markup=get_score_input_keyboard()
        )
        
    except ValueError:
        await message.answer(
            "❌ Неверная дата. Проверьте правильность ввода.",
            reply_markup=get_date_input_keyboard()
        )

@router.callback_query(F.data == "set_record_score")
async def set_record_score(callback: CallbackQuery, state: FSMContext):
    """Установить количество очков"""
    await state.set_state(RecordSubmissionStates.waiting_for_score)
    
    await callback.message.edit_text(
        "🎯 Укажите количество набранных очков\n\n"
        "Введите число от 0 до максимально возможного количества очков.\n"
        "Максимальное количество очков: 700\n\n"
        "💡 Убедитесь, что указываете точное количество очков, "
        "которое видно на финальном экране."
    )
    
    await callback.message.answer(
        "Введите количество очков:",
        reply_markup=get_score_input_keyboard()
    )

@router.message(RecordSubmissionStates.waiting_for_score)
async def process_score_input(message: Message, state: FSMContext):
    """Обработать ввод очков"""
    user_id = message.from_user.id
    text = message.text
    
    if text == "🔙 Отмена":
        await state.clear()
        await message.answer(
            "Отправка рекорда отменена.",
            reply_markup=remove_keyboard()
        )
        await message.answer(
            "🏆 Меню рекордов",
            reply_markup=get_record_main_menu()
        )
        return
    
    # Если пользователь нажал кнопку из клавиатуры, подскажем ввести число
    if text.strip() == "🎯 Ввести количество очков":
        await message.answer(
            "Введите число очков (0-700) цифрами, например: 345",
            reply_markup=get_score_input_keyboard()
        )
        return
    
    try:
        score = int(text)
        if score < 0:
            await message.answer(
                "❌ Количество очков не может быть отрицательным.",
                reply_markup=get_score_input_keyboard()
            )
            return
        
        if score > 700:
            await message.answer(
                "❌ Максимальное количество очков: 700",
                reply_markup=get_score_input_keyboard()
            )
            return
        
        # Сохраняем очки
        user_record_data[user_id]['score'] = score
        
        # Переходим к следующему шагу — видео
        await state.set_state(RecordSubmissionStates.waiting_for_video)
        await message.answer(
            f"✅ Количество очков установлено: {score}",
            reply_markup=remove_keyboard()
        )
        await message.answer(
            "🎥 Шаг 3 из 3 — отправьте видео-подтверждение.\n\n"
            "Можно загрузить видео файлом (до 50 МБ и до 5 минут) или отправить ссылку на платформу (YouTube, Vimeo и т.д.)",
            reply_markup=get_video_upload_keyboard()
        )
        
    except ValueError:
        await message.answer(
            "❌ Введите корректное число.",
            reply_markup=get_score_input_keyboard()
        )

@router.callback_query(F.data == "upload_video")
async def upload_video(callback: CallbackQuery, state: FSMContext):
    """Загрузить видео или ссылку на видео"""
    await state.set_state(RecordSubmissionStates.waiting_for_video)
    
    await callback.message.edit_text(
        "🎥 Загрузка видео-подтверждения\n\n"
        "Вы можете отправить:\n"
        "📹 Видео файл - загрузить видео напрямую\n"
        "🔗 Ссылку на видео - вставить ссылку на YouTube, Vimeo и т.д.\n\n"
        "📋 Требования к видео:\n"
        "• Четко видна игровая область\n"
        "• Видно финальный счет\n"
        "• Полный раунд от начала до конца\n"
        "• Соблюдение всех правил Лиги Решений\n\n"
        "⚠️ Видео будет проверено модераторами"
    )
    
    await callback.message.answer(
        "Отправьте видео файл или ссылку на видео:",
        reply_markup=get_video_upload_keyboard()
    )

@router.message(RecordSubmissionStates.waiting_for_video, F.content_type == "video")
async def process_video_upload(message: Message, state: FSMContext):
    """Обработать загрузку видео файла"""
    user_id = message.from_user.id
    
    # Проверяем размер файла (50 МБ = 50 * 1024 * 1024 байт)
    if message.video.file_size > 50 * 1024 * 1024:
        await message.answer(
            "❌ Размер файла слишком большой. Максимальный размер: 50 МБ",
            reply_markup=get_video_upload_keyboard()
        )
        return
    
    # Проверяем длительность видео (5 минут = 300 секунд)
    if message.video.duration > 300:
        await message.answer(
            "❌ Видео слишком длинное. Максимальная длительность: 5 минут",
            reply_markup=get_video_upload_keyboard()
        )
        return
    
    # Сохраняем информацию о видео
    user_record_data[user_id]['video'] = {
        'type': 'file',
        'file_id': message.video.file_id,
        'file_unique_id': message.video.file_unique_id,
        'duration': message.video.duration,
        'file_size': message.video.file_size,
        'file_name': message.video.file_name or "video.mp4"
    }
    
    # Переходим к подтверждению
    await state.set_state(RecordSubmissionStates.confirming_submission)
    await message.answer(
        f"✅ Видео файл загружен: {user_record_data[user_id]['video']['file_name']}",
        reply_markup=remove_keyboard()
    )
    user_data = user_record_data[user_id]
    video_info = f"📹 {user_data['video']['file_name']} ({user_data['video']['duration']}с, {user_data['video']['file_size'] // 1024 // 1024}МБ)"
    confirmation_text = (
        "✅ ПОДТВЕРЖДЕНИЕ ОТПРАВКИ РЕКОРДА\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Проверьте данные перед отправкой:\n\n"
        f"👤 Пользователь: {message.from_user.first_name or 'Неизвестно'}\n"
        f"🆔 ID: {user_id}\n"
        f"📅 Дата рекорда: {user_data['date']}\n"
        f"🎯 Количество очков: {user_data['score']}\n"
        f"🎥 Видео: {video_info}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "⚠️ После отправки данные нельзя будет изменить!\n"
        "Рекорд будет отправлен на проверку администраторам.\n\n"
        "Подтвердите отправку:")
    await message.answer(
        confirmation_text,
        reply_markup=get_confirmation_keyboard()
    )

@router.message(RecordSubmissionStates.waiting_for_video)
async def process_video_input(message: Message, state: FSMContext):
    """Обработать ввод видео (файл или ссылка)"""
    user_id = message.from_user.id
    text = message.text
    
    if text == "🔙 Отмена":
        await state.clear()
        await message.answer(
            "Отправка рекорда отменена.",
            reply_markup=remove_keyboard()
        )
        await message.answer(
            "🏆 Меню рекордов",
            reply_markup=get_record_main_menu()
        )
        return
    
    # Если пользователь нажал кнопку из клавиатуры, подскажем отправить файл или ссылку
    if text.strip() == "🎥 Загрузить видео":
        await message.answer(
            "Пришлите видео файлом (до 50 МБ, до 5 минут) или отправьте ссылку на платформу (YouTube, Vimeo и т.д.)",
            reply_markup=get_video_upload_keyboard()
        )
        return
    
    # Проверяем, является ли текст ссылкой на видео
    if is_video_url(text):
        # Сохраняем ссылку на видео
        user_record_data[user_id]['video'] = {
            'type': 'url',
            'url': text,
            'platform': get_video_platform(text)
        }
        
        # Переходим к подтверждению
        await state.set_state(RecordSubmissionStates.confirming_submission)
        await message.answer(
            f"✅ Ссылка на видео сохранена: {text}",
            reply_markup=remove_keyboard()
        )
        user_data = user_record_data[user_id]
        video_info = f"🔗 {user_data['video']['platform']}: {user_data['video']['url']}"
        confirmation_text = (
            "✅ ПОДТВЕРЖДЕНИЕ ОТПРАВКИ РЕКОРДА\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Проверьте данные перед отправкой:\n\n"
            f"👤 **Пользователь:** {message.from_user.first_name or 'Неизвестно'}\n"
            f"🆔 ID: {user_id}\n"
            f"📅 Дата рекорда: {user_data['date']}\n"
            f"🎯 Количество очков: {user_data['score']}\n"
            f"🎥 Видео: {video_info}\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "⚠️ После отправки данные нельзя будет изменить!\n"
            "Рекорд будет отправлен на проверку администраторам.\n\n"
            "Подтвердите отправку:")
        await message.answer(
            confirmation_text,
            reply_markup=get_confirmation_keyboard()
        )
        return
    
    # Если это не ссылка, просим отправить видео файл или ссылку
    await message.answer(
        "❌ Пожалуйста, отправьте видео файл или ссылку на видео.\n\n"
        "Поддерживаемые платформы:\n"
        "• YouTube\n"
        "• Vimeo\n"
        "• Dailymotion\n"
        "• И другие популярные видеохостинги",
        reply_markup=get_video_upload_keyboard()
    )

@router.callback_query(F.data == "submit_for_review")
async def submit_for_review(callback: CallbackQuery):
    """Отправить рекорд на проверку"""
    user_id = callback.from_user.id
    
    # Проверяем регистрацию пользователя еще раз для безопасности
    if not check_user_registration_simple(user_id):
        await callback.answer(
            "❌ Для отправки рекорда необходимо зарегистрироваться в системе!", 
            show_alert=True
        )
        return
    
    # Проверяем, что все данные заполнены
    if user_id not in user_record_data:
        await callback.answer("❌ Нет данных для отправки", show_alert=True)
        return
    
    user_data = user_record_data[user_id]
    
    if not all(key in user_data for key in ['date', 'score', 'video']):
        missing = []
        if 'date' not in user_data:
            missing.append("📅 Дата")
        if 'score' not in user_data:
            missing.append("🎯 Очки")
        if 'video' not in user_data:
            missing.append("🎥 Видео")
        
        await callback.answer(
            f"❌ Не хватает данных: {', '.join(missing)}",
            show_alert=True
        )
        return
    
    # Показываем финальное подтверждение
    video_info = ""
    if user_data['video']['type'] == 'file':
        video_info = f"📹 {user_data['video']['file_name']} ({user_data['video']['duration']}с, {user_data['video']['file_size'] // 1024 // 1024}МБ)"
    else:
        video_info = f"🔗 {user_data['video']['platform']}: {user_data['video']['url']}"
    
    confirmation_text = (
        "✅ **ПОДТВЕРЖДЕНИЕ ОТПРАВКИ РЕКОРДА**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "**Проверьте данные перед отправкой:**\n\n"
        f"👤 **Пользователь:** {callback.from_user.first_name or 'Неизвестно'}\n"
        f"🆔 **ID:** {user_id}\n"
        f"📅 **Дата рекорда:** {user_data['date']}\n"
        f"🎯 **Количество очков:** {user_data['score']}\n"
        f"🎥 **Видео:** {video_info}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "⚠️ **После отправки данные нельзя будет изменить!**\n"
        "Рекорд будет отправлен на проверку администраторам.\n\n"
        "Подтвердите отправку:"
    )
    
    try:
        await callback.message.edit_text(
            confirmation_text,
            reply_markup=get_confirmation_keyboard()
        )
    except TelegramBadRequest as e:
        # Страхуемся от слишком длинного текста
        header = "ПОДТВЕРЖДЕНИЕ ОТПРАВКИ РЕКОРДА"
        await callback.message.edit_text(header, reply_markup=get_confirmation_keyboard())
        await _send_message_chunked(callback.message.bot, callback.message.chat.id, confirmation_text)

@router.callback_query(F.data == "confirm_submit")
async def confirm_submit_record(callback: CallbackQuery):
    """Подтвердить отправку рекорда"""
    user_id = callback.from_user.id
    
    # Проверяем регистрацию пользователя еще раз для безопасности
    if not check_user_registration_simple(user_id):
        await callback.answer(
            "❌ Для отправки рекорда необходимо зарегистрироваться в системе!", 
            show_alert=True
        )
        return
    
    user_data = user_record_data[user_id]
    
    # Создаем уникальный ID для рекорда
    import time
    record_id = f"record_{user_id}_{int(time.time())}"
    
    try:
        # Получаем team_id пользователя
        conn = sqlite3.connect('mydatabase.db')
        cursor = conn.cursor()
        cursor.execute("SELECT team_id FROM users WHERE tg_id = ?", (user_id,))
        result = cursor.fetchone()
        team_id = result[0] if result else None
        conn.close()
        
        if not team_id:
            await callback.answer("❌ Ошибка: пользователь не привязан к команде!", show_alert=True)
            return
        
        # Сохраняем рекорд в БД
        async with async_session_factory() as session:
            await save_submitted_record(
                record_id=record_id,
                user_tg_id=user_id,
                team_id=team_id,
                username=callback.from_user.username or "Не указан",
                first_name=callback.from_user.first_name or "Неизвестно",
                date=user_data['date'],
                score=user_data['score'],
                video_data=user_data['video'],
                session=session
            )
        
        # Создаем данные для уведомления админов (совместимость)
        record_data = {
            'id': record_id,
            'user_id': user_id,
            'username': callback.from_user.username or "Не указан",
            'first_name': callback.from_user.first_name or "Неизвестно",
            'date': user_data['date'],
            'score': user_data['score'],
            'video': user_data['video'],
            'status': 'pending',
            'submission_time': datetime.now().strftime("%d.%m.%Y %H:%M"),
            'admin_comment': None
        }
        
        # Отправляем уведомление администраторам
        await send_record_to_admins(callback.message.bot, record_data)
        
        # Очищаем данные пользователя
        del user_record_data[user_id]
        
    except Exception as e:
        await callback.answer(f"❌ Ошибка при сохранении рекорда: {str(e)}", show_alert=True)
        return
    
    # Уведомляем пользователя об успешной отправке
    success_text = (
        "🎉 **РЕКОРД УСПЕШНО ОТПРАВЛЕН!**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📋 **ID рекорда:** `{record_id}`\n"
        f"📅 **Дата:** {record_data['date']}\n"
        f"🎯 **Очки:** {record_data['score']}\n"
        f"⏰ **Время отправки:** {record_data['submission_time']}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "✅ Ваш рекорд отправлен на проверку администраторам\n"
        "⏳ Ожидайте результатов проверки\n"
        "📧 Вы получите уведомление о статусе рекорда\n\n"
        "💡 Вы можете отслеживать статус в разделе \"Мои рекорды\""
    )
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏆 Мои рекорды", callback_data="my_records")],
        [InlineKeyboardButton(text="📊 Топ рекордов", callback_data="top_records")],
        [InlineKeyboardButton(text="🔙 Назад к рекордам", callback_data="records")]
    ])
    
    try:
        await callback.message.edit_text(
            success_text,
            reply_markup=keyboard
        )
    except TelegramBadRequest:
        # Если сообщение слишком длинное — отправляем заголовок с кнопками, остальное — отдельными сообщениями
        await callback.message.edit_text("🎉 РЕКОРД УСПЕШНО ОТПРАВЛЕН!", reply_markup=keyboard)
        await _send_message_chunked(callback.message.bot, callback.message.chat.id, success_text)

@router.callback_query(F.data == "cancel_submit")
async def cancel_submit_record(callback: CallbackQuery):
    """Отменить отправку рекорда"""
    await callback.message.edit_text(
        "❌ **Отправка отменена**\n\n"
        "Вы можете продолжить редактирование данных рекорда.",
        reply_markup=get_record_submission_menu()
    )

async def send_record_to_admins(bot, record_data):
    """Отправить рекорд администраторам для проверки"""
    # Список ID администраторов (в реальном проекте лучше хранить в конфиге)
    ADMIN_IDS = [1349663945]  # ID администратора
    
    # Формируем информацию о видео
    video_info = ""
    if record_data['video']['type'] == 'file':
        video_info = (
            f"🎥 **Видео:** {record_data['video']['file_name']}\n"
            f"⏱ **Длительность:** {record_data['video']['duration']} сек\n"
            f"📦 **Размер:** {record_data['video']['file_size'] // 1024 // 1024} МБ"
        )
    else:
        video_info = (
            f"🔗 **Ссылка на видео:** {record_data['video']['url']}\n"
            f"📺 **Платформа:** {record_data['video']['platform']}"
        )
    
    admin_text = (
        "🔔 НОВЫЙ РЕКОРД НА ПРОВЕРКУ\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📋 ID рекорда: `{record_data['id']}`\n"
        f"👤 Пользователь: {record_data['first_name']}\n"
        f"🆔 User ID: `{record_data['user_id']}`\n"
        f"👤 Username: @{record_data['username']}\n\n"
        f"📅 Дата рекорда: {record_data['date']}\n"
        f"🎯 Количество очков: {record_data['score']}\n"
        f"⏰ Время отправки: {record_data['submission_time']}\n\n"
        f"{video_info}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "Проверьте видео и примите решение:"
    )
    
    for admin_id in ADMIN_IDS:
        try:
            # Отправляем текст с информацией
            await _send_message_chunked(
                bot=bot,
                chat_id=admin_id,
                text=admin_text + "\n\nОткройте /admin → 🏆 Проверка рекордов для модерации."
            )
            
            # Отправляем видео или ссылку без кнопок модерации (проверка только в админ-панели)
            if record_data['video']['type'] == 'file':
                await bot.send_video(
                    chat_id=admin_id,
                    video=record_data['video']['file_id'],
                    caption=f"🎥 Видео рекорда от {record_data['first_name']} ({record_data['score']} очков)"
                )
            else:
                await _send_message_chunked(
                    bot=bot,
                    chat_id=admin_id,
                    text=(
                        f"🔗 Ссылка на видео рекорда:\n{record_data['video']['url']}\n\n"
                        f"👤 От: {record_data['first_name']}\n"
                        f"🎯 Очки: {record_data['score']}"
                    )
                )
            
        except Exception as e:
            print(f"Ошибка отправки админу {admin_id}: {e}")

# Добавляем обработчики для кнопок "Назад"
@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery):
    """Вернуться в главное меню"""
    from keybords.keybord_client import kb_client
    
    await callback.message.edit_text(
        "Главное меню бота:",
        reply_markup=kb_client
    )

@router.callback_query(F.data == "back_to_records")
async def back_to_records(callback: CallbackQuery):
    """Вернуться к меню рекордов"""
    await show_records_menu(callback)


@router.callback_query(F.data == "my_records")
async def show_my_records(callback: CallbackQuery, session: AsyncSession):
    """Показать рекорды пользователя"""
    user_id = callback.from_user.id
    
    # Проверяем регистрацию пользователя
    if not check_user_registration_simple(user_id):
        await callback.answer("❌ Для просмотра рекордов необходимо зарегистрироваться в системе!", show_alert=True)
        return
    
    try:
        # Получаем одобренные рекорды пользователя
        approved_records = await get_user_records(user_id, session)
        
        # Получаем отправленные рекорды пользователя
        submitted_records = await get_user_submitted_records(user_id, session)
        
        if not approved_records and not submitted_records:
            await callback.message.edit_text(
                "📊 **Мои рекорды**\n\n"
                "У вас пока нет рекордов.\n\n"
                "Отправьте свой первый рекорд на проверку!",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📤 Отправить рекорд", callback_data="submit_record")],
                    [InlineKeyboardButton(text="◀️ Назад", callback_data="records")]
                ])
            )
            return
        
        # Формируем текст с рекордами
        text = "📊 **Мои рекорды**\n\n"
        
        if approved_records:
            text += "✅ **Одобренные рекорды:**\n"
            for i, record in enumerate(approved_records[:5], 1):  # Показываем только первые 5
                text += f"{i}. 🎯 {record.result} очков\n"
            if len(approved_records) > 5:
                text += f"... и еще {len(approved_records) - 5} рекордов\n"
            text += "\n"
        
        if submitted_records:
            text += "⏳ **Отправленные на проверку:**\n"
            for i, record in enumerate(submitted_records[:3], 1):  # Показываем только первые 3
                status_emoji = "⏳" if record.status == "pending" else "✅" if record.status == "approved" else "❌"
                text += f"{i}. {status_emoji} {record.score} очков ({record.date})\n"
            if len(submitted_records) > 3:
                text += f"... и еще {len(submitted_records) - 3} рекордов\n"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📤 Отправить рекорд", callback_data="submit_record")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="records")]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        await callback.answer(f"Ошибка: {str(e)}")




@router.callback_query(F.data == "russia_record")
async def show_russia_record(callback: CallbackQuery, session: AsyncSession):
    """Показать актуальный рекорд России"""
    try:
        record = await get_russia_record(session)
        
        if not record:
            await callback.message.edit_text(
                "🏆 **Актуальный рекорд России**\n\n"
                "Пока нет установленных рекордов.\n\n"
                "Станьте первым! Отправьте свой рекорд на проверку.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📤 Отправить рекорд", callback_data="submit_record")],
                    [InlineKeyboardButton(text="📊 Топ рекордов", callback_data="top_records")],
                    [InlineKeyboardButton(text="◀️ Назад", callback_data="records")]
                ])
            )
            return
        
        # Получаем информацию о команде
        team_query = await session.execute(
            select(UserTeams).where(UserTeams.id == record.r_team)
        )
        team = team_query.scalar_one_or_none()
        
        team_name = team.team if team else "Неизвестная команда"
        team_city = team.city if team else "Неизвестный город"
        
        text = (
            "🏆 **Актуальный рекорд России**\n\n"
            f"🥇 **Рекорд:** {record.result} очков\n"
            f"👥 **Команда:** {team_name}\n"
            f"🏙️ **Город:** {team_city}\n\n"
            "💡 Хотите побить рекорд? Отправьте свой результат!"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📤 Отправить рекорд", callback_data="submit_record")],
            [InlineKeyboardButton(text="📊 Топ рекордов", callback_data="top_records")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="records")]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        await callback.answer(f"Ошибка: {str(e)}")




@router.callback_query(F.data == "top_records")
async def show_top_records(callback: CallbackQuery, session: AsyncSession):
    """Показать топ рекордов"""
    try:
        records = await get_top_records(session, 10)
        
        if not records:
            await callback.message.edit_text(
                "📊 **Топ рекордов**\n\n"
                "Пока нет рекордов в базе данных.\n\n"
                "Станьте первым! Отправьте свой рекорд на проверку.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📤 Отправить рекорд", callback_data="submit_record")],
                    [InlineKeyboardButton(text="◀️ Назад", callback_data="records")]
                ])
            )
            return
        
        text = "📊 **Топ рекордов России**\n\n"
        
        for i, record in enumerate(records, 1):
            # Получаем информацию о команде
            team_query = await session.execute(
                select(UserTeams).where(UserTeams.id == record.r_team)
            )
            team = team_query.scalar_one_or_none()
            
            team_name = team.team if team else "Неизвестная команда"
            team_city = team.city if team else "Неизвестный город"
            
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            
            text += f"{medal} **{record.result} очков**\n"
            text += f"   👥 {team_name} ({team_city})\n\n"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📤 Отправить рекорд", callback_data="submit_record")],
            [InlineKeyboardButton(text="🏆 Рекорд России", callback_data="russia_record")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="records")]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        await callback.answer(f"Ошибка: {str(e)}")





