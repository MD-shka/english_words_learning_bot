CREATE TABLE IF NOT EXISTS users (
    user_id SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    username VARCHAR(50) NOT NULL,
    reminder_time TIME,
    last_activity TIMESTAMP
);

CREATE TABLE IF NOT EXISTS dictionary  (
    word_id SERIAL PRIMARY KEY,
    word VARCHAR(50) UNIQUE NOT NULL,
    translation VARCHAR(50) NOT NULL,
    grade VARCHAR(50) NOT NULL
);

CREATE TABLE IF NOT EXISTS user_progress (
    user_id INT REFERENCES users(user_id),
    word_id INT REFERENCES dictionary (word_id),
    status VARCHAR(50) CHECK (status IN (
                                         'Новое слово',
                                         'В процессе изучения',
                                         'Выучено'
                                        )
        ),
    UNIQUE (user_id, word_id)
);
