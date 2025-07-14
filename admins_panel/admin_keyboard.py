from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from database.models import User, UserTeams
from database.engine import async_session_factory
import os
from sqlalchemy.ext.asyncio import async_session

# Пароль для админ-панели
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

class AdminAuth(StatesGroup):
    waiting_password = State()

class AdminBroadcast(StatesGroup):
    waiting_message = State()

router = Router()

def get_admin_keyboard():
    """Создает клавиатуру админ-панели"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="👥 Список команд", callback_data="admin_teams")],
        [InlineKeyboardButton(text="🏆 Проверка рекордов", callback_data="admin_records")],
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="🗑 Очистить данные", callback_data="admin_clear")],
        [InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_refresh")],
        [InlineKeyboardButton(text="❌ Закрыть панель", callback_data="admin_close")]
    ])

def get_admin_record_review_keyboard(record_id):
    """Клавиатура для админа для проверки рекорда"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve_record_{record_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_record_{record_id}")
        ],
        [InlineKeyboardButton(text="💬 Запросить дополнительную информацию", callback_data=f"request_info_{record_id}")],
        [InlineKeyboardButton(text="📊 Детали рекорда", callback_data=f"record_details_{record_id}")]
    ])
    return keyboard

def get_back_to_admin_keyboard():
    """Создает кнопку возврата к админ-панели"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад к панели", callback_data="admin_back")]
    ])

def get_records_filter_keyboard():
    """Клавиатура для фильтрации рекордов"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏳ На проверке", callback_data="admin_records_pending")],
        [InlineKeyboardButton(text="✅ Одобренные", callback_data="admin_records_approved")],
        [InlineKeyboardButton(text="❌ Отклоненные", callback_data="admin_records_rejected")],
        [InlineKeyboardButton(text="📋 Все рекорды", callback_data="admin_records_all")],
        [InlineKeyboardButton(text="⬅️ Назад к панели", callback_data="admin_back")]
    ])

@router.callback_query(F.data == "admin_records")
async def show_admin_records_menu(callback: CallbackQuery):
    """Показать меню проверки рекордов"""
    pending_count = len([r for r in submitted_records if r['status'] == 'pending'])
    approved_count = len([r for r in submitted_records if r['status'] == 'approved'])
    rejected_count = len([r for r in submitted_records if r['status'] == 'rejected'])
    total_count = len(submitted_records)
    
    records_text = (
        "🏆 **УПРАВЛЕНИЕ РЕКОРДАМИ**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📊 **Статистика рекордов:**\n"
        f"⏳ На проверке: **{pending_count}**\n"
        f"✅ Одобренные: **{approved_count}**\n"
        f"❌ Отклоненные: **{rejected_count}**\n"
        f"📋 Всего: **{total_count}**\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "Выберите категорию для просмотра:"
    )
    
    await callback.message.edit_text(
        records_text,
        reply_markup=get_records_filter_keyboard()
    )

