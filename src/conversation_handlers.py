import time
from logging import getLogger

from telegram import ReplyKeyboardMarkup, BotCommand
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    CallbackContext,
    ContextTypes,
)

from src.admin_handlers import (
    voice_handler,
)
from src.config import SCENARIO_PROMPTS
from src.dal import MessagesRepository, UsersRepository
from src.language import Language
from src.utils import load_history_and_generate_answer, log_memory_usage

logger = getLogger(__name__)

ASK_NATIVE_LANGUAGE = 0
ASK_TARGET_LANGUAGE = 1
ASK_CURRENT_LEVEL = 2
ASK_GOAL = 3
ASK_SCENARIO = 4
EXECUTE_SCENARIO = 5


def register_conversation_handlers(app: Application):
    """Register all command and message handlers."""

    # Add conversation handler
    conversation_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_NATIVE_LANGUAGE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, ask_native_language)
            ],
            ASK_TARGET_LANGUAGE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, ask_target_language)
            ],
            ASK_CURRENT_LEVEL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, ask_current_level)
            ],
            ASK_GOAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_goal)],
            ASK_SCENARIO: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, ask_scenario)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conversation_handler)
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message)
    )
    app.add_handler(
        MessageHandler(
            filters.VOICE & ~filters.COMMAND, voice_handler.handle_voice_message
        )
    )


async def set_bot_commands(app: Application) -> None:
    """Set bot commands to show in Telegram GUI menu."""
    commands = [
        BotCommand("start", "Start learning Turkish "),
        # BotCommand("help", "Show help message "),
        # BotCommand("practice", "Start a practice session "),
        # BotCommand("progress", "View your learning progress "),
        BotCommand("morning_reminder", "Set morning practice time "),
        BotCommand("afternoon_reminder", "Set afternoon practice time "),
        BotCommand("evening_reminder", "Set evening practice time "),
        BotCommand("cancel", "Cancel current operation ")
    ]

    await app.bot.set_my_commands(commands)
    logger.info("Bot commands have been set")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the conversation and ask user for their native language."""
    user = update.message.from_user
    tg_id = user.id

    # Schedule daily practice sessions for this user
    # scheduler.schedule_daily_sessions(tg_id)
    # logger.info(f"Scheduled daily practice sessions for user {tg_id}")

    reply_keyboard = [[item.value for item in Language]]
    await update.message.reply_text(
        "Hi! I'm your language learning assistant. " "What is your native language?",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard,
            one_time_keyboard=True,
            input_field_placeholder="Your language?",
        ),
    )

    return ASK_NATIVE_LANGUAGE


async def ask_native_language(update: Update, context: CallbackContext) -> int:
    user_response = update.message.text.strip()
    context.user_data["native_language"] = user_response

    reply_keyboard = [[item.value for item in Language]]
    await update.message.reply_text(
        "Great! What language do you want to learn?",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard,
            one_time_keyboard=True,
            input_field_placeholder="Target language?",
        ),
    )

    return ASK_TARGET_LANGUAGE


async def ask_target_language(update: Update, context: CallbackContext) -> int:
    user_response = update.message.text.strip()
    context.user_data["target_language"] = user_response


    reply_keyboard = [["Beginner", "Intermediate", "Advanced", "Fluent"]]
    await update.message.reply_text(
        "What is your current level? (Beginner, Intermediate, Advanced, Fluent)",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard,
            one_time_keyboard=True,
            input_field_placeholder="Current level?",
        ),
    )

    return ASK_CURRENT_LEVEL


async def ask_current_level(update: Update, context: CallbackContext) -> int:
    user_response = update.message.text.strip()
    context.user_data["current_level"] = user_response
    await update.message.reply_text(
        "What is your goal? (e.g., reason for learning, timeframe, time available each week)"
    )
    return ASK_GOAL


async def ask_goal(update: Update, context: CallbackContext) -> int:
    user_response = update.message.text.strip()
    context.user_data["learning_goal"] = user_response
    # username, telegram_user_id, native_language, target_language,
    # current_level, target_level, learning_goal, weekly_hours

    # Save to database (make sure UsersRepository is defined elsewhere)
    user_id = update.message.from_user.id
    name = (
        update.message.from_user.first_name
    )  # Use first name instead of text for clarity
    UsersRepository.create_user(name, user_id, **context.user_data)

    await update.message.reply_text("Thanks! Your preferences have been saved.")

    await update.message.reply_text(
        "Welcome to your language learning session! From where would you like to start today?",
        reply_markup=ReplyKeyboardMarkup(
            [list(SCENARIO_PROMPTS.keys())], one_time_keyboard=True
        ),
    )
    return ASK_SCENARIO


async def ask_scenario(update: Update, context: CallbackContext) -> int:
    """Function to handle user's scenario choice"""
    log_memory_usage()
    tg_id = update.message.from_user.id
    scenario = update.message.text

    logger.info(f"Set current scenario to '{scenario}'.")
    context.user_data["current_scenario"] = (
        scenario  # Store selected scenario in user data
    )

    logger.info(f"Call LLM for the first prompt in the selected scenario")
    llm_response = load_history_and_generate_answer(tg_id, SCENARIO_PROMPTS[scenario])

    if llm_response:
        await update.message.reply_text(llm_response)

        logger.info(f"Saving user input and llm's response.")
        MessagesRepository.save_message(
            tg_id, f"[Scenario: {scenario}]" + llm_response, is_llm=True
        )

    # Continue in the scenario
    return EXECUTE_SCENARIO


async def handle_text_message(
        update: Update, context: CallbackContext, transcribed_text: str = None
):
    """Handle text messages or transcribed voice messages"""
    start_time = time.time()
    log_memory_usage()
    tg_id = update.message.from_user.id

    # Use transcribed text if provided, otherwise use the text message
    message_text = transcribed_text or update.message.text

    logger.info(f"Processing message from user '{tg_id}': {message_text}")

    try:
        # Save message to history
        current_scenario = get_current_scenario(context.user_data)
        MessagesRepository.save_message(
            tg_id, f"[Scenario: {current_scenario}] {message_text}"
        )

        # Generate response
        response = load_history_and_generate_answer(tg_id, message_text)

        # Save bot's response
        MessagesRepository.save_message(tg_id, response, is_llm=True)

        # Send response
        await update.message.reply_text(response)

        processing_time = time.time() - start_time
        logger.info(f"Message processing took {processing_time:.2f} seconds")
        log_memory_usage()

    except Exception as e:
        logger.error(f"Error processing message: {e}", exc_info=True)
        await update.message.reply_text(
            "I'm having trouble processing your message right now. Please try again in a moment."
        )


async def cancel(update: Update, context: CallbackContext) -> int:
    """Function to stop conversation"""
    await update.message.reply_text(
        "Goodbye! Feel free to come back anytime for more practice."
    )
    return ConversationHandler.END


def get_current_scenario(user_data):
    if not user_data.get("current_scenario"):
        user_data["current_scenario"] = "General Conversation"
    current_scenario = user_data["current_scenario"]
    logger.info(f"Current scenario is '{current_scenario}'.")
    return current_scenario
