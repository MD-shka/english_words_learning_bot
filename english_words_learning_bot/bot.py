import os
import signal
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from middlewares.last_activity_middleware import LastActivityMiddleware
from config import load_config
from database import create_pool
from handlers import register_handlers
from utils import cleanup, check_inactivity

config = load_config()
bot = Bot(token=config['API_TOKEN'])
storage = MemoryStorage()

LOCK_FILE = 'bot.lock'


async def main():
    if os.path.exists(LOCK_FILE):
        print("Another instance of the bot is already running.")
        return

    open(LOCK_FILE, 'w').close()
    pool = await create_pool(config)
    dp = Dispatcher(storage=storage)
    dp["pool"] = pool
    _ = asyncio.create_task(check_inactivity(pool, bot))

    # Update to include the middleware
    dp.update.outer_middleware(LastActivityMiddleware(pool))

    register_handlers(dp, bot, config)

    loop = asyncio.get_event_loop()
    for signame in {'SIGINT', 'SIGTERM'}:
        loop.add_signal_handler(getattr(signal, signame),
                                lambda: asyncio.create_task(cleanup(
                                    pool,
                                    bot,
                                    config['ADMIN_ID']
                                )))
    try:
        await dp.start_polling(bot)
    finally:
        await cleanup(pool, bot, config['ADMIN_ID'])

if __name__ == '__main__':
    asyncio.run(main())
