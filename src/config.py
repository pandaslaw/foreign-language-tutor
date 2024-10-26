import os
from logging import getLogger

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

    TELEGRAM_BOT_TOKEN: str

    DB_CONNECTION_STRING: str

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
app_settings.load_prompts_from_yaml()

logger.info(f"CONFIG (LANGUAGE_MODEL): {app_settings.LANGUAGE_MODEL}")
logger.info(f"CONFIG (SYSTEM_PROMPT): {app_settings.SYSTEM_PROMPT}")
