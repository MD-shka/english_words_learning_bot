from aiogram import Dispatcher, Bot
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from english_words_learning_bot.database import update_last_activity


def register_general_handlers(dp: Dispatcher, bot: Bot):
    @dp.message()
    async def handle_all_messages(message: Message, state: FSMContext):
        pool = dp.get("pool")
        telegram_id = message.from_user.id

        await update_last_activity(pool, telegram_id)

        if message.text == "Учить слова":
            await message.answer("Начнем учить слова!",
                                 reply_markup=ReplyKeyboardRemove())
            await dp.get("choose_training_length_command")(message, state)
        if message.text == "duel":
            await message.answer("Начнем дуэль!",
                                 reply_markup=ReplyKeyboardRemove())
            await dp.get("duel")(message, state) # pass
        elif message.text == "Прогресс":
            await message.answer("Ваш прогресс:",
                                 reply_markup=ReplyKeyboardRemove())
            await dp.get("stats_command")(message)
        elif message.text == "Рейтинг":
            await message.answer("Лучшие игроки:",
                                 reply_markup=ReplyKeyboardRemove())
            await dp.get("rating")(message) # pass
        elif message.text == "Настройки":
            await message.answer("Установите интервал уведомлений:",
                                 reply_markup=ReplyKeyboardRemove())
            await dp.get("settings_command")(message)
