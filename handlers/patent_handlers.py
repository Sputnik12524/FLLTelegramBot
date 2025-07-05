from aiogram import F, Router
from aiogram.types import CallbackQuery, Message, InputMediaPhoto, InputMediaVideo
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from keybords.patent_kb import main_patent_kb_client, zero_patent_kb_client, back_pt_client, confirm_pt_client
from keybords.keybord_client import kb_client
import gspread

router = Router()
"""gc = gspread.service_account(filename="credentials.json")
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
        return 0"""


class Publish(StatesGroup):
    publish = State()
    mission_number = State()
    media = State()
    caption = State()
    description = State()
    confirm = ()


@router.callback_query(F.data == "menu_pt")
async def back(callback: CallbackQuery):
    await callback.answer("Назад")
    await callback.message.answer(
        text="Привет! Этот бот был разработан для Лиги Решений и предоставляет следующие полезные функции: ",
        reply_markup=kb_client)


@router.callback_query(F.data == "patent")
async def show_patent_menu(callback: CallbackQuery):
    await callback.answer()
    """filled_rows = count_filled_rows(worksheet)
    if filled_rows == 1:
        await callback.message.edit_text(
            "Пока что здесь ничего нет, но вы можете первыми показать свои изобретения другим командам!",
            reply_markup=zero_patent_kb_client)
    else:
        await callback.message.edit_text("Насадки / Страница 1", reply_markup=main_patent_kb_client)"""
    await callback.message.answer(
        "Пока что здесь ничего нет, но вы можете первыми показать свои изобретения другим командам!",
        reply_markup=zero_patent_kb_client)


@router.callback_query(F.data == "publish_pt")
async def publish_attachment(callback: CallbackQuery, state: FSMContext):
    await callback.answer("Опубликовать насадку")
    await state.set_state(Publish.mission_number)
    await callback.message.edit_text(
        "Выберите миссию(-и), в которых используется насадка.\nВведите названия миссий через запятую",
        reply_markup=back_pt_client)


@router.message(Publish.mission_number)
async def load_image(message: Message, state: FSMContext):
    await state.update_data(missions=message.text)
    await state.set_state(Publish.media)
    await message.answer(
        "Пожалуйста, отправьте фото/видео вашей насадки. На фото насасдка должна быть показана целиком, весь дизайн и функционал должны быть продемонстрированы")


@router.message(Publish.media)
async def photo_received(message: Message, state: FSMContext):
    print(message.video)
    if not message.photo and not message.video:
        await message.answer(
            "Пожалуйста, отправьте фото/видео вашей насадки. На фото насадка должна быть показана целиком, весь дизайн и функционал должны быть продемонстрированы.")
        return

    images_ids, video_ids = [], []

    # Проверяем есть ли фото
    if message.photo:
        for _photo in message.photo:
            images_ids.append(_photo.file_id)

    # Проверяем есть ли видео
    if message.video:
        video_ids.append(message.video.file_id)

    await state.update_data(images_ids=images_ids)
    await state.update_data(video_ids=video_ids)
    await state.set_state(Publish.caption)
    await message.answer("Введите название насадки.")


@router.message(Publish.caption)
async def caption_received(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("Подпись не может быть пустой, введите текст.")
        return

    await state.update_data(caption=message.text)
    await state.set_state(Publish.description)
    await message.answer("Введите описание.")


@router.message(Publish.description)
async def description_received(message: Message, state: FSMContext):
    await state.update_data(description=message.text)

    data = await state.get_data()
    image_ids = data.get('images_ids')
    video_ids = data.get('video_ids')
    missions = data.get('missions')
    caption = data.get('caption')
    description = data.get('description')

    media = []

    for image in image_ids:
        media.append(InputMediaPhoto(media=image))
    for video in video_ids:
        media.append(InputMediaVideo(media=video))

    if media:
        await message.answer_media_group(media)  # Отправка медиагруппы
        await message.answer(f"Миссии: {missions}\nНазвание: {caption}\nОписание: {description}\n<b>ID:</b>\nвидео - {video_ids}\nкартинки - {image_ids}",
                             reply_markup=confirm_pt_client, parse_mode="html")

    await state.set_state(Publish.confirm)


@router.callback_query(F.data == "confirm_pt")
async def patent_sent(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer("Ваша насадка была успешна отправлена на модерацию и будет опубликована в ближайшие дни.", reply_markup=back_pt_client)

    data = await state.get_data()
    # image_ids = data.get('images_ids')
    # video_ids = data.get('video_ids')
    missions = data.get('missions')
    caption = data.get('caption')
    description = data.get('description')

    # Действия с БД



