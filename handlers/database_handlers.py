from aiogram import Router, F
from aiogram.types import CallbackQuery

router = Router()

@router.callback_query(F.data.startswith("register"))
async def register(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit("Зарегистрируйтесь в системе, чтобы сохранять результаты!")
    await callback.message.answer(f"Отправьте мне информацию о своей команде в таком формате:\n Название \n Город \n Номер")
    