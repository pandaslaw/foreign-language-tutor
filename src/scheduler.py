import os
import asyncio
from logging import getLogger
from datetime import datetime, time, timedelta
from typing import Optional

import pytz
import yaml
import requests
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from telegram.ext import Application

from src.dal import MessagesRepository, UsersRepository
from src.dal.reminder_settings import ReminderSettings
from src.utils import load_history_and_generate_answer

logger = getLogger(__name__)

class LearningScheduler:
    REMINDER_TYPES = {
        'morning': 'Morning practice 🌅 (9:00)',
        'afternoon': 'Afternoon practice 🌞 (15:00)',
        'evening': 'Evening practice 🌙 (22:00)'
    }

    def __init__(self, app: Application):
        self.scheduler = BackgroundScheduler()
        self.app = app
        self.tz = pytz.timezone("Europe/Istanbul")
        self.prompts = {}
        self.load_prompts()
        self.morning_jobs = {}
        self.lunch_jobs = {}
        self.evening_jobs = {}
        self.health_check_jobs = {}
        
        # Default times (in UTC+3)
        self.morning_time = time(9, 0)  # 9:00 AM
        self.lunch_time = time(15, 0)   # 3:00 PM
        self.evening_time = time(22, 0)  # 10:00 PM

        # Add logging for scheduler events
        self.scheduler.add_listener(self._log_job_events)

    def _log_job_events(self, event):
        """Log scheduler events for debugging"""
        if event.code == 4:  # EVENT_JOB_MISSED
            logger.warning(f"Job missed: {event.job_id}")
        elif event.code == 2:  # EVENT_JOB_EXECUTED
            logger.info(f"Job executed successfully: {event.job_id}")
        elif event.code == 8:  # EVENT_JOB_ERROR
            logger.error(f"Job failed: {event.job_id}, Error: {event.exception}")

    async def send_practice_message(self, user_id: int, session_type: str):
        """Send a practice message based on the time of day"""
        try:
            logger.info(f"Attempting to send {session_type} message to user {user_id}")

            # Get user data
            user_data = UsersRepository.get_user_by_id(user_id)
            if not user_data:
                logger.warning(f"User {user_id} not found in database")
                return

            native_lang = user_data.get("native_language", "Russian").lower()
            base_prompt = (
                f"You are Leyla, a warm and supportive Turkish language tutor. "
                f"The student's native language is {native_lang}, so ALWAYS respond in {native_lang} with Turkish examples. "
                f"The student is at A1 level. "
                f"ALWAYS check any Turkish sentences they write for grammar mistakes. "
                f"If you find mistakes: "
                f"1. Point out the error "
                f"2. Explain the correct form "
                f"3. Suggest how natives would naturally express this idea "
                f"4. Give 2-3 alternative ways to say the same thing\n\n"
            )

            # Select appropriate prompt based on session type
            if session_type == "morning":
                prompt = base_prompt + (
                    "Start a morning conversation about daily routines and plans. "
                    "Keep the tone feminine, graceful, and full of positive energy. "
                    "Ask about their morning routine or plans for the day. "
                    "Include simple A1 level Turkish phrases with translations."
                )
            elif session_type == "midday":
                prompt = base_prompt + (
                    "Start a midday conversation about food, cooking, shopping, or daily activities. "
                    "Keep the tone practical and engaging. "
                    "Ask about their lunch, shopping plans, or current activities. "
                    "Include simple A1 level Turkish phrases with translations."
                )
            else:  # evening
                prompt = base_prompt + (
                    "Start an evening conversation reviewing the day. "
                    "Keep the tone soulful and warm. "
                    "Ask about their day or evening plans. "
                    "Include simple A1 level Turkish phrases with translations."
                )

            # Generate response using LLM
            response = load_history_and_generate_answer(user_id, "", prompt)
            logger.info(f"Generated response for user {user_id}")

            # Validate response
            if not response or not response.strip():
                logger.error("LLM generated an empty response")
                # Use fallback message based on session type and native language
                if native_lang == "russian":
                    fallback_messages = {
                        "morning": "Доброе утро! 🌞 Давайте попрактикуем турецкий. Как вы спали? По-турецки это: Nasıl uyudun?",
                        "midday": "Здравствуйте! 🌤️ Время практики турецкого. Вы уже обедали? По-турецки это: Öğle yemeği yedin mi?",
                        "evening": "Добрый вечер! 🌙 Давайте обсудим ваш день. Как прошёл день? По-турецки это: Günün nasıl geçti?",
                    }
                else:
                    fallback_messages = {
                        "morning": "Good morning! 🌞 Let's practice Turkish. How did you sleep? In Turkish: Nasıl uyudun?",
                        "midday": "Hello! 🌤️ Time for Turkish practice. Have you had lunch? In Turkish: Öğle yemeği yedin mi?",
                        "evening": "Good evening! 🌙 Let's review your day. How was your day? In Turkish: Günün nasıl geçti?",
                    }
                response = fallback_messages.get(
                    session_type, "Merhaba! Let's practice Turkish!"
                )

            # Save bot's message
            MessagesRepository.save_message(user_id, response, is_llm=True)

            # Send message - using the bot instance directly from app
            await self.app.bot.send_message(
                chat_id=user_id,
                text=response,
                parse_mode=None,  # Don't use markdown to avoid formatting issues
            )

            logger.info(
                f"Successfully sent {session_type} practice message to user {user_id}"
            )

        except Exception as e:
            logger.error(f"Error sending practice message: {e}", exc_info=True)

    def _run_coroutine(self, coroutine):
        """Helper function to run coroutines in the scheduler"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coroutine)
        finally:
            loop.close()

    async def _health_check(self, user_id: int):
        """Perform health check to wake up the service"""
        try:
            await self.app.bot.send_message(
                chat_id=user_id,
                text="__System health check__",
                parse_mode=None,  # Don't use markdown to avoid formatting issues
            )
        except Exception as e:
            logger.error(f"Health check failed: {e}")

    def _schedule_health_check(self, user_id: int, scenario_time: time):
        """Schedule a health check 5 minutes before a scenario"""
        if user_id in self.health_check_jobs:
            self.health_check_jobs[user_id].schedule_removal()

        # Calculate health check time (5 minutes before scenario)
        next_run = self._get_next_run_time(scenario_time)
        health_check_time = (next_run - timedelta(minutes=5)).time()
        
        # Schedule daily health check
        job = self.scheduler.add_job(
            self._run_coroutine,
            CronTrigger(hour=health_check_time.hour, minute=health_check_time.minute, timezone=self.tz),
            args=[self._health_check(user_id)],
            id=f"health_check_{user_id}_{scenario_time}",
            replace_existing=True,
            misfire_grace_time=300,
        )
        self.health_check_jobs[user_id] = job
        logger.info(f"Scheduled health check for user {user_id} at {health_check_time}")

    def _get_next_run_time(self, target_time: time) -> datetime:
        """Get the next run time in the specified timezone"""
        now = datetime.now(self.tz)
        target_dt = datetime.combine(now.date(), target_time)
        target_dt = self.tz.localize(target_dt)
        
        if target_dt <= now:
            target_dt += timedelta(days=1)
        
        return target_dt

    def schedule_daily_sessions(self, user_id: int):
        """Schedule daily practice sessions for a user"""
        try:
            logger.info(f"Scheduling daily sessions for user {user_id}")

            # Morning session (9-10 GMT+3)
            self.scheduler.add_job(
                self._run_coroutine,
                CronTrigger(hour=9, minute="0-59/15", timezone=self.tz),
                args=[self.send_practice_message(user_id, "morning")],
                id=f"morning_session_{user_id}",
                replace_existing=True,
                misfire_grace_time=300,
            )
            self._schedule_health_check(user_id, self.morning_time)

            # Afternoon session (15-16 GMT+3)
            self.scheduler.add_job(
                self._run_coroutine,
                CronTrigger(hour=15, minute="0-59/15", timezone=self.tz),
                args=[self.send_practice_message(user_id, "midday")],
                id=f"midday_session_{user_id}",
                replace_existing=True,
                misfire_grace_time=300,
            )
            self._schedule_health_check(user_id, self.lunch_time)

            # Evening session (22-23 GMT+3)
            self.scheduler.add_job(
                self._run_coroutine,
                CronTrigger(hour=22, minute="0-59/15", timezone=self.tz),
                args=[self.send_practice_message(user_id, "evening")],
                id=f"evening_session_{user_id}",
                replace_existing=True,
                misfire_grace_time=300,
            )
            self._schedule_health_check(user_id, self.evening_time)

            logger.info(f"Successfully scheduled all sessions for user {user_id}")
            # Print all jobs for this user
            jobs = self.scheduler.get_jobs()
            for job in jobs:
                logger.info(
                    f"Scheduled job: {job.id} - Next run time: {job.next_run_time}"
                )

        except Exception as e:
            logger.error(f"Error scheduling sessions: {e}", exc_info=True)

    def load_prompts(self):
        """Load conversation prompts from YAML file"""
        prompts_file = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "docs",
            "prompts_conversation.yaml",
        )
        try:
            with open(prompts_file, "r", encoding="utf-8") as f:
                self.prompts = yaml.safe_load(f)
            logger.info("Successfully loaded conversation prompts")
        except Exception as e:
            logger.error(f"Error loading prompts: {e}")
            self.prompts = {
                "morning_session": {
                    "default": ["Good morning! Let's practice Turkish!"]
                },
                "midday_session": {
                    "default": ["Hello! Time for some Turkish practice!"]
                },
                "evening_session": {
                    "default": ["Good evening! Let's review what we learned today!"]
                },
            }

    async def start(self):
        """Start the scheduler and restore all active reminders"""
        # Start the scheduler
        self.scheduler.start()
        
        # Restore all active reminders
        await self._restore_reminders()
        
        logger.info("Learning scheduler started successfully")

    async def _restore_reminders(self):
        """Restore all active reminders from the database"""
        try:
            # Get all active reminders
            reminders = await ReminderSettings.get_all_active_reminders()
            
            # Schedule each reminder
            for reminder in reminders:
                reminder_time = datetime.strptime(reminder['reminder_time'], '%H:%M').time()
                self.scheduler.add_job(
                    self._run_coroutine,
                    CronTrigger(hour=reminder_time.hour, minute=reminder_time.minute, timezone=self.tz),
                    args=[self.send_practice_message(reminder['user_id'], reminder['reminder_type'])],
                    id=f"reminder_{reminder['reminder_type']}_{reminder['user_id']}",
                    replace_existing=True,
                    misfire_grace_time=300,
                )
                
            logger.info(f"Restored {len(reminders)} active reminders")
            
        except Exception as e:
            logger.error(f"Error restoring reminders: {e}")

    def stop(self):
        """Stop the scheduler"""
        try:
            if self.scheduler.running:
                self.scheduler.shutdown()
                logger.info("Learning scheduler stopped successfully")
            else:
                logger.warning("Scheduler is not running")
        except Exception as e:
            logger.error(f"Error stopping scheduler: {e}", exc_info=True)

    async def update_reminder_time(self, user_id: int, reminder_type: str, new_time: str) -> bool:
        """Update reminder time and reschedule the job"""
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

            # Remove existing job if any
            job_id = f"reminder_{reminder_type}_{user_id}"
            if job_id in self.scheduler.get_job_ids():
                self.scheduler.remove_job(job_id)

            # Schedule new job
            job = self.scheduler.add_job(
                self._run_coroutine,
                CronTrigger(hour=hour, minute=minute, timezone=self.tz),
                args=[self.send_practice_message(user_id, reminder_type)],
                id=job_id,
                replace_existing=True,
                misfire_grace_time=300,
            )
            
            logger.info(f"Updated {reminder_type} reminder for user {user_id} to {new_time}")
            return True

        except Exception as e:
            logger.error(f"Error updating reminder time: {e}")
            return False

    async def schedule_daily_sessions(self, user_id: int):
        """Schedule personalized daily learning sessions"""
        try:
            # Get user's reminder preferences
            reminders = await ReminderSettings.get_user_reminders(user_id)
            
            # Schedule each reminder type
            for reminder_type, settings in reminders.items():
                if settings['enabled']:
                    hour, minute = map(int, settings['time'].split(':'))
                    job_id = f"reminder_{reminder_type}_{user_id}"
                    
                    # Remove existing job if any
                    if job_id in self.scheduler.get_job_ids():
                        self.scheduler.remove_job(job_id)
                    
                    # Schedule new job
                    job = self.scheduler.add_job(
                        self._run_coroutine,
                        CronTrigger(hour=hour, minute=minute, timezone=self.tz),
                        args=[self.send_practice_message(user_id, reminder_type)],
                        id=job_id,
                        replace_existing=True,
                        misfire_grace_time=300,
                    )
                    
                    logger.info(f"Scheduled {reminder_type} reminder for user {user_id} at {settings['time']}")
                else:
                    # Disable reminder in database and remove job
                    await ReminderSettings.disable_reminder(user_id, reminder_type)
                    job_id = f"reminder_{reminder_type}_{user_id}"
                    if job_id in self.scheduler.get_job_ids():
                        self.scheduler.remove_job(job_id)
            
        except Exception as e:
            logger.error(f"Error scheduling sessions for user {user_id}: {e}")
