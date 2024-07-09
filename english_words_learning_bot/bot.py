import os
import signal
import asyncio
import asyncpg
import training
from aiogram import Bot, Dispatcher
from aiogram.types import (
    Message,
    CallbackQuery,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

API_TOKEN = os.getenv('API_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID'))
POSTGRES_USER = os.getenv('POSTGRES_USER')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD')
POSTGRES_DB = os.getenv('POSTGRES_DB')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')

bot = Bot(token=API_TOKEN)
dp = Dispatcher()
storage = MemoryStorage()

LOCK_FILE = 'bot.lock'


async def create_pool():
    return await asyncpg.create_pool(
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        database=POSTGRES_DB,
        host=DB_HOST,
        port=DB_PORT
    )


async def add_user(pool, telegram_id: int, username: str):
    async with pool.acquire() as connection:
        await connection.execute(
            """
            INSERT INTO users (telegram_id, username)
            VALUES ($1, $2)
            ON CONFLICT (telegram_id) DO UPDATE 
            SET username = $2
            """,
            telegram_id, username
        )


async def update_last_activity(pool, telegram_id: int):
    async with pool.acquire() as connection:
        await connection.execute(
            """
            UPDATE users
            SET last_activity = $1
            WHERE telegram_id = $2
            """,
            datetime.utcnow(), telegram_id
        )


async def check_inactivity(pool):
    while True:
        inactive_threshold = datetime.utcnow() - timedelta(hours=24)
        async with pool.acquire() as connection:
            users = await connection.fetch(
                """
                SELECT telegram_id
                FROM users
                WHERE last_activity < $1
                """,
                inactive_threshold
            )
            for user in users:
                await bot.send_message(
                    user['telegram_id'],
                    f'Вас не было более 24 часов. '
                    f'Пора продолжить обучение!'
                )
            await asyncio.sleep(900)  # 15 minutes


# Дубль в двух модулях БОТ и ТРЕНИНГ необходимо вынести отдельно
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


async def get_user_statistics(pool, user_id: int):
    async with pool.acquire() as connection:
        progress = await connection.fetch(
            """
            SELECT g.grade, up.status, COUNT(*) as count
            FROM user_progress up
            JOIN dictionary d ON up.word_id = d.word_id
            JOIN grades g ON d.grade_id = g.grade_id
            WHERE up.user_id = $1
            GROUP BY g.grade, up.status
            ORDER BY g.grade, up.status
            """,
            user_id
        )
        stats = await connection.fetchrow(
            """
            SELECT SUM(total_training_time) as total_training_time,
                   SUM(correct_answers) as correct_answers,
                   SUM(incorrect_answers) as incorrect_answers
            FROM user_statistics
            WHERE user_id = $1
            """,
            user_id
        )
        total_words_by_grade = await connection.fetch(
            """
            SELECT g.grade, COUNT(*) as total_words
            FROM dictionary d
            JOIN grades g ON d.grade_id = g.grade_id
            GROUP BY g.grade
            ORDER BY g.grade
        """
        )
        if stats:
            learning_time = stats['total_training_time']
            total_answers = stats['correct_answers'] + stats[
                'incorrect_answers']
            correct_percentage = (stats[
                                      'correct_answers'
                                  ] / total_answers
                                  * 100) if total_answers > 0 else 0
        else:
            learning_time = None
            total_answers = 0
            correct_percentage = 0
        return (
            progress,
            learning_time,
            total_answers,
            correct_percentage,
            total_words_by_grade
        )


buttons = [
    [KeyboardButton(text="Учиться")],
    [KeyboardButton(text="Прогресс")],
]
main_menu = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


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

    total_words_dict = {record['grade']: record['total_words'] for record in
                        total_words_by_grade}

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


@dp.message(Command('learn'))
async def choose_grade_command(message: Message, state: FSMContext):
    await training.choose_grade_command(message, state, bot)


@dp.callback_query(lambda c: c.data.startswith('training_length_'))
async def process_training_length_choice(callback_query: CallbackQuery,
                                         state: FSMContext):
    training_length = int(callback_query.data.split("_")[2])
    await state.update_data(training_length=training_length)
    await bot.delete_message(
        callback_query.message.chat.id,
        callback_query.message.message_id
    )
    await choose_grade_command(callback_query.message, state)


@dp.message(Command('start_training'))
async def choose_training_length_command(message: Message, state: FSMContext):
    await training.choose_training_length(message, state, bot)


@dp.callback_query(lambda c: c.data.startswith('grade_'))
async def process_grade_choice(callback_query: CallbackQuery,
                               state: FSMContext):
    pool = dp.get("pool")
    await bot.delete_message(
        callback_query.message.chat.id,
        callback_query.message.message_id
    )
    await training.process_grade_choice(callback_query, pool, bot, state)


@dp.callback_query(lambda c: c.data.startswith(
    'next_words') or c.data.startswith('back_words'))
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
    await training.show_words(callback_query, state, bot)


@dp.callback_query(lambda c: c.data.startswith('start_training_'))
async def start_training(callback_query: CallbackQuery, bot: Bot,
                         state: FSMContext):
    pool = dp.get("pool")
    await training.start_training(callback_query, pool, bot, state, main_menu)


@dp.callback_query(lambda c: c.data.startswith("answer_"))
async def handle_answer(callback_query: CallbackQuery, state: FSMContext):
    pool = dp.get("pool")

    await bot.delete_message(
        callback_query.message.chat.id,
        callback_query.message.message_id
    )
    await training.handle_answer(callback_query, pool, state, bot, main_menu)


@dp.callback_query(lambda c: c.data.startswith("finish_training"))
async def finish_training(callback_query: CallbackQuery, state: FSMContext):
    pool = dp.get("pool")
    await training.finish_training(callback_query, state, pool, bot, main_menu)


@dp.callback_query(lambda c: c.data.startswith("report_error_"))
async def report_error(callback_query: CallbackQuery, state: FSMContext):
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

    await bot.send_message(ADMIN_ID, admin_message)
    await bot.delete_message(
        callback_query.message.chat.id,
        callback_query.message.message_id
    )
    await bot.send_message(
        callback_query.from_user.id,
        "Ваша жалоба была отправлена. Спасибо за вашу помощь!",
        reply_markup=main_menu
    )
    await training.show_training_word(callback_query, state, pool,
                                      bot, main_menu)


@dp.message()
async def handle_all_messages(message: Message, state: FSMContext):
    pool = dp.get("pool")
    telegram_id = message.from_user.id

    await update_last_activity(pool, telegram_id)

    if message.text == "Учиться":
        await choose_training_length_command(message, state)
    elif message.text == "Прогресс":
        await stats_command(message)


async def cleanup(pool):
    print("Cleaning up...")
    await bot.send_message(ADMIN_ID, "Бот был остановлен.")
    if os.path.exists(LOCK_FILE):
        os.remove(LOCK_FILE)
    await pool.close()


async def main():
    if os.path.exists(LOCK_FILE):
        print("Another instance of the bot is already running.")
        return

    # Создаем файл блокировки
    open(LOCK_FILE, 'w').close()

    pool = await create_pool()
    dp["pool"] = pool
    _ = asyncio.create_task(check_inactivity(pool))

    # Обработка сигналов завершения
    loop = asyncio.get_event_loop()
    for signame in {'SIGINT', 'SIGTERM'}:
        loop.add_signal_handler(getattr(signal, signame),
                                lambda: asyncio.create_task(cleanup(pool)))
    try:
        await dp.start_polling(bot)
    finally:
        await cleanup(pool)


if __name__ == '__main__':
    asyncio.run(main())
