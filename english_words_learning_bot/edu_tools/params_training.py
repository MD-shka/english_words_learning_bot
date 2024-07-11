from aiogram import Bot
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from english_words_learning_bot.keyboards import (
    choose_grade_keyboard,
    choose_training_length_keyboard
)
from .utils import delete_last_message


async def choose_grade_command(message: Message, state: FSMContext,
                               bot: Bot):
    state_data = await state.get_data()

    if "last_message_id" in state_data:
        await delete_last_message(bot, message.chat.id,
                                  state_data["last_message_id"])

    await message.answer("Уровень сложности",
                         reply_markup=choose_grade_keyboard
                         )


async def choose_training_length(message: Message, state: FSMContext,
                                 bot: Bot):
    state_data = await state.get_data()

    if "last_message_id" in state_data:
        await delete_last_message(bot, message.chat.id,
                                  state_data["last_message_id"])

    await bot.send_message(
        chat_id=message.chat.id,
        text="Выберите параметры тренировки:",
        reply_markup=ReplyKeyboardRemove()
    )

    sent_message = await message.answer(
        "Колличество слов тренировки",
        reply_markup=choose_training_length_keyboard
    )
    await state.update_data(last_message_id=sent_message.message_id)
