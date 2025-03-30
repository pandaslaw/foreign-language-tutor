import glob
import os
from dataclasses import dataclass
from logging import getLogger
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from yaml import safe_load

from src.logging_config import setup_logging

logger = getLogger(__name__)


@dataclass
class DBConfig:
    """Database configuration with secure defaults"""
    host: str
    port: int
    database: str
    user: str
    password: str
    ssl_mode: str = 'require'  # Requires SSL
    min_connections: int = 1
    max_connections: int = 10
    connection_timeout: int = 30
    idle_timeout: int = 600
    application_name: str = 'language_tutor_bot'

    @classmethod
    def from_url(cls, url: str) -> 'DBConfig':
        """Create config from database URL"""
        parsed = urlparse(url)
        return cls(
            host=parsed.hostname or 'localhost',
            port=parsed.port or 5432,
            database=parsed.path[1:] if parsed.path else 'language_tutor',
            user=parsed.username or 'postgres',
            password=parsed.password or ''
        )


class AppSettings(BaseSettings):
    """Application settings."""

    # Database settings
    DATABASE_URL: str
    MAX_CONNECTIONS: int = 10
    REQUEST_TIMEOUT: int = 30
    DATA_RETENTION_DAYS: int = 365
    ENV: str = "development"
    
    # Bot settings
    TELEGRAM_BOT_TOKEN: str
    ADMIN_USER_IDS: list[int]

    # Voice API settings
    ELEVENLABS_API_KEY: str
    
    # Voice settings
    ELEVENLABS_VOICE_ID: str = "Leyla"  # Default voice name
    VOICE_STYLE: str = "Empathetic"  # Default style for voice generation
    
    # OpenRouter API settings
    OPENROUTER_API_KEY: str
    LANGUAGE_MODEL: str

    SYSTEM_PROMPT: str = ""
    SYSTEM_PROMPTS: Dict[str, Dict[str, str]] = {}

    @property
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.ENV.lower() == "production"

    @property
    def db_config(self) -> DBConfig:
        """Get database configuration"""
        config = DBConfig.from_url(self.DATABASE_URL)
        # Update database pool settings based on environment config
        config.max_connections = self.MAX_CONNECTIONS
        config.connection_timeout = self.REQUEST_TIMEOUT
        return config

    class Config:
        """Pydantic config."""
        env_file = ".env"
        env_file_encoding = "utf-8"

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
                prompts = safe_load(file)
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
            prompts = safe_load(file)

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
