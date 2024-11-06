import glob
import os
from logging import getLogger
from pathlib import Path
from typing import Dict

import yaml
from dotenv import load_dotenv
from pydantic.v1 import BaseSettings

from src.logging_config import setup_logging

logger = getLogger(__name__)


class AppSettings(BaseSettings):
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    OPENROUTER_API_KEY: str

    LANGUAGE_MODEL: str

    SYSTEM_PROMPT: str = None
    SYSTEM_PROMPTS: Dict[str, Dict[str, str]] = None

    TELEGRAM_BOT_TOKEN: str

    DB_CONNECTION_STRING: str

    def load_all_prompts(self, dir_path="docs"):
        """Load all prompts from YAML files in the specified directory recursively."""
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
        logger.info(f"Root dir: {root_dir}")
        yaml_files_pattern = os.path.join(root_dir, dir_path, "**", "*.yaml")
        logger.info(f"yaml_files_pattern: {yaml_files_pattern}")
        yaml_files = glob.glob(yaml_files_pattern, recursive=True)
        logger.info(f"yaml_files: {yaml_files}")

        self.SYSTEM_PROMPTS = {}

        for yaml_file in yaml_files:

            with open(yaml_file, "r", encoding="utf-8") as file:
                prompts = yaml.safe_load(file)
                file_path = Path(file.name)
                prompt_category = file_path.stem.replace("prompts_", "")
                self.SYSTEM_PROMPTS[prompt_category] = {}

                if isinstance(prompts, dict):
                    for key, value in prompts.items():
                        self.SYSTEM_PROMPTS[prompt_category][key] = value
                        if file.name.endswith("prompts.yaml"):
                            self.SYSTEM_PROMPT = value

    def load_prompts_from_yaml(self, yaml_file="prompts.yaml"):
        """Load prompts from the specified YAML file."""
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
        docs_dir = "docs"
        yaml_file_full_path = os.path.join(root_dir, docs_dir, yaml_file)

        with open(yaml_file_full_path, "r", encoding="utf-8") as file:
            prompts = yaml.safe_load(file)

        self.SYSTEM_PROMPT = prompts.get("system_prompt", "")


setup_logging()
logger.info("Loading environment variables from .env file.")
load_dotenv()

app_settings = AppSettings()
app_settings.load_all_prompts()

logger.info(f"CONFIG (LANGUAGE_MODEL): {app_settings.LANGUAGE_MODEL}")
logger.info(f"CONFIG (SYSTEM_PROMPT): {app_settings.SYSTEM_PROMPT}")

# Scenarios and their corresponding prompts
SCENARIO_PROMPTS = {
    "Daily Diary": app_settings.SYSTEM_PROMPTS["daily_diary"]["daily_diary_exercise"],
    "Grammar": app_settings.SYSTEM_PROMPTS["grammar"]["explain_grammar_rules"],
    "Plan": app_settings.SYSTEM_PROMPTS["plan"]["create_learning_plan"],
    "Reading": app_settings.SYSTEM_PROMPTS["reading"]["suggest_reading_texts"],
    "Vocabulary": app_settings.SYSTEM_PROMPTS["vocabulary"][
        "suggest_vocabulary_methods"
    ],
    "Writing": app_settings.SYSTEM_PROMPTS["writing"]["suggest_writing_exercises"],
    "General Conversation": "",
}
