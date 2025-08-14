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
    text="Посмотреть/запатентовать инновационные решения",
    callback_data="patent"
)
b4 = InlineKeyboardButton(
    text="Посмотреть матчи команд",
    callback_data="matches"
)
b5 = InlineKeyboardButton(
    text="Актуальный рекорд России",
    callback_data="records"
)
b6 = InlineKeyboardButton(
    text="Посмотреть расписание товарищеских встреч",
    url="https://sputnik.lab244.ru/scrimmages-calendar"
)

first_row = [b1]
second_row = [b2]
third_row = [b3, b6]
fourth_row = [b4, b5]
rows = [first_row, second_row, third_row, fourth_row]
kb_client = InlineKeyboardMarkup(inline_keyboard=rows)
