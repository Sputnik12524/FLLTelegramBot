from aiogram import F, Router
from sqlalchemy import JSON
import asyncio
from typing import List, Dict, Union
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
album_collector: Dict[int, Dict[str, Union[str, List[str], asyncio.Task]]] = {}
ALBUM_PROCESSING_DELAY = 0.2


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
        await message.answer(
            "Некорректный ввод. Отправьте номера миссий через запятую. Убедитесь, что все номера миссий натуральные и не больше 15.")
        return

    await state.update_data(missions=proceed_missions)
    await state.set_state(Publish.media)
    await message.answer(
        "Пожалуйста, отправьте фото/видео вашей насадки. На фото насасдка должна быть показана целиком, весь дизайн и функционал должны быть продемонстрированы")


"""@router.message(Publish.media)
async def photo_received(message: Message, state: FSMContext):
    # Проверяем, содержит ли сообщение медиа
    if not message.photo and not message.video:
        await message.answer(
            "Пожалуйста, отправьте фото/видео вашей насадки. На фото насадка должна быть показана целиком, весь дизайн и функционал должны быть продемонстрированы."
        )
        return

    # Здесь будут храниться id фотографий и видео
    images_ids, video_ids = [], []

    # Если сообщение содержит фотографии
    if message.photo:
        for _photo in message.photo:
            images_ids.append(_photo.file_id)

    # Если сообщение содержит видео
    if message.video:
        video_ids.append(message.video.file_id)

    # Сохраняем полученные id в состоянии
    await state.update_data(images_ids=images_ids)
    await state.update_data(video_ids=video_ids)

    # Переходим к следующему состоянию
    await state.set_state(Publish.caption)

    # Отправляем одно сообщение о вводе названия
    await message.answer("Введите название насадки.")"""


@router.message(Publish.media)
async def process_media_and_ask_caption(message: Message, state: FSMContext):
    chat_id = message.chat.id
    current_media_group_id = message.media_group_id

    # 1. Проверка на НЕ-медиа сообщение
    if not message.photo and not message.video:
        await message.answer(
            "Пожалуйста, отправьте фото/видео вашей насадки. На фото насадка должна быть показана целиком, весь дизайн и функционал должны быть продемонстрированы.")
        return

    # 2. Обработка ОДИНОЧНОГО фото/видео (не часть альбома)
    if not current_media_group_id:
        images_ids = [message.photo[-1].file_id] if message.photo else []
        video_ids = [message.video.file_id] if message.video else []

        await state.update_data(images_ids=images_ids, video_ids=video_ids)
        await state.set_state(Publish.caption)
        await message.answer("Введите название насадки.")

        # Очищаем данные альбома для этого чата, если они были (на случай, если пользователь отправил альбом, а потом одиночное медиа)
        if chat_id in album_collector:
            if album_collector[chat_id].get("processing_task") and not album_collector[chat_id]["processing_task"].done():
                album_collector[chat_id]["processing_task"].cancel()
            del album_collector[chat_id]
        return

    # 3. Обработка СООБЩЕНИЙ, ЯВЛЯЮЩИХСЯ ЧАСТЬЮ МЕДИАГРУППЫ (АЛЬБОМА)

    # Инициализируем или сбрасываем данные для нового альбома
    if chat_id not in album_collector or album_collector[chat_id]["media_group_id"] != current_media_group_id:
        # Отменяем предыдущую задачу, если она была и еще не завершилась (например, если новый альбом начался до завершения старого)
        if chat_id in album_collector and album_collector[chat_id].get("processing_task") and not \
                album_collector[chat_id]["processing_task"].done():
            album_collector[chat_id]["processing_task"].cancel()
        album_collector[chat_id] = {
            "media_group_id": current_media_group_id,
            "photos": [],
            "videos": [],
            "processing_task": None  # Здесь будем хранить ссылку на запланированную задачу
        }

    collector_data = album_collector[chat_id]

    # Добавляем текущее медиа в список собранных
    if message.photo:
        collector_data["photos"].append(message.photo[-1].file_id)  # Берем самый большой размер фото
    elif message.video:
        collector_data["videos"].append(message.video.file_id)

    # Отменяем любую ранее запланированную задачу для этого альбома.
    # Это ключевой момент дебоунса: если пришло новое медиа из того же альбома,
    # мы "сбрасываем" таймер и ждем еще немного.
    if collector_data["processing_task"] and not collector_data["processing_task"].done():
        collector_data["processing_task"].cancel()

    # Запускаем новую задачу для обработки альбома после короткой задержки.
    # Эта задача выполнится только в том случае, если за время задержки не придет
    # новых сообщений для ЭТОГО ЖЕ альбома.
    collector_data["processing_task"] = asyncio.create_task(
        _finalize_album_processing(chat_id, state, current_media_group_id)
    )


# Асинхронная функция для окончательной обработки альбома
async def _finalize_album_processing(chat_id: int, state: FSMContext, media_group_id: str):
    global bot
    """
    Вызывается после небольшой задержки для окончательной обработки собранных медиа
    и отправки ОДНОГО ответного сообщения.
    """
    try:
        await asyncio.sleep(ALBUM_PROCESSING_DELAY)

        # Проверяем, что это все еще тот же альбом, который мы ждали,
        # и что он не был обработан или сброшен другим способом.
        if chat_id in album_collector and album_collector[chat_id]["media_group_id"] == media_group_id:
            collected_photos = album_collector[chat_id]["photos"]
            collected_videos = album_collector[chat_id]["videos"]

            # Обновляем FSM-контекст всеми собранными ID медиафайлов
            await state.update_data(images_ids=collected_photos, video_ids=collected_videos)
            await state.set_state(Publish.caption)

            # Отправляем ответное сообщение ТОЛЬКО ОДИН РАЗ
            # bot тут должен быть доступен (можно передать его в аргументы функции или сделать глобальным)
            await bot.send_message(chat_id, "Введите название насадки.")  # Предполагается, что 'bot' доступен

            # Очищаем данные из временного хранилища, так как альбом обработан
            del album_collector[chat_id]

    except asyncio.CancelledError:
        # Задача была отменена, потому что пришло новое сообщение для того же альбома
        # до того, как завершился сон. Это нормально, просто ничего не делаем.
        pass
    except Exception as e:
        print(f"Ошибка в _finalize_album_processing для чата {chat_id}: {e}")


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
        await message.answer(
            f"Миссии: {missions}\nНазвание: {caption}\nОписание: {description}\n<b>ID:</b>\nвидео - {video_ids}\nкартинки - {image_ids}",
            reply_markup=confirm_pt_client, parse_mode="html")

    await state.set_state(Publish.confirm)


@router.callback_query(F.data == "confirm_pt")
async def patent_sent(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer(
        "Ваша насадка была успешна отправлена на модерацию и будет опубликована в ближайшие дни.",
        reply_markup=back_pt_client)

    data = await state.get_data()
    image_ids = data.get('images_ids')
    video_ids = data.get('video_ids')
    missions = data.get('missions')
    caption = data.get('caption')
    description = data.get('description')

    print(proceed_missions)
    # Действия с БД
    await rq.add_patent(1, missions=list(proceed_missions), caption=caption, description=description,
                        image_id=image_ids, video_id=video_ids)
