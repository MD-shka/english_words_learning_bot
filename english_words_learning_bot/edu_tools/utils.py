async def delete_last_message(bot, chat_id, last_message_id):
    try:
        await bot.delete_message(chat_id, last_message_id)
    except Exception as e:
        print(f"Failed to delete message: {e}")
