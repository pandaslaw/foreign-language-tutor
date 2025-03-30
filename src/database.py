import time
import logging
from contextlib import contextmanager
from typing import Optional, Generator
import ssl

import psycopg2
from psycopg2 import pool, OperationalError, InterfaceError
from psycopg2.extensions import connection as pg_connection

from src.config import app_settings

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds
METRICS = {
    'total_connections': 0,
    'active_connections': 0,
    'connection_errors': 0,
    'query_count': 0
}

class DatabaseConnectionError(Exception):
    """Custom exception for database connection errors."""
    pass

class DatabasePool:
    """Thread-safe database connection pool with monitoring"""
    
    def __init__(self):
        self._pool = None
        self.create_pool()

    def create_pool(self):
        """Creates a new connection pool with secure settings."""
        try:
            if self._pool is not None:
                self.close_all()

            db_config = app_settings.db_config
            
            # Setup SSL context for secure connection
            ssl_context = ssl.create_default_context()
            if app_settings.is_production:
                ssl_context.verify_mode = ssl.CERT_REQUIRED
            
            self._pool = pool.ThreadedConnectionPool(
                minconn=db_config.min_connections,
                maxconn=db_config.max_connections,
                host=db_config.host,
                port=db_config.port,
                database=db_config.database,
                user=db_config.user,
                password=db_config.password,
                sslmode=db_config.ssl_mode,
                sslcert=None,  # Add your SSL cert path in production
                connect_timeout=db_config.connection_timeout,
                application_name=db_config.application_name,
                keepalives=1,
                keepalives_idle=db_config.idle_timeout
            )
            
            logger.info(
                f"Created new database pool: min={db_config.min_connections}, "
                f"max={db_config.max_connections}, ssl={db_config.ssl_mode}"
            )
            
        except Exception as e:
            METRICS['connection_errors'] += 1
            logger.error(f"Error creating connection pool: {e}")
            raise DatabaseConnectionError("Could not create database pool") from e

    def get_connection(self, retries: int = MAX_RETRIES) -> Optional[pg_connection]:
        """Gets a connection from the pool with retry logic and monitoring."""
        last_error = None
        
        for attempt in range(retries):
            try:
                if self._pool is None:
                    self.create_pool()
                    
                conn = self._pool.getconn()
                METRICS['total_connections'] += 1
                METRICS['active_connections'] += 1
                
                # Set session parameters for security
                with conn.cursor() as cur:
                    cur.execute("SET SESSION statement_timeout = '30s';")
                    if app_settings.is_production:
                        cur.execute("SET SESSION ssl_min_protocol_version = 'TLSv1.2';")
                
                return conn
                
            except (OperationalError, InterfaceError) as e:
                last_error = e
                METRICS['connection_errors'] += 1
                logger.warning(f"Connection attempt {attempt + 1} failed: {e}")
                
                if attempt < retries - 1:
                    time.sleep(RETRY_DELAY * (attempt + 1))
                    self.create_pool()  # Try recreating the pool
                    
        logger.error(f"Failed to get connection after {retries} attempts: {last_error}")
        raise DatabaseConnectionError(f"Could not get database connection: {last_error}")

    def return_connection(self, conn: pg_connection):
        """Returns a connection to the pool."""
        if conn and self._pool:
            self._pool.putconn(conn)
            METRICS['active_connections'] -= 1

    def close_all(self):
        """Closes all connections in the pool."""
        try:
            if self._pool:
                self._pool.closeall()
                logger.info("Closed all database connections")
        except Exception as e:
            logger.error(f"Error closing connection pool: {e}")
        finally:
            METRICS['active_connections'] = 0

# Global database pool instance
db_pool = DatabasePool()

@contextmanager
def get_db_connection() -> Generator[pg_connection, None, None]:
    """Context manager for database connections with monitoring."""
    conn = None
    try:
        conn = db_pool.get_connection()
        METRICS['query_count'] += 1
        yield conn
    finally:
        if conn:
            db_pool.return_connection(conn)

def get_db_metrics() -> dict:
    """Get current database metrics."""
    return METRICS.copy()

def cleanup_db():
    """Cleanup database connections on shutdown."""
    db_pool.close_all()
