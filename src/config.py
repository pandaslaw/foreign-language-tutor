from dotenv import load_dotenv
from loguru import logger
from pydantic.v1 import BaseSettings


class AppSettings(BaseSettings):
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    OPENROUTER_API_KEY: str

    LANGUAGE_MODEL: str

    SYSTEM_PROMPT: str

    TELEGRAM_BOT_TOKEN: str

    DB_CONNECTION_STRING: str


logger.info("Loading environment variables from .env file.")
load_dotenv()

app_settings = AppSettings()
logger.info(f"CONFIG (LANGUAGE_MODEL): {app_settings.LANGUAGE_MODEL}")
logger.info(f"CONFIG (SYSTEM_PROMPT): {app_settings.SYSTEM_PROMPT}")
