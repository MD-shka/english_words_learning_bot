CREATE TABLE IF NOT EXISTS users (
    user_id SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    username VARCHAR(50) NOT NULL,
    reminder_time TIME,
    last_activity TIMESTAMP,
    notification_interval INTEGER DEFAULT 24
);

CREATE TABLE IF NOT EXISTS grades (
    grade_id SERIAL PRIMARY KEY,
    grade VARCHAR(50) UNIQUE NOT NULL
);

INSERT INTO grades (grade) VALUES ('Easy'), ('Intermediate'), ('Advanced');

CREATE TABLE IF NOT EXISTS dictionary  (
    word_id SERIAL PRIMARY KEY,
    grade_id INT REFERENCES grades(grade_id),
    word VARCHAR(50) UNIQUE NOT NULL,
    translation VARCHAR(50) NOT NULL
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
    current_progress SMALLINT,
    UNIQUE (user_id, word_id)
);

CREATE TABLE IF NOT EXISTS user_statistics (
    stat_id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(user_id),
    total_training_time INTERVAL,
    correct_answers INT DEFAULT 0,
    incorrect_answers INT DEFAULT 0,
    grade_id INT NOT NULL REFERENCES grades(grade_id),
    UNIQUE (user_id, grade_id)
);
