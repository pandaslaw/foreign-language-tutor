from datetime import datetime, timedelta
from typing import Dict, List
import json
import os


class ProgressTracker:
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.progress = {
            "daily_streaks": 0,
            "words_learned": {"nouns": 0, "verbs": 0, "adjectives": 0},
            "conversation_topics": set(),
            "cultural_facts_learned": set(),
            "last_practice": None,
            "daily_goals": {
                "morning_session": False,
                "midday_session": False,
                "evening_session": False,
            },
            "weekly_stats": {
                "sessions_completed": 0,
                "new_words_learned": 0,
                "cultural_facts": 0,
            },
        }

    def update_session(self, session_type: str):
        """Update progress after completing a session"""
        current_time = datetime.now()

        # Update daily goals
        self.progress["daily_goals"][f"{session_type}_session"] = True

        # Update streak
        if self.progress["last_practice"]:
            last_practice = datetime.fromisoformat(self.progress["last_practice"])
            if current_time.date() - last_practice.date() == timedelta(days=1):
                self.progress["daily_streaks"] += 1
            elif current_time.date() - last_practice.date() > timedelta(days=1):
                self.progress["daily_streaks"] = 1
        else:
            self.progress["daily_streaks"] = 1

        self.progress["last_practice"] = current_time.isoformat()
        self.progress["weekly_stats"]["sessions_completed"] += 1

    def add_learned_word(self, category: str):
        """Track newly learned words"""
        self.progress["words_learned"][category] += 1
        self.progress["weekly_stats"]["new_words_learned"] += 1

    def add_cultural_fact(self, fact_id: str):
        """Track learned cultural facts"""
        self.progress["cultural_facts_learned"].add(fact_id)
        self.progress["weekly_stats"]["cultural_facts"] += 1

    def get_progress_summary(self) -> str:
        """Generate a motivational progress summary"""
        total_words = sum(self.progress["words_learned"].values())
        return f"""🌟 *Your Learning Journey* 🌟

📚 _Words Mastered:_ {total_words} words
• Nouns: {self.progress['words_learned']['nouns']}
• Verbs: {self.progress['words_learned']['verbs']}
• Adjectives: {self.progress['words_learned']['adjectives']}

🔥 _Daily Streak:_ {self.progress['daily_streaks']} days
🎯 _Today's Progress:_ {sum(self.progress['daily_goals'].values())}/3 sessions

_Keep going! `Her gün bir adım daha!` (One more step each day!)_"""

    def get_weekly_report(self) -> str:
        """Generate a weekly progress report"""
        return f"""📊 *Weekly Progress Report* 📊

🎯 _Sessions Completed:_ {self.progress['weekly_stats']['sessions_completed']}
📚 _New Words Learned:_ {self.progress['weekly_stats']['new_words_learned']}
🏺 _Cultural Facts Discovered:_ {self.progress['weekly_stats']['cultural_facts']}

_`Harika ilerleme!` (Wonderful progress!)_"""
