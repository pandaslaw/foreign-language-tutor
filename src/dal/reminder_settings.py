import logging
from typing import Dict, List, Optional
from datetime import datetime

from src.database import get_db_connection

logger = logging.getLogger(__name__)

class ReminderSettings:
    """Repository for user reminder settings."""

    @staticmethod
    async def get_all_active_reminders() -> List[Dict]:
        """Get all active reminders for all users."""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT user_id, reminder_type, reminder_time, enabled
                        FROM reminder_settings
                        WHERE enabled = true
                    """)
                    return [
                        {
                            'user_id': row[0],
                            'reminder_type': row[1],
                            'reminder_time': row[2],
                            'enabled': row[3]
                        }
                        for row in cur.fetchall()
                    ]
        except Exception as e:
            logger.error(f"Error getting active reminders: {e}")
            return []

    @staticmethod
    async def get_user_reminders(user_id: int) -> Dict:
        """Get reminder settings for a specific user."""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT reminder_type, reminder_time, enabled
                        FROM reminder_settings
                        WHERE user_id = %s
                    """, (user_id,))
                    
                    reminders = {}
                    for row in cur.fetchall():
                        reminders[row[0]] = {
                            'time': row[1].strftime('%H:%M'),
                            'enabled': row[2]
                        }
                    return reminders
        except Exception as e:
            logger.error(f"Error getting reminders for user {user_id}: {e}")
            return {}

    @staticmethod
    async def update_reminder(
        user_id: int,
        reminder_type: str,
        reminder_time: str,
        enabled: bool = True
    ) -> bool:
        """Update or create a reminder setting."""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO reminder_settings (
                            user_id, reminder_type, reminder_time, enabled
                        ) VALUES (%s, %s, %s, %s)
                        ON CONFLICT (user_id, reminder_type) 
                        DO UPDATE SET
                            reminder_time = EXCLUDED.reminder_time,
                            enabled = EXCLUDED.enabled,
                            updated_at = CURRENT_TIMESTAMP
                    """, (user_id, reminder_type, reminder_time, enabled))
                    conn.commit()
                    return True
        except Exception as e:
            logger.error(f"Error updating reminder for user {user_id}: {e}")
            return False

    @staticmethod
    async def disable_reminder(user_id: int, reminder_type: str) -> bool:
        """Disable a specific reminder."""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE reminder_settings
                        SET enabled = false,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE user_id = %s AND reminder_type = %s
                    """, (user_id, reminder_type))
                    conn.commit()
                    return True
        except Exception as e:
            logger.error(f"Error disabling reminder for user {user_id}: {e}")
            return False
