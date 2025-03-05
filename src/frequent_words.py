from typing import Dict, List
import json
import os


class FrequentWords:
    def __init__(self):
        self.categories = {
            "nouns": self._load_frequent_words("nouns"),
            "verbs": self._load_frequent_words("verbs"),
            "adjectives": self._load_frequent_words("adjectives"),
        }
        self.user_progress: Dict[int, Dict] = {}

    def _load_frequent_words(self, category: str) -> List[Dict]:
        # Top 100 most frequent Turkish words for each category
        # This is a sample - you should replace with actual frequency data
        basic_words = {
            "nouns": [
                {"word": "ev", "translation": "house", "example": "Bu benim evim."},
                {"word": "yemek", "translation": "food", "example": "Yemek çok güzel."},
                # Add more words...
            ],
            "verbs": [
                {
                    "word": "gelmek",
                    "translation": "to come",
                    "example": "Yarın geliyorum.",
                },
                {
                    "word": "gitmek",
                    "translation": "to go",
                    "example": "Okula gidiyorum.",
                },
                # Add more words...
            ],
            "adjectives": [
                {
                    "word": "güzel",
                    "translation": "beautiful",
                    "example": "Çok güzel bir gün.",
                },
                {"word": "büyük", "translation": "big", "example": "Büyük bir ev."},
                # Add more words...
            ],
        }
        return basic_words.get(category, [])

    def get_next_words(self, user_id: int, category: str, count: int = 3) -> List[Dict]:
        """Get next unseen words for the user in the specified category"""
        if user_id not in self.user_progress:
            self.user_progress[user_id] = {cat: 0 for cat in self.categories}

        start_idx = self.user_progress[user_id][category]
        words = self.categories[category][start_idx : start_idx + count]

        self.user_progress[user_id][category] += len(words)
        return words

    def create_practice_sentence(self, word: Dict) -> str:
        """Create a practice sentence using the word"""
        return f"Practice: {word['example']}\nTranslation: {word['translation']}"

    def get_review_words(
        self, user_id: int, category: str, count: int = 3
    ) -> List[Dict]:
        """Get random words from previously learned ones for review"""
        if user_id not in self.user_progress:
            return []

        learned_count = self.user_progress[user_id][category]
        if learned_count == 0:
            return []

        # In a real implementation, you would use spaced repetition here
        # For now, we'll just return the last learned words
        return self.categories[category][max(0, learned_count - count) : learned_count]
