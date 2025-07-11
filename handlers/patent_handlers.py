from aiogram import F, Router
import asyncio
from aiogram.client.bot import Bot
from typing import Dict, Optional

from aiogram.types import CallbackQuery, Message, InputMediaPhoto, InputMediaVideo
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User, Patent
from keybords.patent_kb import zero_patent_kb_client, back_pt_client, confirm_pt_client, get_patent_menu_keyboard, \
    patent_kb_client, get_input_page_keyboard, get_single_patent_view_keyboard, get_team_patents_list_keyboard, \
    get_cancel_input_keyboard
from keybords.keybord_client import kb_client
import database.requests as rq
from typing import Union, List, Tuple

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
    if not isinstance(data, (list, tuple)):
        return None

    # Используем set для удаления дубликатов, затем преобразуем обратно в список
    unique_numbers = sorted(list(set(data)))  # Сортируем после удаления дубликатов

    processed_list = []
    for item in unique_numbers:  # Итерируемся по уникальным и отсортированным числам
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
            return None  # Прерываем, так как ввод некорректен

    # Передаем список целых чисел в функцию валидации
    result = validate_and_process_numbers(numbers_for_validation)

    if result is not None:
        print(f"\nВведенные данные прошли проверку: {result}")
        return result
    else:
        print(f"\nВведенные данные не прошли проверку.")
        # Дополнительные подсказки пользователю
        print("Убедитесь, что все числа являются натуральными (от 1) и не превышают 15.")
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
    await callback.message.answer(
        "Выберите функцию:",
        reply_markup=patent_kb_client)


