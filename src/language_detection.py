"""
Language detection utilities for the language tutor bot.
"""

import logging
from typing import Optional, Tuple, Dict

from langdetect import detect, detect_langs, LangDetectException

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


def detect_language_with_confidence(text: str) -> Tuple[str, float]:
    """
    Detect the language of the given text with confidence score.
    
    Args:
        text: The text to detect language from
        
    Returns:
        Tuple of (language_code, confidence_score)
    """
    if not text or len(text.strip()) < 5:
        logger.warning(f"Text too short for reliable language detection: '{text}'")
        return DEFAULT_LANGUAGE, 0.0
        
    try:
        # Get all possible languages with probabilities
        langs = detect_langs(text)
        if not langs:
            return DEFAULT_LANGUAGE, 0.0
            
        # Get the most probable language
        top_lang = langs[0]
        lang_code = top_lang.lang
        confidence = top_lang.prob
        
        logger.info(f"Detected language: {lang_code} with confidence {confidence:.2f}")
        logger.debug(f"All detected languages: {langs}")
        
        return lang_code, confidence
    except LangDetectException as e:
        logger.error(f"Language detection with confidence failed: {e}")
        return DEFAULT_LANGUAGE, 0.0


def detect_language(text: str) -> str:
    """
    Detect the language of the given text.
    
    Args:
        text: The text to detect language from
        
    Returns:
        A two-letter language code (e.g., 'en', 'tr', 'ru')
        If detection fails, returns the default language code
    """
    # Clean the text for better detection
    clean_text = text.strip()
    
    if not clean_text or len(clean_text) < 5:
        logger.warning(f"Text too short for reliable language detection: '{text}'")
        return DEFAULT_LANGUAGE
        
    try:
        # Get language with confidence
        lang_code, confidence = detect_language_with_confidence(text)
        
        # Log with more detail
        lang_name = LANGUAGE_MAP.get(lang_code, 'Unknown')
        logger.info(f"Final language detection: {lang_code} ({lang_name}) with confidence {confidence:.2f}")
        
        # Set minimum confidence threshold for reliable detection
        MIN_CONFIDENCE = 0.6  # Require at least 60% confidence
        
        # If confidence is too low or language not supported, use default
        if confidence < MIN_CONFIDENCE:
            logger.warning(f"Low confidence ({confidence:.2f}) for language {lang_code}, using {DEFAULT_LANGUAGE}")
            return DEFAULT_LANGUAGE
            
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
