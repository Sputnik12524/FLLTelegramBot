import asyncio
from config import TOKEN
from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message
from keybords import kb_client
from handlers.handlers import router as handlers_router
from handlers.patent_handlers import router as patent_router
from admins_panel.admin_keyboard import router as admin_router
from database.models import async_main
import database.requests as rq


bot = Bot(TOKEN)
dp = Dispatcher()
dp.include_routers(
  handlers_router,
  patent_router,
  admin_router
)


@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer("Привет! Этот бот был разработан для Лиги Решений и предоставляет следующие полезные функции: ", reply_markup=kb_client)


async def main():
    await async_main()
    await dp.start_polling(bot)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Exit')