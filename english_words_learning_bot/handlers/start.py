from aiogram import Dispatcher, Bot
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from english_words_learning_bot.database import add_user
from english_words_learning_bot.keyboards import main_menu
from english_words_learning_bot.edu_tools.utils import delete_last_message


def register_start_handlers(dp: Dispatcher, bot: Bot):
    @dp.message(Command('start'))
    async def start_command(message: Message, state: FSMContext):
        pool = dp.get("pool")
        telegram_id = message.from_user.id
        username = message.from_user.username

        state_data = await state.get_data()
        if "last_message_id" in state_data:
            await delete_last_message(bot, message.chat.id,
                                      state_data["last_message_id"])

        await add_user(pool, telegram_id, username)
        await message.answer(
            f'Выберите пункт меню:',
            reply_markup=main_menu
        )
