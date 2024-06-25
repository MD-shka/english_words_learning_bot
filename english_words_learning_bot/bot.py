import os
import asyncio
import asyncpg
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import Command
from dotenv import load_dotenv


load_dotenv()

API_TOKEN = os.getenv('API_TOKEN')
POSTGRES_USER = os.getenv('POSTGRES_USER')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD')
POSTGRES_DB = os.getenv('POSTGRES_DB')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')

bot = Bot(token=API_TOKEN)
dp = Dispatcher()


@dp.message(Command("start"))
async def start_command(message: Message):
    await message.answer("Hello! Bot is working!")


async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


@dp.message(Command("show_dictionary"))
async def get_dictionary(message: Message):
    conn = await asyncpg.connect(
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        database=POSTGRES_DB,
        host=DB_HOST,
        port=DB_PORT
    )
    dictionary = await conn.fetch('SELECT * FROM dictionary')
    await message.answer(str(dictionary))
    await conn.close()

if __name__ == '__main__':
    asyncio.run(main())
