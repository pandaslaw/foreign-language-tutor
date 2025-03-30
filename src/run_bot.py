import logging
import os

from dotenv import load_dotenv
from telegram.ext import (
    Application,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from src.config import app_settings
from src.scheduler import LearningScheduler
from src.handlers import (
    start,
    ask_native_language,
    ask_target_language,
    ask_current_level,
    ask_goal,
    handle_text_message,
    handle_voice_message,
    handle_callback_query,
    cancel,
    practice,
    progress,
    help_command,
    set_bot_commands,
    ASK_NATIVE_LANGUAGE,
    ASK_TARGET_LANGUAGE,
    ASK_CURRENT_LEVEL,
    ASK_GOAL,
    ASK_REMINDER_PREFS,
    CONFIRM_SETTINGS,
    ASK_SCENARIO,
    EXECUTE_SCENARIO, show_settings_summary,
)
from src.admin_handlers import (
    health_check,
    send_today_logs,
    send_all_logs,
    trigger_morning_scenario,
)

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    filename="bot.log",
)
logger = logging.getLogger(__name__)


async def post_init(application: Application) -> None:
    """Post-initialization hook to set up bot commands"""
    await set_bot_commands(application.bot)


def main() -> None:
    """Start the bot."""
    # Create the Application with post_init
    application = (
        Application.builder()
        .token(app_settings.TELEGRAM_BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    # Create scheduler instance
    scheduler = LearningScheduler(application.bot)
    application.scheduler = scheduler

    # Add conversation handler for onboarding
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CommandHandler("practice", practice),
            CommandHandler("settings", show_settings_summary),
        ],
        states={
            ASK_NATIVE_LANGUAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_native_language)],
            ASK_TARGET_LANGUAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_target_language)],
            ASK_CURRENT_LEVEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_current_level)],
            ASK_GOAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_goal)],
            ASK_REMINDER_PREFS: [
                CallbackQueryHandler(handle_callback_query, pattern=r"^reminder_|^time_|^reminders_done$")
            ],
            CONFIRM_SETTINGS: [
                CallbackQueryHandler(handle_callback_query, pattern=r"^settings_")
            ],
            ASK_SCENARIO: [
                CallbackQueryHandler(handle_callback_query, pattern=r"^(scenario_|group_)"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message),
            ],
            EXECUTE_SCENARIO: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message),
                MessageHandler(filters.VOICE, handle_voice_message),
                CallbackQueryHandler(handle_callback_query)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        name="main_conversation",
        persistent=True,
    )

    # Add handlers
    application.add_handler(conv_handler)
    
    # Add standalone command handlers
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("progress", progress))
    
    # Add admin handlers
    application.add_handler(CommandHandler("health", health_check))
    application.add_handler(CommandHandler("send_logs", send_today_logs))
    application.add_handler(CommandHandler("send_all_logs", send_all_logs))
    application.add_handler(CommandHandler("trigger_morning", trigger_morning_scenario))

    # Start the bot
    application.run_polling()


if __name__ == "__main__":
    main()
