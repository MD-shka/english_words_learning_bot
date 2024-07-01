import random
from datetime import datetime
from aiogram import Bot
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardRemove
)
from aiogram.fsm.context import FSMContext


async def get_user_words(pool, user_id: int, grade: str, limit: int):
    async with pool.acquire() as connection:
        user_words = await connection.fetch(
            """
            SELECT d.word_id, d.word, d.translation, up.status 
            FROM dictionary d
            LEFT JOIN user_progress up ON d.word_id = up.word_id AND up.user_id = $1
            WHERE d.grade = $2
            ORDER BY RANDOM()
            LIMIT $3
            """,
            user_id, grade, limit
        )
    return user_words


async def choose_grade_command(message: Message, state: FSMContext, bot: Bot):
    state_data = await state.get_data()
    if "last_message_id" in state_data:
        try:
            await bot.delete_message(message.chat.id, state_data["last_message_id"])
        except Exception as e:
            print(f"Failed to delete message: {e}")

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Easy", callback_data="grade_Easy")],
        [InlineKeyboardButton(text="Intermediate", callback_data="grade_Intermediate")],
        [InlineKeyboardButton(text="Advanced", callback_data="grade_Advanced")]
    ])
    await message.answer("Выберите уровень сложности", reply_markup=keyboard)


async def process_grade_choice(callback_query: CallbackQuery, pool, bot: Bot, state: FSMContext, main_menu):
    grade = callback_query.data.split("_")[1]
    telegram_id = callback_query.from_user.id
    user_id = await get_user_id(pool, telegram_id)

    state_data = await state.get_data()
    print(f"Limit before fetching words: {state_data.get('training_length')}")
    words = await get_user_words(pool, user_id, grade, limit=state_data.get("training_length"))
    print(f"Received {len(words)} words for training.")
    if not words:
        await bot.send_message(telegram_id, f"Вы выучили все слова на уровне {grade}")
        return

    await state.update_data(user_id=user_id, grade=grade, words=words, index=0)
    sent_message = await bot.send_message(telegram_id, "Начнем обучение! Запомните слова и их переводы:")
    await state.update_data(last_message_id=sent_message.message_id)
    await start_training(callback_query, bot, state, main_menu)


async def choose_training_length(message: Message, state: FSMContext, bot: Bot):
    state_data = await state.get_data()
    if "last_message_id" in state_data:
        try:
            await bot.delete_message(message.chat.id, state_data["last_message_id"])
        except Exception as e:
            print(f"Failed to delete message: {e}")

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=str(i), callback_data=f"training_length_{i}")] for i in range(10, 51, 5)
    ])
    sent_message = await message.answer("Выберите колличество слов тренировки", reply_markup=keyboard)
    await state.update_data(last_message_id=sent_message.message_id)


async def show_words(callback_query: CallbackQuery, state: FSMContext, bot: Bot):
    state_data = await state.get_data()
    if "last_message_id" in state_data:
        try:
            await bot.delete_message(callback_query.message.chat.id, state_data["last_message_id"])
        except Exception as e:
            print(f"Failed to delete message: {e}")
    start_index = state_data["index"]
    words = state_data["words"]
    response = ""
    for word in words[start_index:start_index + 5]:
        response += f"{word['word']} - {word['translation']}\n"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Далее", callback_data="next_words")]
    ])
    sent_message = await callback_query.message.answer(response, reply_markup=keyboard)
    await state.update_data(last_message_id=sent_message.message_id)


async def next_words(callback_query: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    if "last_message_id" in data:
        try:
            await bot.delete_message(callback_query.message.chat.id, data["last_message_id"])
        except Exception as e:
            print(f"Failed to delete message: {e}")
    data["index"] += 5
    await state.update_data(index=data["index"])

    if data["index"] < len(data["words"]):
        await show_words(callback_query, state, bot)
    else:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Начать тренировку", callback_data=f"start_training_{data['grade']}")]
        ])
        sent_message = await callback_query.message.answer("Все слова были показаны. Готовы начать тренировку?",
                                                           reply_markup=keyboard)
        await state.update_data(last_message_id=sent_message.message_id)


