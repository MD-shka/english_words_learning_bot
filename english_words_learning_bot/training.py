import random
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardRemove
)
from aiogram.fsm.context import FSMContext

dp = Dispatcher()


async def get_user_words(pool, user_id: int, grade: str, limit: int):
    async with pool.acquire() as connection:
        user_words = await connection.fetch(
            """
            SELECT d.word_id, d.word, d.translation, up.status 
            FROM dictionary d
            LEFT JOIN user_progress up 
            ON d.word_id = up.word_id AND up.user_id = $1
            JOIN grades g ON d.grade_id = g.grade_id
            WHERE g.grade = $2
            ORDER BY RANDOM()
            LIMIT $3
            """,
            user_id, grade, limit
        )
    return user_words


async def update_word_status(pool,
                             user_id: int,
                             word_id: int,
                             is_correct: bool
                             ):
    async with pool.acquire() as connection:
        result = await connection.fetchrow(
            """
            SELECT status, current_progress
            FROM user_progress
            WHERE user_id = $1 AND word_id = $2
            """,
            user_id, word_id
        )

        if result is None:
            status = "Новое слово"
            current_progress = 0
            await connection.execute(
                """
                INSERT INTO user_progress (
                user_id,
                word_id,
                status,
                current_progress
                )
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (user_id, word_id) DO NOTHING 
                """,
                user_id, word_id, status, current_progress
            )
        else:
            status, current_progress = result

        if is_correct:
            current_progress += 1
            new_status = "В процессе изучения"
            if current_progress >= 5:
                new_status = "Выучено"
            await connection.execute(
                """
                UPDATE user_progress
                SET status = $3, current_progress = $4
                WHERE user_id = $1 AND word_id = $2
                """,
                user_id, word_id, new_status, current_progress
            )
        else:
            await connection.execute(
                """
                UPDATE user_progress
                SET status = $3, current_progress = $4
                WHERE user_id = $1 AND word_id = $2
                """,
                user_id, word_id, "В процессе изучения", 0
            )


async def update_user_statistic(
        pool,
        user_id: int,
        grade_id: int,
        training_time: timedelta,
        correct_answers: int,
        incorrect_answers: int
):
    async with pool.acquire() as connection:
        stat = await connection.fetchrow(
            """
            SELECT * FROM user_statistics WHERE user_id = $1 AND grade_id = $2
            """,
            user_id, grade_id
        )
        if stat:
            await connection.execute(
                """
                UPDATE user_statistics
                SET total_training_time = total_training_time + $3,
                correct_answers = correct_answers + $4,
                incorrect_answers = incorrect_answers + $5
                WHERE user_id = $1 AND grade_id = $2
                """,
                user_id, grade_id, training_time, correct_answers,
                incorrect_answers
            )
        else:
            await connection.execute(
                """
                INSERT INTO user_statistics (user_id, grade_id,
                 total_training_time, correct_answers, incorrect_answers)
                VALUES ($1, $2, $3, $4, $5)
                """,
                user_id, grade_id, training_time, correct_answers,
                incorrect_answers
            )


async def choose_grade_command(message: Message, state: FSMContext, bot: Bot):
    state_data = await state.get_data()
    if "last_message_id" in state_data:
        try:
            await bot.delete_message(message.chat.id,
                                     state_data["last_message_id"])
        except Exception as e:
            print(f"Failed to delete message: {e}")

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Easy", callback_data="grade_Easy")],
        [InlineKeyboardButton(text="Intermediate",
                              callback_data="grade_Intermediate")],
        [InlineKeyboardButton(text="Advanced", callback_data="grade_Advanced")]
    ])
    await message.answer("Выберите уровень сложности",
                         reply_markup=keyboard
                         )


async def process_grade_choice(callback_query: CallbackQuery, pool, bot: Bot,
                               state: FSMContext):
    grade_name = callback_query.data.split("_")[1]
    telegram_id = callback_query.from_user.id
    user_id = await get_user_id(pool, telegram_id)

    async with pool.acquire() as connection:
        grade_id = await connection.fetchval(
            """
            SELECT grade_id FROM grades WHERE grade = $1
            """,
            grade_name
        )

