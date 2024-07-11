from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

main_menu = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Учить слова")],
                                          [KeyboardButton(text="Прогресс")],],
                                resize_keyboard=True)

choose_grade_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Easy", callback_data="grade_Easy")],
        [InlineKeyboardButton(text="Intermediate",
                              callback_data="grade_Intermediate")],
        [InlineKeyboardButton(text="Advanced", callback_data="grade_Advanced")]
    ])

choose_training_length_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=str(i),
                              callback_data=f"training_length_{i}")] for i in
        range(10, 51, 5)
    ])


async def start_training_keyboard(grade):
    return InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="▶️", callback_data=f"start_training_{grade}")],
    [InlineKeyboardButton(text="🔄", callback_data="repeat_words")]])


async def navigation_keyboard(start_index):
    keyboard = [[(InlineKeyboardButton(text="➡️",
                                       callback_data="next_words"))]]
    if start_index != 0:
        keyboard.append([InlineKeyboardButton(text="⬅️",
                                              callback_data="back_words")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


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
