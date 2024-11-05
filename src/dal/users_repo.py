from src.database import get_db_connection, release_db_connection


class UsersRepository:
    """Repository for users table."""

    @staticmethod
    def get_user_by_id(telegram_user_id):
        """Gets user by his telegram ID."""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM users WHERE telegram_user_id = %s",
                    (telegram_user_id,),
                )
                return cursor.fetchone()
        finally:
            release_db_connection(conn)

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
        conn = get_db_connection()
        try:
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
        finally:
            release_db_connection(conn)

    @staticmethod
    def update_username(telegram_user_id, new_username):
        """Updates a user's username by his telegram ID."""
        conn = get_db_connection()
        try:
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
        finally:
            release_db_connection(conn)

    @staticmethod
    def update_goal(telegram_user_id, new_goal):
        """Updates a user's goal by his telegram ID."""
        conn = get_db_connection()
        try:
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
        finally:
            release_db_connection(conn)