# Возможно удалить бесполеная проверка
    if grade_id is None:
        await bot.send_message(
            telegram_id,
            "Ошибка: Невозможно найти выбранный уровень сложности.")
        return

    state_data = await state.get_data()
    words = await get_user_words(pool, user_id, grade_name,
                                 limit=state_data.get("training_length"))
    if not words:
        await bot.send_message(telegram_id,
                               f"Вы выучили все слова на уровне {grade_name}")
        return

    await state.update_data(user_id=user_id, grade=grade_name,
                            grade_id=grade_id, words=words, index=0)
    sent_message = await bot.send_message(telegram_id,
                                          "Начнем обучение! "
                                          "Запомните слова и их переводы:")
    await state.update_data(last_message_id=sent_message.message_id)
    await show_words(callback_query, state, bot)


async def choose_training_length(message: Message, state: FSMContext,
                                 bot: Bot):
    state_data = await state.get_data()
    if "last_message_id" in state_data:
        try:
            await bot.delete_message(message.chat.id,
                                     state_data["last_message_id"])
        except Exception as e:
            print(f"Failed to delete message: {e}")

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=str(i),
                              callback_data=f"training_length_{i}")] for i in
        range(10, 51, 5)
    ])
    sent_message = await message.answer(
        "Выберите колличество слов тренировки",
        reply_markup=keyboard
    )
    await state.update_data(last_message_id=sent_message.message_id)


async def show_words(callback_query: CallbackQuery, state: FSMContext,
                     bot: Bot):
    state_data = await state.get_data()
    if "last_message_id" in state_data:
        try:
            await bot.delete_message(callback_query.message.chat.id,
                                     state_data["last_message_id"])
        except Exception as e:
            print(f"Failed to delete message: {e}")
    start_index = state_data["index"]
    words = state_data["words"]
    response = ""
    for word in words[start_index:start_index + 5]:
        response += (f"🇬🇧 {word['word'].upper()}  "
                     f"🇷🇺 {word['translation'].upper()}\n")

    buttons = [[(InlineKeyboardButton(text="Далее",
                                      callback_data="next_words"))]]
    if start_index > 0:
        buttons.append([InlineKeyboardButton(
            text="Назад",
            callback_data="back_words")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    sent_message = await callback_query.message.answer(response,
                                                       reply_markup=keyboard)
    await state.update_data(last_message_id=sent_message.message_id)


async def next_words(callback_query: CallbackQuery, state: FSMContext,
                     bot: Bot):
    data = await state.get_data()
    if "last_message_id" in data:
        try:
            await bot.delete_message(callback_query.message.chat.id,
                                     data["last_message_id"])
        except Exception as e:
            print(f"Failed to delete message: {e}")
    if callback_query.data == "back_words":
        data["index"] = max(0, data["index"] - 5)
    else:
        data["index"] += 5

    await state.update_data(index=data["index"])

    if data["index"] < len(data["words"]):
        await show_words(callback_query, state, bot)
    else:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(
                    text="Начать тренировку",
                    callback_data=f"start_training_{data['grade']}"
                )],
                [InlineKeyboardButton(
                    text="Повторить слова",
                    callback_data="repeat_words"
                )]
            ]
        )
        sent_message = await callback_query.message.answer(
            "Все слова были показаны. Готовы начать тренировку?",
            reply_markup=keyboard)
        await state.update_data(last_message_id=sent_message.message_id)


async def start_training(callback_query: CallbackQuery, pool, bot: Bot,
                         state: FSMContext, main_menu):
    data = await state.get_data()
    if "last_message_id" in data:
        try:
            await bot.delete_message(callback_query.message.chat.id,
                                     data["last_message_id"])
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
    await bot.send_message(callback_query.from_user.id,
                           "Начнем тренировку!",
                           reply_markup=hide_keyboard)
    await show_training_word(callback_query, state, pool, bot, main_menu)


async def finish_training(callback_query: CallbackQuery, state: FSMContext,
                          pool, bot: Bot, main_menu):
    state_data = await state.get_data()
    last_message_id = state_data.get("last_message_id")
    if last_message_id:
        try:
            await bot.delete_message(callback_query.message.chat.id,
                                     last_message_id)
        except Exception as e:
            print(f"Failed to delete message: {e}")

    correct_answers = state_data.get("correct_answers", 0)
    incorrect_answers = state_data.get("incorrect_answers", 0)
    elapsed = timedelta(0)

    if "start_time" in state_data:
        state_time = state_data["start_time"]
        elapsed = datetime.utcnow() - state_time

    elapsed_str = str(elapsed).split('.')[0]

    response = (f"Тренировка завершена!\n"
                f"Правильных ответов: {correct_answers}\n"
                f"Ошибок: {incorrect_answers}\n"
                f"Время тренировки: {elapsed_str}")

    grade_id = state_data.get("grade_id")
    user_id = state_data.get("user_id")
    training_time = elapsed

    await update_user_statistic(
        pool,
        user_id,
        grade_id,
        training_time,
        correct_answers,
        incorrect_answers
    )

    await bot.send_message(callback_query.from_user.id, response,
                           reply_markup=main_menu)
    await state.clear()


