import asyncpg
from datetime import datetime


async def create_pool(config):
    return await asyncpg.create_pool(
        user=config['POSTGRES_USER'],
        password=config['POSTGRES_PASSWORD'],
        database=config['POSTGRES_DB'],
        host=config['DB_HOST'],
        port=config['DB_PORT']
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
            SELECT g.grade_id, g.grade, up.status, COUNT(*) as count
            FROM user_progress up
            JOIN dictionary d ON up.word_id = d.word_id
            JOIN grades g ON d.grade_id = g.grade_id
            WHERE up.user_id = $1
            GROUP BY g.grade_id, g.grade, up.status
            ORDER BY g.grade_id, g.grade, up.status
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
