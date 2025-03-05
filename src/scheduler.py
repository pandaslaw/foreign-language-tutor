import os
import asyncio
from logging import getLogger

import pytz
import yaml
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from telegram.ext import Application

from src.dal import MessagesRepository, UsersRepository
from src.utils import load_history_and_generate_answer

logger = getLogger(__name__)


class LearningScheduler:
    def __init__(self, app: Application):
        self.scheduler = BackgroundScheduler()
        self.app = app
        self.tz = pytz.timezone("Europe/Istanbul")
        self.prompts = {}
        self.load_prompts()

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

            # Select appropriate prompt based on session type
            if session_type == "morning":
                prompt = (
                    "Let's start our morning Turkish practice! As Leyla, be warm and encouraging. "
                    "Focus on morning routines, sports, and daily planning. Keep the tone feminine, "
                    "graceful, and full of positive energy. Ask about their morning routine or plans "
                    "for the day. Use simple A1 level Turkish with English translations."
                )
            elif session_type == "midday":
                prompt = (
                    "Time for our midday Turkish practice! As Leyla, be warm and supportive. "
                    "Focus on food, cooking, shopping, and daily life activities. Keep the tone practical "
                    "and engaging. Ask about their lunch, shopping plans, or current activities. "
                    "Use simple A1 level Turkish with English translations."
                )
            else:  # evening
                prompt = (
                    "Let's have our evening Turkish conversation! As Leyla, be warm and reflective. "
                    "Focus on reviewing the day, sharing feelings, and peaceful evening activities. "
                    "Keep the tone soulful and warm. Ask about their day or evening plans. "
                    "Use simple A1 level Turkish with English translations."
                )

            # Generate response using LLM
            response = load_history_and_generate_answer(user_id, "", prompt)
            logger.info(f"Generated response for user {user_id}")

            # Validate response
            if not response or not response.strip():
                logger.error("LLM generated an empty response")
                # Use fallback message based on session type
                fallback_messages = {
                    "morning": "Günaydın! 🌞 Good morning! Let's practice some Turkish. How did you sleep? Nasıl uyudun?",
                    "midday": "Merhaba! 🌤️ Hello! Time for our Turkish practice. Have you had lunch? Öğle yemeği yedin mi?",
                    "evening": "İyi akşamlar! 🌙 Good evening! Let's review what we learned today. How was your day? Günün nasıl geçti?",
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

            # Afternoon session (15-16 GMT+3)
            self.scheduler.add_job(
                self._run_coroutine,
                CronTrigger(hour=15, minute="0-59/15", timezone=self.tz),
                args=[self.send_practice_message(user_id, "midday")],
                id=f"midday_session_{user_id}",
                replace_existing=True,
                misfire_grace_time=300,
            )

            # Evening session (22-23 GMT+3)
            self.scheduler.add_job(
                self._run_coroutine,
                CronTrigger(hour=22, minute="0-59/15", timezone=self.tz),
                args=[self.send_practice_message(user_id, "evening")],
                id=f"evening_session_{user_id}",
                replace_existing=True,
                misfire_grace_time=300,
            )

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

    def start(self):
        """Start the scheduler"""
        try:
            if not self.scheduler.running:
                self.scheduler.start()
                logger.info("Learning scheduler started successfully")
                # Print all scheduled jobs
                jobs = self.scheduler.get_jobs()
                logger.info(f"Current scheduled jobs: {len(jobs)}")
                for job in jobs:
                    logger.info(f"Job: {job.id} - Next run time: {job.next_run_time}")
            else:
                logger.warning("Scheduler is already running")
        except Exception as e:
            logger.error(f"Error starting scheduler: {e}", exc_info=True)

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
