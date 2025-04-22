import logging
import re

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, Application, CallbackQueryHandler

from src.dal.reminder_settings import ReminderSettings
from src.scheduler import LearningScheduler

logger = logging.getLogger(__name__)


async def set_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle setting reminder time commands like /morning_reminder 09:30"""
    try:
        # Get user ID
        user_id = update.effective_user.id

        # Get reminder type from command
        command = update.message.text.split()[0][1:]  # Remove leading /
        reminder_type = command.replace("_reminder", "")

        # Get scheduler instance
        scheduler: LearningScheduler = context.application.scheduler

        # Validate reminder type
        valid_types = scheduler.REMINDER_PROMPTS.keys()
        if reminder_type not in valid_types:
            await update.message.reply_text(
                f"❌ Invalid reminder type. Available types are:\n"
                + "\n".join([f"/{k}_reminder HH:MM" for k in valid_types])
            )
            return

        # Get time from command
        try:
            time_str = update.message.text.split()[1]
            if not re.match(r"^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$", time_str):
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


async def list_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /reminders command to show all reminders"""
    try:
        user_id = update.effective_user.id
        reminders = await ReminderSettings.get_user_reminders(user_id)

        if not reminders:
            await update.message.reply_text(
                "🔔 У тебя пока нет установленных напоминаний.\n\n"
                "Чтобы установить напоминание, используй команды:\n"
                "/morning_reminder HH:MM\n"
                "/afternoon_reminder HH:MM\n"
                "/evening_reminder HH:MM"
            )
            return

        # Create message with inline keyboard for each reminder
        message = "🔔 Твои напоминания:\n\n"
        keyboard = []

        for reminder_type, settings in reminders.items():
            status = "✅ Включено" if settings["enabled"] else "❌ Выключено"
            message += f"{reminder_type}: {settings['time']} - {status}\n"

            # Add button to delete each reminder
            keyboard.append(
                [
                    InlineKeyboardButton(
                        f"❌ Удалить {reminder_type}",
                        callback_data=f"delete_reminder:{reminder_type}",
                    )
                ]
            )

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(message, reply_markup=reply_markup)

    except Exception as e:
        logger.error(f"Error in list_reminders: {e}")
        await update.message.reply_text(
            "❌ Извини, что-то пошло не так. Попробуй позже."
        )


async def handle_reminder_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle callback queries from reminder management buttons"""
    try:
        query = update.callback_query
        await query.answer()

        if query.data.startswith("delete_reminder:"):
            reminder_type = query.data.split(":")[1]
            user_id = query.from_user.id

            # Get scheduler instance and disable reminder
            scheduler: LearningScheduler = context.application.scheduler
            success = await scheduler.disable_reminder(user_id, reminder_type)

            if success:
                # Update the message to show current reminders
                reminders = await ReminderSettings.get_user_reminders(user_id)
                if not reminders:
                    await query.edit_message_text(
                        "🔔 У тебя больше нет установленных напоминаний.\n\n"
                        "Чтобы установить новое напоминание, используй команды:\n"
                        "/morning_reminder HH:MM\n"
                        "/afternoon_reminder HH:MM\n"
                        "/evening_reminder HH:MM"
                    )
                    return

                message = "🔔 Твои напоминания:\n\n"
                keyboard = []

                for r_type, settings in reminders.items():
                    status = "✅ Включено" if settings["enabled"] else "❌ Выключено"
                    message += f"{r_type}: {settings['time']} - {status}\n"

                    # Add button to delete each reminder
                    keyboard.append(
                        [
                            InlineKeyboardButton(
                                f"❌ Удалить {r_type}",
                                callback_data=f"delete_reminder:{r_type}",
                            )
                        ]
                    )

                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(message, reply_markup=reply_markup)
            else:
                await query.edit_message_text(
                    "❌ Извини, не удалось удалить напоминание. Попробуй позже."
                )

    except Exception as e:
        logger.error(f"Error in handle_reminder_callback: {e}")
        await query.edit_message_text("❌ Извини, что-то пошло не так. Попробуй позже.")


def get_reminder_handlers():
    """Get all reminder-related command handlers"""
    handlers = [
        CommandHandler(f"{reminder_type}_reminder", set_reminder)
        for reminder_type in LearningScheduler.REMINDER_PROMPTS.keys()
    ]

    # Add handlers for listing and managing reminders
    handlers.extend(
        [
            CommandHandler("reminders", list_reminders),
            CallbackQueryHandler(
                handle_reminder_callback, pattern=r"^delete_reminder:"
            ),
        ]
    )

    return handlers


def register_reminder_handlers(app: Application):
    """Register all reminder handlers."""
    for handler in get_reminder_handlers():
        app.add_handler(handler)
