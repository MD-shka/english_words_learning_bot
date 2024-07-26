import os
import asyncio
from datetime import datetime, timedelta
from keyboards import notation_keyboard


async def delete_last_message(bot, chat_id, last_message_id):
    try:
        await bot.delete_message(chat_id, last_message_id)
    except Exception as e:
        print(f"Failed to delete message: {e}")


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
                    current_activity = await connection.fetchval(
                        """
                        SELECT last_activity
                        FROM users
                        WHERE telegram_id = $1
                        """,
                        user['telegram_id']
                    )
                    if current_activity < inactive_threshold:
                        await bot.send_message(
                            user['telegram_id'],
                            f'Вас давно не было. Пора продолжить обучение!',
                            reply_markup=await notation_keyboard()
                        )
            await asyncio.sleep(300)  # 5 minutes
