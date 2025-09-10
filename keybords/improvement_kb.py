from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# Главное меню доработок
def get_improvement_main_keyboard():
    b1 = InlineKeyboardButton(text="📸 Добавить фото робота", callback_data="improvement_add_robot")
    b2 = InlineKeyboardButton(text="💻 Добавить код", callback_data="improvement_add_code")
    b3 = InlineKeyboardButton(text="📋 Мои доработки", callback_data="improvement_my_list")
    b5 = InlineKeyboardButton(text="👥 Доработки команды", callback_data="improvement_team_list")
    b4 = InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [b1],
        [b2],
        [b3],
        [b5],
        [b4]
    ])
    return keyboard

# Клавиатура для выбора типа доработки
def get_improvement_type_keyboard():
    b1 = InlineKeyboardButton(text="🤖 Робот", callback_data="improvement_type_robot")
    b2 = InlineKeyboardButton(text="💻 Код", callback_data="improvement_type_code")
    b3 = InlineKeyboardButton(text="📝 Другое", callback_data="improvement_type_other")
    b4 = InlineKeyboardButton(text="◀️ Назад", callback_data="improvement_main")
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [b1, b2],
        [b3],
        [b4]
    ])
    return keyboard

# Клавиатура для подтверждения загрузки
def get_improvement_confirm_keyboard(improvement_type: str):
    b1 = InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"improvement_confirm_{improvement_type}")
    b2 = InlineKeyboardButton(text="🔄 Заново", callback_data=f"improvement_add_{improvement_type}")
    b3 = InlineKeyboardButton(text="◀️ Назад", callback_data="improvement_main")
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [b1],
        [b2, b3]
    ])
    return keyboard

# Клавиатура для просмотра доработки
def get_improvement_view_keyboard(improvement_id: int):
    b1 = InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"improvement_edit_{improvement_id}")
    b2 = InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"improvement_delete_{improvement_id}")
    b3 = InlineKeyboardButton(text="◀️ Назад", callback_data="improvement_my_list")
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [b1],
        [b2, b3]
    ])
    return keyboard

# Клавиатура для списка доработок
def get_improvement_list_keyboard(improvements: list):
    buttons = []
    for improvement in improvements:
        # Создаем кнопку для каждой доработки
        emoji = "🤖" if improvement.improvement_type == "robot" else "💻" if improvement.improvement_type == "code" else "📝"
        title_or_desc = improvement.title or improvement.description or 'Без названия'
        text = f"{emoji} {title_or_desc[:30]}..." if len(title_or_desc) > 30 else f"{emoji} {title_or_desc}"
        callback_data = f"improvement_view_{improvement.id}"
        buttons.append([InlineKeyboardButton(text=text, callback_data=callback_data)])
    
    # Добавляем кнопку "Назад"
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="improvement_main")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard

# Клавиатура для редактирования
def get_improvement_edit_keyboard(improvement_id: int):
    b1 = InlineKeyboardButton(text="📝 Изменить описание", callback_data=f"improvement_edit_desc_{improvement_id}")
    b2 = InlineKeyboardButton(text="📸 Добавить файлы", callback_data=f"improvement_add_files_{improvement_id}")
    b3 = InlineKeyboardButton(text="🗑️ Удалить файлы", callback_data=f"improvement_remove_files_{improvement_id}")
    b4 = InlineKeyboardButton(text="◀️ Назад", callback_data=f"improvement_view_{improvement_id}")
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [b1],
        [b2, b3],
        [b4]
    ])
    return keyboard
