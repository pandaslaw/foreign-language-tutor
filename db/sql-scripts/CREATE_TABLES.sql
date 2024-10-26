--CREATE DATABASE languagebot;

\c language_bot;

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username TEXT NOT NULL,
    telegram_user_id BIGINT UNIQUE NOT NULL,
    goal TEXT,
    join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE lessons (
    id SERIAL PRIMARY KEY,
    level TEXT CHECK (level IN ('A1', 'A2')) NOT NULL,
    title TEXT NOT NULL,
    description TEXT
);

CREATE TABLE materials (
    id SERIAL PRIMARY KEY,
    lesson_id INT REFERENCES lessons(id) ON DELETE CASCADE,
    material_type TEXT CHECK (material_type IN ('grammar', 'vocabulary', 'example')) NOT NULL,
    content TEXT NOT NULL
);

CREATE TABLE exercises (
    id SERIAL PRIMARY KEY,
    lesson_id INT REFERENCES lessons(id) ON DELETE CASCADE,
    description TEXT NOT NULL,
    resource_link TEXT
);

CREATE TABLE user_progress (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id) ON DELETE CASCADE,
    lesson_id INT REFERENCES lessons(id) ON DELETE CASCADE,
    status TEXT CHECK (status IN ('not started', 'in progress', 'completed')) DEFAULT 'not started',
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE feedback (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id) ON DELETE CASCADE,
    lesson_id INT REFERENCES lessons(id) ON DELETE CASCADE,
    feedback_text TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE message_history (
    id SERIAL PRIMARY KEY,
    telegram_user_id BIGINT NOT NULL,
    session_id UUID DEFAULT gen_random_uuid(),
    message_type TEXT CHECK (message_type IN ('user', 'bot')) NOT NULL,
    message_text TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    token_count INT DEFAULT 0
);

