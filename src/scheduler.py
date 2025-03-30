import logging
import random
from datetime import datetime, time
from typing import Dict, List

import yaml
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from src.config import app_settings
from src.user_settings import UserSettings
from src.learning.vocabulary_manager import VocabularyManager
from src.learning.progress_tracker import ProgressTracker
from src.utils import load_history_and_generate_answer
from src.database import get_db_connection

logger = logging.getLogger(__name__)

class LearningScheduler:
    def __init__(self, bot):
        self.bot = bot
        self.scheduler = AsyncIOScheduler()
        self.prompts = app_settings.SYSTEM_PROMPTS["daily_interactions"]
        self.scheduler.start()

    def _get_prompt_for_session(self, session_type: str, user_data: Dict) -> str:
        """Get a personalized prompt for the session"""
        if session_type not in self.prompts:
            return ""

        session_data = self.prompts[session_type]
        base_prompt = session_data['base_prompt']
        
        # Get a random theme that matches user's goals
        themes = session_data['themes']
        if 'learning_goal' in user_data:
            # Filter themes based on user's goal
            goal = user_data['learning_goal'].lower()
            if 'daily' in goal or 'conversation' in goal:
                preferred_themes = [t for t in themes if any(k in str(t).lower() for k in ['daily', 'routine', 'casual'])]
            elif 'shopping' in goal:
                preferred_themes = [t for t in themes if any(k in str(t).lower() for k in ['shopping', 'market', 'food'])]
            elif 'direction' in goal:
                preferred_themes = [t for t in themes if any(k in str(t).lower() for k in ['location', 'direction', 'travel'])]
            else:
                preferred_themes = themes
            
            theme = random.choice(preferred_themes if preferred_themes else themes)
        else:
            theme = random.choice(themes)
            
        theme_data = list(theme.values())[0]
        
        # Customize base prompt with user data
        prompt = base_prompt.format(
            native_lang=user_data['native_language'],
            level=user_data['current_level']
        )
        
        # Add theme context
        prompt += f"\n\nUse this Turkish phrase: {theme_data['tr']}"
        prompt += f"\nContext: {theme_data['context']}"
        
        # Add personality guidance
        prompt += "\n\nRemember to be like Leyla from Kara Sevda - warm, wise, and supportive in your responses."
        
        # Add session-specific tone
        if session_type == 'morning':
            prompt += "\nKeep the tone inspiring, feminine, graceful, with positive energy."
        elif session_type == 'afternoon':
            prompt += "\nFocus on practical daily life activities and cultural elements."
        else:  # evening
            prompt += "\nMaintain a soulful, warm, retrospective tone."
        
        return prompt

    def schedule_daily_sessions(self, user_id: int):
        """Schedule personalized daily learning sessions"""
        try:
            # Get user's reminder preferences
            reminders = UserSettings.get_reminder_preferences(user_id)
            
            # Schedule each reminder type
            for reminder_type, settings in reminders.items():
                if settings['enabled']:
                    hour, minute = map(int, settings['time'].split(':'))
                    
                    # Schedule the reminder
                    self.scheduler.add_job(
                        self._send_reminder,
                        CronTrigger(hour=hour, minute=minute),
                        args=[user_id, reminder_type],
                        id=f"reminder_{reminder_type}_{user_id}",
                        replace_existing=True
                    )
                    
                    logger.info(f"Scheduled {reminder_type} reminder for user {user_id} at {settings['time']}")
            
        except Exception as e:
            logger.error(f"Error scheduling sessions for user {user_id}: {e}")

    async def _send_reminder(self, user_id: int, reminder_type: str):
        """Send a reminder with personalized content"""
        try:
            # Get user data for personalization
            user_data = await self._get_user_data(user_id)
            if not user_data:
                return

            # Generate personalized message using LLM
            prompt = self._get_prompt_for_session(reminder_type, user_data)
            conversation_message = await load_history_and_generate_answer(user_id, "", prompt)

            # Get learning content based on reminder type
            if reminder_type == 'morning':
                await self._morning_session(user_id, conversation_message)
            elif reminder_type == 'afternoon':
                await self._vocabulary_session(user_id, conversation_message)
            elif reminder_type == 'evening':
                await self._progress_review(user_id, conversation_message)
                
        except Exception as e:
            logger.error(f"Error sending {reminder_type} reminder to user {user_id}: {e}")

    async def _get_user_data(self, user_id: int) -> Dict:
        """Get user data for personalization"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT 
                            username,
                            first_name,
                            last_name,
                            native_language,
                            target_language,
                            current_level,
                            learning_goal,
                            settings
                        FROM users 
                        WHERE telegram_user_id = %s
                    """, (user_id,))
                    
                    row = cur.fetchone()
                    if not row:
                        logger.error(f"User {user_id} not found in database")
                        return None
                        
                    return {
                        'username': row[0],
                        'first_name': row[1],
                        'last_name': row[2],
                        'native_language': row[3],
                        'target_language': row[4],
                        'current_level': row[5],
                        'learning_goal': row[6],
                        'settings': row[7]
                    }
        except Exception as e:
            logger.error(f"Error getting user data: {e}")
            return None

    async def _morning_session(self, user_id: int, conversation_message: str):
        """Morning grammar practice session with conversation"""
        # Get practice suggestions
        suggestions = ProgressTracker.get_practice_suggestions(user_id, limit=1)
        
        # Create keyboard based on available practice
        keyboard = []
        if suggestions:
            suggestion = suggestions[0]
            keyboard.append([
                InlineKeyboardButton(
                    f"🎯 Practice {suggestion['skill'].replace('_', ' ').title()}", 
                    callback_data=f"practice_{suggestion['skill']}"
                )
            ])
        
        keyboard.extend([
            [InlineKeyboardButton("💬 Continue Conversation", callback_data="continue_chat")],
            [InlineKeyboardButton("⏰ Remind Later", callback_data="remind_later")]
        ])
        
        await self.bot.send_message(
            user_id,
            conversation_message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def _vocabulary_session(self, user_id: int, conversation_message: str):
        """Afternoon vocabulary learning session with conversation"""
        # Get words due for review
        words = VocabularyManager.get_words_for_review(user_id, limit=5)
        
        # Send conversation message first
        await self.bot.send_message(
            user_id,
            conversation_message
        )
        
        # Then send vocabulary practice options
        if not words:
            message = (
                "Would you like to learn some new words from the most frequent 100 words? "
                "I'll focus on words related to our conversation topic."
            )
            keyboard = [[
                InlineKeyboardButton("📚 Learn New Words", callback_data="new_words"),
                InlineKeyboardButton("💬 Just Chat", callback_data="continue_chat")
            ]]
        else:
            message = f"You have {len(words)} words to review:\n"
            for word in words[:3]:
                message += f"• {word['word']} ({word['mastery_label']})\n"
            
            if len(words) > 3:
                message += f"...and {len(words) - 3} more\n"
            
            keyboard = [
                [InlineKeyboardButton("📝 Review Words", callback_data="review_vocab")],
                [InlineKeyboardButton("💬 Continue Conversation", callback_data="continue_chat")],
                [InlineKeyboardButton("⏰ Remind Later", callback_data="remind_later")]
            ]
        
        await self.bot.send_message(
            user_id,
            message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def _progress_review(self, user_id: int, conversation_message: str):
        """Evening progress review with conversation"""
        # Send conversation message first
        await self.bot.send_message(
            user_id,
            conversation_message
        )
        
        # Get progress data
        streak = ProgressTracker.calculate_daily_streak(user_id)
        progress = ProgressTracker.get_skill_progress(user_id)
        
        # Create progress message
        message = (
            f"🔥 Your learning streak: {streak} days\n\n"
            "Today's Achievements:\n"
        )
        
        # Add today's progress
        achievements_found = False
        for category, skills in progress.items():
            for skill, data in skills.items():
                if data['last_practice'] and data['last_practice'].date() == datetime.now().date():
                    message += f"• {skill.replace('_', ' ').title()}: +{data['progress']}%\n"
                    achievements_found = True
        
        if not achievements_found:
            message += "No practice completed today yet. There's still time! 💪\n"
        
        keyboard = [
            [InlineKeyboardButton("📊 View Progress Details", callback_data="view_progress")],
            [InlineKeyboardButton("🎯 Set Tomorrow's Goals", callback_data="set_goals")],
            [InlineKeyboardButton("💬 Continue Conversation", callback_data="continue_chat")]
        ]
        
        await self.bot.send_message(
            user_id,
            message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
