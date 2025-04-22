import time
import logging
from contextlib import contextmanager
from typing import Optional

from psycopg2 import pool, OperationalError, InterfaceError

from src.config import app_settings

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds


class DatabaseConnectionError(Exception):
    """Custom exception for database connection errors."""

    pass


class DatabasePool:
    def __init__(self):
        self._pool = None
        self.create_pool()

    def create_pool(self):
        """Creates a new connection pool."""
        try:
            if self._pool is not None:
                try:
                    self._pool.closeall()
                except Exception as e:
                    logger.warning(f"Error closing existing pool: {e}")

            self._pool = pool.SimpleConnectionPool(
                minconn=1, maxconn=10, dsn=app_settings.DB_CONNECTION_STRING
            )
            logger.info("Created new database connection pool")
        except Exception as e:
            logger.error(f"Error creating connection pool: {e}")
            raise DatabaseConnectionError("Could not create database pool") from e

    def get_connection(
        self, retries: int = MAX_RETRIES
    ) -> Optional[pool.AbstractConnectionPool]:
        """Gets a connection from the pool with retry logic."""
        last_error = None
        for attempt in range(retries):
            try:
                if self._pool is None:
                    self.create_pool()
                return self._pool.getconn()
            except (OperationalError, InterfaceError) as e:
                last_error = e
                logger.warning(f"Database connection attempt {attempt + 1} failed: {e}")
                if attempt < retries - 1:
                    time.sleep(RETRY_DELAY * (attempt + 1))  # Exponential backoff
                    try:
                        self.create_pool()  # Try to recreate the pool
                    except Exception as pool_error:
                        logger.error(f"Error recreating pool: {pool_error}")
            except Exception as e:
                logger.error(f"Unexpected error getting database connection: {e}")
                raise DatabaseConnectionError(
                    "Could not get database connection"
                ) from e

        logger.error(f"All {retries} database connection attempts failed")
        raise DatabaseConnectionError(
            "Could not establish database connection after retries"
        ) from last_error

    def release_connection(self, conn):
        """Releases a connection back to the pool."""
        try:
            self._pool.putconn(conn)
        except Exception as e:
            logger.error(f"Error releasing database connection: {e}")
            # Try to close the connection if we can't return it to the pool
            try:
                conn.close()
            except Exception:
                pass


# Global database pool instance
db_pool = DatabasePool()


@contextmanager
def get_db_connection():
    """Context manager for database connections with retry logic."""
    conn = None
    try:
        conn = db_pool.get_connection()
        yield conn
    except Exception as e:
        logger.error(f"Database operation failed: {e}")
        raise
    finally:
        if conn is not None:
            db_pool.release_connection(conn)


def release_db_connection(conn):
    """Legacy function for backward compatibility."""
    db_pool.release_connection(conn)
