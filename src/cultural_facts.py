from datetime import datetime
import random


class CulturalFacts:
    def __init__(self):
        self.meal_culture = {
            "breakfast": [
                {
                    "fact": "Turkish breakfast (kahvaltı) is a feast! It typically includes cheese, olives, eggs, tomatoes, cucumbers, honey, jam, and bread.",
                    "vocabulary": {
                        "kahvaltı": "breakfast",
                        "peynir": "cheese",
                        "zeytin": "olives",
                        "bal": "honey",
                    },
                },
                {
                    "fact": "Menemen, a traditional breakfast dish, is made with eggs, tomatoes, and peppers. It's served hot with bread.",
                    "vocabulary": {
                        "menemen": "Turkish egg dish",
                        "yumurta": "egg",
                        "ekmek": "bread",
                    },
                },
            ],
            "lunch_dinner": [
                {
                    "fact": "Lunch (öğle yemeği) is often a hearty meal. Many Turks have çorba (soup) to start.",
                    "vocabulary": {
                        "öğle yemeği": "lunch",
                        "çorba": "soup",
                        "akşam yemeği": "dinner",
                    },
                },
                {
                    "fact": "Turkish tea (çay) is served throughout the day, especially after meals.",
                    "vocabulary": {"çay": "tea", "şeker": "sugar", "bardak": "glass"},
                },
            ],
        }

        self.islamic_traditions = [
            {
                "fact": "During Ramadan, the evening meal (iftar) begins with eating a date or drinking water.",
                "vocabulary": {
                    "iftar": "evening meal during Ramadan",
                    "hurma": "date (fruit)",
                },
            },
            {
                "fact": "Friday (Cuma) is a special day in Islamic culture, with many people attending Friday prayers.",
                "vocabulary": {"Cuma": "Friday", "namaz": "prayer"},
            },
        ]

        self.daily_customs = [
            {
                "fact": "Removing shoes before entering a home is a common Turkish custom.",
                "vocabulary": {"ayakkabı": "shoes", "ev": "home", "terlik": "slippers"},
            },
            {
                "fact": "Turkish coffee is often served with a glass of water and sometimes Turkish delight.",
                "vocabulary": {
                    "Türk kahvesi": "Turkish coffee",
                    "lokum": "Turkish delight",
                },
            },
        ]

    def get_morning_fact(self) -> dict:
        """Get a fact suitable for morning conversation"""
        return random.choice(self.meal_culture["breakfast"])

    def get_midday_fact(self) -> dict:
        """Get a fact suitable for midday conversation"""
        return random.choice(self.meal_culture["lunch_dinner"])

    def get_evening_fact(self) -> dict:
        """Get a fact suitable for evening conversation"""
        all_evening_facts = self.islamic_traditions + self.daily_customs
        return random.choice(all_evening_facts)

    def get_holiday_fact(self) -> dict:
        """Get information about current/upcoming Turkish holidays"""
        # This would ideally be connected to a calendar API
        # For now, returning some example holidays
        holidays = {
            "Ramazan Bayramı": "The feast celebrating the end of Ramadan",
            "Kurban Bayramı": "The feast of sacrifice",
            "Cumhuriyet Bayramı": "Republic Day of Turkey (October 29)",
        }
        return random.choice(list(holidays.items()))
