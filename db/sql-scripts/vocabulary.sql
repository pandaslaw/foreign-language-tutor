CREATE TABLE vocabulary (
    id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(telegram_user_id),
    word VARCHAR(255) NOT NULL,
    translation VARCHAR(255) NOT NULL,
    category VARCHAR(50),
    mastery_level INTEGER DEFAULT 0,
    last_reviewed TIMESTAMP WITH TIME ZONE,
    next_review TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
