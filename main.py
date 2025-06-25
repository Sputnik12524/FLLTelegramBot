import asyncio

from config import TOKEN
from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message
from keybords import kb_client

bot = Bot(TOKEN)
dp = Dispatcher()


@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer("Привет! Этот бот был разработан для Лиги Решений и предоставляет следующие полезные функции: ", reply_markup=kb_client)


async def main():
    await dp.start_polling(bot)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Exit')
