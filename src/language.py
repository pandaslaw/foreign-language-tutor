from enum import Enum
from typing import Dict, Optional

class Language(str, Enum):
    """Supported languages with their display names"""
    ENGLISH = "English"
    TURKISH = "Turkish"
    RUSSIAN = "Russian"

    @property
    def code(self) -> str:
        """Get ISO 639-1 language code"""
        codes = {
            Language.ENGLISH: "en",
            Language.TURKISH: "tr",
            Language.RUSSIAN: "ru"
        }
        return codes[self]

    @property
    def display_name(self) -> str:
        """Get localized display name in the language itself"""
        names = {
            Language.ENGLISH: "English",
            Language.TURKISH: "Türkçe",
            Language.RUSSIAN: "Русский"
        }
        return names[self]

    @classmethod
    def from_code(cls, code: Optional[str]) -> 'Language':
        """Get Language enum from ISO 639-1 code"""
        if not code:
            return cls.ENGLISH
            
        # Map of language codes to Language enum
        code_to_language = {
            'en': cls.ENGLISH,
            'tr': cls.TURKISH,
            'ru': cls.RUSSIAN,
        }
        
        # Get first part of language code (e.g., 'en-US' -> 'en')
        base_code = code.split('-')[0].lower()
        
        # Return mapped language or English as default
        return code_to_language.get(base_code, cls.ENGLISH)
