CREATE TABLE Messages
(
    id             SERIAL PRIMARY KEY,
    chat_id        NUMERIC,
    sender_tg_id   NUMERIC,
    status         VARCHAR(15),
    message_text   TEXT,
    sent_date_time TIMESTAMP
);