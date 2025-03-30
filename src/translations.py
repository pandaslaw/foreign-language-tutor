from enum import Enum
from typing import Dict, Optional

from src.language import Language

class TranslationKey(str, Enum):
    """Keys for translations"""
    GREETING = "greeting"
    SELECT_NATIVE_LANGUAGE = "select_native_language"
    SELECT_TARGET_LANGUAGE = "select_target_language"
    SELECT_CURRENT_LEVEL = "select_current_level"
    SELECT_LEARNING_GOAL = "select_learning_goal"
    SELECT_REMINDER_PREFS = "select_reminder_prefs"
    SELECT_REMINDER_TIME = "select_reminder_time"
    CONTINUE = "continue"
    BACK = "back"
    SETTINGS_SUMMARY = "settings_summary"
    NATIVE_LANGUAGE = "native_language"
    TARGET_LANGUAGE = "target_language"
    CURRENT_LEVEL = "current_level"
    LEARNING_GOAL = "learning_goal"
    REMINDER_PREFS = "reminder_prefs"
    CONFIRM = "confirm"
    CHANGE_SETTINGS = "change_settings"
    WELCOME_MESSAGE = "welcome_message"
    START_LEARNING = "start_learning"
    START_LEARNING_BUTTON = "start_learning_button"
    SCENARIO_PROMPT = "scenario_prompt"
    PRACTICE_SESSION = "practice_session"
    SELECT_SCENARIO = "select_scenario"
    HELP_MESSAGE = "help_message"
    COMMANDS = "commands"
    LEARNING_STREAK = "learning_streak"
    PROGRESS_BY_SKILL = "progress_by_skill"
    DETAILED_STATS = "detailed_stats"
    SET_GOALS = "set_goals"
    ERROR_MESSAGE = "error_message"
    AUDIO_ERROR = "audio_error"
    REMINDER_LATER = "reminder_later"
    CANCEL_CONVERSATION = "cancel_conversation"
    GREAT = "great"

