import logging
from typing import Dict, List, Optional
from datetime import datetime, time

from src.database import get_db_connection

logger = logging.getLogger(__name__)

class UserSettings:
    """Manages user preferences and settings"""
    
    DEFAULT_REMINDERS = {
        'morning': {'enabled': True, 'time': '09:00', 'type': 'grammar_practice'},
        'afternoon': {'enabled': True, 'time': '15:00', 'type': 'vocabulary_practice'},
        'evening': {'enabled': True, 'time': '22:00', 'type': 'progress_review'}
    }
    
    @staticmethod
    def save_reminder_preferences(
        user_id: int,
        reminder_type: str,
        enabled: bool,
        preferred_time: str
    ) -> bool:
        """Save user's reminder preferences"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE users 
                        SET settings = jsonb_set(
                            COALESCE(settings, '{}'::jsonb),
                            '{reminders, %s}',
                            %s::jsonb
                        )
                        WHERE telegram_user_id = %s
                    """, (
                        reminder_type,
                        {
                            'enabled': enabled,
                            'time': preferred_time,
                            'type': UserSettings.DEFAULT_REMINDERS[reminder_type]['type']
                        },
                        user_id
                    ))
                    conn.commit()
                    return True
        except Exception as e:
            logger.error(f"Error saving reminder preferences for user {user_id}: {e}")
            return False

    @staticmethod
    def get_reminder_preferences(user_id: int) -> Dict:
        """Get user's reminder preferences"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT settings->'reminders' 
                        FROM users 
                        WHERE telegram_user_id = %s
                    """, (user_id,))
                    
                    row = cur.fetchone()
                    if row and row[0]:
                        return row[0]
                    return UserSettings.DEFAULT_REMINDERS
        except Exception as e:
            logger.error(f"Error getting reminder preferences for user {user_id}: {e}")
            return UserSettings.DEFAULT_REMINDERS

    @staticmethod
    def get_active_users_for_reminder(reminder_type: str, current_time: time) -> List[Dict]:
        """Get users who have enabled a specific reminder for the current time"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT 
                            telegram_user_id,
                            username,
                            native_language,
                            target_language,
                            current_level,
                            settings->'reminders'->%s as reminder_settings
                        FROM users
                        WHERE 
                            (settings->'reminders'->%s->>'enabled')::boolean = true
                            AND (settings->'reminders'->%s->>'time')::time = %s
                    """, (reminder_type, reminder_type, reminder_type, current_time))
                    
                    return [
                        {
                            'user_id': row[0],
                            'username': row[1],
                            'native_language': row[2],
                            'target_language': row[3],
                            'current_level': row[4],
                            'reminder_settings': row[5]
                        }
                        for row in cur.fetchall()
                    ]
        except Exception as e:
            logger.error(f"Error getting users for reminder {reminder_type}: {e}")
            return []
