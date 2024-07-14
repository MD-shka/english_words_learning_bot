import asyncpg
from datetime import datetime, timedelta


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


async def get_user_words(pool, user_id: int, grade: str, limit: int):
    async with pool.acquire() as connection:
        user_words = await connection.fetch(
            """
            SELECT d.word_id, d.word, d.translation, up.status 
            FROM dictionary d
            LEFT JOIN user_progress up 
            ON d.word_id = up.word_id AND up.user_id = $1
            JOIN grades g ON d.grade_id = g.grade_id
            WHERE g.grade = $2
            ORDER BY RANDOM()
            LIMIT $3
            """,
            user_id, grade, limit
        )
    return user_words


async def update_word_status(pool,
                             user_id: int,
                             word_id: int,
                             is_correct: bool
                             ):
    async with pool.acquire() as connection:
        result = await connection.fetchrow(
            """
            SELECT status, current_progress
            FROM user_progress
            WHERE user_id = $1 AND word_id = $2
            """,
            user_id, word_id
        )

        if result is None:
            status = "Новое слово"
            current_progress = 0
            await connection.execute(
                """
                INSERT INTO user_progress (
                user_id,
                word_id,
                status,
                current_progress
                )
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (user_id, word_id) DO NOTHING 
                """,
                user_id, word_id, status, current_progress
            )
        else:
            status, current_progress = result

        if is_correct:
            current_progress += 1
            new_status = "В процессе изучения"
            if current_progress >= 5:
                new_status = "Выучено"
            await connection.execute(
                """
                UPDATE user_progress
                SET status = $3, current_progress = $4
                WHERE user_id = $1 AND word_id = $2
                """,
                user_id, word_id, new_status, current_progress
            )
        else:
            await connection.execute(
                """
                UPDATE user_progress
                SET status = $3, current_progress = $4
                WHERE user_id = $1 AND word_id = $2
                """,
                user_id, word_id, "В процессе изучения", 0
            )


async def update_user_statistic(
        pool,
        user_id: int,
        grade_id: int,
        training_time: timedelta,
        correct_answers: int,
        incorrect_answers: int
):
    async with pool.acquire() as connection:
        stat = await connection.fetchrow(
            """
            SELECT * FROM user_statistics WHERE user_id = $1 AND grade_id = $2
            """,
            user_id, grade_id
        )
        if stat:
            await connection.execute(
                """
                UPDATE user_statistics
                SET total_training_time = total_training_time + $3,
                correct_answers = correct_answers + $4,
                incorrect_answers = incorrect_answers + $5
                WHERE user_id = $1 AND grade_id = $2
                """,
                user_id, grade_id, training_time, correct_answers,
                incorrect_answers
            )
        else:
            await connection.execute(
                """
                INSERT INTO user_statistics (user_id, grade_id,
                 total_training_time, correct_answers, incorrect_answers)
                VALUES ($1, $2, $3, $4, $5)
                """,
                user_id, grade_id, training_time, correct_answers,
                incorrect_answers
            )


async def update_notafication_interval(pool, telegram_id: int, interval: int):
    async with pool.acquire() as connection:
        await connection.execute(
            """
            UPDATE users
            SET notification_interval = $1
            WHERE telegram_id = $2
            """,
            interval, telegram_id
        )
