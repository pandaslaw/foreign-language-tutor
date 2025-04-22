import datetime as dt
import os
import zipfile
from logging import getLogger
from typing import List

from telegram import Update
from telegram.ext import CallbackContext, Application, CommandHandler

from src.config import app_settings
from src.scheduler import LearningScheduler
from src.voice_handler import VoiceHandler

logger = getLogger(__name__)

# Define log directory relative to project root
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# Initialize voice handler for global use
voice_handler = VoiceHandler()


def get_today_logs() -> List[str]:
    """Collects all file paths of log files for today."""
    today = dt.datetime.now().date()
    today_logs = []

    for filename in os.listdir(LOG_DIR):
        if filename.endswith(".log"):
            file_date = dt.datetime.fromtimestamp(
                os.path.getmtime(os.path.join(LOG_DIR, filename))
            ).date()
            if file_date == today:
                today_logs.append(os.path.join(LOG_DIR, filename))

    return today_logs


def create_zip_archive(log_files: List[str]) -> str:
    """Creates zip archive with the specified log files."""
    zip_filename = "logs.zip"
    with zipfile.ZipFile(zip_filename, "w") as zipf:
        for log_file in log_files:
            zipf.write(log_file, os.path.basename(log_file))
    return zip_filename


async def health_check(update: Update, context: CallbackContext) -> None:
    """Check if bot is running and responding."""
    user_id = update.message.from_user.id
    if user_id in app_settings.ADMIN_USER_IDS:
        await update.message.reply_text("Bot is live and running!")
        logger.info(
            f"User {user_id} checked bot's status via /health command. Bot is live and running!"
        )
    else:
        logger.warning(f"User {user_id} not authorized to perform /health command.")


async def send_today_logs(update: Update, context: CallbackContext) -> None:
    """Send today's log files to admin users."""
    user_id = update.message.from_user.id

    if user_id in app_settings.ADMIN_USER_IDS:
        today_logs = get_today_logs()

        if today_logs:
            zip_filename = create_zip_archive(today_logs)

            with open(zip_filename, "rb") as zip_file:
                await update.message.reply_document(
                    zip_file, caption="Here are today's logs."
                )

            os.remove(zip_filename)
            logger.info(f"Logs sent to user {user_id}.")
        else:
            logger.info("No logs found for today.")
            await update.message.reply_text("No logs found for today.")
    else:
        logger.warning(f"User {user_id} not authorized to perform /send_logs command.")


async def send_all_logs(update: Update, context: CallbackContext) -> None:
    """Send all log files to admin users."""
    user_id = update.message.from_user.id

    if user_id in app_settings.ADMIN_USER_IDS:
        all_logs = [
            os.path.join(LOG_DIR, f) for f in os.listdir(LOG_DIR) if f.endswith(".log")
        ]

        if all_logs:
            zip_filename = create_zip_archive(all_logs)

            with open(zip_filename, "rb") as zip_file:
                await update.message.reply_document(
                    zip_file, caption="Here are all the logs."
                )

            os.remove(zip_filename)
            logger.info(f"All logs sent to user {user_id}.")
        else:
            logger.info("No logs found.")
            await update.message.reply_text("No logs found.")
    else:
        logger.warning(
            f"User {user_id} not authorized to perform /send_all_logs command."
        )


async def trigger_morning_scenario(update: Update, context: CallbackContext) -> None:
    """Manually trigger morning scenario for testing."""
    user_id = update.message.from_user.id

    if user_id in app_settings.ADMIN_USER_IDS:
        try:
            # Get the scheduler instance from application
            scheduler = context.application.scheduler

            # Reuse the scheduler's send_practice_message
            await scheduler._send_reminder(user_id, "morning")
            logger.info(f"Morning scenario triggered manually by admin {user_id}")
        except Exception as e:
            error_msg = "Error triggering morning scenario"
            logger.error(f"{error_msg}: {e}", exc_info=True)
            await update.message.reply_text(f"{error_msg}. Please try again later.")
    else:
        logger.warning(f"User {user_id} not authorized to trigger morning scenario.")


async def say_text(update: Update, context: CallbackContext) -> None:
    """Text-to-speech test command handler. Usage: /say [text]
    If no text provided, uses a default greeting."""

    chat_id = update.effective_chat.id
    if not chat_id:
        return

    # Get text from command arguments or use default
    text = (
        " ".join(context.args)
        if context.args
        else "Merhaba! Nasılsın? Bugün seninle Türkçe pratik yapalım!"
    )

    try:
        # Show recording indicator
        await context.bot.send_chat_action(chat_id=chat_id, action="record_voice")

        # Generate voice
        success, result = await voice_handler.text_to_voice(text, voice_name="Lily")

        if success:
            # Send voice message
            with open(result, "rb") as audio:
                await context.bot.send_voice(chat_id=chat_id, voice=audio)
        else:
            await update.message.reply_text(f"Error generating voice: {result}")

    except Exception as e:
        logger.error(f"Error in say_text: {e}")
        await update.message.reply_text(f"Error: {str(e)}")


def register_admin_handlers(app: Application):
    """Register all admin handlers."""
    app.add_handler(CommandHandler("health", health_check))
    app.add_handler(CommandHandler("send_logs", send_today_logs))
    app.add_handler(CommandHandler("send_all_logs", send_all_logs))
    app.add_handler(CommandHandler("trigger_morning", trigger_morning_scenario))
    app.add_handler(CommandHandler("say", say_text))  # Add /say command handler
