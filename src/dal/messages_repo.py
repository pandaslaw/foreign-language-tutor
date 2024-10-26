from src.database import get_db_connection, release_db_connection


class MessagesRepository:
    """Repository for conversation_history table."""

    @staticmethod
    def save_message(user_id, message_text, is_llm=False):
        """Saves a user message."""
        message_type = "bot" if is_llm else "user"

        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO message_history (telegram_user_id, message_type, message_text)
                    VALUES (%s, %s, %s);
                    """,
                    (user_id, message_type, message_text),
                )
                conn.commit()
        finally:
            release_db_connection(conn)

    @staticmethod
    def get_recent_messages(user_id, limit=50):
        """Gets last N user messages."""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT message_type, message_text
                    FROM message_history
                    WHERE user_id = %s
                    ORDER BY timestamp DESC
                    LIMIT %s;
                    """,
                    (user_id, limit),
                )
                rows = cursor.fetchall()
                return [{"role": row[0], "content": row[1]} for row in rows]
                # return [row[0] for row in cursor.fetchall()]
        finally:
            release_db_connection(conn)
