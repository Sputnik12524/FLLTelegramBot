from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from database.models import User, UserTeams
from database.engine import async_session_factory
import os
from sqlalchemy.ext.asyncio import AsyncSession
from scheduler import get_reminder_scheduler

# Пароль для админ-панели
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "48)a$7yHRI6BM%_l5R(s")

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
        [InlineKeyboardButton(text="📸 Управление напоминаниями", callback_data="admin_reminders")],
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
    # Получаем данные из базы данных
    async with async_session_factory() as session:
        from database.models import SubmittedRecord
        from sqlalchemy import select, func
        
        # Подсчитываем рекорды по статусам
        pending_result = await session.execute(
            select(func.count(SubmittedRecord.id)).where(SubmittedRecord.status == "pending")
        )
        pending_count = pending_result.scalar() or 0
        
        approved_result = await session.execute(
            select(func.count(SubmittedRecord.id)).where(SubmittedRecord.status == "approved")
        )
        approved_count = approved_result.scalar() or 0
        
        rejected_result = await session.execute(
            select(func.count(SubmittedRecord.id)).where(SubmittedRecord.status == "rejected")
        )
        rejected_count = rejected_result.scalar() or 0
        
        total_result = await session.execute(select(func.count(SubmittedRecord.id)))
        total_count = total_result.scalar() or 0
    
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
    async with async_session_factory() as session:
        from database.models import SubmittedRecord
        from sqlalchemy import select
        
        result = await session.execute(
            select(SubmittedRecord).where(SubmittedRecord.status == "pending")
        )
        pending_records = result.scalars().all()
    
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
            f"**{i}. {record.first_name}** - {record.score} очков\n"
            f"   📅 {record.date} | ⏰ {record.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            f"   🆔 `{record.record_id}`\n\n"
        )
    
    if len(pending_records) > 5:
        records_text += f"... и еще {len(pending_records) - 5} рекордов\n\n"
    
    records_text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n💡 Нажмите на ID рекорда для детального просмотра"
    
    await callback.message.edit_text(
        records_text,
        reply_markup=get_back_to_admin_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.message(Command('admin'))
async def admin_login(message: Message, state: FSMContext):
    """Запрос пароля для входа в админ-панель"""
    print(f"Admin command received from user {message.from_user.id}")  # Отладка
    await message.answer(
        "🔐 **Вход в админ-панель**\n\n"
        f"Введите пароль:\n\n",
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
        async with async_session_factory() as session:
            from sqlalchemy import select, func
            
            # Подсчитываем количество пользователей
            users_result = await session.execute(select(func.count(User.id)))
            users_count = users_result.scalar()
            
            # Подсчитываем количество команд
            teams_result = await session.execute(select(func.count(UserTeams.id)))
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
        async with async_session_factory() as session:
            from sqlalchemy import select
            
            result = await session.execute(
                select(UserTeams.team, UserTeams.city, UserTeams.number)
                .order_by(UserTeams.id.desc())
                .limit(10)
            )
            teams = result.all()
            
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

def get_reminders_keyboard():
    """Клавиатура управления напоминаниями"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статус напоминаний", callback_data="reminders_status")],
        [InlineKeyboardButton(text="📤 Отправить напоминание всем", callback_data="reminders_send_all")],
        [InlineKeyboardButton(text="📱 Отправить конкретному пользователю", callback_data="reminders_send_user")],
        [InlineKeyboardButton(text="⬅️ Назад к панели", callback_data="admin_back")]
    ])

class AdminReminder(StatesGroup):
    waiting_user_id = State()

@router.callback_query(F.data == "admin_reminders")
async def admin_show_reminders(callback: CallbackQuery):
    """Показывает меню управления напоминаниями"""
    scheduler = get_reminder_scheduler()
    
    if scheduler is None:
        await callback.message.edit_text(
            "❌ **Планировщик не инициализирован**\n\n"
            "Система напоминаний не запущена.",
            reply_markup=get_back_to_admin_keyboard(),
            parse_mode="Markdown"
        )
        return
    
    reminders_text = (
        "📸 **УПРАВЛЕНИЕ НАПОМИНАНИЯМИ**\n\n"
        "Система автоматических напоминаний о присылке фотографий:\n\n"
        "• Напоминания отправляются раз в 2 недели\n"
        "• При получении фото таймер сбрасывается\n"
        "• Можно отправить напоминание вручную\n\n"
        "Выберите действие:"
    )
    
    await callback.message.edit_text(
        reminders_text,
        reply_markup=get_reminders_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data == "reminders_status")
async def show_reminders_status(callback: CallbackQuery):
    """Показывает статус напоминаний для всех пользователей"""
    try:
        scheduler = get_reminder_scheduler()
        
        if scheduler is None:
            await callback.answer("❌ Планировщик не инициализирован!")
            return
        
        status_list = await scheduler.get_users_reminder_status()
        
        if not status_list:
            await callback.message.edit_text(
                "📊 **СТАТУС НАПОМИНАНИЙ**\n\n"
                "❌ Нет зарегистрированных пользователей.",
                reply_markup=get_back_to_admin_keyboard(),
                parse_mode="Markdown"
            )
            return
        
        # Подсчитываем статистику
        total_users = len(status_list)
        need_reminder = sum(1 for user in status_list if user['needs_reminder'])
        have_reminder = total_users - need_reminder
        
        status_text = (
            "📊 **СТАТУС НАПОМИНАНИЙ**\n\n"
            f"👥 Всего пользователей: **{total_users}**\n"
            f"🔔 Нужно напоминание: **{need_reminder}**\n"
            f"✅ Получали недавно: **{have_reminder}**\n\n"
        )
        
        if need_reminder > 0:
            status_text += "🔔 **Пользователи, нуждающиеся в напоминании:**\n"
            for user in status_list[:10]:  # Показываем первых 10
                if user['needs_reminder']:
                    if user['last_reminder']:
                        from datetime import datetime
                        last_date = user['last_reminder'].strftime('%d.%m.%Y')
                        status_text += f"• ID {user['tg_id']} (последнее: {last_date})\n"
                    else:
                        status_text += f"• ID {user['tg_id']} (никогда)\n"
            
            if need_reminder > 10:
                status_text += f"... и еще {need_reminder - 10} пользователей\n"
        
        await callback.message.edit_text(
            status_text,
            reply_markup=get_back_to_admin_keyboard(),
            parse_mode="Markdown"
        )
        await callback.answer()
        
    except Exception as e:
        await callback.answer(f"Ошибка: {str(e)}")

@router.callback_query(F.data == "reminders_send_all")
async def send_reminders_to_all(callback: CallbackQuery):
    """Отправляет напоминания всем пользователям, которым нужно"""
    try:
        scheduler = get_reminder_scheduler()
        
        if scheduler is None:
            await callback.answer("❌ Планировщик не инициализирован!")
            return
        
        # Принудительно проверяем и отправляем напоминания
        await scheduler._check_and_send_reminders()
        
        await callback.message.edit_text(
            "✅ **НАПОМИНАНИЯ ОТПРАВЛЕНЫ**\n\n"
            "Все пользователи, которым нужно напоминание, получили сообщения.\n\n"
            "Проверьте логи для подробной информации.",
            reply_markup=get_back_to_admin_keyboard(),
            parse_mode="Markdown"
        )
        await callback.answer("✅ Напоминания отправлены!")
        
    except Exception as e:
        await callback.answer(f"Ошибка: {str(e)}")

@router.callback_query(F.data == "reminders_send_user")
async def send_reminder_to_user_start(callback: CallbackQuery, state: FSMContext):
    """Начинает процесс отправки напоминания конкретному пользователю"""
    await callback.message.edit_text(
        "📱 **ОТПРАВКА НАПОМИНАНИЯ ПОЛЬЗОВАТЕЛЮ**\n\n"
        "Введите Telegram ID пользователя (число):\n\n"
        "Например: 123456789",
        parse_mode="Markdown"
    )
    await state.set_state(AdminReminder.waiting_user_id)
    await callback.answer()

@router.message(AdminReminder.waiting_user_id)
async def send_reminder_to_user_process(message: Message, state: FSMContext):
    """Обрабатывает ID пользователя и отправляет напоминание"""
    try:
        user_id = int(message.text.strip())
        
        scheduler = get_reminder_scheduler()
        if scheduler is None:
            await message.answer("❌ Планировщик не инициализирован!")
            await state.clear()
            return
        
        # Отправляем принудительное напоминание
        success = await scheduler.force_reminder_for_user(user_id)
        
        if success:
            await message.answer(
                f"✅ **НАПОМИНАНИЕ ОТПРАВЛЕНО**\n\n"
                f"Пользователю с ID {user_id} отправлено напоминание.\n\n"
                "Используйте /admin для возврата к панели.",
                parse_mode="Markdown"
            )
        else:
            await message.answer(
                f"❌ **ОШИБКА ОТПРАВКИ**\n\n"
                f"Не удалось отправить напоминание пользователю {user_id}.\n"
                "Возможные причины:\n"
                "• Пользователь заблокировал бота\n"
                "• Неверный ID\n"
                "• Технические проблемы\n\n"
                "Используйте /admin для возврата к панели.",
                parse_mode="Markdown"
            )
        
        await state.clear()
        
    except ValueError:
        await message.answer(
            "❌ **НЕВЕРНЫЙ ФОРМАТ**\n\n"
            "ID должен быть числом. Попробуйте еще раз:",
            parse_mode="Markdown"
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")
        await state.clear()
