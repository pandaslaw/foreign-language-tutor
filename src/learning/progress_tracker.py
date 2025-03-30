import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta

from src.database import get_db_connection

logger = logging.getLogger(__name__)

class ProgressTracker:
    """Tracks user's learning progress and achievements"""
    
    SKILLS = {
        'speaking': ['pronunciation', 'fluency', 'vocabulary_usage'],
        'listening': ['comprehension', 'accent_adaptation'],
        'grammar': ['sentence_structure', 'verb_conjugation', 'tenses'],
        'vocabulary': {
            'daily_life': ['nouns', 'verbs', 'adjectives'],
            'social': ['greetings', 'expressions', 'cultural'],
            'professional': ['business', 'academic', 'technical']
        }
    }
    
    @staticmethod
    async def get_user_progress(user_id: int) -> Dict:
        """Get complete progress for a user"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    # Get skill progress
                    cur.execute("""
                        SELECT category, skill, level, progress
                        FROM learning_progress
                        WHERE user_id = %s
                    """, (user_id,))
                    
                    progress = {}
                    for row in cur.fetchall():
                        cat = row[0]
                        if cat not in progress:
                            progress[cat] = {}
                            
                        progress[cat][row[1]] = {
                            'level': row[2],
                            'progress': row[3]
                        }
                    
                    # Get vocabulary progress
                    cur.execute("""
                        SELECT word_type, COUNT(*)
                        FROM learned_vocabulary
                        WHERE user_id = %s
                        GROUP BY word_type
                    """, (user_id,))
                    
                    vocab_progress = dict(cur.fetchall())
                    if 'vocabulary' not in progress:
                        progress['vocabulary'] = {}
                    
                    for word_type in ['nouns', 'verbs', 'adjectives']:
                        progress['vocabulary'][word_type] = {
                            'count': vocab_progress.get(word_type, 0),
                            'progress': min(100, vocab_progress.get(word_type, 0) / 100 * 100)
                        }
                    
                    return progress
                    
        except Exception as e:
            logger.error(f"Error getting progress for user {user_id}: {e}")
            return {}

    @staticmethod
    async def get_learning_streak(user_id: int) -> int:
        """Get user's current learning streak"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    # Get streak from daily_activity table
                    cur.execute("""
                        WITH practice_dates AS (
                            SELECT DISTINCT date_trunc('day', activity_date) as practice_day
                            FROM daily_activity
                            WHERE user_id = %s
                            ORDER BY practice_day DESC
                        )
                        SELECT count(*)
                        FROM (
                            SELECT practice_day,
                                   lag(practice_day) OVER (ORDER BY practice_day DESC) as next_day
                            FROM practice_dates
                        ) as consecutive
                        WHERE (practice_day - next_day) = interval '-1 day'
                        AND practice_day >= CURRENT_DATE - interval '2 day'
                    """, (user_id,))
                    
                    return cur.fetchone()[0] or 0
                    
        except Exception as e:
            logger.error(f"Error calculating streak for user {user_id}: {e}")
            return 0

    @staticmethod
    async def update_skill_progress(
        user_id: int,
        category: str,
        skill: str,
        progress_delta: float
    ) -> bool:
        """Update progress for a specific skill"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    # First get current progress
                    cur.execute("""
                        SELECT progress, level FROM learning_progress
                        WHERE user_id = %s AND category = %s AND skill = %s
                    """, (user_id, category, skill))
                    
                    row = cur.fetchone()
                    if row:
                        current_progress = row[0]
                        current_level = row[1]
                    else:
                        current_progress = 0
                        current_level = 0
                    
                    # Calculate new progress
                    new_progress = max(0, min(100, current_progress + progress_delta))
                    
                    # Check for level up (every 20% is a new level)
                    new_level = int(new_progress / 20)
                    
                    # Update progress
                    cur.execute("""
                        INSERT INTO learning_progress (
                            user_id, category, skill, level, progress,
                            last_practice, next_review
                        ) VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP,
                            CURRENT_TIMESTAMP + interval '1 day')
                        ON CONFLICT (user_id, category, skill) DO UPDATE
                        SET progress = %s,
                            level = %s,
                            last_practice = CURRENT_TIMESTAMP,
                            next_review = CURRENT_TIMESTAMP + interval '1 day',
                            updated_at = CURRENT_TIMESTAMP
                    """, (
                        user_id, category, skill, new_level, new_progress,
                        new_progress, new_level
                    ))
                    
                    # Update daily activity
                    cur.execute("""
                        INSERT INTO daily_activity (user_id, activity_date)
                        VALUES (%s, CURRENT_TIMESTAMP)
                        ON CONFLICT (user_id, date_trunc('day', activity_date)) DO NOTHING
                    """, (user_id,))
                    
                    conn.commit()
                    
                    # Return True if leveled up
                    return new_level > current_level
                    
        except Exception as e:
            logger.error(f"Error updating progress for user {user_id}: {e}")
            return False

    @staticmethod
    async def get_practice_suggestions(user_id: int, limit: int = 3) -> List[Dict]:
        """Get suggested skills to practice based on progress and last practice"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT category, skill, level, progress,
                               last_practice, next_review
                        FROM learning_progress
                        WHERE user_id = %s
                        AND (next_review <= CURRENT_TIMESTAMP
                             OR next_review IS NULL)
                        ORDER BY 
                            COALESCE(last_practice, '1970-01-01'::timestamp) ASC,
                            progress ASC
                        LIMIT %s
                    """, (user_id, limit))
                    
                    return [
                        {
                            'category': row[0],
                            'skill': row[1],
                            'level': row[2],
                            'progress': row[3],
                            'last_practice': row[4],
                            'next_review': row[5]
                        }
                        for row in cur.fetchall()
                    ]
                    
        except Exception as e:
            logger.error(f"Error getting practice suggestions for user {user_id}: {e}")
            return []

    @staticmethod
    def update_skill_progress_sync(
        user_id: int,
        category: str,
        skill: str,
        progress_delta: float
    ) -> bool:
        """Update progress for a specific skill"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    # First get current progress
                    cur.execute("""
                        SELECT progress, level FROM learning_progress
                        WHERE user_id = %s AND category = %s AND skill = %s
                    """, (user_id, category, skill))
                    
                    row = cur.fetchone()
                    if row:
                        current_progress = row[0]
                        current_level = row[1]
                    else:
                        current_progress = 0
                        current_level = 0
                    
                    # Calculate new progress
                    new_progress = max(0, min(100, current_progress + progress_delta))
                    
                    # Check for level up (every 20% is a new level)
                    new_level = int(new_progress / 20)
                    
                    cur.execute("""
                        INSERT INTO learning_progress (
                            user_id, category, skill, level, progress,
                            last_practice, next_review
                        ) VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP,
                            CURRENT_TIMESTAMP + interval '1 day')
                        ON CONFLICT (user_id, category, skill) DO UPDATE
                        SET progress = %s,
                            level = %s,
                            last_practice = CURRENT_TIMESTAMP,
                            next_review = CURRENT_TIMESTAMP + interval '1 day',
                            updated_at = CURRENT_TIMESTAMP
                    """, (
                        user_id, category, skill, new_level, new_progress,
                        new_progress, new_level
                    ))
                    
                    conn.commit()
                    
                    # Return True if leveled up
                    return new_level > current_level
                    
        except Exception as e:
            logger.error(f"Error updating progress for user {user_id}: {e}")
            return False

    @staticmethod
    def get_skill_progress(user_id: int, category: str = None) -> Dict:
        """Get progress for all skills or a specific category"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    query = """
                        SELECT category, skill, level, progress, 
                               last_practice, next_review
                        FROM learning_progress
                        WHERE user_id = %s
                    """
                    params = [user_id]
                    
                    if category:
                        query += " AND category = %s"
                        params.append(category)
                        
                    cur.execute(query, params)
                    
                    progress = {}
                    for row in cur.fetchall():
                        cat = row[0]
                        if cat not in progress:
                            progress[cat] = {}
                            
                        progress[cat][row[1]] = {
                            'level': row[2],
                            'progress': row[3],
                            'last_practice': row[4],
                            'next_review': row[5]
                        }
                    
                    return progress
                    
        except Exception as e:
            logger.error(f"Error getting progress for user {user_id}: {e}")
            return {}

    @staticmethod
    def get_practice_suggestions_sync(user_id: int, limit: int = 3) -> List[Dict]:
        """Get suggested skills to practice based on progress and last practice"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT category, skill, level, progress,
                               last_practice, next_review
                        FROM learning_progress
                        WHERE user_id = %s
                        AND (next_review <= CURRENT_TIMESTAMP
                             OR next_review IS NULL)
                        ORDER BY 
                            COALESCE(last_practice, '1970-01-01'::timestamp) ASC,
                            progress ASC
                        LIMIT %s
                    """, (user_id, limit))
                    
                    return [
                        {
                            'category': row[0],
                            'skill': row[1],
                            'level': row[2],
                            'progress': row[3],
                            'last_practice': row[4],
                            'next_review': row[5]
                        }
                        for row in cur.fetchall()
                    ]
                    
        except Exception as e:
            logger.error(f"Error getting practice suggestions for user {user_id}: {e}")
            return []

    @staticmethod
    def calculate_daily_streak(user_id: int) -> int:
        """Calculate user's current daily practice streak"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        WITH practice_dates AS (
                            SELECT DISTINCT date_trunc('day', last_practice) as practice_day
                            FROM learning_progress
                            WHERE user_id = %s
                            ORDER BY practice_day DESC
                        )
                        SELECT count(*)
                        FROM (
                            SELECT practice_day,
                                   lag(practice_day) OVER (ORDER BY practice_day DESC) as next_day
                            FROM practice_dates
                        ) as consecutive
                        WHERE (practice_day - next_day) = interval '-1 day'
                        AND practice_day >= CURRENT_DATE - interval '2 day'
                    """, (user_id,))
                    
                    return cur.fetchone()[0] or 0
                    
        except Exception as e:
            logger.error(f"Error calculating streak for user {user_id}: {e}")
            return 0
