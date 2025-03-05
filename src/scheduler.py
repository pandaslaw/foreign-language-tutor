import os
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

    async def send_practice_message(self, user_id: int, session_type: str):
        """Send a practice message based on the time of day"""
        try:
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

            # Save bot's message
            MessagesRepository.save_message(user_id, response, is_llm=True)

            # Send message
            await self.app.builder().bot.send_message(
                chat_id=user_id,
                text=response,
                parse_mode=None,  # Don't use markdown to avoid formatting issues
            )

            logger.info(f"Sent {session_type} practice message to user {user_id}")

        except Exception as e:
            logger.error(f"Error sending practice message: {e}", exc_info=True)

    def schedule_daily_sessions(self, user_id: int):
        """Schedule daily practice sessions for a user"""
        try:
            # Morning session (9-10 GMT+3)
            self.scheduler.add_job(
                self.send_practice_message,
                CronTrigger(hour=9, minute="0-59/15", timezone=self.tz),
                args=[user_id, "morning"],
                id=f"morning_session_{user_id}",
                replace_existing=True,
            )

            # Afternoon session (15-16 GMT+3)
            self.scheduler.add_job(
                self.send_practice_message,
                CronTrigger(hour=15, minute="0-59/15", timezone=self.tz),
                args=[user_id, "midday"],
                id=f"midday_session_{user_id}",
                replace_existing=True,
            )

            # Evening session (22-23 GMT+3)
            self.scheduler.add_job(
                self.send_practice_message,
                CronTrigger(hour=22, minute="0-59/15", timezone=self.tz),
                args=[user_id, "evening"],
                id=f"evening_session_{user_id}",
                replace_existing=True,
            )

            logger.info(f"Scheduled daily sessions for user {user_id}")

        except Exception as e:
            logger.error(f"Error scheduling sessions: {e}", exc_info=True)

    def start(self):
        """Start the scheduler"""
        try:
            self.scheduler.start()
            logger.info("Learning scheduler started")
        except Exception as e:
            logger.error(f"Error starting scheduler: {e}", exc_info=True)

    def stop(self):
        """Stop the scheduler"""
        try:
            self.scheduler.shutdown()
            logger.info("Learning scheduler stopped")
        except Exception as e:
            logger.error(f"Error stopping scheduler: {e}", exc_info=True)
