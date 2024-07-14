from aiogram import Dispatcher, Bot
from aiogram.types import Message
from aiogram.filters import Command
from english_words_learning_bot.database import update_notafication_interval
from english_words_learning_bot.keyboards import (
    notification_interval_keyboard,
    main_menu
)
from english_words_learning_bot.edu_tools.utils import delete_last_message


def register_settings_handlers(dp: Dispatcher, bot: Bot):
    @dp.message(Command('settings'))
    async def settings_command(message: Message):
        await message.answer(
            'Через сколько часов вы хотите получать уведомления?',
            reply_markup=await notification_interval_keyboard())

    @dp.callback_query(lambda c: c.data and
                                 c.data.startswith('notification_interval_'))
    async def prosess_notification_interval(callback_query):
        pool = dp.get("pool")
        interval = int(callback_query.data.split('_')[-1])
        user_id = callback_query.from_user.id
        await update_notafication_interval(pool, user_id, interval)
        await callback_query.message.answer(
            f'Интервал уведомлений обновлен на {interval} часов.',
            reply_markup=main_menu)
        await callback_query.message.delete()

    dp["settings_command"] = settings_command
