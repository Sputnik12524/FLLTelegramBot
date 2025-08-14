from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Команда уже зарегистрирована в боте', callback_data='already_registered')],
                                     [InlineKeyboardButton(text='Команда регистрируется впервые', callback_data='first_register')],
                                     [InlineKeyboardButton(text='Назад', callback_data='back_to_menu')]])
keyboard_error = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Зарегистрироваться', callback_data='register')], [InlineKeyboardButton(text='Назад', callback_data='menu_pt')]])