import datetime as dt
from typing import List, Dict, Union

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
    def get_recent_messages(
        user_id: int, limit: int = 50
    ) -> List[Dict[str, Union[str, dt.datetime]]]:
        """Gets last N user messages."""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT message_type, message_text, timestamp 
                    FROM message_history
                    WHERE telegram_user_id = %s
                    ORDER BY timestamp DESC
                    LIMIT %s;
                    """,
                    (user_id, limit),
                )

                rows = cursor.fetchall()
                messages_with_role = [
                    {"role": row[0], "content": row[1], "timestamp": row[2]}
                    for row in rows
                ]
                return messages_with_role

        finally:
            release_db_connection(conn)

    @staticmethod
    def join_messages_to_string(messages: List[Dict[str, Union[str, dt.datetime]]]):
        """
        Structure the message history as a dialogue with clear separation between user and assistant messages.
        Groups consecutive messages by the same person and adds separators for clarity.
        """
        if not messages:
            return ""

        dialogue = []
        last_role = None
        current_chunk = ""

        # Process messages, grouping by role
        for msg in messages:
            role = msg["role"]
            content = msg["content"].strip()
            timestamp: dt.datetime = msg["timestamp"]
            timestamp_str = timestamp.isoformat(timespec="seconds")

            if role != last_role and current_chunk:
                # Add the previous chunk to the dialogue with a separator
                dialogue.append(current_chunk)
                current_chunk = ""

            # Append the message content to the current chunk
            prefix = "User" if role == "user" else "You"
            current_chunk += f"{prefix} ({timestamp_str}): {content}\n"

            last_role = role

        if current_chunk:
            dialogue.append(current_chunk)

        return "---\n".join(dialogue)
