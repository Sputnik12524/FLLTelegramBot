from aiogram import F, Router
import asyncio
from aiogram.client.bot import Bot
from typing import Dict, Optional, Union, List, Tuple

from aiogram.types import CallbackQuery, Message, InputMediaPhoto, InputMediaVideo
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, func, and_, text
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User, Patent
from keybords.patent_kb import (
    zero_patent_kb_client, back_pt_client, confirm_pt_client, get_patent_menu_keyboard,
    patent_kb_client, get_input_page_keyboard, get_single_patent_view_keyboard, get_team_patents_list_keyboard,
    get_cancel_input_keyboard
)
from keybords.registration_keyboard import keyboard_error as kb_er
from keybords.keybord_client import kb_client
import database.requests as rq

router = Router()

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
    confirm = State()


class PatentBrowsing(StatesGroup):
    browsing_menu = State()
    waiting_page_number = State()
    waiting_mission_number = State()
    waiting_team_number = State()
    displaying_team_patents = State()


def validate_and_process_numbers(data: Union[List[int], Tuple[int, ...]]) -> Union[List[int], None]:
    """Проверяет, что все элементы - уникальные целые числа от 1 до 15."""
    if not isinstance(data, (list, tuple)):
        return None
    unique_numbers = sorted(set(data))
    for item in unique_numbers:
        if not isinstance(item, int) or not (1 <= item <= 15):
            return None
    return unique_numbers


def get_missions_input_and_validate(missions):
    """Преобразует строку с номерами миссий в список и проверяет его на валидность."""
    str_numbers = missions.split(", ")
    numbers_for_validation = []
    for s_num in str_numbers:
        try:
            num = int(s_num)
            numbers_for_validation.append(num)
        except ValueError:
            return None
    return validate_and_process_numbers(numbers_for_validation)


@router.callback_query(F.data == "menu_pt")
async def back(callback: CallbackQuery):
    await callback.answer("Назад")
    await callback.message.answer(
        text="Привет! Этот бот был разработан для Лиги Решений и предоставляет следующие полезные функции: ",
        reply_markup=kb_client
    )


