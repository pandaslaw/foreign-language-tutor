"""
Language detection utilities for the language tutor bot.
"""

import logging
from typing import Optional

from langdetect import detect, LangDetectException

logger = logging.getLogger(__name__)

# Map of language codes to full language names
LANGUAGE_MAP = {
    "tr": "Turkish",
    "en": "English",
    "ru": "Russian",
    # Add more languages as needed
}

# Default language if detection fails
DEFAULT_LANGUAGE = "en"


def detect_language(text: str) -> str:
    """
    Detect the language of the given text.
    
    Args:
        text: The text to detect language from
        
    Returns:
        A two-letter language code (e.g., 'en', 'tr', 'ru')
        If detection fails, returns the default language code
    """
    if not text or len(text.strip()) < 5:
        logger.warning(f"Text too short for reliable language detection: '{text}'")
        return DEFAULT_LANGUAGE
        
    try:
        lang_code = detect(text)
        logger.info(f"Detected language: {lang_code} ({LANGUAGE_MAP.get(lang_code, 'Unknown')})")
        
        # If detected language is not in our supported languages, use default
        if lang_code not in LANGUAGE_MAP:
            logger.warning(f"Detected language {lang_code} not supported, using {DEFAULT_LANGUAGE}")
            return DEFAULT_LANGUAGE
            
        return lang_code
    except LangDetectException as e:
        logger.error(f"Language detection failed: {e}")
        return DEFAULT_LANGUAGE


def get_voice_for_language(lang_code: str, app_settings) -> tuple:
    """
    Get the appropriate voice model for the given language code.
    
    Args:
        lang_code: Two-letter language code
        app_settings: Application settings with voice model configurations
        
    Returns:
        Tuple of (language_code, voice_name)
    """
    voice_config = app_settings.VOICE_MODELS.get(lang_code, None)
    
    if not voice_config:
        # Fallback to default voice
        logger.warning(f"No voice configuration for language {lang_code}, using default")
        return (app_settings.GOOGLE_TTS_LANGUAGE_CODE, app_settings.GOOGLE_TTS_VOICE_NAME)
    
    return (voice_config["code"], voice_config["voice"])
