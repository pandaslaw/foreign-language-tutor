import logging
from typing import Dict, Optional

from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler

from src.config import SCENARIO_PROMPTS
from src.language import Language
from src.learning.progress_tracker import ProgressTracker
from src.translations import TranslationKey, get_translation
from src.utils import load_history_and_generate_answer, transcribe_audio
from src.voice_handler import VoiceHandler
from src.user_settings import UserSettings

logger = logging.getLogger(__name__)

# Initialize voice handler
voice_handler = VoiceHandler()

# Conversation states
ASK_NATIVE_LANGUAGE = 0
ASK_TARGET_LANGUAGE = 1
ASK_CURRENT_LEVEL = 2
ASK_GOAL = 3
ASK_REMINDER_PREFS = 4
CONFIRM_SETTINGS = 5
ASK_SCENARIO = 6
EXECUTE_SCENARIO = 7

# Command descriptions for Telegram UI
COMMANDS = {
    'start': 'Start learning Turkish or update your preferences 🎯',
    'practice': 'Begin a new practice session 📚',
    'vocab': 'Review your vocabulary words 📝',
    'progress': 'Check your learning progress 📊',
    'settings': 'Update your learning preferences ⚙️',
    'help': 'Get help with using the bot ❓',
    'cancel': 'Cancel current conversation 🚫'
}

# Scenario groups for better organization
SCENARIO_GROUPS = {
    "Learning": [
        ("Grammar", "Learn grammar rules and patterns 📖"),
        ("Vocabulary", "Practice new words and phrases 📝"),
    ],
    "Practice": [
        ("Daily Diary", "Practice through daily journaling ✍️"),
        ("Reading", "Improve reading comprehension 📚"),
        ("Writing", "Enhance writing skills ✏️"),
    ],
    "Planning": [
        ("Plan", "Create a personalized learning plan 🎯"),
        ("General Conversation", "Free conversation practice 💭"),
    ]
}

async def set_bot_commands(bot):
    """Set bot commands in Telegram UI"""
    commands = [
        (cmd, desc) for cmd, desc in COMMANDS.items()
        if not cmd.startswith('_')  # Exclude private commands
    ]
    await bot.set_my_commands(commands)

def create_scenario_keyboard():
    """Create an inline keyboard for scenario selection with grouping"""
    keyboard = []
    
    for group_name, scenarios in SCENARIO_GROUPS.items():
        # Add group header
        keyboard.append([
            InlineKeyboardButton(f"== {group_name} ==", callback_data=f"group_{group_name.lower()}")
        ])
        
        # Add scenarios in pairs
        row = []
        for scenario, description in scenarios:
            row.append(InlineKeyboardButton(
                f"{scenario} {description.split()[0]}",  # Add first emoji as visual aid
                callback_data=f"scenario_{scenario}"
            ))
            if len(row) == 2:  # Create pairs of buttons
                keyboard.append(row)
                row = []
        
        if row:  # Add any remaining single button
            keyboard.append(row)
    
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the conversation with a welcoming message."""
    user = update.message.from_user
    
    # Store user's Telegram info
    context.user_data['telegram_id'] = user.id
    context.user_data['username'] = user.username
    context.user_data['first_name'] = user.first_name
    context.user_data['last_name'] = user.last_name
    
    # Detect user's preferred language from Telegram settings
    user_language = Language.from_code(user.language_code)
    context.user_data['interface_language'] = user_language
    
    # Create keyboard with language display names
    reply_keyboard = [[lang.display_name for lang in Language]]
    
    # Get localized welcome message
    welcome_msg = (
        get_translation(TranslationKey.GREETING, user_language, name=user.first_name, target="") + "\n\n" +
        get_translation(TranslationKey.SELECT_NATIVE_LANGUAGE, user_language)
    )
    
    await update.message.reply_text(
        welcome_msg,
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard,
            one_time_keyboard=True,
            input_field_placeholder=get_translation(TranslationKey.SELECT_NATIVE_LANGUAGE, user_language),
        ),
    )

    return ASK_NATIVE_LANGUAGE

async def ask_native_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle native language selection."""
    user_response = update.message.text.strip()
    context.user_data["native_language"] = user_response
    
    # Get user's interface language
    user_language = context.user_data.get('interface_language', Language.ENGLISH)
    
    # Create keyboard with available target languages (excluding native language)
    available_languages = [
        lang.display_name for lang in Language 
        if lang.display_name != user_response
    ]
    
    await update.message.reply_text(
        get_translation(TranslationKey.SELECT_TARGET_LANGUAGE, user_language),
        reply_markup=ReplyKeyboardMarkup(
            [available_languages],
            one_time_keyboard=True
        )
    )
    return ASK_TARGET_LANGUAGE

