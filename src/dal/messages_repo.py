import datetime as dt
from typing import List, Dict, Union
import logging

from src.database import get_db_connection

logger = logging.getLogger(__name__)


class MessagesRepository:
    """Repository for conversation_history table."""

    @staticmethod
    def save_message(user_id, message_text, is_llm=False):
        """Saves a user message."""
        message_type = "bot" if is_llm else "user"

        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO message_history (telegram_user_id, message_type, message_text)
                        VALUES (%s, %s, %s);
                        """,
                        (user_id, message_type, message_text),
                    )
                    conn.commit()
        except Exception as e:
            logger.error(f"Error saving message for user {user_id}: {e}")

    @staticmethod
    def get_recent_messages(
        user_id: int, limit: int = 50
    ) -> List[Dict[str, Union[str, dt.datetime]]]:
        """Gets last N user messages."""
        try:
            with get_db_connection() as conn:
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

        except Exception as e:
            logger.error(f"Error getting messages for user {user_id}: {e}")
            return []

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
