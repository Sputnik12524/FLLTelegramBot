import asyncio
from config import TOKEN
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import CommandStart
from aiogram.types import Message
from keybords import kb_client
from handlers.handlers import router as handlers_router
from handlers.patent_handlers import router as patent_router
from admins_panel.admin_keyboard import router as admin_router
from records.record_handler import router as record_router
from database.engine import proceed_schemas, async_session_factory
from database.middleware import DbSessionMiddleware
from database.models import User
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select



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

    await message.answer("Привет! Этот бот был разработан для Лиги Решений и предоставляет следующие полезные функции: ", reply_markup=kb_client)


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
        record_router
    )
    print("Роутеры включены в диспетчер.")
    await dp.start_polling(bot)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Exit')
