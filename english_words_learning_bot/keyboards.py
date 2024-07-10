from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


buttons = [
    [KeyboardButton(text="Учиться")],
    [KeyboardButton(text="Прогресс")],
]
main_menu = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
