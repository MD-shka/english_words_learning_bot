from aiogram import Dispatcher, Bot
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from english_words_learning_bot.keyboards import main_menu
import english_words_learning_bot.edu_tools.params_training as params_training
import english_words_learning_bot.edu_tools.training as training


def register_learn_handlers(dp: Dispatcher, bot: Bot, config):
    @dp.message(Command('learn'))
    async def choose_grade_command(message: Message, state: FSMContext):
        await params_training.choose_grade_command(message, state, bot)

    @dp.callback_query(lambda c: c.data.startswith('training_length_'))
    async def process_training_length_choice(callback_query: CallbackQuery,
                                             state: FSMContext):
        pool = dp.get("pool")
        telegram_id = callback_query.message.from_user.id
        training_length = int(callback_query.data.split("_")[2])
        await state.update_data(training_length=training_length)
        await bot.delete_message(
            callback_query.message.chat.id,
            callback_query.message.message_id
        )
        await choose_grade_command(callback_query.message, state)

    @dp.message(Command('start_training'))
    async def choose_training_length_command(message: Message,
                                             state: FSMContext):
        await params_training.choose_training_length(message, state, bot)

    @dp.callback_query(lambda c: c.data == 'start_training_from_notification')
    async def choose_training_length_from_notification(
            callback_query: CallbackQuery,
            state: FSMContext
    ):
        await bot.delete_message(chat_id=callback_query.from_user.id,
                                 message_id=callback_query.message.message_id)
        await params_training.choose_training_length(callback_query.message,
                                                     state, bot)

    @dp.callback_query(lambda c: c.data.startswith('grade_'))
    async def process_grade_choice(callback_query: CallbackQuery,
                                   state: FSMContext):
        pool = dp.get("pool")
        await bot.delete_message(
            callback_query.message.chat.id,
            callback_query.message.message_id
        )
        await training.process_grade_choice(callback_query, pool, bot, state)

    @dp.callback_query(lambda c:
                       c.data.startswith('next_words')
                       or c.data.startswith('back_words'))
    async def next_words(callback_query: CallbackQuery, state: FSMContext):
        await bot.delete_message(
            callback_query.message.chat.id,
            callback_query.message.message_id
        )
        await training.next_words(callback_query, state, bot)

    @dp.callback_query(lambda c: c.data.startswith('repeat_word'))
    async def repeat_word(callback_query: CallbackQuery, state: FSMContext):
        await bot.delete_message(
            callback_query.message.chat.id,
            callback_query.message.message_id
        )
        await state.update_data(index=0)
        telegram_id = callback_query.from_user.id
        state_data = await state.get_data()
        sent_message_word_translate = await bot.send_message(
            telegram_id,
            state_data["sent_message_word_translate_text"])

        await state.update_data(
            sent_message_word_translate_id=sent_message_word_translate.message_id,
            sent_message_word_translate_text=sent_message_word_translate.text)

        await training.show_words(callback_query, state, bot)

    @dp.callback_query(lambda c: c.data.startswith('start_training_'))
    async def start_training(callback_query: CallbackQuery, bot: Bot,
                             state: FSMContext):
        pool = dp.get("pool")
        await training.start_training(callback_query, pool,
                                      bot, state, main_menu)

    @dp.callback_query(lambda c: c.data.startswith("answer_"))
    async def handle_answer(callback_query: CallbackQuery, state: FSMContext):
        pool = dp.get("pool")

        await bot.delete_message(
            callback_query.message.chat.id,
            callback_query.message.message_id
        )
        await training.handle_answer(callback_query, pool,
                                     state, bot, main_menu)

    @dp.callback_query(lambda c: c.data.startswith("finish_training"))
    async def finish_training(callback_query: CallbackQuery,
                              state: FSMContext):
        pool = dp.get("pool")
        await training.finish_training(callback_query, state, pool,
                                       bot, main_menu)

    @dp.callback_query(lambda c: c.data.startswith("report_error_"))
    async def report_error(callback_query: CallbackQuery,
                           state: FSMContext):
        word_id = int(callback_query.data.split("_")[2])
        pool = dp.get("pool")

        async with pool.acquire() as connection:
            word_info = await connection.fetchrow(
                """
                SELECT word, translation
                FROM dictionary
                WHERE word_id = $1
                """,
                word_id
            )

            admin_message = (
                f"Получена жалоба на слово:\n"
                f"ID слова: {word_id}\n"
                f"Слово: {word_info['word']}\n"
                f"Перевод: {word_info['translation']}\n"
            )

        await bot.send_message(config['ADMIN_ID'], admin_message)
        await bot.delete_message(callback_query.message.chat.id,
                                 callback_query.message.message_id)
        await bot.send_message(callback_query.from_user.id,
                               "Ваша жалоба была отправлена. "
                               "Спасибо за вашу помощь!",
                               reply_markup=ReplyKeyboardRemove())
        await training.show_training_word(callback_query, state, pool,
                                          bot, main_menu)

    dp["choose_training_length_command"] = choose_training_length_command
