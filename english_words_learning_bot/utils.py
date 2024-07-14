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
        async with pool.acquire() as connection:
            users = await connection.fetch(
                """
                SELECT telegram_id, notification_interval, last_activity
                FROM users
                """,
            )
            for user in users:
                inactive_threshold = datetime.utcnow() - timedelta(
                    hours=user['notification_interval'])
                if user['last_activity'] < inactive_threshold:
                    await bot.send_message(
                        user['telegram_id'],
                        f'Вас давно не было. Пора продолжить обучение!'
                    )
            await asyncio.sleep(300)  # 5 minutes
