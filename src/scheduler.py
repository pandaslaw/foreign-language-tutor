import logging
import random
from datetime import datetime, time
from typing import Dict, Optional
import asyncio

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.job import Job
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application

from src.config import app_settings
from src.dal.reminder_settings import ReminderSettings
from src.dal.users_repo import UsersRepository
from src.utils import generate_answer

logger = logging.getLogger(__name__)

class LearningScheduler:
    """Handles scheduling and managing learning reminders."""
    
    REMINDER_PROMPTS = {
        'morning': """Generate a warm and engaging morning message for a language learning student. The message should:
1. Start with a warm Turkish greeting
2. Include a "Quote of the Day" in both Turkish and Russian that:
   - Is inspiring and motivational
   - Relates to learning, growth, or daily life
   - Uses simple Turkish that an A1 level student can understand
3. Ask 2-3 engaging questions about:
   - Morning routine
   - Plans for the day
   - Current feelings or mood
4. End with an encouraging note about practicing Turkish

Make the tone personal and caring, like a supportive friend. Use emojis naturally.
The entire message should be in Turkish except for the Russian translation of the quote.""",

        'afternoon': """Generate a friendly afternoon check-in message for a language learning student. The message should:
1. Start with a warm Turkish greeting
2. Ask 2-3 engaging questions about:
   - Lunch or current activities
   - How their day is going
   - Plans for the rest of the day
3. Include some encouraging words about language practice
4. Keep the tone casual and friendly

Make it feel like a natural conversation with a caring friend. Use emojis naturally.
The entire message should be in Turkish.""",

        'evening': """Generate a cozy evening reflection message for a language learning student. The message should:
1. Start with a warm Turkish greeting
2. Ask 2-3 engaging questions about:
   - Highlights of their day
   - Something they learned
   - Plans for tomorrow
3. Include some words of encouragement about their progress
4. End with a gentle reminder about tomorrow's practice

Make it feel like a warm evening chat with a close friend. Use emojis naturally.
The entire message should be in Turkish."""
    }

    def __init__(self, application: Application):
        self.application = application
        self.scheduler = AsyncIOScheduler()
        self.jobs: Dict[str, Job] = {}  # Store jobs by job_id
        self.prompts = app_settings.SYSTEM_PROMPTS.get("daily_interactions", {})

    async def start(self):
        """Start the scheduler and restore all active reminders."""
        if not self.scheduler.running:
            self.scheduler.start()
            await self._restore_reminders()
            logger.info("Learning scheduler started successfully")
        else:
            logger.warning("Scheduler is already running")

    def _get_job_id(self, user_id: int, reminder_type: str) -> str:
        """Generate consistent job ID."""
        return f"reminder_{reminder_type}_{user_id}"

    async def _restore_reminders(self):
        """Restore all active reminders from the database."""
        try:
            # Get all active reminders
            reminders = await ReminderSettings.get_all_active_reminders()
            
            # Schedule each reminder
            for reminder in reminders:
                await self._schedule_reminder(
                    user_id=reminder['user_id'],
                    reminder_type=reminder['reminder_type'],
                    reminder_time=reminder['reminder_time']
                )
                
            logger.info(f"Restored {len(reminders)} active reminders")
            
        except Exception as e:
            logger.error(f"Error restoring reminders: {e}")

    async def _schedule_reminder(
        self, 
        user_id: int, 
        reminder_type: str, 
        reminder_time: str
    ) -> Optional[Job]:
        """Schedule a single reminder job."""
        try:
            # Parse time
            hour, minute = map(int, reminder_time.split(':'))
            
            # Generate job ID
            job_id = self._get_job_id(user_id, reminder_type)
            
            # Remove existing job if any
            if job_id in self.jobs:
                self.scheduler.remove_job(job_id)
                del self.jobs[job_id]
            
            # Create new job
            job = self.scheduler.add_job(
                self._send_reminder,
                CronTrigger(hour=hour, minute=minute),
                args=[user_id, reminder_type],
                id=job_id,
                replace_existing=True,
                misfire_grace_time=300  # 5 minutes grace time
            )
            
            # Store job reference
            self.jobs[job_id] = job
            
            logger.info(f"Scheduled {reminder_type} reminder for user {user_id} at {reminder_time}")
            return job
            
        except Exception as e:
            logger.error(f"Error scheduling reminder: {e}")
            return None

    async def update_reminder_time(
        self, 
        user_id: int, 
        reminder_type: str, 
        new_time: str
    ) -> bool:
        """Update reminder time and reschedule the job."""
        try:
            # Validate time format
            try:
                hour, minute = map(int, new_time.split(':'))
                if not (0 <= hour <= 23 and 0 <= minute <= 59):
                    raise ValueError("Invalid time")
                new_time = f"{hour:02d}:{minute:02d}"
            except ValueError:
                logger.error(f"Invalid time format: {new_time}")
                return False

            # Update in database
            success = await ReminderSettings.update_reminder(
                user_id=user_id,
                reminder_type=reminder_type,
                reminder_time=new_time,
                enabled=True
            )
            
            if not success:
                return False

            # Schedule new job
            job = await self._schedule_reminder(user_id, reminder_type, new_time)
            return job is not None

        except Exception as e:
            logger.error(f"Error updating reminder time: {e}")
            return False

    async def _send_reminder(self, user_id: int, reminder_type: str):
        """Send a practice reminder with exercises to the user."""
        try:
            # Get user data
            user = UsersRepository.get_user_by_id(user_id)
            if not user:
                logger.error(f"User {user_id} not found for reminder")
                return

            # Get reminder settings to confirm it's still enabled
            settings = await ReminderSettings.get_user_reminders(user_id)
            if not settings.get(reminder_type, {}).get('enabled', False):
                logger.info(f"Reminder {reminder_type} disabled for user {user_id}")
                return

            # Show typing indicator while generating message
            await self.application.bot.send_chat_action(chat_id=user_id, action="typing")
            
            # Generate personalized message using LLM
            message = generate_answer(
                user_input=self.REMINDER_PROMPTS[reminder_type],
                system_prompt=app_settings.SYSTEM_PROMPT
            )

            # Split message into logical parts
            # Common separators in LLM responses
            separators = [
                "\n\nСмысл:",
                "\n\nИсправления:",
                "\n\nКак сказать правильно:",
                "\n\nПолезные фразы:",
                "\n\nПример:",
            ]

            parts = [message]
            for sep in separators:
                new_parts = []
                for part in parts:
                    split = part.split(sep)
                    if len(split) > 1:
                        for i, s in enumerate(split):
                            if i > 0:
                                s = sep.lstrip('\n') + s
                            if s.strip():
                                new_parts.append(s.strip())
                    else:
                        new_parts.append(part)
                parts = new_parts

            # Send each part with a small delay and typing indicator
            last_message = None
            for part in parts:
                # Show typing indicator proportional to message length
                typing_time = min(max(len(part) / 100, 1), 3)  # between 1-3 seconds
                await self.application.bot.send_chat_action(chat_id=user_id, action="typing")
                await asyncio.sleep(typing_time)
                last_message = await self.application.bot.send_message(
                    chat_id=user_id,
                    text=part,
                    parse_mode='Markdown'
                )
                # Small delay between messages for natural flow
                await asyncio.sleep(0.5)
            
            logger.info(f"Sent {reminder_type} conversation starter to user {user_id}")
            return last_message
            
        except Exception as e:
            logger.error(f"Error sending reminder to user {user_id}: {e}")
            return None

    async def _send_reminder_with_reaction(self, user_id: int, reminder_type: str):
        """Send a reminder and add a reaction to encourage interaction."""
        message = await self._send_reminder(user_id, reminder_type)
        if message:
            try:
                # Add a friendly reaction to encourage interaction
                reactions = ["👋", "🌟", "✨", "🎯", "💫"]
                await message.react(random.choice(reactions))
            except Exception as e:
                logger.error(f"Error adding reaction: {e}")

    async def disable_reminder(self, user_id: int, reminder_type: str) -> bool:
        """Disable a specific reminder."""
        try:
            # Disable in database
            success = await ReminderSettings.disable_reminder(user_id, reminder_type)
            if not success:
                return False

            # Remove job if exists
            job_id = self._get_job_id(user_id, reminder_type)
            if job_id in self.jobs:
                self.scheduler.remove_job(job_id)
                del self.jobs[job_id]
                
            return True
            
        except Exception as e:
            logger.error(f"Error disabling reminder: {e}")
            return False

    async def stop(self):
        """Stop the scheduler gracefully."""
        try:
            if self.scheduler.running:
                self.scheduler.shutdown()
                self.jobs.clear()
                logger.info("Learning scheduler stopped")
            else:
                logger.warning("Scheduler is not running")
        except Exception as e:
            logger.error(f"Error stopping scheduler: {e}")
