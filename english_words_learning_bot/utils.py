import os
import asyncio
from datetime import datetime, timedelta


async def cleanup(pool, bot, admin_id):
    print("Cleaning up...")
    await bot.send_message(admin_id, "Бот был остановлен.")
    if os.path.exists('bot.lock'):
        os.remove('bot.lock')
    await pool.close()


async def check_inactivity(pool, bot):
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