# Translations for each supported language
TRANSLATIONS: Dict[Language, Dict[TranslationKey, str]] = {
    Language.ENGLISH: {
        TranslationKey.GREETING: "Hi dear {name}! 👋\n\nI'm your personal language tutor. I'll help you learn {target} through natural conversations, focusing on practical daily situations.",
        TranslationKey.SELECT_NATIVE_LANGUAGE: "First, let me get to know you better.\nWhat is your native language?",
        TranslationKey.SELECT_TARGET_LANGUAGE: "Great! And which language would you like to learn?",
        TranslationKey.SELECT_CURRENT_LEVEL: "What's your current level?\n\nDon't worry if you're just starting - we'll begin with the basics!",
        TranslationKey.SELECT_LEARNING_GOAL: "What's your main goal for learning?\n\nThis will help me customize your learning experience.",
        TranslationKey.SELECT_REMINDER_PREFS: "When would you like to practice? 🕒\n\nI can remind you at these suggested times:\n• Morning (09:00) - Grammar practice\n• Afternoon (15:00) - Vocabulary learning\n• Evening (22:00) - Progress review\n\nClick each time to customize, or Continue to use these defaults.",
        TranslationKey.SELECT_REMINDER_TIME: "Select preferred time for {reminder_type} practice:",
        TranslationKey.CONTINUE: "✅ Continue",
        TranslationKey.BACK: "« Back",
        TranslationKey.SETTINGS_SUMMARY: "Here's your learning profile:",
        TranslationKey.NATIVE_LANGUAGE: "📝 Native language",
        TranslationKey.TARGET_LANGUAGE: "🎯 Learning",
        TranslationKey.CURRENT_LEVEL: "📊 Current level",
        TranslationKey.LEARNING_GOAL: "🎯 Main goal",
        TranslationKey.REMINDER_PREFS: "Practice reminders",
        TranslationKey.CONFIRM: "✅ Confirm",
        TranslationKey.CHANGE_SETTINGS: "🔄 Change settings",
        TranslationKey.WELCOME_MESSAGE: "Perfect! Your profile is all set. 🎉",
        TranslationKey.START_LEARNING: "I'll help you learn through:\n• Daily conversations\n• Vocabulary practice\n• Grammar explanations\n• Cultural insights\n\nReady to start your first lesson?",
        TranslationKey.START_LEARNING_BUTTON: "🎯 Start Learning",
        TranslationKey.SCENARIO_PROMPT: "Starting {scenario} practice!\n\nI'll guide you through this session. Feel free to ask questions or request help at any time.",
        TranslationKey.PRACTICE_SESSION: "What would you like to practice today? 🎯",
        TranslationKey.SELECT_SCENARIO: "Choose from these options:",
        TranslationKey.HELP_MESSAGE: "Here's how to use your language tutor:",
        TranslationKey.COMMANDS: "🎯 /start - Begin learning or update preferences\n📚 /practice - Start a new practice session\n📝 /vocab - Review vocabulary words\n📊 /progress - Check your learning progress\n⚙️ /settings - Update your preferences\n❓ /help - Show this help message\n🚫 /cancel - Stop current conversation\n\nJust choose a command or type a message to start chatting!",
        TranslationKey.LEARNING_STREAK: "🔥 Your learning streak",
        TranslationKey.PROGRESS_BY_SKILL: "Progress by skill",
        TranslationKey.DETAILED_STATS: "📊 Detailed Stats",
        TranslationKey.SET_GOALS: "🎯 Set Goals",
        TranslationKey.ERROR_MESSAGE: "I'm having trouble processing your message right now. Please try again in a moment.",
        TranslationKey.AUDIO_ERROR: "I couldn't understand the audio. Could you please try again or type your message?",
        TranslationKey.REMINDER_LATER: "I'll remind you in an hour! 🕐\nYou can always start practicing by sending me a message.",
        TranslationKey.CANCEL_CONVERSATION: "Conversation ended. You can start a new one with /start",
        TranslationKey.GREAT: "Great!",
    },
    Language.TURKISH: {
        TranslationKey.GREETING: "Merhaba sevgili {name}! 👋\n\nBen senin kişisel dil öğretmeninim. Günlük konuşmalara odaklanarak {target} öğrenmene yardımcı olacağım.",
        TranslationKey.SELECT_NATIVE_LANGUAGE: "Önce seni daha iyi tanıyayım.\nAnadilini seçer misin?",
        TranslationKey.SELECT_TARGET_LANGUAGE: "Harika! Hangi dili öğrenmek istersin?",
        TranslationKey.SELECT_CURRENT_LEVEL: "Şu anki seviyen nedir?\n\nEndişelenme, yeni başlıyorsan temellerden başlayacağız!",
        TranslationKey.SELECT_LEARNING_GOAL: "Öğrenme hedefin nedir?\n\nBu, öğrenme deneyimini kişiselleştirmeme yardımcı olacak.",
        TranslationKey.SELECT_REMINDER_PREFS: "Ne zaman pratik yapmak istersin? 🕒\n\nŞu saatlerde hatırlatma yapabilirim:\n• Sabah (09:00) - Gramer çalışması\n• Öğleden sonra (15:00) - Kelime öğrenimi\n• Akşam (22:00) - İlerleme değerlendirmesi\n\nHer saati özelleştirebilir veya varsayılanları kullanabilirsin.",
        TranslationKey.SELECT_REMINDER_TIME: "{reminder_type} çalışması için tercih ettiğin saati seç:",
        TranslationKey.CONTINUE: "✅ Devam et",
        TranslationKey.BACK: "« Geri",
        TranslationKey.SETTINGS_SUMMARY: "İşte öğrenme profilin:",
        TranslationKey.NATIVE_LANGUAGE: "📝 Anadil",
        TranslationKey.TARGET_LANGUAGE: "🎯 Öğrenilen dil",
        TranslationKey.CURRENT_LEVEL: "📊 Mevcut seviye",
        TranslationKey.LEARNING_GOAL: "🎯 Ana hedef",
        TranslationKey.REMINDER_PREFS: "Pratik hatırlatmaları",
        TranslationKey.CONFIRM: "✅ Onayla",
        TranslationKey.CHANGE_SETTINGS: "🔄 Ayarları değiştir",
        TranslationKey.WELCOME_MESSAGE: "Harika! Profilin hazır. 🎉",
        TranslationKey.START_LEARNING: "Sana şunlarla yardımcı olacağım:\n• Günlük konuşmalar\n• Kelime pratiği\n• Gramer açıklamaları\n• Kültürel bilgiler\n\nİlk dersine başlamaya hazır mısın?",
        TranslationKey.START_LEARNING_BUTTON: "🎯 Öğrenmeye Başla",
        TranslationKey.SCENARIO_PROMPT: "{scenario} pratiğine başlıyoruz!\n\nBu oturumda sana rehberlik edeceğim. İstediğin zaman soru sorabilir veya yardım isteyebilirsin.",
        TranslationKey.PRACTICE_SESSION: "Bugün ne çalışmak istersin? 🎯",
        TranslationKey.SELECT_SCENARIO: "Şu seçeneklerden birini seç:",
        TranslationKey.HELP_MESSAGE: "Dil öğretmeninizi nasıl kullanacağınız:",
        TranslationKey.COMMANDS: "🎯 /start - Öğrenmeye başla veya tercihleri güncelle\n📚 /practice - Yeni bir pratik oturumu başlat\n📝 /vocab - Kelimeleri gözden geçir\n📊 /progress - İlerlemeni kontrol et\n⚙️ /settings - Tercihlerini güncelle\n❓ /help - Bu yardım mesajını göster\n🚫 /cancel - Mevcut konuşmayı bitir\n\nBir komut seç veya mesaj yazarak sohbete başla!",
        TranslationKey.LEARNING_STREAK: "🔥 Öğrenme serisi",
        TranslationKey.PROGRESS_BY_SKILL: "Becerilere göre ilerleme",
        TranslationKey.DETAILED_STATS: "📊 Detaylı İstatistikler",
        TranslationKey.SET_GOALS: "🎯 Hedef Belirle",
        TranslationKey.ERROR_MESSAGE: "Şu anda mesajını işlemekte sorun yaşıyorum. Lütfen biraz sonra tekrar dene.",
        TranslationKey.AUDIO_ERROR: "Ses kaydını anlayamadım. Lütfen tekrar dene veya mesajını yazılı olarak gönder.",
        TranslationKey.REMINDER_LATER: "Bir saat sonra hatırlatacağım! 🕐\nDilersen bana mesaj göndererek her zaman pratik yapabilirsin.",
        TranslationKey.CANCEL_CONVERSATION: "Konuşma sonlandı. /start ile yeni bir konuşma başlatabilirsin",
        TranslationKey.GREAT: "Harika!",
    },
    Language.RUSSIAN: {
        TranslationKey.GREETING: "Привет, {name}! 👋\n\nЯ твой персональный репетитор по языку. Я помогу тебе выучить {target} через естественные разговоры, фокусируясь на повседневных ситуациях.",
        TranslationKey.SELECT_NATIVE_LANGUAGE: "Сначала давай познакомимся поближе.\nКакой твой родной язык?",
        TranslationKey.SELECT_TARGET_LANGUAGE: "Отлично! Какой язык ты хочешь изучать?",
        TranslationKey.SELECT_CURRENT_LEVEL: "Какой твой текущий уровень?\n\nНе волнуйся, если ты только начинаешь - мы начнем с основ!",
        TranslationKey.SELECT_LEARNING_GOAL: "Какая твоя основная цель изучения?\n\nЭто поможет мне персонализировать твой опыт обучения.",
        TranslationKey.SELECT_REMINDER_PREFS: "Когда ты хочешь практиковаться? 🕒\n\nЯ могу напоминать тебе в эти предложенные времена:\n• Утро (09:00) - Практика грамматики\n• День (15:00) - Изучение словарного запаса\n• Вечер (22:00) - Обзор прогресса\n\nНажми на каждое время, чтобы настроить, или Продолжить, чтобы использовать эти значения по умолчанию.",
        TranslationKey.SELECT_REMINDER_TIME: "Выберите предпочитаемое время для {reminder_type} практики:",
        TranslationKey.CONTINUE: "✅ Продолжить",
        TranslationKey.BACK: "« Назад",
        TranslationKey.SETTINGS_SUMMARY: "Вот твой профиль обучения:",
        TranslationKey.NATIVE_LANGUAGE: "📝 Родной язык",
        TranslationKey.TARGET_LANGUAGE: "🎯 Язык обучения",
        TranslationKey.CURRENT_LEVEL: "📊 Текущий уровень",
        TranslationKey.LEARNING_GOAL: "🎯 Основная цель",
        TranslationKey.REMINDER_PREFS: "Напоминания о практике",
        TranslationKey.CONFIRM: "✅ Подтвердить",
        TranslationKey.CHANGE_SETTINGS: "🔄 Изменить настройки",
        TranslationKey.WELCOME_MESSAGE: "Отлично! Твой профиль готов. 🎉",
        TranslationKey.START_LEARNING: "Я помогу тебе выучить через:\n• Ежедневные разговоры\n• Практику словарного запаса\n• Объяснения грамматики\n• Культурные знания\n\nГотов начать свой первый урок?",
        TranslationKey.START_LEARNING_BUTTON: "🎯 Начать обучение",
        TranslationKey.SCENARIO_PROMPT: "Начинаем {scenario} практику!\n\nЯ буду руководить тобой в течение этого занятия. Не стесняйся задавать вопросы или просить помощи в любое время.",
        TranslationKey.PRACTICE_SESSION: "Что ты хочешь практиковать сегодня? 🎯",
        TranslationKey.SELECT_SCENARIO: "Выберите один из вариантов:",
        TranslationKey.HELP_MESSAGE: "Как использовать твоего языкового репетитора:",
        TranslationKey.COMMANDS: "🎯 /start - Начать обучение или обновить предпочтения\n📚 /practice - Начать новое занятие\n📝 /vocab - Просмотреть словарный запас\n📊 /progress - Проверить прогресс\n⚙️ /settings - Обновить предпочтения\n❓ /help - Показать это сообщение помощи\n🚫 /cancel - Остановить текущий разговор\n\nПросто выбери команду или напиши сообщение, чтобы начать общение!",
        TranslationKey.LEARNING_STREAK: "🔥 Серия обучения",
        TranslationKey.PROGRESS_BY_SKILL: "Прогресс по навыкам",
        TranslationKey.DETAILED_STATS: "📊 Подробная статистика",
        TranslationKey.SET_GOALS: "🎯 Установить цели",
        TranslationKey.ERROR_MESSAGE: "У меня проблемы с обработкой твоего сообщения. Пожалуйста, попробуй снова через минуту.",
        TranslationKey.AUDIO_ERROR: "Я не смог понять аудио. Пожалуйста, попробуй снова или напиши сообщение.",
        TranslationKey.REMINDER_LATER: "Я напомню тебе через час! 🕐\nТы всегда можешь начать практиковаться, отправив мне сообщение.",
        TranslationKey.CANCEL_CONVERSATION: "Разговор окончен. Ты можешь начать новый с /start",
        TranslationKey.GREAT: "Отлично!",
    }
}

def get_translation(key: TranslationKey, language: Language = Language.ENGLISH, **kwargs) -> str:
    """Get translation for a key in specified language with optional formatting"""
    # Get translations for the language, fallback to English
    translations = TRANSLATIONS.get(language, TRANSLATIONS[Language.ENGLISH])
    
    # Get the translation string
    translation = translations.get(key, TRANSLATIONS[Language.ENGLISH][key])
    
    # Format if kwargs provided
    if kwargs:
        translation = translation.format(**kwargs)
    
    return translation

def detect_language_from_code(language_code: Optional[str]) -> Language:
    """Detect Language enum from Telegram language code"""
    if not language_code:
        return Language.ENGLISH
        
    # Map of Telegram language codes to our Language enum
    code_to_language = {
        'en': Language.ENGLISH,
        'tr': Language.TURKISH,
        'ru': Language.RUSSIAN,
    }
    
    # Get first part of language code (e.g., 'en-US' -> 'en')
    base_code = language_code.split('-')[0].lower()
    
    # Return mapped language or English as default
    return code_to_language.get(base_code, Language.ENGLISH)
