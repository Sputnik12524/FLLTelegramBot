from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

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
b_back = InlineKeyboardButton(
    text="Назад ↩️",
    callback_data="menu_pt"
)

first_row = [b1]
second_row = [b2]
third_row = [b3, b4, b5]
fourth_row = [b6]
back_row = [b_back]

main_rows = [first_row, second_row, third_row, fourth_row, back_row]
zero_rows = [fourth_row, back_row]
back_rows = [back_row]

main_patent_kb_client = InlineKeyboardMarkup(inline_keyboard=main_rows)
zero_patent_kb_client = InlineKeyboardMarkup(inline_keyboard=zero_rows)
back_pt_client = InlineKeyboardMarkup(inline_keyboard=back_rows)