@router.callback_query(F.data == "publish_pt")
async def publish_attachment(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    await callback.answer("Опубликовать насадку")
    user_tg_id = callback.from_user.id

    # Проверяем наличие пользователя и его team_id.
    # Используем асинхронную сессию, переданную через middleware
    user_query = await session.execute(
        select(User).where(User.tg_id == user_tg_id)
    )
    user_obj = user_query.scalar_one_or_none()  # Получаем один объект User или None

    # Логика проверки:
    # 1. Пользователь не найден в таблице 'users' вообще (значит, он новый)
    # 2. Пользователь найден, но его team_id = NULL (если `nullable=True` для team_id)
    # 3. Пользователь найден, но его team_id указывает на "пустую" или "дефолтную" команду (если `nullable=False` и вы используете такую команду)

    # В данной реализации модели User (с nullable=True для team_id)
    if user_obj is None or user_obj.team_id is None:
        await callback.message.answer(
            "Вы еще не зарегистрированы в команде. Пожалуйста, сначала зарегистрируйтесь, чтобы публиковать изобретения.\n",
            reply_markup=back_pt_client
        )
    else:
        await state.set_state(Publish.mission_number)
        await callback.message.edit_text(
            "Выберите миссию(-и), в которых используется насадка.\nВведите названия миссий через запятую",
            reply_markup=back_pt_client)


PATENTS_PER_PAGE = 5  # Количество патентов на одной странице


# --- ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ ДЛЯ ОТПРАВКИ СТРАНИЦЫ ПАТЕНТОВ ---
async def send_patents_page(
        chat_id: int,
        bot_instance: Bot,
        session: AsyncSession,
        page_to_display: int,
        filter_condition=None,
        message_to_edit: Optional[Message] = None  # Для редактирования сообщения с клавиатурой
):
    # Базовый фильтр: только одобренные патенты
    base_filter = Patent.approved == True

    # Комбинируем с дополнительным условием, если оно есть
    final_filter = and_(base_filter, filter_condition) if filter_condition is not None else base_filter

    total_patents = await session.scalar(select(func.count(Patent.id)).where(final_filter)) # Получаем общее количество одобренных патентов
    total_pages = (total_patents + PATENTS_PER_PAGE - 1) // PATENTS_PER_PAGE if total_patents > 0 else 1

    # Корректировка номера страницы для зацикливания
    if total_patents == 0:
        page_to_display = 1
    elif page_to_display < 1:
        page_to_display = total_pages
    elif page_to_display > total_pages:
        page_to_display = 1

    offset = (page_to_display - 1) * PATENTS_PER_PAGE

    # Запрос патентов для текущей страницы, упорядоченных по created_at (самые старые первыми)
    patents_query = await session.scalars(
        select(Patent)
        .where(Patent.approved == True)
        .order_by(Patent.created_at)
        .offset(offset)
        .limit(PATENTS_PER_PAGE)
    )
    patents_on_page = patents_query.all()

    # Отправляем патенты
    if not patents_on_page:
        await bot_instance.send_message(chat_id, "Пока нет опубликованных насадок. Будьте первым!",
                                        reply_markup=zero_patent_kb_client)
        return None
    else:
        for patent in patents_on_page:
            caption_text = (
                f"**Название:** {patent.caption}\n"
                f"**Описание:** {patent.description}\n"
                f"**Миссии:** {patent.missions}\n"  # JSON-поле будет выведено как список Python
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
                # Если нет медиа, отправляем только текст
                await bot_instance.send_message(
                    chat_id,
                    caption_text,
                    parse_mode="Markdown"  # Используем Markdown для жирного текста
                )
            elif len(media_group_items) == 1:
                # Если одно медиа, отправляем его с подписью
                item = media_group_items[0]
                if isinstance(item, InputMediaPhoto):
                    await bot_instance.send_photo(
                        chat_id,
                        photo=item.media,
                        caption=caption_text,
                        parse_mode="Markdown"
                    )
                elif isinstance(item, InputMediaVideo):
                    await bot_instance.send_video(
                        chat_id,
                        video=item.media,
                        caption=caption_text,
                        parse_mode="Markdown"
                    )
            else:
                # Если несколько медиа, отправляем медиагруппу, а затем текст отдельно
                # Важно: первая медиа в группе может иметь caption, остальные нет.
                # Для упрощения: отправляем все медиа без caption, а затем caption отдельным сообщением.
                # Это стандартная практика, так как общая подпись для media_group не предусмотрена API.
                media_group_items[0].caption = caption_text  # Добавляем подпись к первому элементу группы
                media_group_items[0].parse_mode = "Markdown"
                await bot_instance.send_media_group(chat_id, media_group_items)
                # await bot_instance.send_message(chat_id, caption_text, parse_mode="Markdown") # Можете отправлять отдельно, если не хотите к первому элементу

            # Отправляем или редактируем клавиатуру навигации
        reply_markup = get_patent_menu_keyboard(page_to_display, total_pages)
        if message_to_edit:
            # Пытаемся отредактировать существующее сообщение с клавиатурой
            try:
                await bot_instance.edit_message_reply_markup(
                    chat_id=chat_id,
                    message_id=message_to_edit.message_id,
                    reply_markup=reply_markup
                )
                # await message_to_edit.edit_reply_markup(reply_markup=reply_markup) # можно так, если message_to_edit - это объект message
            except Exception as e:
                # Если не удалось отредактировать (например, сообщение слишком старое), отправляем новое
                print(f"Error editing message reply markup: {e}. Sending new keyboard message.")
                await bot_instance.send_message(chat_id, f"Страница {page_to_display}/{total_pages}",
                                                reply_markup=reply_markup)
        else:
            # Если message_to_edit не передан (первый вход), отправляем новое сообщение с клавиатурой
            await bot_instance.send_message(chat_id, f"Страница {page_to_display}/{total_pages}",
                                            reply_markup=reply_markup)

        return page_to_display  # Возвращаем фактический номер страницы


@router.callback_query(F.data == "view_pt")  # Кнопка из главного меню
async def view_patents_entry(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    await callback.answer()

    current_bot_instance = callback.bot
    chat_id = callback.message.chat.id

    # Устанавливаем начальное состояние просмотра патентов
    await state.set_state(PatentBrowsing.browsing_menu)
    await state.update_data(current_page=1, current_filter=None)  # Начинаем с первой страницы

    # Отправляем первую страницу патентов и сохраняем ID сообщения с клавиатурой
    displayed_page = await send_patents_page(
        chat_id=chat_id,
        bot_instance=current_bot_instance,
        session=session,
        page_to_display=1,
        filter_condition=None
    )
    await state.update_data(current_page=displayed_page)  # Сохраняем фактическую страницу


@router.callback_query(F.data.in_({"prev_page_pt", "next_page_pt", "select_page_pt"}), PatentBrowsing.browsing_menu)
async def navigate_patents_pages(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    await callback.answer()

    current_bot_instance = callback.bot
    chat_id = callback.message.chat.id
    current_page_data = await state.get_data()
    current_page = current_page_data.get('current_page', 1)  # Получаем текущую страницу
    current_filter = current_page_data.get('current_filter') # Получаем текущий фильтр, если есть

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
        bot_instance=current_bot_instance,
        session=session,
        page_to_display=new_page,
        filter_condition=current_filter,
        message_to_edit=callback.message  # Передаем текущее сообщение для редактирования клавиатуры
    )
    await state.update_data(current_page=displayed_page)  # Сохраняем актуальную страницу


@router.message(PatentBrowsing.waiting_page_number)
async def process_page_number_input(message: Message, state: FSMContext, session: AsyncSession):
    current_bot_instance = message.bot
    chat_id = message.chat.id
    current_page_data = await state.get_data()
    current_filter = current_page_data.get('current_filter')  # Получаем текущий фильтр

    try:
        requested_page = int(message.text)
    except ValueError:
        await message.answer("Пожалуйста, введите корректный номер страницы (целое число).")
        return

    base_filter = Patent.approved == True
    final_filter = and_(base_filter, current_filter) if current_filter is not None else base_filter

    # Получаем общее количество одобренных патентов для проверки валидности введенной страницы
    total_patents = await session.scalar(select(func.count(Patent.id)).where(final_filter))
    total_pages = (total_patents + PATENTS_PER_PAGE - 1) // PATENTS_PER_PAGE if total_patents > 0 else 1

    if not (1 <= requested_page <= total_pages):
        await message.answer(
            f"Страница с номером {requested_page} не существует. Всего страниц: {total_pages}. Пожалуйста, введите номер страницы от 1 до {total_pages}.")
        return

    # Если номер страницы валиден, переходим на неё
    await state.set_state(PatentBrowsing.browsing_menu)  # Возвращаем пользователя в состояние просмотра
    displayed_page = await send_patents_page(
        chat_id=chat_id,
        bot_instance=current_bot_instance,
        session=session,
        page_to_display=requested_page
        # message_to_edit здесь не передаем, так как это новое сообщение после ввода числа
    )
    await state.update_data(current_page=displayed_page)


@router.callback_query(F.data == "cancel_input_pt", PatentBrowsing.waiting_page_number)
@router.callback_query(F.data == "cancel_input_pt", PatentBrowsing.waiting_mission_number)
@router.callback_query(F.data == "cancel_input_pt", PatentBrowsing.waiting_team_number)
async def cancel_any_input(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    await callback.answer()

    current_bot_instance = callback.bot
    chat_id = callback.message.chat.id
    current_page_data = await state.get_data()
    current_page = current_page_data.get('current_page', 1)
    current_filter = current_page_data.get('current_filter')  # Сохраняем текущий фильтр

    await state.set_state(PatentBrowsing.browsing_menu)  # Возвращаем в основное меню просмотра

    await callback.message.delete()  # Удаляем сообщение "Введите номер..."

    displayed_page = await send_patents_page(
        chat_id=chat_id,
        bot_instance=current_bot_instance,
        session=session,
        page_to_display=current_page,
        filter_condition=current_filter  # Возвращаемся с тем же фильтром
    )
    await state.update_data(current_page=displayed_page)



# --- ПОИСК ПО НОМЕРУ МИССИИ ---
@router.callback_query(F.data == "find_by_mission_pt", PatentBrowsing.browsing_menu)
async def find_by_mission_entry(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(PatentBrowsing.waiting_mission_number)
    await callback.message.answer("Введите номер миссии (от 1 до 15):", reply_markup=get_cancel_input_keyboard())


@router.message(PatentBrowsing.waiting_mission_number)
async def process_mission_number_input(message: Message, state: FSMContext, session: AsyncSession):
    current_bot_instance = message.bot
    chat_id = message.chat.id

    try:
        mission_number = int(message.text)
        if not (1 <= mission_number <= 15):
            raise ValueError("Номер миссии должен быть от 1 до 15.")
    except ValueError as e:
        await message.answer(f"Некорректный номер миссии: {e}. Пожалуйста, введите число от 1 до 15.")
        return

    # Условие поиска: Patent.missions (JSONB/JSON) содержит mission_number
    # Для SQLite, JSON-поле обрабатывается как строка, и contains работает как LIKE '%"value"%'.
    # В SQLAlchemy для JSON-типа есть специальные операторы.
    # Если missions объявлен как Mapped[List[int]] = mapped_column(JSON), то используем .contains()
    mission_filter = Patent.missions.contains([mission_number])  # Ищет [1] в [1,2,3]

    await state.set_state(PatentBrowsing.browsing_menu)  # Возвращаем в основное меню просмотра
    await state.update_data(current_filter=mission_filter, current_page=1)  # Устанавливаем фильтр и сбрасываем страницу

    displayed_page = await send_patents_page(
        chat_id=chat_id,
        bot_instance=current_bot_instance,
        session=session,
        page_to_display=1,
        filter_condition=mission_filter  # Передаем фильтр по миссии
    )
    await state.update_data(current_page=displayed_page)


# --- ПОИСК ПО НОМЕРУ КОМАНДЫ ---
@router.callback_query(F.data == "find_by_team_pt", PatentBrowsing.browsing_menu)
async def find_by_team_entry(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(PatentBrowsing.waiting_team_number)
    await callback.message.answer("Введите номер команды:", reply_markup=get_cancel_input_keyboard())


@router.message(PatentBrowsing.waiting_team_number)
async def process_team_number_input(message: Message, state: FSMContext, session: AsyncSession):
    current_bot_instance = message.bot
    chat_id = message.chat.id

    try:
        team_number = int(message.text)
        if team_number <= 0: # Номер команды должен быть положительным
            raise ValueError("Номер команды должен быть положительным числом.")
    except ValueError as e:
        await message.answer(f"Некорректный номер команды: {e}. Пожалуйста, введите целое число.")
        return

    # Запрос всех одобренных патентов для данной команды
    team_patents_query = await session.scalars(
        select(Patent)
        .where(Patent.team_number == team_number, Patent.approved == True)
        .order_by(Patent.created_at)
    )
    team_patents = team_patents_query.all()

    await state.set_state(PatentBrowsing.displaying_team_patents) # Устанавливаем новое состояние
    await state.update_data(current_team_id=team_number) # Можно сохранить номер команды для отладки

    if not team_patents:
        await message.answer(f"Для команды №{team_number} пока нет одобренных изобретений.")
        # Возвращаем пользователя в общее меню просмотра после неудачного поиска
        await state.set_state(PatentBrowsing.browsing_menu)
        current_page_data = await state.get_data()
        current_page = current_page_data.get('current_page', 1)
        current_filter = current_page_data.get('current_filter') # Сохраняем фильтр
        await send_patents_page(
            chat_id=chat_id,
            bot_instance=current_bot_instance,
            session=session,
            page_to_display=current_page,
            filter_condition=current_filter # Возвращаемся с тем же фильтром
        )
        return

    # Отправляем клавиатуру со списком патентов
    reply_markup = get_team_patents_list_keyboard(team_patents)
    await message.answer(f"Изобретения команды №{team_number}:", reply_markup=reply_markup)


@router.callback_query(F.data.startswith("view_patent_id_"), PatentBrowsing.displaying_team_patents)
async def view_specific_team_patent(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    await callback.answer()

    patent_id = int(callback.data.split("_")[-1])

    patent = await session.scalar(select(Patent).where(Patent.id == patent_id, Patent.approved == True))

    if not patent:
        await callback.message.answer("Изобретение не найдено или не одобрено.")
        return

    # Отправляем информацию об одном патенте
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


# --- НАЗАД К ОБЩЕМУ ПРОСМОТРУ ИЗОБРЕТЕНИЙ ---
@router.callback_query(F.data == "back_to_general_browsing_pt", PatentBrowsing.displaying_team_patents)
@router.callback_query(F.data == "back_to_general_browsing_pt") # Общий фильтр для возврата из любого места поиска
async def back_to_general_browsing(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    await callback.answer()

    current_bot_instance = callback.bot
    chat_id = callback.message.chat.id

    await state.set_state(PatentBrowsing.browsing_menu) # Возвращаемся в основное меню просмотра
    await state.update_data(current_page=1, current_filter=None) # Сбрасываем все фильтры и возвращаемся на 1-ю страницу

    # Удаляем сообщение с текущей клавиатурой/списком
    try:
        await callback.message.delete()
    except Exception as e:
        print(f"Failed to delete message: {e}") # Сообщение могло быть слишком старым или уже удалено

    displayed_page = await send_patents_page(
        chat_id=chat_id,
        bot_instance=current_bot_instance,
        session=session,
        page_to_display=1,
        filter_condition=None # Без фильтра; общий список одобренных патентов
    )
    await state.update_data(current_page=displayed_page)


# --- ВОЗВРАТ В ГЛАВНОЕ МЕНЮ ИЗ ЛЮБОГО РЕЖИМА ПРОСМОТРА ---
@router.callback_query(F.data == "menu_pt", PatentBrowsing.browsing_menu)
@router.callback_query(F.data == "menu_pt", PatentBrowsing.displaying_team_patents) # Из всех состояний просмотра
async def return_to_main_menu_from_patents(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()

    await callback.message.answer("Вы вернулись в главное меню.", reply_markup=kb_client)



# -- Хэндлеры для публикации насадки --


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
        "Пожалуйста, отправьте фото/видео вашей насадки. На фото насадка должна быть показана целиком, весь дизайн и функционал должны быть продемонстрированы")


# Асинхронная функция для окончательной обработки альбома
async def _finalize_album_processing(bot_instance: Bot, chat_id: int, state: FSMContext, media_group_id: str):
    """
    Вызывается после небольшой задержки для окончательной обработки собранных медиа
    и отправки ОДНОГО ответного сообщения.
    """
    try:
        await asyncio.sleep(ALBUM_PROCESSING_DELAY)

        # Проверяем, что это тот же альбом, который мы ждали,
        # и он не был обработан или сброшен другим способом.
        if chat_id in album_collector and album_collector[chat_id]["media_group_id"] == media_group_id:
            collected_photos = album_collector[chat_id]["photos"]
            collected_videos = album_collector[chat_id]["videos"]

            print(f"DEBUG: Collected photos for album {media_group_id}: {collected_photos}")
            print(f"DEBUG: Collected videos for album {media_group_id}: {collected_videos}")

            # Обновляем FSM-контекст всеми собранными ID медиафайлов
            await state.update_data(images_ids=collected_photos, video_ids=collected_videos)
            await state.set_state(Publish.caption)

            # Отправляем ответное сообщение ТОЛЬКО ОДИН РАЗ
            # bot тут должен быть доступен (можно передать его в аргументы функции или сделать глобальным)
            await bot_instance.send_message(chat_id, "Введите название насадки.")  # Предполагается, что 'bot' доступен

            # Очищаем данные из временного хранилища, так как альбом обработан
            del album_collector[chat_id]

    except asyncio.CancelledError:
        # Задача была отменена, потому что пришло новое сообщение для того же альбома
        # до того, как завершился сон. Это нормально, просто ничего не делаем.
        pass
    except Exception as e:
        print(f"Ошибка в _finalize_album_processing для чата {chat_id}: {e}")


@router.message(Publish.media)
async def process_media_and_ask_caption(message: Message, state: FSMContext):
    chat_id = message.chat.id
    current_media_group_id = message.media_group_id

    # Проверка на НЕ-медиа сообщение
    if not message.photo and not message.video:
        await message.answer(
            "Пожалуйста, отправьте фото/видео вашей насадки. На фото насадка должна быть показана целиком, весь дизайн и функционал должны быть продемонстрированы.")
        return

    current_bot_instance = message.bot

    # Обработка ОДИНОЧНОГО фото/видео (не часть альбома)
    # Если media_group_id отсутствует, это одиночное медиа
    if not current_media_group_id:
        images_ids = [message.photo[-1].file_id] if message.photo else []  # Берем только ID самой большой фотографии
        video_ids = [message.video.file_id] if message.video else []  # Берем ID видео

        await state.update_data(images_ids=images_ids, video_ids=video_ids)
        await state.set_state(Publish.caption)
        await message.answer("Введите название насадки.")

        # Если было незавершенное ожидание альбома, отменяем его
        if chat_id in album_collector:
            if album_collector[chat_id].get("processing_task") and not album_collector[chat_id][
                "processing_task"].done():
                album_collector[chat_id]["processing_task"].cancel()
            del album_collector[chat_id]  # Очищаем данные по альбому
        return

    # Обработка СООБЩЕНИЙ, ЯВЛЯЮЩИХСЯ ЧАСТЬЮ МЕДИАГРУППЫ (АЛЬБОМА)

    # Инициализируем или сбрасываем данные для нового альбома.
    # Инициализируем или сбрасываем данные для нового альбома/группы
    # Проверяем, это новый альбом или продолжение существующего?
    if chat_id not in album_collector or album_collector[chat_id]["media_group_id"] != current_media_group_id:
        # Если это новый альбом, или предыдущий альбом был отменен/заброшен,
        # отменяем любую старую задачу и инициализируем новые данные
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

    # Добавляем текущее медиа в список собранных ID
    if message.photo:
        collector_data["photos"].append(message.photo[-1].file_id)  # Добавляем только ID самого большого размера фото
    elif message.video:
        collector_data["videos"].append(message.video.file_id)  # Добавляем ID видео

    # Отменяем любую ранее запланированную задачу для этого альбома.
    # Это позволяет "сбросить" таймер, если пришло новое медиа из той же группы.
    if collector_data["processing_task"] and not collector_data["processing_task"].done():
        collector_data["processing_task"].cancel()

    # Запускаем новую задачу для обработки альбома после короткой задержки.
    # Эта задача выполнится только в том случае, если за время задержки не придет
    # новых сообщений для ЭТОГО ЖЕ альбома.
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
    image_ids = data.get('images_ids', [])  # Инициализируем пустым списком, если нет данных
    video_ids = data.get('video_ids', [])  # Инициализируем пустым списком, если нет данных
    missions = data.get('missions')
    caption = data.get('caption')
    description = data.get('description')

    media = []

    for image in image_ids:
        media.append(InputMediaPhoto(media=image))
    for video in video_ids:
        media.append(InputMediaVideo(media=video))

    if not media:  # Если медиа вообще не было
        await message.answer(
            f"Нет медиа для отправки.\n\nМиссии: {missions}\nНазвание: {caption}\nОписание: {description}\n<b>ID:</b>",
            reply_markup=confirm_pt_client, parse_mode="html"
        )
    elif len(media) == 1:  # Если только ОДИН медиафайл
        # Определяем тип медиа и отправляем его с подписью и клавиатурой
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
    else:  # Если МНОГО медиафайлов (медиагруппа)
        # Отправляем медиагруппу (без общей подписи и клавиатуры)
        await message.answer_media_group(media)
        # А затем ОТДЕЛЬНЫМ сообщением отправляем подпись и клавиатуру
        await message.answer(
            f"Миссии: {missions}\nНазвание: {caption}\nОписание: {description}\n<b>ID:</b>\nвидео - {video_ids}\nкартинки - {image_ids}",
            reply_markup=confirm_pt_client,
            parse_mode="html"
        )

    await state.set_state(state=Publish.confirm)


@router.callback_query(F.data == "confirm_pt")
async def patent_sent(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    user_tg_id = callback.from_user.id  # Получаем Telegram ID пользователя

    # Извлекаем все данные из состояния
    caption = data.get('caption', 'Без названия')
    description = data.get('description', 'Без описания')
    missions = data.get('missions', [])  # Получаем список миссий
    image_ids = data.get('images_ids', [])
    video_ids = data.get('video_ids', [])

    # Проверка длины полей
    if len(caption) > 50:
        await callback.message.answer("Название насадки слишком длинное (макс. 50 символов).",
                                      reply_markup=back_pt_client)
        return
    if len(description) > 250:
        await callback.message.answer("Описание насадки слишком длинное (макс. 250 символов).",
                                      reply_markup=back_pt_client)
        return

    try:
        # Вызываем функцию для сохранения патента
        await rq.add_patent_to_db(
            user_tg_id=user_tg_id,
            missions=missions,  # Передаем список
            caption=caption,
            description=description,
            image_ids=image_ids,  # Передаем список
            video_ids=video_ids,  # Передаем список
            session=session  # Передаем текущую сессию
        )

        await session.commit()  # Фиксируем изменения в базе данных
        await callback.message.answer(
            "Насадка успешно сохранена и отправлена на модерацию! Вскоре она будет видна здесь в ближайшие дни :)")
        await state.clear()  # Очищаем состояние после успешной публикации

    except ValueError as ve:  # Отлавливаем ошибку, если пользователь не найден (хотя она не должна срабатывать, если пользователь уже зарегистрирован)
        await session.rollback()
        print(f"Ошибка сохранения изобретения (ValueError): {ve}")
        await callback.message.answer(f"Ошибка: {ve} Пожалуйста, попробуйте снова или свяжитесь с администратором.")
    except Exception as e:  # Общая ошибка при сохранении
        await session.rollback()  # Откатываем все изменения в случае любой ошибки
        print(f"Произошла непредвиденная ошибка при сохранении изобретения: {e}")
        await callback.message.answer("Произошла непредвиденная ошибка при сохранении патента. Попробуйте еще раз.")
    finally:
        await state.clear()
