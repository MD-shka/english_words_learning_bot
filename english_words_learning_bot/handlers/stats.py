from aiogram import Dispatcher, Bot
from aiogram.types import Message
from aiogram.filters import Command
from english_words_learning_bot.database import (
    get_user_id,
    get_user_statistics
)
from english_words_learning_bot.keyboards import main_menu


def register_stats_handlers(dp: Dispatcher, bot: Bot):
    @dp.message(Command('stats'))
    async def stats_command(message: Message):
        pool = dp.get("pool")
        telegram_id = message.from_user.id

        user_id = await get_user_id(pool, telegram_id)
        (
            progress,
            learning_time,
            total_answers,
            correct_percentage,
            total_words_by_grade
        ) = await get_user_statistics(pool, user_id)

        total_words_dict = {record['grade']: record['total_words']
                            for record in total_words_by_grade}

        response = "Ваша статистика:\n\n"
        for record in progress:
            grade, status, count = (
                record['grade'], record['status'], record['count']
            )
            total_words = total_words_dict.get(grade, 0)
            response += f"Грейд {grade}:\n"
            response += (f"  {status.capitalize()}: {count} из "
                         f"{total_words} слов\n\n")

        response += (f"Общее время обучения: "
                     f"{learning_time}").rsplit('.', 1)[0]
        response += f"\nОбщее количество ответов: {total_answers}\n"
        response += f"Процент правильных ответов: {correct_percentage:.2f}%"
        await message.answer(response, reply_markup=main_menu)

    dp["stats_command"] = stats_command
