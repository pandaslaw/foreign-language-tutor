import logging
import re
from datetime import datetime
from typing import Dict

from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, Application

from src.scheduler import LearningScheduler

logger = logging.getLogger(__name__)

async def set_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle setting reminder time commands like /morning_reminder 09:30"""
    try:
        # Get user ID
        user_id = update.effective_user.id
        
        # Get reminder type from command
        command = update.message.text.split()[0][1:]  # Remove leading /
        reminder_type = command.replace('_reminder', '')
        
        # Get scheduler instance
        scheduler: LearningScheduler = context.application.scheduler
        
        # Validate reminder type
        valid_types = scheduler.REMINDER_PROMPTS.keys()
        if reminder_type not in valid_types:
            await update.message.reply_text(
                f"❌ Invalid reminder type. Available types are:\n" + 
                "\n".join([f"/{k}_reminder HH:MM" for k in valid_types])
            )
            return

        # Get time from command
        try:
            time_str = update.message.text.split()[1]
            if not re.match(r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$', time_str):
                raise ValueError("Invalid time format")
        except (IndexError, ValueError):
            await update.message.reply_text(
                f"❌ Please provide time in 24-hour format (HH:MM)\n"
                f"Example: /{reminder_type}_reminder 09:30"
            )
            return

        # Update reminder
        success = await scheduler.update_reminder_time(user_id, reminder_type, time_str)
        
        if success:
            await update.message.reply_text(
                f"✅ {reminder_type}_reminder set to {time_str}\n"
                f"I'll remind you every day at this time!"
            )
        else:
            await update.message.reply_text(
                "❌ Sorry, there was an error setting your reminder. Please try again later."
            )

    except Exception as e:
        logger.error(f"Error in set_reminder: {e}")
        await update.message.reply_text(
            "❌ Sorry, something went wrong. Please try again later."
        )

def get_reminder_handlers():
    """Get all reminder-related command handlers"""
    return [
        CommandHandler(f"{reminder_type}_reminder", set_reminder)
        for reminder_type in LearningScheduler.REMINDER_PROMPTS.keys()
    ]


def register_reminder_handlers(app: Application):
    """Register all reminder handlers."""
    for handler in get_reminder_handlers():
        app.add_handler(handler)
