from aiogram import F, Router
from sqlalchemy import JSON
from aiogram.types import CallbackQuery, Message, InputMediaPhoto, InputMediaVideo
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from keybords.patent_kb import main_patent_kb_client, zero_patent_kb_client, back_pt_client, confirm_pt_client
from keybords.keybord_client import kb_client
import database.requests as rq
from typing import Union, List, Tuple

"""import gspread"""

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

approved_missions = False
proceed_missions = None

class Publish(StatesGroup):
    publish = State()
    mission_number = State()
    media = State()
    caption = State()
    description = State()
    confirm = ()


def validate_and_process_numbers(data: Union[List[int], Tuple[int, ...]]) -> Union[List[int], None]:
    """
    Проверяет, является ли входной аргумент списком или кортежем натуральных чисел,
    где каждое число находится в диапазоне от 1 до 15 включительно.

    Args:
        data: Входные данные, которые должны быть списком или кортежем целых чисел.

    Returns:
        Список чисел, если все условия соблюдены;
        None, если входные данные не соответствуют условиям.
    """
    if not isinstance(data, (list, tuple)):
        return None

    processed_list = []
    for item in data:
        # Проверяем, является ли элемент целым числом
        if not isinstance(item, int):
            return None

        # Проверяем, что число является натуральным (>= 1) и не больше 15
        if not (1 <= item <= 15):
            return None

        processed_list.append(item)

    return processed_list


def get_missions_input_and_validate(missions):
    # Разделяем строку по пробелам на отдельные строковые числа
    str_numbers = missions.split(", ")

    numbers_for_validation = []
    # Попытка преобразовать каждую строку в целое число
    for s_num in str_numbers:
        try:
            num = int(s_num)
            numbers_for_validation.append(num)
        except ValueError:
            print(f"Ошибка: '{s_num}' не является целым числом. Ввод должен содержать только числа.")
            approved_missions = False
            return None  # Прерываем, так как ввод некорректен

    # Передаем список целых чисел в функцию валидации
    result = validate_and_process_numbers(numbers_for_validation)

    if result is not None:
        print(f"\nВведенные данные прошли проверку: {result}")
        approved_missions = True
        return result
    else:
        print(f"\nВведенные данные не прошли проверку.")
        # Дополнительные подсказки пользователю
        print("Убедитесь, что все числа являются натуральными (от 1) и не превышают 15.")
        approved_missions = False
        return None


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
    global proceed_missions
    proceed_missions = get_missions_input_and_validate(message.text)
    if proceed_missions is None:
        await message.answer("Некорректный ввод. Отправьте номера миссий через запятую. Убедитесь, что все номера миссий натуральные и не больше 15.")
        return

    await state.update_data(missions=proceed_missions)
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
    image_ids = data.get('images_ids')
    video_ids = data.get('video_ids')
    missions = data.get('missions')
    caption = data.get('caption')
    description = data.get('description')

    print(proceed_missions)
    # Действия с БД
    await rq.add_patent(1, missions=list(proceed_missions), caption=caption, description=description, image_id=image_ids, video_id=video_ids)