async def show_training_word(callback_query: CallbackQuery, state: FSMContext,
                             pool, bot: Bot, main_menu):
    data = await state.get_data()
    if "last_message_id" in data:
        try:
            await bot.delete_message(callback_query.message.chat.id,
                                     data["last_message_id"])
        except Exception as e:
            print(f"Failed to delete message: {e}")
    index = data["training_index"]

    if index >= len(data["training_words"]):
        await finish_training(callback_query, state, pool,
                              bot, main_menu)
        return

    word = data["training_words"][index]
    correct_translation = word["translation"]
    all_translations = [w["translation"] for w in data["training_words"] if
                        w["word_id"] != word["word_id"]]
    random.shuffle(all_translations)
    options = all_translations[:7] + [correct_translation]
    random.shuffle(options)

    keyboard = InlineKeyboardMarkup(row_width=2, inline_keyboard=[
        [InlineKeyboardButton(
            text=option,
            callback_data=f"answer_{word['word_id']}_{option}"
        )
            for option in
            options[:2]],
        [InlineKeyboardButton(
            text=option,
            callback_data=f"answer_{word['word_id']}_{option}"
        )
            for option in
            options[2:4]],
        [InlineKeyboardButton(
            text=option,
            callback_data=f"answer_{word['word_id']}_{option}"
        )
            for option in
            options[4:6]],
        [InlineKeyboardButton(
            text=option,
            callback_data=f"answer_{word['word_id']}_{option}"
        )
            for option in
            options[6:8]],
        [InlineKeyboardButton(
            text="Пропустить слово",
            callback_data=f"answer_{word['word_id']}_unknown"
        )],
        [InlineKeyboardButton(
            text="Завершить тренировку",
            callback_data="finish_training"
        )],
        [InlineKeyboardButton(
            text="Сообщить об ошибке",
            callback_data=f"report_error_{word['word_id']}"
        )]
    ])

    sent_message = await callback_query.message.answer(
        f"Переведите слово:\n⚪ *{word['word'].upper()}*",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await state.update_data(last_message_id=sent_message.message_id)


async def handle_answer(callback_query: CallbackQuery, pool, state: FSMContext,
                        bot: Bot, main_menu):
    data = callback_query.data.split("_")
    chosen_translation = data[2]

    state_data = await state.get_data()
    training_index = state_data["training_index"]

    if training_index >= len(state_data["training_words"]):
        await finish_training(callback_query, state, pool,
                              bot, main_menu)
        return

    current_word = state_data["training_words"][training_index]
    is_correct = chosen_translation == current_word["translation"]

    await update_word_status(pool,
                             state_data["user_id"],
                             current_word["word_id"],
                             is_correct
                             )

    if chosen_translation == "unknown":
        response = (f"⚪ Пропушено: {current_word['word'].upper()} \\- "
                    f"{current_word['translation'].upper()}")
        state_data["incorrect_answers"] = state_data.get("incorrect_answers",
                                                         0) + 1
    elif chosen_translation == current_word["translation"]:
        state_data["correct_answers"] = state_data.get("correct_answers",
                                                       0) + 1
        response = (f"🟢 {current_word['word'].upper()} \\- "
                    f"{current_word['translation'].upper()}")
    else:
        state_data["incorrect_answers"] = state_data.get("incorrect_answers",
                                                         0) + 1
        response = (f"🔴 ~{chosen_translation.upper()}~ "
                    f"{current_word['word'].upper()} \\- "
                    f"{current_word['translation'].upper()}")
    await callback_query.message.answer(f"{response}",
                                        parse_mode="MarkdownV2")

    state_data["training_index"] += 1
    await state.update_data(
        training_index=state_data["training_index"],
        correct_answers=state_data["correct_answers"],
        incorrect_answers=state_data["incorrect_answers"]
    )

    await show_training_word(callback_query, state, pool, bot, main_menu)


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