@router.callback_query(F.data == "patent")
async def show_patent_menu(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer("Выберите функцию:", reply_markup=patent_kb_client)


@router.callback_query(F.data == "publish_pt")
async def publish_attachment(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    await callback.answer("Опубликовать насадку")
    user_tg_id = callback.from_user.id
    try:
        user_query = await session.execute(select(User).where(User.tg_id == user_tg_id))
        user_obj = user_query.scalar_one_or_none()
        if user_obj is None or user_obj.team_id is None:
            await callback.message.answer(
                "Вы еще не зарегистрированы в команде. Пожалуйста, сначала зарегистрируйтесь, чтобы публиковать изобретения.",
                reply_markup=kb_er
            )
            return
        await state.set_state(Publish.mission_number)
        await callback.message.edit_text(
            "Выберите миссию(-и), в которых используется насадка.\nВведите названия миссий через запятую",
            reply_markup=get_cancel_input_keyboard()
        )
    except Exception as e:
        await callback.message.answer("Ошибка при проверке пользователя. Попробуйте позже.", reply_markup=back_pt_client)
        print(f"Ошибка publish_attachment: {e}")


PATENTS_PER_PAGE = 5


async def send_patents_page(
    chat_id: int,
    bot_instance: Bot,
    session: AsyncSession,
    page_to_display: int,
    filter_condition=None,
    message_to_edit: Optional[Message] = None
):
    """Отправляет страницу патентов с учетом фильтра и пагинации."""
    base_filter = Patent.approved == True
    final_filter = and_(base_filter, filter_condition) if filter_condition is not None else base_filter

    try:
        total_patents = await session.scalar(select(func.count(Patent.id)).where(final_filter))
        total_pages = (total_patents + PATENTS_PER_PAGE - 1) // PATENTS_PER_PAGE if total_patents > 0 else 1

        if total_patents == 0:
            page_to_display = 1
        elif page_to_display < 1:
            page_to_display = total_pages
        elif page_to_display > total_pages:
            page_to_display = 1

        offset = (page_to_display - 1) * PATENTS_PER_PAGE
        patents_query = await session.scalars(
            select(Patent)
            .where(final_filter)
            .order_by(Patent.created_at)
            .offset(offset)
            .limit(PATENTS_PER_PAGE)
        )
        patents_on_page = patents_query.all()

        if not patents_on_page:
            await bot_instance.send_message(chat_id, "Пока нет опубликованных насадок. Будьте первым!",
                                            reply_markup=zero_patent_kb_client)
            return None

        for patent in patents_on_page:
            caption_text = (
                f"**Название:** {patent.caption}\n"
                f"**Описание:** {patent.description}\n"
                f"**Миссии:** {', '.join(map(str, patent.missions))}\n"
                f"**Команда №:** {patent.team_number}\n"
                f"**Опубликовано:** {patent.created_at.strftime('%Y-%m-%d %H:%M')}"
            )
            media_group_items = []
            if patent.image_ids:
                for img_id in patent.image_ids:
                    media_group_items.append(InputMediaPhoto(media=img_id))
            if patent.video_ids:
                for vid_id in patent.video_ids:
                    media_group_items.append(InputMediaVideo(media=vid_id))

            if not media_group_items:
                await bot_instance.send_message(chat_id, caption_text, parse_mode="Markdown")
            elif len(media_group_items) == 1:
                item = media_group_items[0]
                if isinstance(item, InputMediaPhoto):
                    await bot_instance.send_photo(chat_id, photo=item.media, caption=caption_text, parse_mode="Markdown")
                elif isinstance(item, InputMediaVideo):
                    await bot_instance.send_video(chat_id, video=item.media, caption=caption_text, parse_mode="Markdown")
            else:
                media_group_items[0].caption = caption_text
                media_group_items[0].parse_mode = "Markdown"
                await bot_instance.send_media_group(chat_id, media_group_items)

        reply_markup = get_patent_menu_keyboard(page_to_display, total_pages)
        if message_to_edit:
            try:
                await bot_instance.edit_message_reply_markup(
                    chat_id=chat_id,
                    message_id=message_to_edit.message_id,
                    reply_markup=reply_markup
                )
            except Exception as e:
                print(f"Ошибка редактирования клавиатуры: {e}")
                await bot_instance.send_message(chat_id, f"Страница {page_to_display}/{total_pages}",
                                                reply_markup=reply_markup)
        else:
            await bot_instance.send_message(chat_id, f"Страница {page_to_display}/{total_pages}",
                                            reply_markup=reply_markup)
        return page_to_display
    except Exception as e:
        print(f"Ошибка при отправке страницы патентов: {e}")
        await bot_instance.send_message(chat_id, "Произошла ошибка при загрузке патентов.")
        return None


@router.callback_query(F.data == "view_pt")
async def view_patents_entry(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    await callback.answer()
    chat_id = callback.message.chat.id
    await state.set_state(PatentBrowsing.browsing_menu)
    await state.update_data(current_page=1, current_filter=None)
    displayed_page = await send_patents_page(
        chat_id=chat_id,
        bot_instance=callback.bot,
        session=session,
        page_to_display=1,
        filter_condition=None
    )
    await state.update_data(current_page=displayed_page)


@router.callback_query(F.data.in_({"prev_page_pt", "next_page_pt", "select_page_pt"}), PatentBrowsing.browsing_menu)
async def navigate_patents_pages(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    await callback.answer()
    chat_id = callback.message.chat.id
    current_page_data = await state.get_data()
    current_page = current_page_data.get('current_page', 1)
    current_filter = current_page_data.get('current_filter')

    if callback.data == "select_page_pt":
        await state.set_state(PatentBrowsing.waiting_page_number)
        await callback.message.answer("Введите номер страницы, на которую хотите перейти:",
                                      reply_markup=get_input_page_keyboard())
        return

    new_page = current_page
    if callback.data == "prev_page_pt":
        new_page -= 1
    elif callback.data == "next_page_pt":
        new_page += 1

    displayed_page = await send_patents_page(
        chat_id=chat_id,
        bot_instance=callback.bot,
        session=session,
        page_to_display=new_page,
        filter_condition=current_filter,
        message_to_edit=callback.message
    )
    await state.update_data(current_page=displayed_page)


@router.message(PatentBrowsing.waiting_page_number)
async def process_page_number_input(message: Message, state: FSMContext, session: AsyncSession):
    chat_id = message.chat.id
    current_page_data = await state.get_data()
    current_filter = current_page_data.get('current_filter')
    try:
        requested_page = int(message.text)
    except ValueError:
        await message.answer("Пожалуйста, введите корректный номер страницы (целое число).")
        return

    base_filter = Patent.approved == True
    final_filter = and_(base_filter, current_filter) if current_filter is not None else base_filter
    total_patents = await session.scalar(select(func.count(Patent.id)).where(final_filter))
    total_pages = (total_patents + PATENTS_PER_PAGE - 1) // PATENTS_PER_PAGE if total_patents > 0 else 1

    if not (1 <= requested_page <= total_pages):
        await message.answer(
            f"Страница с номером {requested_page} не существует. Всего страниц: {total_pages}. Пожалуйста, введите номер страницы от 1 до {total_pages}.")
        return

    await state.set_state(PatentBrowsing.browsing_menu)
    displayed_page = await send_patents_page(
        chat_id=chat_id,
        bot_instance=message.bot,
        session=session,
        page_to_display=requested_page
    )
    await state.update_data(current_page=displayed_page)


@router.callback_query(F.data == "cancel_input_pt", PatentBrowsing.waiting_page_number)
@router.callback_query(F.data == "cancel_input_pt", PatentBrowsing.waiting_mission_number)
@router.callback_query(F.data == "cancel_input_pt", PatentBrowsing.waiting_team_number)
async def cancel_any_input(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    await callback.answer()
    chat_id = callback.message.chat.id
    current_page_data = await state.get_data()
    current_page = current_page_data.get('current_page', 1)
    current_filter = current_page_data.get('current_filter')
    await state.set_state(PatentBrowsing.browsing_menu)
    await callback.message.delete()
    displayed_page = await send_patents_page(
        chat_id=chat_id,
        bot_instance=callback.bot,
        session=session,
        page_to_display=current_page,
        filter_condition=current_filter
    )
    await state.update_data(current_page=displayed_page)


@router.callback_query(F.data == "find_by_mission_pt", PatentBrowsing.browsing_menu)
async def find_by_mission_entry(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(PatentBrowsing.waiting_mission_number)
    await callback.message.answer("Введите номер миссии (от 1 до 15):", reply_markup=get_cancel_input_keyboard())


@router.message(PatentBrowsing.waiting_mission_number)
async def process_mission_number_input(message: Message, state: FSMContext, session: AsyncSession):
    chat_id = message.chat.id
    try:
        mission_number = int(message.text)
        if not (1 <= mission_number <= 15):
            raise ValueError("Номер миссии должен быть от 1 до 15.")
    except ValueError as e:
        await message.answer(f"Некорректный номер миссии: {e}. Пожалуйста, введите число от 1 до 15.")
        return

    mission_filter = text(
        f"EXISTS (SELECT 1 FROM json_each(patents.missions) WHERE json_each.value = {mission_number})"
    )
    await state.set_state(PatentBrowsing.browsing_menu)
    await state.update_data(current_filter=mission_filter, current_page=1)
    displayed_page = await send_patents_page(
        chat_id=chat_id,
        bot_instance=message.bot,
        session=session,
        page_to_display=1,
        filter_condition=mission_filter
    )
    await state.update_data(current_page=displayed_page)


@router.callback_query(F.data == "find_by_team_pt", PatentBrowsing.browsing_menu)
async def find_by_team_entry(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(PatentBrowsing.waiting_team_number)
    await callback.message.answer("Введите номер команды:", reply_markup=get_cancel_input_keyboard())


@router.message(PatentBrowsing.waiting_team_number)
async def process_team_number_input(message: Message, state: FSMContext, session: AsyncSession):
    chat_id = message.chat.id
    try:
        team_number = int(message.text)
        if team_number <= 0:
            raise ValueError("Номер команды должен быть положительным числом.")
    except ValueError as e:
        await message.answer(f"Некорректный номер команды: {e}. Пожалуйста, введите целое число.")
        return

    team_patents_query = await session.scalars(
        select(Patent)
        .where(Patent.team_number == team_number, Patent.approved == True)
        .order_by(Patent.created_at)
    )
    team_patents = team_patents_query.all()

    await state.set_state(PatentBrowsing.displaying_team_patents)
    await state.update_data(current_team_id=team_number)

    if not team_patents:
        await message.answer(f"Для команды №{team_number} пока нет одобренных изобретений.")
        await state.set_state(PatentBrowsing.browsing_menu)
        current_page_data = await state.get_data()
        current_page = current_page_data.get('current_page', 1)
        current_filter = current_page_data.get('current_filter')
        await send_patents_page(
            chat_id=chat_id,
            bot_instance=message.bot,
            session=session,
            page_to_display=current_page,
            filter_condition=current_filter
        )
        return

    reply_markup = get_team_patents_list_keyboard(team_patents)
    await message.answer(f"Изобретения команды №{team_number}:", reply_markup=reply_markup)


@router.callback_query(F.data.startswith("view_patent_id_"), PatentBrowsing.displaying_team_patents)
async def view_specific_team_patent(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    await callback.answer()
    try:
        patent_id = int(callback.data.split("_")[-1])
        patent = await session.scalar(select(Patent).where(Patent.id == patent_id, Patent.approved == True))
        if not patent:
            await callback.message.answer("Изобретение не найдено или не одобрено.")
            return

        caption_text = (
            f"**Название:** {patent.caption}\n"
            f"**Описание:** {patent.description}\n"
            f"**Миссии:** {', '.join(map(str, patent.missions))}\n"
            f"**Команда №:** {patent.team_number}\n"
            f"**Опубликовано:** {patent.created_at.strftime('%Y-%m-%d %H:%M')}"
        )

        media_group_items = []
        if patent.image_ids:
            for img_id in patent.image_ids:
                media_group_items.append(InputMediaPhoto(media=img_id))
        if patent.video_ids:
            for vid_id in patent.video_ids:
                media_group_items.append(InputMediaVideo(media=vid_id))

        if not media_group_items:
            await callback.message.answer(caption_text, parse_mode="Markdown", reply_markup=get_single_patent_view_keyboard())
        elif len(media_group_items) == 1:
            item = media_group_items[0]
            if isinstance(item, InputMediaPhoto):
                await callback.bot.send_photo(callback.message.chat.id, photo=item.media, caption=caption_text, parse_mode="Markdown", reply_markup=get_single_patent_view_keyboard())
            elif isinstance(item, InputMediaVideo):
                await callback.bot.send_video(callback.message.chat.id, video=item.media, caption=caption_text, parse_mode="Markdown", reply_markup=get_single_patent_view_keyboard())
        else:
            media_group_items[0].caption = caption_text
            media_group_items[0].parse_mode = "Markdown"
            await callback.bot.send_media_group(callback.message.chat.id, media_group_items)
            await callback.message.answer("Нажмите, чтобы вернуться:", reply_markup=get_single_patent_view_keyboard())
    except Exception as e:
        await callback.message.answer("Ошибка при просмотре изобретения.")
        print(f"Ошибка view_specific_team_patent: {e}")


@router.callback_query(F.data == "back_to_general_browsing_pt", PatentBrowsing.displaying_team_patents)
@router.callback_query(F.data == "back_to_general_browsing_pt")
async def back_to_general_browsing(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    await callback.answer()
    chat_id = callback.message.chat.id
    await state.set_state(PatentBrowsing.browsing_menu)
    await state.update_data(current_page=1, current_filter=None)
    try:
        await callback.message.delete()
    except Exception as e:
        print(f"Не удалось удалить сообщение: {e}")
    displayed_page = await send_patents_page(
        chat_id=chat_id,
        bot_instance=callback.bot,
        session=session,
        page_to_display=1,
        filter_condition=None
    )
    await state.update_data(current_page=displayed_page)


@router.callback_query(F.data == "menu_pt", PatentBrowsing.browsing_menu)
@router.callback_query(F.data == "menu_pt", PatentBrowsing.displaying_team_patents)
async def return_to_main_menu_from_patents(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await callback.message.answer("Вы вернулись в главное меню.", reply_markup=kb_client)


@router.message(Publish.mission_number)
async def process_mission_number(message: Message, state: FSMContext):
    global proceed_missions
    proceed_missions = get_missions_input_and_validate(message.text)
    if proceed_missions is None:
        await message.answer(
            "Неверный формат или значения номеров миссий. Введите числа от 1 до 15, через запятую с пробелом (например: 1, 5, 10).")
        return

    await state.update_data(missions=proceed_missions)
    await state.set_state(Publish.media)
    await message.answer(
        "Пожалуйста, отправьте фото/видео вашей насадки. На фото насадка должна быть показана целиком, весь дизайн и функционал должны быть продемонстрированы"
    )


async def _finalize_album_processing(bot_instance: Bot, chat_id: int, state: FSMContext, media_group_id: str):
    """Собирает медиа из альбома и переводит пользователя к вводу названия."""
    try:
        await asyncio.sleep(ALBUM_PROCESSING_DELAY)
        if chat_id in album_collector and album_collector[chat_id]["media_group_id"] == media_group_id:
            collected_photos = album_collector[chat_id]["photos"]
            collected_videos = album_collector[chat_id]["videos"]
            await state.update_data(images_ids=collected_photos, video_ids=collected_videos)
            await state.set_state(Publish.caption)
            await bot_instance.send_message(chat_id, "Введите название насадки.")
            del album_collector[chat_id]
    except asyncio.CancelledError:
        pass
    except Exception as e:
        print(f"Ошибка в _finalize_album_processing для чата {chat_id}: {e}")


@router.message(Publish.media)
async def process_media_and_ask_caption(message: Message, state: FSMContext):
    chat_id = message.chat.id
    current_media_group_id = message.media_group_id

    if not message.photo and not message.video:
        await message.answer(
            "Пожалуйста, отправьте фото/видео вашей насадки. На фото насадка должна быть показана целиком, весь дизайн и функционал должны быть продемонстрированы.")
        return

    current_bot_instance = message.bot

    if not current_media_group_id:
        images_ids = [message.photo[-1].file_id] if message.photo else []
        video_ids = [message.video.file_id] if message.video else []
        await state.update_data(images_ids=images_ids, video_ids=video_ids)
        await state.set_state(Publish.caption)
        await message.answer("Введите название насадки.")
        if chat_id in album_collector:
            if album_collector[chat_id].get("processing_task") and not album_collector[chat_id]["processing_task"].done():
                album_collector[chat_id]["processing_task"].cancel()
            del album_collector[chat_id]
        return

    if chat_id not in album_collector or album_collector[chat_id]["media_group_id"] != current_media_group_id:
        if chat_id in album_collector and album_collector[chat_id].get("processing_task") and not \
                album_collector[chat_id]["processing_task"].done():
            album_collector[chat_id]["processing_task"].cancel()
        album_collector[chat_id] = {
            "media_group_id": current_media_group_id,
            "photos": [],
            "videos": [],
            "processing_task": None
        }

    collector_data = album_collector[chat_id]
    if message.photo:
        collector_data["photos"].append(message.photo[-1].file_id)
    elif message.video:
        collector_data["videos"].append(message.video.file_id)

    if collector_data["processing_task"] and not collector_data["processing_task"].done():
        collector_data["processing_task"].cancel()

    collector_data["processing_task"] = asyncio.create_task(
        _finalize_album_processing(current_bot_instance, chat_id, state, current_media_group_id)
    )


@router.message(Publish.caption)
async def caption_received(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("Подпись не может быть пустой, введите текст.")
        return
    if len(message.text) > 50:
        await message.answer("Превышен лимит символов, введите название еще раз")
        return

    await state.update_data(caption=message.text)
    await state.set_state(Publish.description)
    await message.answer("Введите описание.")


@router.message(Publish.description)
async def description_received(message: Message, state: FSMContext):
    if len(message.text) > 250:
        await message.answer("Превышен лимит символов, введите описание еще раз")
        return

    await state.update_data(description=message.text)
    data = await state.get_data()
    image_ids = data.get('images_ids', [])
    video_ids = data.get('video_ids', [])
    missions = data.get('missions')
    caption = data.get('caption')
    description = data.get('description')

    media = []
    for image in image_ids:
        media.append(InputMediaPhoto(media=image))
    for video in video_ids:
        media.append(InputMediaVideo(media=video))

    if not media:
        await message.answer(
            f"Нет медиа для отправки.\n\nМиссии: {missions}\nНазвание: {caption}\nОписание: {description}\n<b>ID:</b>",
            reply_markup=confirm_pt_client, parse_mode="html"
        )
    elif len(media) == 1:
        if isinstance(media[0], InputMediaPhoto):
            await message.answer_photo(
                photo=media[0].media,
                caption=f"Миссии: {missions}\nНазвание: {caption}\nОписание: {description}\n<b>ID:</b>\nИзображения - {image_ids}",
                reply_markup=confirm_pt_client,
                parse_mode="html"
            )
        elif isinstance(media[0], InputMediaVideo):
            await message.answer_video(
                video=media[0].media,
                caption=f"Миссии: {missions}\nНазвание: {caption}\nОписание: {description}\n<b>ID:</b>\nвидео - {video_ids}",
                reply_markup=confirm_pt_client,
                parse_mode="html"
            )
    else:
        await message.answer_media_group(media)
        await message.answer(
            f"Миссии: {missions}\nНазвание: {caption}\nОписание: {description}\n<b>ID:</b>\nвидео - {video_ids}\nкартинки - {image_ids}",
            reply_markup=confirm_pt_client,
            parse_mode="html"
        )

    await state.set_state(state=Publish.confirm)


@router.callback_query(F.data == "confirm_pt")
async def patent_sent(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    user_tg_id = callback.from_user.id
    caption = data.get('caption', 'Без названия')
    description = data.get('description', 'Без описания')
    missions = data.get('missions', [])
    image_ids = data.get('images_ids', [])
    video_ids = data.get('video_ids', [])

    if len(caption) > 50:
        await callback.message.answer("Название насадки слишком длинное (макс. 50 символов).",
                                      reply_markup=back_pt_client)
        return
    if len(description) > 250:
        await callback.message.answer("Описание насадки слишком длинное (макс. 250 символов).",
                                      reply_markup=back_pt_client)
        return

    try:
        await rq.add_patent_to_db(
            user_tg_id=user_tg_id,
            missions=missions,
            caption=caption,
            description=description,
            image_ids=image_ids,
            video_ids=video_ids,
            session=session
        )
        await session.commit()
        await callback.message.answer(
            "Насадка успешно сохранена и отправлена на модерацию! Вскоре она будет видна здесь в ближайшие дни :)")
        await state.clear()
    except ValueError as ve:
        await session.rollback()
        print(f"Ошибка сохранения изобретения (ValueError): {ve}")
        await callback.message.answer(f"Ошибка: {ve} Пожалуйста, попробуйте снова или свяжитесь с администратором.")
        await state.clear()
    except Exception as e:
        await session.rollback()
        print(f"Произошла непредвиденная ошибка при сохранении изобретения: {e}")
        await callback.message.answer("Произошла непредвиденная ошибка при сохранении патента. Попробуйте еще раз.")
        await state.clear()
