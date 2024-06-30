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


# Дубль в двух модулях БОТ и ТРЕНИНГ необходимо вынести отдельно как и другие запросы
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
            SELECT d.grade, up.status, COUNT(*) as count
            FROM user_progress up
            JOIN dictionary d ON up.word_id = d.word_id
            WHERE up.user_id = $1
            GROUP BY d.grade, up.status
            ORDER BY d.grade, up.status
            """,
            user_id
        )
        learning_time = await connection.fetchval(
            """
            SELECT learning_time
            FROM users
            WHERE user_id = $1
            """,
            user_id
        )
    return progress, learning_time


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
    progress, learning_time = await get_user_statistics(pool, user_id)

    response = "Ваша статистика:\n\n"
    current_grade = None
    for record in progress:
        grade, status, count = record['grade'], record['status'], record['count']
        if grade != current_grade:
            if current_grade is not None:
                response += "\n"
            current_grade = grade
            response += f"Грейд: {grade}\n"
        response += f"{status.capitalize()}: {count}\n"

    response += f"\nОбщее время обучения: {learning_time}"
    await message.answer(response, reply_markup=main_menu)


@dp.message(Command('learn'))
async def choose_grade_command(message: Message, state: FSMContext):
    await training.choose_grade_command(message, state)


@dp.callback_query(lambda c: c.data.startswith('grade_'))
async def process_grade_choice(callback_query: CallbackQuery, state: FSMContext):
    pool = dp.get("pool")
    await training.process_grade_choice(callback_query, pool, bot, state)


@dp.callback_query(lambda c: c.data.startswith('next_words'))
async def next_words(callback_query: CallbackQuery, state: FSMContext):
    await training.next_words(callback_query, state, bot)


@dp.callback_query(lambda c: c.data.startswith('start_training_'))
async def start_training(callback_query: CallbackQuery, state: FSMContext):
    pool = dp.get("pool")
    await training.start_training(callback_query, pool, bot, state)


@dp.callback_query(lambda c: c.data.startswith("answer_"))
async def handle_answer(callback_query: CallbackQuery, state: FSMContext):
    await training.handle_answer(callback_query, state, bot)


@dp.message()
async def handle_all_messages(message: Message, state: FSMContext):
    pool = dp.get("pool")
    telegram_id = message.from_user.id

    await update_last_activity(pool, telegram_id)

    if message.text == "Учиться":
        await choose_grade_command(message, state)
    elif message.text == "Прогресс":
        await stats_command(message)


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
                    f'Вас не было более 24 часов. Пора продолжить обучение!'
                )
            await asyncio.sleep(900)  # 15 minutes


async def main():
    if os.path.exists(LOCK_FILE):
        print("Another instance of the bot is already running.")
        return

    # Создаем файл блокировки
    open(LOCK_FILE, 'w').close()

    pool = await create_pool()
    dp["pool"] = pool
    asyncio.create_task(check_inactivity(pool))

    def cleanup():
        print("Cleaning up...")
        os.remove(LOCK_FILE)
        asyncio.create_task(pool.close())

    # Обработка сигналов завершения
    for signame in {'SIGINT', 'SIGTERM'}:
        signal.signal(getattr(signal, signame), lambda signum, frame: asyncio.create_task(cleanup()))

    try:
        await dp.start_polling(bot)
    finally:
        await pool.close()
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)

if __name__ == '__main__':
    asyncio.run(main())
