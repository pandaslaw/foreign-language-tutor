from logging import getLogger

from telegram.error import TelegramError
from telegram.ext import CallbackContext

from src.config import app_settings

logger = getLogger(__name__)


async def error_handler(update: object, context: CallbackContext):
    """Log the error and notify admins."""
    error_message = f"An error occurred: {context.error}"
    logger.error(error_message)

    try:
        for admin_chat_id in app_settings.ADMIN_USER_IDS:
            await context.bot.send_message(chat_id=admin_chat_id, text=error_message)
    except TelegramError as notify_error:
        logger.error(f"Failed to notify admin: {notify_error}")


async def notify_admin_on_error(bot_app, error_message):
    """Send error notification to the admin."""
    try:
        for admin_chat_id in app_settings.ADMIN_USER_IDS:
            logger.info(
                f"Trying to send a notification to admin user with id={admin_chat_id}"
            )
            await bot_app.send_message(
                chat_id=admin_chat_id, text=f"Error occurred: {error_message}"
            )
    except Exception as e:
        logger.error(f"Failed to notify admin: {e}")