async def ask_target_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle target language selection."""
    user_response = update.message.text.strip()
    context.user_data["target_language"] = user_response
    
    # Get user's interface language
    user_language = context.user_data.get('interface_language', Language.ENGLISH)
    
    level_keyboard = [
        ["A1 (Beginner)", "A2 (Elementary)"],
        ["B1 (Intermediate)", "B2 (Upper Intermediate)"],
        ["C1 (Advanced)", "C2 (Mastery)"]
    ]
    
    await update.message.reply_text(
        get_translation(TranslationKey.SELECT_CURRENT_LEVEL, user_language),
        reply_markup=ReplyKeyboardMarkup(
            level_keyboard,
            one_time_keyboard=True
        )
    )
    return ASK_CURRENT_LEVEL

async def ask_current_level(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle current level selection."""
    user_response = update.message.text.strip()
    context.user_data["current_level"] = user_response.split()[0]  # Store just the level code
    
    # Get user's interface language
    user_language = context.user_data.get('interface_language', Language.ENGLISH)
    
    goals_keyboard = [
        ["Daily conversations", "Travel"],
        ["Business Turkish", "Academic Turkish"],
        ["Cultural exchange", "Other"]
    ]
    
    await update.message.reply_text(
        get_translation(TranslationKey.SELECT_LEARNING_GOAL, user_language),
        reply_markup=ReplyKeyboardMarkup(
            goals_keyboard,
            one_time_keyboard=True
        )
    )
    return ASK_GOAL

