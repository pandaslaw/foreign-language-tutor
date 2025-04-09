import logging
from typing import Dict, Any

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from src.dal.users_repo import UsersRepository
from src.dal.reminder_settings import ReminderSettings
from src.scheduler import LearningScheduler

# Define conversation states
ASK_NATIVE_LANGUAGE = "ASK_NATIVE_LANGUAGE"
ASK_TARGET_LANGUAGE = "ASK_TARGET_LANGUAGE"
ASK_CURRENT_LEVEL = "ASK_CURRENT_LEVEL"
ASK_GOAL = "ASK_GOAL"
ASK_REMINDER_PREFS = "ASK_REMINDER_PREFS"
CONFIRM_SETTINGS = "CONFIRM_SETTINGS"
ASK_SCENARIO = "ASK_SCENARIO"
EXECUTE_SCENARIO = "EXECUTE_SCENARIO"

logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    """Start the conversation and check if user exists."""
    user = update.effective_user
    user_id = user.id
    
    try:
        # Check if user exists
        existing_user = await UsersRepository.get_user_by_id(user_id)
        
        if existing_user:
            # User exists, show welcome back message
            await update.message.reply_text(
                f"Welcome back {user.first_name}! 👋\n"
                "What would you like to do?\n\n"
                "/practice - Start a practice session\n"
                "/progress - View your progress\n"
                "/help - Show help"
            )
            return ConversationHandler.END
            
        # New user, start onboarding
        await update.message.reply_text(
            f"Merhaba {user.first_name}! 👋\n"
            "I'm your Turkish language tutor. Let's get you started!\n\n"
            "First, what's your native language?"
        )
        return ASK_NATIVE_LANGUAGE
        
    except Exception as e:
        logger.error(f"Error in start handler: {e}")
        await update.message.reply_text(
            "Sorry, something went wrong. Please try again later."
        )
        return ConversationHandler.END

async def ask_native_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    """Handle native language response and ask for target language."""
    context.user_data['native_language'] = update.message.text
    
    await update.message.reply_text(
        "Great! And which language would you like to learn?\n"
        "(Currently I only support Turkish 🇹🇷)"
    )
    return ASK_TARGET_LANGUAGE

async def ask_target_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    """Handle target language response and ask for current level."""
    text = update.message.text.lower()
    if 'turkish' not in text:
        await update.message.reply_text(
            "I'm currently only able to teach Turkish. "
            "Please type 'Turkish' to continue."
        )
        return ASK_TARGET_LANGUAGE
    
    context.user_data['target_language'] = 'Turkish'
    
    # Ask for current level with buttons
    keyboard = [
        [
            InlineKeyboardButton("A1 (Beginner)", callback_data="level_A1"),
            InlineKeyboardButton("A2 (Elementary)", callback_data="level_A2")
        ],
        [
            InlineKeyboardButton("B1 (Intermediate)", callback_data="level_B1"),
            InlineKeyboardButton("B2 (Upper Int.)", callback_data="level_B2")
        ],
        [
            InlineKeyboardButton("C1 (Advanced)", callback_data="level_C1"),
            InlineKeyboardButton("C2 (Mastery)", callback_data="level_C2")
        ]
    ]
    
    await update.message.reply_text(
        "What's your current level in Turkish?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ASK_CURRENT_LEVEL

async def ask_current_level(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    """Handle current level response and ask for learning goal."""
    query = update.callback_query
    await query.answer()
    
    level = query.data.replace('level_', '')
    context.user_data['current_level'] = level
    
    await query.message.reply_text(
        "What's your main learning goal?\n\n"
        "For example:\n"
        "- Daily conversations\n"
        "- Shopping and directions\n"
        "- Work communication\n"
        "- Cultural understanding"
    )
    return ASK_GOAL

async def ask_goal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    """Handle learning goal response and ask for reminder preferences."""
    context.user_data['learning_goal'] = update.message.text
    
    # Get scheduler instance
    scheduler: LearningScheduler = context.application.scheduler
    reminder_types = scheduler.get_reminder_types()
    
    # Create keyboard for reminder preferences
    keyboard = []
    for reminder_type, display_name in reminder_types.items():
        keyboard.append([
            InlineKeyboardButton(
                f"✅ {display_name}", 
                callback_data=f"reminder_{reminder_type}_on"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton("Done ✨", callback_data="reminders_done")
    ])
    
    await update.message.reply_text(
        "When would you like to practice? Choose your preferred times:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ASK_REMINDER_PREFS

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    """Handle various callback queries."""
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith('reminder_'):
        if query.data == 'reminders_done':
            return await finish_onboarding(update, context)
            
        # Handle reminder toggle
        reminder_type = query.data.split('_')[1]
        is_on = query.data.endswith('_on')
        
        # Toggle the state
        new_state = '_off' if is_on else '_on'
        new_text = '❌' if is_on else '✅'
        
        # Update button
        keyboard = query.message.reply_markup.inline_keyboard
        for row in keyboard:
            for button in row:
                if button.callback_data.startswith(f'reminder_{reminder_type}'):
                    display_name = button.text[2:]  # Remove the emoji
                    button.text = f"{new_text} {display_name}"
                    button.callback_data = f"reminder_{reminder_type}{new_state}"
                    
        await query.edit_message_reply_markup(reply_markup=query.message.reply_markup)
        return ASK_REMINDER_PREFS

async def finish_onboarding(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Save user data and finish onboarding."""
    query = update.callback_query
    user = query.from_user
    user_data = context.user_data
    
    try:
        # Create user in database
        user_id = await UsersRepository.create_user(
            username=user.username or user.first_name,
            telegram_user_id=user.id,
            native_language=user_data['native_language'],
            target_language=user_data['target_language'],
            current_level=user_data['current_level'],
            learning_goal=user_data['learning_goal']
        )
        
        if not user_id:
            raise Exception("Failed to create user")
        
        # Set up default reminders
        scheduler: LearningScheduler = context.application.scheduler
        default_times = {
            'morning': '09:00',
            'afternoon': '15:00',
            'evening': '22:00'
        }
        
        # Schedule reminders
        for reminder_type, time in default_times.items():
            await ReminderSettings.update_reminder(
                user_id=user_id,
                reminder_type=reminder_type,
                reminder_time=time,
                enabled=True
            )
        
        # Schedule daily sessions
        await scheduler.schedule_daily_sessions(user_id)
        
        # Send success message
        await query.message.reply_text(
            f"Perfect! You're all set up {user.first_name}! 🎉\n\n"
            f"I've scheduled your practice sessions at:\n"
            f"🌅 Morning: 9:00\n"
            f"🌞 Afternoon: 15:00\n"
            f"🌙 Evening: 22:00\n\n"
            f"You can change these times using:\n"
            f"/morning_reminder HH:MM\n"
            f"/afternoon_reminder HH:MM\n"
            f"/evening_reminder HH:MM\n\n"
            f"Ready to start practicing? Use /practice to begin!"
        )
        
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"Error in finish_onboarding: {e}")
        await query.message.reply_text(
            "Sorry, something went wrong. Please try /start again."
        )
        return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel and end the conversation."""
    await update.message.reply_text(
        "Operation cancelled. What would you like to do?\n\n"
        "/start - Start over\n"
        "/practice - Start practicing\n"
        "/help - Show help"
    )
    return ConversationHandler.END
