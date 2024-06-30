import random
from aiogram import Bot
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from aiogram.fsm.context import FSMContext


async def get_user_words(pool, user_id: int, grade: str, limit: int = 25):
    async with pool.acquire() as connection:
        user_words = await connection.fetch(
            """
            SELECT d.word_id, d.word, d.translation, up.status FROM dictionary d
            LEFT JOIN user_progress up ON d.word_id = up.word_id
            AND up.user_id = $1
            WHERE d.grade = $2
            ORDER BY  up.status DESC NULLS LAST
            LIMIT $3
            """,
            user_id, grade, limit
        )
    return user_words


async def choose_grade_command(message: Message, state: FSMContext):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Easy", callback_data="grade_Easy")],
        [InlineKeyboardButton(text="Intermediate", callback_data="grade_Intermediate")],
        [InlineKeyboardButton(text="Advanced", callback_data="grade_Advanced")]
    ])
    await message.answer("Выберите уровень сложности", reply_markup=keyboard)


async def process_grade_choice(callback_query: CallbackQuery, pool, bot: Bot, state: FSMContext):
    grade = callback_query.data.split("_")[1]
    telegram_id = callback_query.from_user.id
    user_id = await get_user_id(pool, telegram_id)

    words = await get_user_words(pool, user_id, grade)
    if not words:
        await bot.send_message(telegram_id, f"Вы выучили все слова на уровне {grade}")
        return

    await state.update_data(user_id=user_id, grade=grade, words=words, index=0)
    await bot.send_message(telegram_id, "Начнем обучение! Вот первые 5 слов и их переводы:")
    await show_words(callback_query.message, state, bot)


async def show_words(message: Message, state: FSMContext, bot: Bot):
    state_data = await state.get_data()
    start_index = state_data["index"]
    words = state_data["words"]
    response = ""
    for word in words[start_index:start_index + 5]:
        response += f"{word['word']} - {word['translation']}\n"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Далее", callback_data="next_words")]
    ])
    await message.answer(response, reply_markup=keyboard)


async def next_words(callback_query: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    data["index"] += 5
    await state.update_data(index=data["index"])

    if data["index"] < len(data["words"]):
        await show_words(callback_query.message, state, bot)
    else:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Начать тренировку", callback_data=f"start_training_{data['grade']}")]
        ])
        await callback_query.message.answer("Все слова были показаны. Готовы начать тренировку?", reply_markup=keyboard)


async def start_training(callback_query: CallbackQuery, pool, bot: Bot, state: FSMContext):
    grade = callback_query.data.split("_")[2]
    data = await state.get_data()
    words = data["words"]
    random.shuffle(words)

    await state.update_data(training_words=words, training_index=0)
    await bot.send_message(callback_query.from_user.id, "Начнем тренировку!")
    await show_training_word(callback_query.message, state, bot)


async def show_training_word(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    index = data["training_index"]

    if index >= len(data["training_words"]):
        await message.answer("Тренировка завершена!")
        return

    word = data["training_words"][index]
    correct_translation = word["translation"]
    all_translations = [w["translation"] for w in data["training_words"] if w["word_id"] != word["word_id"]]
    random.shuffle(all_translations)
    options = all_translations[:7] + [correct_translation]
    random.shuffle(options)

    keyboard = InlineKeyboardMarkup(row_width=2, inline_keyboard=[
        [InlineKeyboardButton(text=option, callback_data=f"answer_{word['word_id']}_{option}") for option in options]
    ])

    await message.answer(f"Переведите слово {word['word']}", reply_markup=keyboard)


async def handle_answer(callback_query: CallbackQuery, state: FSMContext, bot: Bot):
    data = callback_query.data.split("_")
    chosen_translation = data[2]

    state_data = await state.get_data()
    training_index = state_data["training_index"]

    if training_index >= len(state_data["training_words"]):
        await callback_query.message.answer("Тренировка завершена!")
        return

    current_word = state_data["training_words"][training_index]

    if chosen_translation == current_word["translation"]:
        await callback_query.message.answer("Правильно!")
    else:
        await callback_query.message.answer(f"Неправильно! Правильный ответ: {current_word['translation']}")

    state_data["training_index"] += 1
    await state.update_data(training_index=state_data["training_index"])

    await show_training_word(callback_query.message, state, bot)


async def get_user_id(pool, telegram_id: int):
    async with pool.acquire() as connection:
        user_id = await connection.fetchval(
            """
            SELECT user_id
            FROM users
            WHERE telegram_id = $1
            """,
            telegram_id
        )
    return user_id
