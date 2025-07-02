from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from keybords.patent_kb import main_patent_kb_client, zero_patent_kb_client, back_pt_client
from keybords.keybord_client import kb_client
import gspread

router = Router()
gc = gspread.service_account(filename="credentials.json")
spreadsheet = gc.open("FLLTelegramBot")
worksheet = spreadsheet.worksheet("patent")


def count_filled_rows(worksheet):
    try:
        all_rows = worksheet.get_all_values()

        filled_rows_count = 0
        for row in all_rows:
            if any(cell.strip() for cell in row):
                filled_rows_count += 1

        return filled_rows_count
    except Exception as e:
        print(f"An error occured: {e}")


class Publish(StatesGroup):
    waiting_for_mission_number = State()
    waiting_for_media = State()
    waiting_for_caption = State()
    waiting_for_description = State()


@router.callback_query(F.data == "menu_pt")
async def back(callback: CallbackQuery):
    await callback.answer("Назад")
    await callback.message.edit_text(
        text="Привет! Этот бот был разработан для Лиги Решений и предоставляет следующие полезные функции: ",
        reply_markup=kb_client)


@router.callback_query(F.data == "patent")
async def show_patent_menu(callback: CallbackQuery):
    await callback.answer()
    filled_rows = count_filled_rows(worksheet)
    if filled_rows == 1:
        await callback.message.edit_text(
            "Пока что здесь ничего нет, но вы можете первыми показать свои изобретения другим командам!",
            reply_markup=zero_patent_kb_client)
    else:
        await callback.message.edit_text("Насадки / Страница 1", reply_markup=main_patent_kb_client)


@router.callback_query(F.data == "publish_pt")
async def publish_attachment(callback: CallbackQuery, state: FSMContext):
    await callback.answer("Опубликовать насадку")
    await callback.message.edit_text(
        "Выберите миссию(-и), в которых используется насадка.\nВведите названия миссий через запятую",
        reply_markup=back_pt_client)


@router.message(Publish.waiting_for_mission_number)
async def load_image(message: Message, state: FSMContext):
    await state.set_state(Publish.waiting_for_media)
    await message.answer("Пожалуйста, отправьте изображение.")


@router.message(state=Publish.waiting_for_media)
async def photo_received(message: Message, state: FSMContext):
    await state.update_data(photo_id=message.photo[-1].file_id)
    await state.set_state(Publish.waiting_for_caption)
    await message.answer("Введите подпись к изображению.")


@router.message(state=Publish.waiting_for_caption)
async def caption_received(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("Подпись не может быть пустой, введите текст.")
        return
    data = await state.get_data()
    photo_id = data.get('photo_id')
    caption = message.text
    await message.answer(f"Изображение ID: {photo_id}, Подпись: {caption}")
    await state.finish()


@router.message(state=Publish.waiting_for_caption)
async def invalid_caption(message: Message):
    await message.answer("Пожалуйста, введите текст.")
