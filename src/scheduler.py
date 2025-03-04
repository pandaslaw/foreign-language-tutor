from datetime import datetime, time
import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from src.dal.users_repo import UsersRepo
from src.dal.messages_repo import MessagesRepo
from src.progress_tracker import ProgressTracker
from src.cultural_facts import CulturalFacts
import yaml
import random

class LearningScheduler:
    def __init__(self, bot, users_repo: UsersRepo, messages_repo: MessagesRepo):
        self.scheduler = BackgroundScheduler()
        self.bot = bot
        self.users_repo = users_repo
        self.messages_repo = messages_repo
        self.tz = pytz.timezone('Europe/Istanbul')
        self.cultural_facts = CulturalFacts()
        self.progress_trackers = {}
        self.load_prompts()
        
    def load_prompts(self):
        with open('docs/prompts_conversation.yaml', 'r', encoding='utf-8') as f:
            self.prompts = yaml.safe_load(f)
        
    def get_progress_tracker(self, user_id: int) -> ProgressTracker:
        if user_id not in self.progress_trackers:
            self.progress_trackers[user_id] = ProgressTracker(user_id)
        return self.progress_trackers[user_id]
        
    def schedule_daily_sessions(self, user_id):
        # Morning session (9-10 GMT+3)
        self.scheduler.add_job(
            self.send_practice_message,
            CronTrigger(hour=9, minute='0-59/15', timezone=self.tz),
            args=[user_id, 'morning'],
            id=f'morning_session_{user_id}'
        )
        
        # Afternoon session (15-16 GMT+3)
        self.scheduler.add_job(
            self.send_practice_message,
            CronTrigger(hour=15, minute='0-59/15', timezone=self.tz),
            args=[user_id, 'midday'],
            id=f'midday_session_{user_id}'
        )
        
        # Evening session (22-23 GMT+3)
        self.scheduler.add_job(
            self.send_practice_message,
            CronTrigger(hour=22, minute='0-59/15', timezone=self.tz),
            args=[user_id, 'evening'],
            id=f'evening_session_{user_id}'
        )

        # Weekly progress report (Sunday evening)
        self.scheduler.add_job(
            self.send_weekly_progress,
            CronTrigger(day_of_week='sun', hour=20, timezone=self.tz),
            args=[user_id],
            id=f'weekly_progress_{user_id}'
        )

    def send_practice_message(self, user_id: int, session_type: str):
        tracker = self.get_progress_tracker(user_id)
        
        # Get session-specific prompts and cultural facts
        if session_type == 'morning':
            prompts = self.prompts['morning_session']
            cultural_fact = self.cultural_facts.get_morning_fact()
            category = random.choice(['inspiration', 'wellness', 'affirmations'])
        elif session_type == 'midday':
            prompts = self.prompts['midday_session']
            cultural_fact = self.cultural_facts.get_midday_fact()
            category = random.choice(['cooking', 'shopping', 'daily_life'])
        else:  # evening
            prompts = self.prompts['evening_session']
            cultural_fact = self.cultural_facts.get_evening_fact()
            category = random.choice(['reflection', 'relaxation', 'connection'])

        # Select a random prompt from the category
        prompt = random.choice(prompts[category])
        
        # Format message with cultural fact
        message = f"{prompt}\n\n🎯 Cultural Note: {cultural_fact['fact']}\n"
        if 'vocabulary' in cultural_fact:
            message += "\n📚 New Words:\n"
            for word, meaning in cultural_fact['vocabulary'].items():
                message += f"• {word}: {meaning}\n"
        
        # Add progress information
        if random.random() < 0.3:  # 30% chance to show progress
            message += f"\n{tracker.get_progress_summary()}"
        
        # Send message through bot
        self.bot.send_message(
            chat_id=user_id,
            text=message,
            parse_mode='Markdown'
        )
        
        # Update progress
        tracker.update_session(session_type)
        tracker.add_cultural_fact(cultural_fact['fact'])

    def send_weekly_progress(self, user_id: int):
        """Send weekly progress report"""
        tracker = self.get_progress_tracker(user_id)
        report = tracker.get_weekly_report()
        
        self.bot.send_message(
            chat_id=user_id,
            text=report,
            parse_mode='Markdown'
        )

    def start(self):
        self.scheduler.start()

    def stop(self):
        self.scheduler.shutdown()
