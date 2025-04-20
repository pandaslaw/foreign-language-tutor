import asyncio
from logging import getLogger

from telegram.ext import (
    ApplicationBuilder,
)

from src.admin_handlers import (
    register_admin_handlers,
)
from src.config import app_settings
from src.conversation_handlers import register_conversation_handlers, set_bot_commands
from src.error_handlers import error_handler
from src.reminder_handlers import register_reminder_handlers
from src.scheduler import LearningScheduler
from src.utils import log_memory_usage

logger = getLogger(__name__)


async def main():
    """Main entry point for the bot."""
    bot_app = ApplicationBuilder().token(app_settings.TELEGRAM_BOT_TOKEN).build()

    # Initialize the application
    await bot_app.initialize()

    # Register all handlers
    register_reminder_handlers(bot_app)
    register_admin_handlers(bot_app)
    register_conversation_handlers(bot_app)
    await set_bot_commands(bot_app)
    bot_app.add_error_handler(error_handler)

    # Initialize and start the learning scheduler
    scheduler = LearningScheduler(bot_app)
    await scheduler.start()
    logger.info("Learning scheduler started")
    # Make scheduler accessible to handlers
    bot_app.scheduler = scheduler

    try:
        logger.info("Starting the bot...")
        await bot_app.start()
        await bot_app.updater.start_polling()
        await asyncio.Future()
    except (KeyboardInterrupt, SystemExit):
        logger.error("Bot stopped.")
    finally:
        logger.info("Shutting down the bot...")
        scheduler.stop()
        logger.info("Learning scheduler stopped")


if __name__ == "__main__":
    log_memory_usage()
    asyncio.run(main())
