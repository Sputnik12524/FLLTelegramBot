from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timedelta
from keybords.keybord_client import kb_client
import re
import sqlite3

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

@router.callback_query(F.data == "records")
async def show_records_menu(callback: CallbackQuery):
    """Показать главное меню рекордов"""
    user_id = callback.from_user.id
    
    # Проверяем регистрацию пользователя
    if not check_user_registration_simple(user_id):
        await callback.message.edit_text(
            "🏆 **Меню рекордов Лиги Решений**\n\n"
            "❌ **Доступ ограничен**\n\n"
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
            "❌ **Доступ запрещен**\n\n"
            "Для отправки рекорда необходимо:\n"
            "✅ Зарегистрироваться в системе\n"
            "Пожалуйста, сначала пройдите регистрацию.",
            reply_markup=get_record_main_menu()
        )
        return
    
    # Инициализируем данные пользователя
    if user_id not in user_record_data:
        user_record_data[user_id] = {}
    
    user_data = user_record_data[user_id]
    
    status_text = (
        "📤 **ОТПРАВКА РЕКОРДА НА ПРОВЕРКУ**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "**Текущий статус заполнения:**\n"
        f"📅 Дата: {'✅ ' + user_data.get('date', '') if 'date' in user_data else '❌ Не указана'}\n"
        f"🎯 Очки: {'✅ ' + str(user_data.get('score', '')) if 'score' in user_data else '❌ Не указаны'}\n"
        f"🎥 Видео: {'✅ Загружено' if 'video' in user_data else '❌ Не загружено'}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "**Для отправки рекорда необходимо:**\n"
        "📅 Указать дату установки рекорда\n"
        "🎯 Указать количество набранных очков\n"
        "🎥 Загрузить видео-подтверждение\n\n"
        "Выберите действие:"
    )
    
    await callback.message.edit_text(
        status_text,
        reply_markup=get_record_submission_menu()
    )

