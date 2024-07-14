from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

main_menu = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Учить слова")],
                                          [KeyboardButton(text="Дуэль слов")],
                                          [KeyboardButton(text="Прогресс")],
                                          [KeyboardButton(text="Рейтинг")],
                                          [KeyboardButton(text="Настройки")]],
                                resize_keyboard=True)

choose_grade_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Easy", callback_data="grade_Easy")],
        [InlineKeyboardButton(text="Intermediate",
                              callback_data="grade_Intermediate")],
        [InlineKeyboardButton(text="Advanced", callback_data="grade_Advanced")]
    ])


async def choose_training_length_keyboard():
    buttons = [
        InlineKeyboardButton(text=str(i), callback_data=f"training_length_{i}")
        for i in range(10, 51, 5)
    ]
    keyboard = [buttons[i:i + 3] for i in range(0, len(buttons), 3)]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


async def start_training_keyboard(grade):
    return InlineKeyboardMarkup(row_width=2, inline_keyboard=[[
        InlineKeyboardButton(text="▶️", callback_data=f"start_training_{grade}"),
        InlineKeyboardButton(text="🔄", callback_data="repeat_words")]])


async def navigation_keyboard(start_index):
    keyboard = [InlineKeyboardButton(text="⬅️", callback_data="back_words"),
                InlineKeyboardButton(text="➡️", callback_data="next_words")]
    return InlineKeyboardMarkup(
        row_width=2,
        inline_keyboard=[keyboard if start_index != 0 else [keyboard[1]]])


async def show_training_word_keyboard(word, options):
    keyboard = InlineKeyboardMarkup(row_width=2, inline_keyboard=[
        [InlineKeyboardButton(
            text=option,
            callback_data=f"answer_{word}_{option}"
        )
            for option in
            options[:2]],
        [InlineKeyboardButton(
            text=option,
            callback_data=f"answer_{word}_{option}"
        )
            for option in
            options[2:4]],
        [InlineKeyboardButton(
            text=option,
            callback_data=f"answer_{word}_{option}"
        )
            for option in
            options[4:6]],
        [InlineKeyboardButton(
            text=option,
            callback_data=f"answer_{word}_{option}"
        )
            for option in
            options[6:8]],
        [InlineKeyboardButton(
            text="Пропустить слово",
            callback_data=f"answer_{word}_unknown"
        )],
        [InlineKeyboardButton(
            text="Завершить тренировку",
            callback_data="finish_training"
        )],
        [InlineKeyboardButton(
            text="Сообщить об ошибке",
            callback_data=f"report_error_{word}"
        )]
    ])
    return keyboard


async def notification_interval_keyboard():
    buttons = [
        InlineKeyboardButton(text=str(i),
                             callback_data=f"notification_interval_{i}")
        for i in range(2, 25, 2)
    ]
    keyboard = [buttons[i:i + 4] for i in range(0, len(buttons), 4)]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