async def ask_goal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle learning goal selection."""
    user_response = update.message.text.strip()
    context.user_data["learning_goal"] = user_response
    
    # Get user's interface language
    user_language = context.user_data.get('interface_language', Language.ENGLISH)
    
    # Default reminder times
    reminders = UserSettings.DEFAULT_REMINDERS
    
    # Create reminder selection keyboard
    keyboard = []
    for reminder_type, settings in reminders.items():
        keyboard.append([
            InlineKeyboardButton(
                f"{reminder_type.title()} ({settings['time']})",
                callback_data=f"reminder_{reminder_type}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton(get_translation(TranslationKey.CONTINUE, user_language), callback_data="reminders_done")])
    
    await update.message.reply_text(
        get_translation(TranslationKey.SELECT_REMINDER_PREFS, user_language),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return ASK_REMINDER_PREFS

async def handle_reminder_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle reminder time selection."""
    query = update.callback_query
    user_data = context.user_data
    
    # Get user's interface language
    user_language = context.user_data.get('interface_language', Language.ENGLISH)
    
    # Extract reminder type from callback data
    reminder_type = query.data.split("_")[1]
    
    # Create time selection keyboard
    keyboard = []
    for hour in range(0, 24, 3):
        row = []
        for h in range(hour, min(hour + 3, 24)):
            time_str = f"{h:02d}:00"
            row.append(
                InlineKeyboardButton(time_str, callback_data=f"time_{reminder_type}_{time_str}")
            )
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton(get_translation(TranslationKey.BACK, user_language), callback_data="reminders_done")])
    
    await query.edit_message_text(
        get_translation(TranslationKey.SELECT_REMINDER_TIME, user_language, reminder_type=reminder_type),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return ASK_REMINDER_PREFS

async def show_settings_summary(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show summary of user settings."""
    query = update.callback_query
    user_data = context.user_data
    
    # Get user's interface language
    user_language = context.user_data.get('interface_language', Language.ENGLISH)
    
    summary = (
        get_translation(TranslationKey.SETTINGS_SUMMARY, user_language) + "\n\n"
        f"{get_translation(TranslationKey.NATIVE_LANGUAGE, user_language)}: {user_data['native_language']}\n"
        f"{get_translation(TranslationKey.TARGET_LANGUAGE, user_language)}: {user_data['target_language']}\n"
        f"{get_translation(TranslationKey.CURRENT_LEVEL, user_language)}: {user_data['current_level']}\n"
        f"{get_translation(TranslationKey.LEARNING_GOAL, user_language)}: {user_data['learning_goal']}\n\n"
        f"{get_translation(TranslationKey.REMINDER_PREFS, user_language)}:\n"
    )
    
    reminders = user_data.get('reminder_settings', UserSettings.DEFAULT_REMINDERS)
    for reminder_type, settings in reminders.items():
        summary += f"• {reminder_type.title()}: {settings['time']}\n"
    
    keyboard = [
        [InlineKeyboardButton(get_translation(TranslationKey.CONFIRM, user_language), callback_data="settings_confirm")],
        [InlineKeyboardButton(get_translation(TranslationKey.CHANGE_SETTINGS, user_language), callback_data="settings_change")]
    ]
    
    await query.edit_message_text(
        summary,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return CONFIRM_SETTINGS

async def handle_scenario_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle scenario selection."""
    query = update.callback_query
    data = query.data
    
    # Get user's interface language
    user_language = context.user_data.get('interface_language', Language.ENGLISH)
    
    if data.startswith("scenario_"):
        scenario = data.replace("scenario_", "")
        if scenario in SCENARIO_PROMPTS:
            await query.edit_message_text(
                get_translation(TranslationKey.SCENARIO_PROMPT, user_language, scenario=scenario)
            )
            return EXECUTE_SCENARIO
    
    return ASK_SCENARIO

async def practice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start a new practice session"""
    # Get user's interface language
    user_language = context.user_data.get('interface_language', Language.ENGLISH)
    
    message = (
        get_translation(TranslationKey.PRACTICE_SESSION, user_language) + "\n\n" +
        get_translation(TranslationKey.SELECT_SCENARIO, user_language)
    )
    
    await update.message.reply_text(
        message,
        reply_markup=create_scenario_keyboard()
    )
    return ASK_SCENARIO

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show help about using the bot"""
    # Get user's interface language
    user_language = context.user_data.get('interface_language', Language.ENGLISH)
    
    help_text = (
        get_translation(TranslationKey.HELP_MESSAGE, user_language) + "\n\n" +
        get_translation(TranslationKey.COMMANDS, user_language)
    )
    await update.message.reply_text(help_text)

async def progress(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user's learning progress"""
    # Get user's interface language
    user_language = context.user_data.get('interface_language', Language.ENGLISH)
    
    # Get progress data
    progress = await ProgressTracker.get_user_progress(update.effective_user.id)
    streak = await ProgressTracker.get_learning_streak(update.effective_user.id)
    
    # Create progress message
    message = (
        f"{get_translation(TranslationKey.LEARNING_STREAK, user_language)}: {streak} days\n\n" +
        get_translation(TranslationKey.PROGRESS_BY_SKILL, user_language) + ":\n"
    )
    
    for category, skills in progress.items():
        for skill, data in skills.items():
            message += f"• {skill.replace('_', ' ').title()}: {data['progress']}%\n"
    
    keyboard = [[
        InlineKeyboardButton(get_translation(TranslationKey.DETAILED_STATS, user_language), callback_data="stats_detailed"),
        InlineKeyboardButton(get_translation(TranslationKey.SET_GOALS, user_language), callback_data="stats_goals")
    ]]
    
    await update.message.reply_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages from the user."""
    # Get user's interface language
    user_language = context.user_data.get('interface_language', Language.ENGLISH)
    
    try:
        user_message = update.message.text
        response = await load_history_and_generate_answer(user_message)
        await update.message.reply_text(response)
    except Exception as e:
        logger.error(f"Error in handle_text_message: {e}")
        await update.message.reply_text(
            get_translation(TranslationKey.ERROR_MESSAGE, user_language)
        )

async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle voice messages from the user."""
    # Get user's interface language
    user_language = context.user_data.get('interface_language', Language.ENGLISH)
    
    try:
        voice_handler = VoiceHandler()
        voice_file = await update.message.voice.get_file()
        transcribed_text = await voice_handler.transcribe_voice(voice_file)
        
        if transcribed_text:
            await handle_text_message(update, context, transcribed_text)
        else:
            await update.message.reply_text(
                get_translation(TranslationKey.AUDIO_ERROR, user_language)
            )
            
    except Exception as e:
        logger.error(f"Error in handle_voice_message: {e}")
        await update.message.reply_text(
            get_translation(TranslationKey.ERROR_MESSAGE, user_language)
        )

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callback queries from inline keyboards."""
    query = update.callback_query
    data = query.data
    
    # Get user's interface language
    user_language = context.user_data.get('interface_language', Language.ENGLISH)
    
    if data.startswith("reminder_"):
        await handle_reminder_time(update, context)
    elif data == "reminders_done":
        await show_settings_summary(update, context)
    elif data == "remind_later":
        # Reschedule reminder
        await query.edit_message_text(
            get_translation(TranslationKey.REMINDER_LATER, user_language)
        )
    elif data.startswith("scenario_"):
        await handle_scenario_selection(update, context)
    else:
        await query.answer()

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel conversation"""
    # Get user's interface language
    user_language = context.user_data.get('interface_language', Language.ENGLISH)
    
    await update.message.reply_text(
        get_translation(TranslationKey.CANCEL_CONVERSATION, user_language)
    )
    return ConversationHandler.END