@router.callback_query(F.data == "set_record_date")
async def set_record_date(callback: CallbackQuery, state: FSMContext):
    """Установить дату рекорда"""
    await state.set_state(RecordSubmissionStates.waiting_for_date)
    
    await callback.message.edit_text(
        "📅 **Укажите дату установки рекорда**\n\n"
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
                "Отменено.",
                reply_markup=remove_keyboard()
            )
            await message.answer(
                "📤 **Отправка рекорда на проверку**\n\n"
                "Выберите действие:",
                reply_markup=get_record_submission_menu()
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
        
        await state.clear()
        await message.answer(
            f"✅ Дата установлена: {record_date}",
            reply_markup=remove_keyboard()
        )
        
        # Показываем обновленный статус
        user_data = user_record_data[user_id]
        status_text = (
            "📤 **ОТПРАВКА РЕКОРДА НА ПРОВЕРКУ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "**Текущий статус заполнения:**\n"
            f"📅 Дата: ✅ {record_date}\n"
            f"🎯 Очки: {'✅ ' + str(user_data.get('score', '')) if 'score' in user_data else '❌ Не указаны'}\n"
            f"🎥 Видео: {'✅ Загружено' if 'video' in user_data else '❌ Не загружено'}\n\n"
            "Выберите следующее действие:"
        )
        
        await message.answer(
            status_text,
            reply_markup=get_record_submission_menu()
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
        "🎯 **Укажите количество набранных очков**\n\n"
        "Введите число от 0 до максимально возможного количества очков.\n"
        "Максимальное количество очков в FLL: 500\n\n"
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
            "Отменено.",
            reply_markup=remove_keyboard()
        )
        await message.answer(
            "📤 **Отправка рекорда на проверку**\n\n"
            "Выберите действие:",
            reply_markup=get_record_submission_menu()
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
        
        if score > 500:
            await message.answer(
                "❌ Максимальное количество очков в FLL: 500",
                reply_markup=get_score_input_keyboard()
            )
            return
        
        # Сохраняем очки
        user_record_data[user_id]['score'] = score
        
        await state.clear()
        await message.answer(
            f"✅ Количество очков установлено: {score}",
            reply_markup=remove_keyboard()
        )
        
        # Показываем обновленный статус
        user_data = user_record_data[user_id]
        status_text = (
            "📤 **ОТПРАВКА РЕКОРДА НА ПРОВЕРКУ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "**Текущий статус заполнения:**\n"
            f"📅 Дата: {'✅ ' + user_data.get('date', '') if 'date' in user_data else '❌ Не указана'}\n"
            f"🎯 Очки: ✅ {score}\n"
            f"🎥 Видео: {'✅ Загружено' if 'video' in user_data else '❌ Не загружено'}\n\n"
            "Выберите следующее действие:"
        )
        
        await message.answer(
            status_text,
            reply_markup=get_record_submission_menu()
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
        "🎥 **Загрузка видео-подтверждения**\n\n"
        "Вы можете отправить:\n"
        "📹 **Видео файл** - загрузить видео напрямую\n"
        "🔗 **Ссылку на видео** - вставить ссылку на YouTube, Vimeo и т.д.\n\n"
        "📋 **Требования к видео:**\n"
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
    
    await state.clear()
    await message.answer(
        f"✅ Видео файл загружен: {user_record_data[user_id]['video']['file_name']}",
        reply_markup=remove_keyboard()
    )
    
    # Показываем обновленный статус
    user_data = user_record_data[user_id]
    status_text = (
        "📤 **ОТПРАВКА РЕКОРДА НА ПРОВЕРКУ**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "**Текущий статус заполнения:**\n"
        f"📅 Дата: {'✅ ' + user_data.get('date', '') if 'date' in user_data else '❌ Не указана'}\n"
        f"🎯 Очки: {'✅ ' + str(user_data.get('score', '')) if 'score' in user_data else '❌ Не указаны'}\n"
        f"🎥 Видео: ✅ Загружено ({user_data['video']['file_name']})\n\n"
        "Выберите следующее действие:"
    )
    
    await message.answer(
        status_text,
        reply_markup=get_record_submission_menu()
    )

@router.message(RecordSubmissionStates.waiting_for_video)
async def process_video_input(message: Message, state: FSMContext):
    """Обработать ввод видео (файл или ссылка)"""
    user_id = message.from_user.id
    text = message.text
    
    if text == "🔙 Отмена":
        await state.clear()
        await message.answer(
            "Отменено.",
            reply_markup=remove_keyboard()
        )
        await message.answer(
            "📤 **Отправка рекорда на проверку**\n\n"
            "Выберите действие:",
            reply_markup=get_record_submission_menu()
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
        
        await state.clear()
        await message.answer(
            f"✅ Ссылка на видео сохранена: {text}",
            reply_markup=remove_keyboard()
        )
        
        # Показываем обновленный статус
        user_data = user_record_data[user_id]
        status_text = (
            "📤 **ОТПРАВКА РЕКОРДА НА ПРОВЕРКУ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "**Текущий статус заполнения:**\n"
            f"📅 Дата: {'✅ ' + user_data.get('date', '') if 'date' in user_data else '❌ Не указана'}\n"
            f"🎯 Очки: {'✅ ' + str(user_data.get('score', '')) if 'score' in user_data else '❌ Не указаны'}\n"
            f"🎥 Видео: ✅ Ссылка сохранена\n\n"
            "Выберите следующее действие:"
        )
        
        await message.answer(
            status_text,
            reply_markup=get_record_submission_menu()
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
    
    await callback.message.edit_text(
        confirmation_text,
        reply_markup=get_confirmation_keyboard()
    )

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
    
    # Сохраняем рекорд в список отправленных
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
    
    submitted_records.append(record_data)
    
    # Отправляем уведомление администраторам
    await send_record_to_admins(callback.message.bot, record_data)
    
    # Очищаем данные пользователя
    del user_record_data[user_id]
    
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
    
    await callback.message.edit_text(
        success_text,
        reply_markup=keyboard
    )

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
    ADMIN_IDS = [123456789, 987654321]  # Замените на реальные ID админов
    
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
        "🔔 **НОВЫЙ РЕКОРД НА ПРОВЕРКУ**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📋 **ID рекорда:** `{record_data['id']}`\n"
        f"👤 **Пользователь:** {record_data['first_name']}\n"
        f"🆔 **User ID:** `{record_data['user_id']}`\n"
        f"👤 **Username:** @{record_data['username']}\n\n"
        f"📅 **Дата рекорда:** {record_data['date']}\n"
        f"🎯 **Количество очков:** {record_data['score']}\n"
        f"⏰ **Время отправки:** {record_data['submission_time']}\n\n"
        f"{video_info}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "Проверьте видео и примите решение:"
    )
    
    for admin_id in ADMIN_IDS:
        try:
            # Отправляем текст с информацией
            await bot.send_message(
                chat_id=admin_id,
                text=admin_text,
                parse_mode="Markdown"
            )
            
            # Отправляем видео или ссылку
            if record_data['video']['type'] == 'file':
                # Отправляем видео файл
                await bot.send_video(
                    chat_id=admin_id,
                    video=record_data['video']['file_id'],
                    caption=f"🎥 Видео рекорда от {record_data['first_name']} ({record_data['score']} очков)",
                    reply_markup=get_admin_record_review_keyboard(record_data['id'])
                )
            else:
                # Отправляем ссылку на видео
                await bot.send_message(
                    chat_id=admin_id,
                    text=f"🔗 **Ссылка на видео рекорда:**\n{record_data['video']['url']}\n\n"
                         f"👤 От: {record_data['first_name']}\n"
                         f"🎯 Очки: {record_data['score']}",
                    reply_markup=get_admin_record_review_keyboard(record_data['id'])
                )
            
        except Exception as e:
            print(f"Ошибка отправки админу {admin_id}: {e}")

# Добавляем обработчики для кнопок "Назад"
@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery):
    """Вернуться в главное меню"""
    from keybords.keybord_client import kb_client
    
    await callback.message.edit_text(
        "🏠 **Главное меню**\n\n"
        "Добро пожаловать в FLL Telegram Bot!\n"
        "Выберите нужный раздел:",
        reply_markup=kb_client
    )

@router.callback_query(F.data == "back_to_records")
async def back_to_records(callback: CallbackQuery):
    """Вернуться к меню рекордов"""
    await show_records_menu(callback)


@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery):
    """Вернуться в главное меню"""
    await callback.message.edit_text(
        "🏠 **Главное меню**\n\n"
        "Добро пожаловать в FLL Telegram Bot!\n"
        "Выберите нужный раздел:",
        reply_markup=kb_client
    )

@router.callback_query(F.data == "back_to_records")
async def back_to_records(callback: CallbackQuery):
    """Вернуться к меню рекордов"""
    await show_records_menu(callback)