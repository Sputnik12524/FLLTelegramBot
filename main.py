import asyncio
from aiogram.fsm.state import State, StatesGroup
from aiogram.methods import pin_chat_message
from config import TOKEN
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from keybords import kb_client
from handlers.handlers import router as handlers_router
from handlers.patent_handlers import router as patent_router
from admins_panel.admin_keyboard import router as admin_router
from records.record_handler import router as record_router
from handlers.registration_handlers import router as reg_router
from database.engine import proceed_schemas, async_session_factory
from database.middleware import DbSessionMiddleware
from database.models import User
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from scheduler import init_reminder_scheduler
from handlers.improvement_handlers import router as improvement_router



bot = Bot(TOKEN)
dp = Dispatcher(storage=MemoryStorage())


@dp.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession):
    user_tg_id = message.from_user.id

    user_query = await session.execute(
        select(User).where(User.tg_id == user_tg_id)
    )
    user_obj = user_query.scalar_one_or_none()  # Получаем объект User или None

    if user_obj is None:
        # Пользователь не найден, значит, он новый
        new_user = User(tg_id=user_tg_id, team_id=None)  # Создаем пользователя без привязки к команде
        session.add(new_user)
        await session.commit()

    # Создаем кнопку для открытия главного меню
    menu_button = InlineKeyboardButton(
        text="Открыть главное меню",
        callback_data="main_menu"
    )
    menu_keyboard = InlineKeyboardMarkup(inline_keyboard=[[menu_button]])
    
    sent_message = await message.answer(
        "Привет! Этот бот был разработан для команд Лиги Решений.\nС его помощью ты поделиться с другими командами своими достижениями, посмотреть рекорды России, посчитать баллы за миссии и многое другое. \nСоветуем зайти тебе к нам в чат, там мы будем публиковать об обновлениях в боте: https://t.me/+544PCMqLwrU3NWEy \n\nДля открытия меню введи команду /menu или нажми на кнопку ниже:",
        reply_markup=menu_keyboard
    )
    # Пытаемся закрепить стартовое сообщение (в группах/супергруппах при наличии прав)
    try:
        await bot.pin_chat_message(chat_id=message.chat.id, message_id=sent_message.message_id, disable_notification=True)
    except Exception:
        pass
    
@dp.message(Command("menu"))
async def cmd_menu(message: Message):
    """Показывает главное меню бота"""
    await message.answer("Главное меню бота:", reply_markup=kb_client)

async def main():
    # Инициализация базы данных (создание таблиц)
    await proceed_schemas()
    print("База данных и таблицы готовы.")

    # РЕГИСТРАЦИЯ MIDDLEWARE ДЛЯ СЕССИЙ БД
    # Это КРИТИЧЕСКИ ВАЖНО. Middleware должно быть зарегистрировано
    # ДО включения роутеров и запуска polling.
    dp.update.middleware(DbSessionMiddleware(session_pool=async_session_factory))
    print("Middleware для сессий БД успешно зарегистрировано.")

    # Включение роутеров
    dp.include_routers(
        handlers_router,
        patent_router,
        admin_router,
        record_router,
        reg_router,
        improvement_router
    )
    print("Роутеры включены в диспетчер.")
    
    # Инициализация и запуск планировщика напоминаний
    scheduler = init_reminder_scheduler(bot)
    await scheduler.start()
    print("Планировщик напоминаний запущен.")
    
    try:
        await dp.start_polling(bot)
    finally:
        # Останавливаем планировщик при завершении работы
        await scheduler.stop()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Exit')