import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta

from src.database import get_db_connection
from src.config import app_settings

logger = logging.getLogger(__name__)

class VocabularyManager:
    """Manages vocabulary learning and spaced repetition"""
    
    CATEGORIES = {
        'nouns': ['family', 'food', 'shopping', 'home', 'travel', 'work'],
        'verbs': ['daily_routine', 'communication', 'movement', 'emotions'],
        'adjectives': ['descriptions', 'feelings', 'quantities', 'qualities'],
        'phrases': ['greetings', 'shopping', 'directions', 'small_talk']
    }
    
    MASTERY_LEVELS = {
        0: "New",
        1: "Learning",
        2: "Practicing",
        3: "Familiar",
        4: "Mastered"
    }
    
    # Spaced repetition intervals (in days) for each mastery level
    REVIEW_INTERVALS = {
        0: 1,    # New words: review next day
        1: 3,    # Learning: review in 3 days
        2: 7,    # Practicing: review in a week
        3: 14,   # Familiar: review in 2 weeks
        4: 30    # Mastered: review monthly
    }

    @staticmethod
    def add_word(user_id: int, word: str, translation: str, category: str) -> bool:
        """Add a new word to user's vocabulary"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO vocabulary (
                            user_id, word, translation, category,
                            mastery_level, last_reviewed, next_review
                        ) VALUES (%s, %s, %s, %s, 0, CURRENT_TIMESTAMP, 
                            CURRENT_TIMESTAMP + interval '1 day')
                        ON CONFLICT (user_id, word) DO UPDATE 
                        SET translation = EXCLUDED.translation,
                            category = EXCLUDED.category
                        RETURNING id
                    """, (user_id, word, translation, category))
                    conn.commit()
                    return True
        except Exception as e:
            logger.error(f"Error adding word for user {user_id}: {e}")
            return False

    @staticmethod
    def get_words_for_review(user_id: int, limit: int = 10) -> List[Dict]:
        """Get words due for review"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT word, translation, category, mastery_level
                        FROM vocabulary
                        WHERE user_id = %s
                        AND next_review <= CURRENT_TIMESTAMP
                        ORDER BY next_review ASC
                        LIMIT %s
                    """, (user_id, limit))
                    
                    return [
                        {
                            'word': row[0],
                            'translation': row[1],
                            'category': row[2],
                            'mastery_level': row[3],
                            'mastery_label': VocabularyManager.MASTERY_LEVELS[row[3]]
                        }
                        for row in cur.fetchall()
                    ]
        except Exception as e:
            logger.error(f"Error getting review words for user {user_id}: {e}")
            return []

    @staticmethod
    def update_word_mastery(user_id: int, word: str, successful_review: bool) -> bool:
        """Update word mastery level based on review success"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    # First get current mastery level
                    cur.execute("""
                        SELECT mastery_level FROM vocabulary
                        WHERE user_id = %s AND word = %s
                    """, (user_id, word))
                    
                    row = cur.fetchone()
                    if not row:
                        return False
                        
                    current_level = row[0]
                    
                    # Adjust mastery level
                    new_level = min(4, current_level + 1) if successful_review else max(0, current_level - 1)
                    next_review = datetime.now() + timedelta(days=VocabularyManager.REVIEW_INTERVALS[new_level])
                    
                    # Update the word
                    cur.execute("""
                        UPDATE vocabulary
                        SET mastery_level = %s,
                            last_reviewed = CURRENT_TIMESTAMP,
                            next_review = %s
                        WHERE user_id = %s AND word = %s
                    """, (new_level, next_review, user_id, word))
                    
                    conn.commit()
                    return True
                    
        except Exception as e:
            logger.error(f"Error updating word mastery for user {user_id}: {e}")
            return False

    @staticmethod
    def get_category_progress(user_id: int, category: str) -> Dict:
        """Get progress statistics for a category"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT 
                            COUNT(*) as total_words,
                            SUM(CASE WHEN mastery_level >= 3 THEN 1 ELSE 0 END) as mastered_words,
                            AVG(mastery_level) as avg_mastery
                        FROM vocabulary
                        WHERE user_id = %s AND category = %s
                    """, (user_id, category))
                    
                    row = cur.fetchone()
                    if row:
                        return {
                            'category': category,
                            'total_words': row[0],
                            'mastered_words': row[1],
                            'average_mastery': float(row[2]) if row[2] else 0.0,
                            'mastery_percentage': (row[1] / row[0] * 100) if row[0] > 0 else 0
                        }
                    return {
                        'category': category,
                        'total_words': 0,
                        'mastered_words': 0,
                        'average_mastery': 0.0,
                        'mastery_percentage': 0
                    }
                    
        except Exception as e:
            logger.error(f"Error getting category progress for user {user_id}: {e}")
            return {
                'category': category,
                'error': str(e)
            }
