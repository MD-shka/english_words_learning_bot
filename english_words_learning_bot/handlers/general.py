from aiogram import Dispatcher, Bot
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from english_words_learning_bot.database import update_last_activity


def register_general_handlers(dp: Dispatcher, bot: Bot):
    @dp.message()
    async def handle_all_messages(message: Message, state: FSMContext):
        pool = dp.get("pool")
        telegram_id = message.from_user.id

        await update_last_activity(pool, telegram_id)

        if message.text == "Учиться":
            await dp.get("choose_training_length_command")(message, state)
        elif message.text == "Прогресс":
            await dp.get("stats_command")(message)
