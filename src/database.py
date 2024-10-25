import psycopg2
from psycopg2 import pool

from src.config import app_settings

db_pool = pool.SimpleConnectionPool(minconn=1, maxconn=10, dsn=app_settings.DB_CONNECTION_STRING)

def get_db_connection():
    """Gets db connection from pool."""
    return db_pool.getconn()

def release_db_connection(conn):
    """Realeases db connection."""
    db_pool.putconn(conn)
