import logging
import random
from datetime import datetime, time
from typing import Dict, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.job import Job
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application

from src.config import app_settings
from src.dal.reminder_settings import ReminderSettings
from src.dal.users_repo import UsersRepository

logger = logging.getLogger(__name__)

class LearningScheduler:
    """Handles scheduling and managing learning reminders."""
    
    REMINDER_TYPES = {
        'morning': 'Morning practice 🌅 (9:00)',
        'afternoon': 'Afternoon practice 🌞 (15:00)',
        'evening': 'Evening practice 🌙 (22:00)'
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

            # Get exercise content based on time of day
            greeting = ""
            exercises = []
            
            if reminder_type == 'morning':
                greeting = "Günaydın! ☀️ Good morning!"
                exercises = [
                    "🌅 Let's start with morning routines:",
                    "Q: How did you sleep? (Nasıl uyudun?)",
                    "Q: What did you have for breakfast? (Kahvaltıda ne yedin?)",
                    "Q: What are your plans for today? (Bugün ne yapacaksın?)",
                    "\nUseful phrases:",
                    "- İyi uyudum = I slept well",
                    "- Kahve içtim = I drank coffee",
                    "- Çalışacağım = I will work"
                ]
            elif reminder_type == 'afternoon':
                greeting = "İyi günler! 🌞 Good afternoon!"
                exercises = [
                    "🍽️ Let's practice daily activities:",
                    "Q: What did you eat for lunch? (Öğle yemeğinde ne yedin?)",
                    "Q: What are you doing now? (Şu an ne yapıyorsun?)",
                    "Q: How is your day going? (Günün nasıl geçiyor?)",
                    "\nUseful phrases:",
                    "- Çorba içtim = I had soup",
                    "- Çalışıyorum = I am working",
                    "- Güzel geçiyor = It's going well"
                ]
            else:  # evening
                greeting = "İyi akşamlar! 🌙 Good evening!"
                exercises = [
                    "🌆 Let's review your day:",
                    "Q: What did you do today? (Bugün ne yaptın?)",
                    "Q: What will you do tomorrow? (Yarın ne yapacaksın?)",
                    "Q: Did you learn something new? (Yeni bir şey öğrendin mi?)",
                    "\nUseful phrases:",
                    "- Alışveriş yaptım = I went shopping",
                    "- Dinleneceğim = I will rest",
                    "- Evet, öğrendim = Yes, I learned"
                ]

            # Combine message parts
            message = (
                f"{greeting}\n\n"
                f"{self.REMINDER_TYPES[reminder_type]}\n\n"
                f"{chr(10).join(exercises)}\n\n"
                "Reply with your answers in Turkish! 🇹🇷\n"
                "I'll check your grammar and help you improve! ✨"
            )

            # Send exercise
            await self.application.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode='HTML'
            )
            
            logger.info(f"Sent {reminder_type} exercises to user {user_id}")
            
        except Exception as e:
            logger.error(f"Error sending reminder to user {user_id}: {e}")

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
