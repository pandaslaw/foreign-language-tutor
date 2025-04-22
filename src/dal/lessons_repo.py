from src.database import get_db_connection
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


class LessonsRepository:
    """Repository for users table."""

    def get_user_by_id(self, user_id):
        """Gets user by his ID."""
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
                return cursor.fetchone()

    def create_user(self, username, telegram_id):
        """Creates a new user."""
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO users (username, telegram_id)
                    VALUES (%s, %s) RETURNING id;
                    """,
                    (username, telegram_id),
                )
                conn.commit()
                return cursor.fetchone()[0]

    def update_username(self, user_id, new_username):
        """Updates a user's username by his ID."""
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE users
                    SET username = %s
                    WHERE id = %s;
                    """,
                    (new_username, user_id),
                )
                conn.commit()

    @staticmethod
    def save_lesson(user_id: int, lesson_type: str, content: str) -> Optional[int]:
        """Save lesson to database."""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO lessons (user_id, lesson_type, content)
                        VALUES (%s, %s, %s)
                        RETURNING id
                        """,
                        (user_id, lesson_type, content),
                    )
                    conn.commit()
                    return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Error saving lesson for user {user_id}: {e}")
            return None

    @staticmethod
    def get_user_lessons(user_id: int, limit: int = 10) -> List[tuple]:
        """Get last N lessons for user."""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT id, lesson_type, content, created_at
                        FROM lessons
                        WHERE user_id = %s
                        ORDER BY created_at DESC
                        LIMIT %s
                        """,
                        (user_id, limit),
                    )
                    return cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting lessons for user {user_id}: {e}")
            return []

    @staticmethod
    def get_lesson_by_id(lesson_id: int) -> Optional[tuple]:
        """Get specific lesson by ID."""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT id, user_id, lesson_type, content, created_at
                        FROM lessons
                        WHERE id = %s
                        """,
                        (lesson_id,),
                    )
                    return cursor.fetchone()
        except Exception as e:
            logger.error(f"Error getting lesson {lesson_id}: {e}")
            return None
