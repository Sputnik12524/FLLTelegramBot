from typing import List

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from database.models import Patent
from typing import Sequence

b1 = InlineKeyboardButton(
    text="🔍 Найти насадку по номеру миссии 🔍",
    callback_data="find_by_mission_pt"
)
b2 = InlineKeyboardButton(
    text="🔍 Найти насадку по номеру команды 🔍",
    callback_data="find_by_team_pt"
)
b3 = InlineKeyboardButton(
    text="⏮️",
    callback_data="prev_page_pt"
)
b4 = InlineKeyboardButton(
    text="1",
    callback_data="select_page_pt"
)
b5 = InlineKeyboardButton(
    text="⏭️",
    callback_data="next_page_pt"
)
b6 = InlineKeyboardButton(
    text="📢 Опубликовать свои изобретения ️ 📢",
    callback_data="publish_pt"
)
b7 = InlineKeyboardButton(
    text="👀 Просмотреть публичные изобретения 👀",
    callback_data="view_pt"
)
b_back = InlineKeyboardButton(
    text="Назад ↩️",
    callback_data="main_menu"
)
b_again = InlineKeyboardButton(
    text="Начать заново",
    callback_data="publish_pt"
)
b_confirm = InlineKeyboardButton(
    text="Подтвердить ✅",
    callback_data="confirm_pt"
)

publish_row = [b6]
view_row = [b7]
back_row = [b_back]
again_row = [b_again]
confirm_row = [b_confirm]

zero_rows = [publish_row, back_row]
back_rows = [back_row]
confirm_rows = [back_row, again_row, confirm_row]
main_rows = [view_row, publish_row, back_row]

patent_kb_client = InlineKeyboardMarkup(inline_keyboard=main_rows)
zero_patent_kb_client = InlineKeyboardMarkup(inline_keyboard=zero_rows)
back_pt_client = InlineKeyboardMarkup(inline_keyboard=back_rows)
confirm_pt_client = InlineKeyboardMarkup(inline_keyboard=confirm_rows)


def get_patent_menu_keyboard(current_page: int, total_pages: int) -> InlineKeyboardMarkup:
    # Защита от деления на ноль, если патентов нет
    if total_pages == 0:
        total_pages = 1  # Если патентов нет, пусть будет одна "пустая" страница

    b1m = InlineKeyboardButton(text="🔍 Найти насадку по номеру миссии 🔍", callback_data="find_by_mission_pt")
    b2m = InlineKeyboardButton(text="🔍 Найти насадку по номеру команды 🔍", callback_data="find_by_team_pt")
    b3m = InlineKeyboardButton(text="⏮️", callback_data="prev_page_pt")
    b4m = InlineKeyboardButton(text=f"{current_page} | {total_pages}",
                              callback_data="select_page_pt")  # Отображаем текущую/всего страниц
    b5m = InlineKeyboardButton(text="⏭️", callback_data="next_page_pt")
    b6m = InlineKeyboardButton(text="📢 Опубликовать свои изобретения 📢", callback_data="publish_pt")
    b_back_m = InlineKeyboardButton(text="Назад ↩️", callback_data="main_menu")  # Callback для возврата в главное меню бота

    first_row_m = [b1m]
    second_row_m = [b2m]
    third_row_m = [b3m, b4m, b5m]
    fourth_row_m = [b6m]
    back_row_m = [b_back_m]

    main_rows_m = [first_row_m, second_row_m, third_row_m, fourth_row_m, back_row_m]
    return InlineKeyboardMarkup(inline_keyboard=main_rows_m)

def get_input_page_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Отмена", callback_data="cancel_input_pt")]
    ])


def get_team_patents_list_keyboard(patents: Sequence[Patent]) -> InlineKeyboardMarkup:
    keyboard = []
    if patents:
        for patent in patents:
            # Формат кнопки: Название (номера миссий)
            missions_str = ', '.join(map(str, patent.missions))
            button_text = f"{patent.caption} ({missions_str})"
            keyboard.append([
                InlineKeyboardButton(text=button_text, callback_data=f"view_patent_id_{patent.id}")
            ])

    keyboard.append([InlineKeyboardButton(text="Назад к просмотру изобретений ↩️", callback_data="back_to_general_browsing_pt")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# Клавиатура для одного просматриваемого патента (чтобы вернуться к общему списку)
def get_single_patent_view_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Назад к просмотру изобретений ↩️", callback_data="back_to_general_browsing_pt")]
    ])


def get_cancel_input_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Отмена", callback_data="cancel_input_pt")]
    ])


def get_confirm_join_team_keyboard() -> InlineKeyboardMarkup:  # Убрали admin_ids из параметров
    keyboard_rows = [
        [InlineKeyboardButton(text="Да, это моя команда", callback_data="confirm_join_existing_team")],
        [InlineKeyboardButton(text="Нет, это не моя команда", callback_data="cancel_join_existing_team")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard_rows)