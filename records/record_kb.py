from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_record_main_menu():
    """Главное меню рекордов"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇷🇺 Актуальный рекорд России", callback_data="russia_record")],
        [InlineKeyboardButton(text="📤 Отправить рекорд на проверку", callback_data="submit_record")],
        [InlineKeyboardButton(text="🏆 Мои рекорды", callback_data="my_records")],
        [InlineKeyboardButton(text="📊 Топ рекордов", callback_data="top_records")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
    ])
    return keyboard

def get_record_submission_menu():
    """Меню для отправки рекорда"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Указать дату рекорда", callback_data="set_record_date")],
        [InlineKeyboardButton(text="🎯 Указать количество очков", callback_data="set_record_score")],
        [InlineKeyboardButton(text="🎥 Загрузить видео", callback_data="upload_video")],
        [InlineKeyboardButton(text="✅ Отправить на проверку", callback_data="submit_for_review")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_records")]
    ])
    return keyboard

def get_date_input_keyboard():
    """Клавиатура для ввода даты"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📅 Сегодня")],
            [KeyboardButton(text="📅 Вчера")],
            [KeyboardButton(text="✏️ Ввести дату вручную")],
            [KeyboardButton(text="🔙 Отмена")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return keyboard

def get_score_input_keyboard():
    """Клавиатура для ввода очков"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎯 Ввести количество очков")],
            [KeyboardButton(text="🔙 Отмена")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return keyboard

def get_video_upload_keyboard():
    """Клавиатура для загрузки видео"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎥 Загрузить видео")],
            [KeyboardButton(text="🔙 Отмена")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return keyboard

def get_admin_record_review_keyboard(record_id):
    """Клавиатура для админа для проверки рекорда"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve_record_{record_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_record_{record_id}")
        ],
        [InlineKeyboardButton(text="💬 Запросить дополнительную информацию", callback_data=f"request_info_{record_id}")],
        [InlineKeyboardButton(text="📊 Детали рекорда", callback_data=f"record_details_{record_id}")]
    ])
    return keyboard

def get_record_status_keyboard():
    """Клавиатура для просмотра статуса рекордов"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏳ На проверке", callback_data="records_pending")],
        [InlineKeyboardButton(text="✅ Одобренные", callback_data="records_approved")],
        [InlineKeyboardButton(text="❌ Отклоненные", callback_data="records_rejected")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_records")]
    ])
    return keyboard

def get_cancel_keyboard():
    """Простая клавиатура отмены"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🔙 Отмена")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return keyboard

def get_confirmation_keyboard():
    """Клавиатура подтверждения отправки"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да, отправить", callback_data="confirm_submit"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_submit")
        ]
    ])
    return keyboard

def remove_keyboard():
    """Убрать клавиатуру"""
    from aiogram.types import ReplyKeyboardRemove
    return ReplyKeyboardRemove()