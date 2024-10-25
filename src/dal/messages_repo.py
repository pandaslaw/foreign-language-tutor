from src.database import get_db_connection, release_db_connection


class MessagesRepository:
    """Repository for conversation_history table."""

    def save_message(self, user_id, message_type, message_text, token_count=0):
        """Saves a user message."""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO conversation_history (user_id, message_type, message_text, token_count)
                    VALUES (%s, %s, %s, %s);
                    """,
                    (user_id, message_type, message_text, token_count),
                )
                conn.commit()
        finally:
            release_db_connection(conn)

    def get_recent_messages(self, user_id, limit=50):
        """Gets last N user messages."""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT message_text
                    FROM conversation_history
                    WHERE user_id = %s
                    ORDER BY timestamp DESC
                    LIMIT %s;
                    """,
                    (user_id, limit),
                )
                return [row[0] for row in cursor.fetchall()]
        finally:
            release_db_connection(conn)
