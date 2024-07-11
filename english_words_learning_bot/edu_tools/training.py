import random
from datetime import datetime, timedelta
from aiogram import Bot
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from english_words_learning_bot.database import (
    get_user_id,
    get_user_words,
    update_word_status,
    update_user_statistic,
)
from english_words_learning_bot.edu_tools.utils import delete_last_message
from english_words_learning_bot.keyboards import (
    navigation_keyboard,
    start_training_keyboard,
    show_training_word_keyboard,
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

    state_data = await state.get_data()
    words = await get_user_words(pool, user_id, grade_name,
                                 limit=state_data.get("training_length"))
    if not words:
        await bot.send_message(telegram_id,
                               f"Вы выучили все слова "
                               f"на уровне {grade_name}")
        return

    await state.update_data(user_id=user_id, grade=grade_name,
                            grade_id=grade_id, words=words, index=0)

    sent_message = await bot.send_message(telegram_id,
                                          "Начнем обучение! "
                                          "Запомните слова и их переводы:")
    await state.update_data(last_message_id=sent_message.message_id)
    await show_words(callback_query, state, bot)


async def show_words(callback_query: CallbackQuery, state: FSMContext,
                     bot: Bot):
    state_data = await state.get_data()
    if "last_message_id" in state_data:
        await delete_last_message(bot, callback_query.message.chat.id,
                                  state_data["last_message_id"])
    start_index = state_data["index"]
    words = state_data["words"]
    response = ""
    for word in words[start_index:start_index + 5]:
        response += (f"🇬🇧 {word['word'].upper()}  "
                     f"🇷🇺 {word['translation'].upper()}\n")

    keyboard = await navigation_keyboard(start_index)
    sent_message = await callback_query.message.answer(response,
                                                       reply_markup=keyboard)

    await state.update_data(last_message_id=sent_message.message_id)


async def next_words(callback_query: CallbackQuery, state: FSMContext,
                     bot: Bot):
    state_data = await state.get_data()
    if "last_message_id" in state_data:
        await delete_last_message(bot, callback_query.message.chat.id,
                                  state_data["last_message_id"])
    if callback_query.data == "back_words":
        state_data["index"] = max(0, state_data["index"] - 5)
    else:
        state_data["index"] += 5

    await state.update_data(index=state_data["index"])

    if state_data["index"] < len(state_data["words"]):
        await show_words(callback_query, state, bot)
    else:
        sent_message = await callback_query.message.answer(
            "Все слова были показаны. Готовы начать тренировку?",
            reply_markup=await start_training_keyboard(state_data["grade"]))
        await state.update_data(last_message_id=sent_message.message_id)


async def start_training(callback_query: CallbackQuery, pool, bot: Bot,
                         state: FSMContext, main_menu):
    state_data = await state.get_data()
    if "last_message_id" in state_data:
        await delete_last_message(bot, callback_query.message.chat.id,
                                  state_data["last_message_id"])

    words = state_data["words"]
    random.shuffle(words)

    await state.update_data(
        training_words=words,
        training_index=0,
        correct_answers=0,
        incorrect_answers=0,
        start_time=datetime.utcnow()
    )
    await bot.send_message(callback_query.from_user.id,
                           "Начнем тренировку!")
    await show_training_word(callback_query, state, pool, bot, main_menu)


async def finish_training(callback_query: CallbackQuery, state: FSMContext,
                          pool, bot: Bot, main_menu):
    state_data = await state.get_data()
    if "last_message_id" in state_data:
        await delete_last_message(bot, callback_query.message.chat.id,
                                  state_data["last_message_id"])

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
    state_data = await state.get_data()
    if "last_message_id" in state_data:
        await delete_last_message(bot, callback_query.message.chat.id,
                                  state_data["last_message_id"])
    index = state_data["training_index"]

    if index >= len(state_data["training_words"]):
        await finish_training(callback_query, state, pool,
                              bot, main_menu)
        return

    word = state_data["training_words"][index]
    correct_translation = word["translation"]
    all_translations = [w["translation"] for w
                        in state_data["training_words"] if
                        w["word_id"] != word["word_id"]]
    random.shuffle(all_translations)
    options = all_translations[:7] + [correct_translation]
    random.shuffle(options)

    keyboard = await show_training_word_keyboard(word["word_id"], options)

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
