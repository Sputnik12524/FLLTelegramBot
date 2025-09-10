from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

b1 = InlineKeyboardButton(
    text="Зарегистрироваться в системе",
    callback_data="register"
)
b2 = InlineKeyboardButton(
    text="Калькулятор миссий",
    callback_data="missions"
)
b3 = InlineKeyboardButton(
    text="Инновационные решения",
    callback_data="patent"
)
b4 = InlineKeyboardButton(
    text="Мои доработки",
    callback_data="changes"
)
b5 = InlineKeyboardButton(
    text="Рекорды России",
    callback_data="records"
)
b6 = InlineKeyboardButton(
    text="Тов. встречи",
    url="https://sputnik.lab244.ru/fll-scrimmages-calendar"
)

first_row = [b1]
second_row = [b2]
third_row = [b3, b6]
fourth_row = [b4, b5]
rows = [first_row, second_row, third_row, fourth_row]
kb_client = InlineKeyboardMarkup(inline_keyboard=rows)