@router.callback_query(F.data == "admin_records_pending")
async def show_pending_records(callback: CallbackQuery):
    """Показать рекорды на проверке"""
    pending_records = [r for r in submitted_records if r['status'] == 'pending']
    
    if not pending_records:
        await callback.message.edit_text(
            "⏳ **РЕКОРДЫ НА ПРОВЕРКЕ**\n\n"
            "📭 Нет рекордов, ожидающих проверки.",
            reply_markup=get_back_to_admin_keyboard()
        )
        return
    
    records_text = (
        "⏳ **РЕКОРДЫ НА ПРОВЕРКЕ**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    )
    
    for i, record in enumerate(pending_records[:5], 1):  # Показываем первые 5
        records_text += (
            f"**{i}. {record['first_name']}** - {record['score']} очков\n"
            f"   📅 {record['date']} | ⏰ {record['submission_time']}\n"
            f"   🆔 `{record['id']}`\n\n"
        )
    
    if len(pending_records) > 5:
        records_text += f"... и еще {len(pending_records) - 5} рекордов\n\n"
    
    records_text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n💡 Нажмите на ID рекорда для детального просмотра"
    

@router.message(Command('admin'))
async def admin_login(message: Message, state: FSMContext):
    """Запрос пароля для входа в админ-панель"""
    print(f"Admin command received from user {message.from_user.id}")  # Отладка
    await message.answer(
        "🔐 **Вход в админ-панель**\n\n"
        f"Введите пароль:\n\n"
        f"*Подсказка: текущий пароль - {ADMIN_PASSWORD}*",  # Временно для отладки
        parse_mode="Markdown"
    )
    await state.set_state(AdminAuth.waiting_password)
    print("State set to waiting_password")  # Отладка

@router.message(AdminAuth.waiting_password)
async def admin_password_check(message: Message, state: FSMContext):
    """Проверка пароля и открытие админ-панели"""
    print(f"Password check: received '{message.text}', expected '{ADMIN_PASSWORD}'")  # Отладка
    
    if message.text.strip() == ADMIN_PASSWORD:
        await state.clear()
        print("Password correct, showing admin panel")  # Отладка
        await show_admin_panel(message)
    else:
        await state.clear()
        print("Password incorrect")  # Отладка
        await message.answer(
            "❌ **Неверный пароль!**\n\n"
            f"Вы ввели: `{message.text}`\n"
            f"Ожидался: `{ADMIN_PASSWORD}`\n\n"
            "Доступ запрещен.",
            parse_mode="Markdown"
        )

async def show_admin_panel(message_or_callback):
    """Показывает главную админ-панель"""
    admin_text = (
        "🔧 **Админ-панель FLL Bot**\n\n"
        "Добро пожаловать в панель управления!\n"
        "Выберите необходимое действие:"
    )
    
    try:
        if isinstance(message_or_callback, Message):
            await message_or_callback.answer(
                admin_text,
                reply_markup=get_admin_keyboard(),
                parse_mode="Markdown"
            )
        else:  # CallbackQuery
            await message_or_callback.message.edit_text(
                admin_text,
                reply_markup=get_admin_keyboard(),
                parse_mode="Markdown"
            )
        print("Admin panel shown successfully")  # Отладка
    except Exception as e:
        print(f"Error showing admin panel: {e}")  # Отладка

@router.callback_query(F.data == "admin_back")
async def admin_back_to_panel(callback: CallbackQuery):
    """Возвращает к главной админ-панели"""
    await show_admin_panel(callback)
    await callback.answer()

@router.callback_query(F.data == "admin_refresh")
async def admin_refresh_panel(callback: CallbackQuery):
    """Обновляет админ-панель"""
    await show_admin_panel(callback)
    await callback.answer("🔄 Панель обновлена!")

@router.callback_query(F.data == "admin_stats")
async def admin_show_stats(callback: CallbackQuery):
    """Показывает статистику пользователей"""
    try:
        async with async_session() as session:
            # Подсчитываем количество пользователей
            users_result = await session.execute("SELECT COUNT(*) FROM users")
            users_count = users_result.scalar()
            
            # Подсчитываем количество команд
            teams_result = await session.execute("SELECT COUNT(*) FROM user_teams")
            teams_count = teams_result.scalar()
            
        stats_text = (
            "📊 **Статистика бота**\n\n"
            f"👤 Всего пользователей: **{users_count}**\n"
            f"👥 Всего команд: **{teams_count}**\n"
        )
            
        await callback.message.edit_text(
            stats_text,
            reply_markup=get_back_to_admin_keyboard(),
            parse_mode="Markdown"
        )
        await callback.answer()
    except Exception as e:
        await callback.answer(f"Ошибка: {str(e)}")

@router.callback_query(F.data == "admin_teams")
async def admin_show_teams(callback: CallbackQuery):
    """Показывает список команд"""
    try:
        async with async_session() as session:
            result = await session.execute(
                "SELECT team, city, number FROM user_teams ORDER BY id DESC LIMIT 10"
            )
            teams = result.fetchall()
            
        if teams:
            teams_text = "👥 **Список команд (последние 10):**\n\n"
            for i, (team, city, number) in enumerate(teams, 1):
                teams_text += f"**{i}.** {team}\n📍 {city} | 🔢 #{number}\n\n"
        else:
            teams_text = "👥 **Команды не найдены**\n\nПока никто не зарегистрировался."
            
        await callback.message.edit_text(
            teams_text,
            reply_markup=get_back_to_admin_keyboard(),
            parse_mode="Markdown"
        )
        await callback.answer()
    except Exception as e:
        await callback.answer(f"Ошибка: {str(e)}")

@router.callback_query(F.data == "admin_close")
async def admin_close_panel(callback: CallbackQuery):
    """Закрывает админ-панель"""
    await callback.message.edit_text(
        "🔒 **Админ-панель закрыта**\n\n"
        "Для повторного входа используйте команду /admin",
        parse_mode="Markdown"
    )
    await callback.answer("Панель закрыта")

# Простой тест-обработчик для проверки работы роутера
@router.message(Command('test_admin'))
async def test_admin_router(message: Message):
    """Тестовый обработчик для проверки работы админ-роутера"""
    await message.answer("✅ Админ-роутер работает!")

def get_admin_record_review_keyboard(record_id):
    """Клавиатура для админа для проверки рекорда"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve_record_{record_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_record_{record_id}")
        ],
        [InlineKeyboardButton(text="💬 Запросить дополнительную информацию", callback_data=f"request_info_{record_id}")],
        [InlineKeyboardButton(text="📊 Детали рекорда", callback_data=f"record_details_{record_id}")]
    ])
    return keyboard

def get_record_status_keyboard():
    """Клавиатура для просмотра статуса рекордов"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏳ На проверке", callback_data="records_pending")],
        [InlineKeyboardButton(text="✅ Одобренные", callback_data="records_approved")],
        [InlineKeyboardButton(text="❌ Отклоненные", callback_data="records_rejected")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_records")]
    ])
    return keyboard

def get_cancel_keyboard():
    """Простая клавиатура отмены"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🔙 Отмена")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return keyboard

def get_confirmation_keyboard():
    """Клавиатура подтверждения отправки"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да, отправить", callback_data="confirm_submit"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_submit")
        ]
    ])
    return keyboard

def remove_keyboard():
    """Убрать клавиатуру"""
    from aiogram.types import ReplyKeyboardRemove
    return ReplyKeyboardRemove()
