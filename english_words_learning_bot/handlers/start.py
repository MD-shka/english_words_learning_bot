from aiogram import Dispatcher, Bot
from aiogram.types import Message
from aiogram.filters import Command
from english_words_learning_bot.database import add_user
from english_words_learning_bot.keyboards import main_menu


def register_start_handlers(dp: Dispatcher, bot: Bot):
    @dp.message(Command('start'))
    async def start_command(message: Message):
        pool = dp.get("pool")
        telegram_id = message.from_user.id
        username = message.from_user.username

        await add_user(pool, telegram_id, username)
        await message.answer(
            f'Удачи в изучении слов!',
            reply_markup=main_menu
        )
