from aiogram import BaseMiddleware
from datetime import datetime
from english_words_learning_bot.database import update_last_activity


class LastActivityMiddleware(BaseMiddleware):
    def __init__(self, pool):
        self.pool = pool
        super().__init__()

    async def __call__(self, handler, event, data):
        telegram_id = None
        if event.callback_query:
            telegram_id = event.callback_query.from_user.id
        elif event.message:
            telegram_id = event.message.from_user.id
        await update_last_activity(self.pool, telegram_id)
        return await handler(event, data)
