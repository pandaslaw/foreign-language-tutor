CREATE TABLE message_history (
    id SERIAL PRIMARY KEY,
    telegram_user_id BIGINT REFERENCES users(telegram_user_id),
    message_type VARCHAR(10) NOT NULL,
    message_text TEXT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB
);