async def start_training(callback_query: CallbackQuery, bot: Bot, state: FSMContext, main_menu):
    data = await state.get_data()
    if "last_message_id" in data:
        try:
            await bot.delete_message(callback_query.message.chat.id, data["last_message_id"])
        except Exception as e:
            print(f"Failed to delete message: {e}")

    words = data["words"]
    random.shuffle(words)

    hide_keyboard = ReplyKeyboardRemove()

    await state.update_data(
        training_words=words,
        training_index=0,
        correct_answers=0,
        incorrect_answers=0,
        start_time=datetime.utcnow()
    )
    await bot.send_message(callback_query.from_user.id, "Начнем тренировку!", reply_markup=hide_keyboard)
    await show_training_word(callback_query, state, bot, main_menu)


async def finish_training(callback_query: CallbackQuery, state: FSMContext, bot: Bot, main_menu):
    state_data = await state.get_data()
    last_message_id = state_data.get("last_message_id")
    if last_message_id:
        try:
            await bot.delete_message(callback_query.message.chat.id, last_message_id)
        except Exception as e:
            print(f"Failed to delete message: {e}")

    correct_answers = state_data.get("correct_answers", 0)
    incorrect_answers = state_data.get("incorrect_answers", 0)
    start_time = state_data["start_time"]
    elapsed = datetime.utcnow() - start_time
    elapsed_str = str(elapsed).split('.')[0]

    response = (f"Тренировка завершена!\n"
                f"Правильных ответов: {correct_answers}\n"
                f"Ошибок: {incorrect_answers}\n"
                f"Время тренировки: {elapsed_str}")

    await bot.send_message(callback_query.from_user.id, response, reply_markup=main_menu)
    await state.clear()


async def show_training_word(callback_query: CallbackQuery, state: FSMContext, bot: Bot, main_menu):
    data = await state.get_data()
    if "last_message_id" in data:
        try:
            await bot.delete_message(callback_query.message.chat.id, data["last_message_id"])
        except Exception as e:
            print(f"Failed to delete message: {e}")
    index = data["training_index"]

    if index >= len(data["training_words"]):
        await finish_training(callback_query, state, bot, main_menu)
        return

    word = data["training_words"][index]
    correct_translation = word["translation"]
    all_translations = [w["translation"] for w in data["training_words"] if w["word_id"] != word["word_id"]]
    random.shuffle(all_translations)
    options = all_translations[:7] + [correct_translation]
    random.shuffle(options)

    keyboard = InlineKeyboardMarkup(row_width=2, inline_keyboard=[
        [InlineKeyboardButton(text=option, callback_data=f"answer_{word['word_id']}_{option}") for option in
         options[:2]],
        [InlineKeyboardButton(text=option, callback_data=f"answer_{word['word_id']}_{option}") for option in
         options[2:4]],
        [InlineKeyboardButton(text=option, callback_data=f"answer_{word['word_id']}_{option}") for option in
         options[4:6]],
        [InlineKeyboardButton(text=option, callback_data=f"answer_{word['word_id']}_{option}") for option in
         options[6:8]],
        [InlineKeyboardButton(text="Завершить тренировку", callback_data="finish_training")]
    ])

    sent_message = await callback_query.message.answer(f"Переведите слово {word['word']}", reply_markup=keyboard)
    await state.update_data(last_message_id=sent_message.message_id)


async def handle_answer(callback_query: CallbackQuery, state: FSMContext, bot: Bot, main_menu):
    data = callback_query.data.split("_")
    chosen_translation = data[2]

    state_data = await state.get_data()
    training_index = state_data["training_index"]

    if training_index >= len(state_data["training_words"]):
        await finish_training(callback_query, state, bot, main_menu)
        return

    current_word = state_data["training_words"][training_index]

    if chosen_translation == current_word["translation"]:
        state_data["correct_answers"] = state_data.get("correct_answers", 0) + 1
        response = "Правильно!"
    else:
        state_data["incorrect_answers"] = state_data.get("incorrect_answers", 0) + 1
        response = f"Неправильно! Правильный ответ: {current_word['translation']}"
    await callback_query.message.answer(response)

    state_data["training_index"] += 1
    await state.update_data(
        training_index=state_data["training_index"],
        correct_answers=state_data["correct_answers"],
        incorrect_answers=state_data["incorrect_answers"]
    )

    await show_training_word(callback_query, state, bot, main_menu)


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
