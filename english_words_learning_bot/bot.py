import os
import asyncio
import asyncpg
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import Command
from dotenv import load_dotenv
from datetime import datetime, timedelta


load_dotenv()

API_TOKEN = os.getenv('API_TOKEN')
POSTGRES_USER = os.getenv('POSTGRES_USER')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD')
POSTGRES_DB = os.getenv('POSTGRES_DB')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')

bot = Bot(token=API_TOKEN)
dp = Dispatcher()


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


@dp.message(Command('start'))
async def start_command(message: Message):
    pool = dp.get("pool")
    telegram_id = message.from_user.id
    username = message.from_user.username

    await add_user(pool, telegram_id, username)
    await message.answer(f'Good luck learning the words!\nУдачи в изучении слов!')


@dp.message()
async def handle_all_messages(message: Message):
    pool = dp.get("pool")
    telegram_id = message.from_user.id
    await update_last_activity(pool, telegram_id)


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
                    f'You have been inactive for more than 24 hours. '
                    f'It is time to continue learning!\n'
                    f'Вас не было более 24 часов. Пора продолжить обучение!'
                )
            await asyncio.sleep(900)  # 15 minutes


async def main():
    pool = await create_pool()
    dp["pool"] = pool
    asyncio.create_task(check_inactivity(pool))
    try:
        await dp.start_polling(bot)
    finally:
        await pool.close()

if __name__ == '__main__':
    asyncio.run(main())
