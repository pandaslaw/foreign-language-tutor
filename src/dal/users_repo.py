import logging
from typing import Optional, Dict, Any

from src.database import get_db_connection

logger = logging.getLogger(__name__)

class UsersRepository:
    """Repository for users table."""

    @staticmethod
    def get_user_by_id(telegram_user_id) -> Optional[Dict[str, Any]]:
        """Gets user by his telegram ID.
        Returns:
            dict: User data with keys:
                - telegram_user_id (int)
                - username (str)
                - first_name (str)
                - last_name (str)
                - native_language (str)
                - target_language (str)
                - created_at (datetime)
                - updated_at (datetime)
        """
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT * FROM users 
                        WHERE telegram_user_id = %s
                        """,
                        (telegram_user_id,),
                    )
                    row = cursor.fetchone()
                    if row:
                        return {
                            "id": row[0],
                            "username": row[1],
                            "telegram_user_id": row[2],
                            "native_language": row[3],
                            "target_language": row[4],
                            "current_level": row[5],
                            "target_level": row[6],
                            "learning_goal": row[7],
                            "weekly_hours": row[8],
                            "created_at": row[9],
                            "updated_at": row[10],
                        }
                    return None
        except Exception as e:
            logger.error(f"Error getting user {telegram_user_id}: {e}")
            return None

    @staticmethod
    def create_user(
        username,
        telegram_user_id,
        native_language,
        target_language,
        current_level,
        target_level="",
        learning_goal="",
        weekly_hours=6,
    ):
        """Creates a new user."""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO users (username, telegram_user_id, native_language, target_language, current_level, target_level, learning_goal, weekly_hours)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id;
                        """,
                        (
                            username,
                            telegram_user_id,
                            native_language,
                            target_language,
                            current_level,
                            target_level,
                            learning_goal,
                            weekly_hours,
                        ),
                    )
                    conn.commit()
                    return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Error creating user {telegram_user_id}: {e}")
            return None

    @staticmethod
    def update_username(telegram_user_id, new_username):
        """Updates a user's username by his telegram ID."""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        UPDATE users
                        SET username = %s
                        WHERE telegram_user_id = %s;
                        """,
                        (new_username, telegram_user_id),
                    )
                    conn.commit()
        except Exception as e:
            logger.error(f"Error updating username for user {telegram_user_id}: {e}")

    @staticmethod
    def update_goal(telegram_user_id, new_goal):
        """Updates a user's goal by his telegram ID."""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        UPDATE users
                        SET learning_goal = %s
                        WHERE telegram_user_id = %s;
                        """,
                        (new_goal, telegram_user_id),
                    )
                    conn.commit()
        except Exception as e:
            logger.error(f"Error updating goal for user {telegram_user_id}: {e}")
