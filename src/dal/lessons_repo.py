from src.database import get_db_connection, release_db_connection

class LessonsRepository:
    """Repository for users table."""

    def get_user_by_id(self, user_id):
        """Gets user by his ID."""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
                return cursor.fetchone()
        finally:
            release_db_connection(conn)

    def create_user(self, username, telegram_id):
        """Creates a new user."""
        conn = get_db_connection()
        try:
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
        finally:
            release_db_connection(conn)

    def update_username(self, user_id, new_username):
        """Updates a user's username by his ID."""
        conn = get_db_connection()
        try:
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
        finally:
            release_db_connection(conn)
