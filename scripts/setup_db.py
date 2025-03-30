import os
import sys
import logging
from pathlib import Path

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.config import app_settings

logger = logging.getLogger(__name__)

def read_sql_file(filename: str) -> str:
    """Read SQL file content"""
    sql_path = project_root / 'db' / 'sql-scripts' / filename
    with open(sql_path, 'r', encoding='utf-8') as f:
        return f.read()

def create_database():
    """Create fresh database"""
    db_config = app_settings.db_config
    
    # Connect to postgres database to create new db
    conn = psycopg2.connect(
        host=db_config.host,
        port=db_config.port,
        user=db_config.user,
        password=db_config.password,
        database='postgres'
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    
    try:
        with conn.cursor() as cur:
            # Drop database if exists
            cur.execute(f'DROP DATABASE IF EXISTS {db_config.database}')
            logger.info(f"Dropped database {db_config.database} if it existed")
            
            # Create fresh database
            cur.execute(f'CREATE DATABASE {db_config.database}')
            logger.info(f"Created fresh database {db_config.database}")
    finally:
        conn.close()

def setup_schema():
    """Create all tables"""
    conn = psycopg2.connect(
        host=app_settings.db_config.host,
        port=app_settings.db_config.port,
        user=app_settings.db_config.user,
        password=app_settings.db_config.password,
        database=app_settings.db_config.database
    )
    
    # Order of table creation matters due to foreign key constraints
    tables = [
        'users.sql',
        'message_history.sql',
        'learning_progress.sql',
        'vocabulary.sql'
    ]
    
    try:
        with conn.cursor() as cur:
            for table_file in tables:
                sql = read_sql_file(table_file)
                cur.execute(sql)
                logger.info(f"Executed {table_file}")
            
            conn.commit()
            logger.info("Created all tables successfully")
            
    except Exception as e:
        conn.rollback()
        logger.error(f"Error creating schema: {e}")
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    try:
        create_database()
        setup_schema()
        print("Database setup completed successfully!")
    except Exception as e:
        print(f"Error setting up database: {e}")
        sys.exit(1)
