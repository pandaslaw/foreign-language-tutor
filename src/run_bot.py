from logging import getLogger

from telegram import ReplyKeyboardMarkup
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    CallbackContext,
    ContextTypes,
    ApplicationBuilder,
)

from src.config import app_settings, SCENARIO_PROMPTS
from src.dal import MessagesRepository, UsersRepository
from src.utils import load_history_and_generate_answer, transcribe_audio
from src.voice_handler import VoiceHandler
from src.admin_handlers import health_check, send_today_logs, send_all_logs

import os
import psutil
import time
import logging

logger = getLogger(__name__)


def log_memory_usage():
    """Log current memory usage"""
    process = psutil.Process(os.getpid())
    mem_info = process.memory_info()
    logger.info(
        f"Memory usage - RSS: {mem_info.rss / 1024 / 1024:.1f}MB, VMS: {mem_info.vms / 1024 / 1024:.1f}MB"
    )


ASK_NATIVE_LANGUAGE = 0
ASK_TARGET_LANGUAGE = 1
ASK_CURRENT_LEVEL = 2
ASK_GOAL = 3

ASK_SCENARIO = 4
EXECUTE_SCENARIO = 5


async def start(update: Update, context: CallbackContext) -> int:
    log_memory_usage()
    logger.info(f"/start command was executed. Greeting the user.")
    if UsersRepository.get_user_by_id(update.message.from_user.id):
        await update.message.reply_text(
            "Welcome to your language learning session! From where would you like to start today?",
            reply_markup=ReplyKeyboardMarkup(
                [list(SCENARIO_PROMPTS.keys())], one_time_keyboard=True
            ),
        )
        return ASK_SCENARIO

    await update.message.reply_text(
        "Welcome! Let's get started with some quick questions."
    )
    await update.message.reply_text(
        "What is your native language? (e.g., Russian, English, Spanish, Turkish)"
    )
    return ASK_NATIVE_LANGUAGE


async def ask_native_language(update: Update, context: CallbackContext) -> int:
    user_response = update.message.text.strip()
    context.user_data["native_language"] = user_response
    await update.message.reply_text("Great! What language do you want to learn?")
    return ASK_TARGET_LANGUAGE


async def ask_target_language(update: Update, context: CallbackContext) -> int:
    user_response = update.message.text.strip()
    context.user_data["target_language"] = user_response
    await update.message.reply_text(
        "What is your current level? (Beginner, Intermediate, Advanced, Fluent)"
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


if __name__ == "__main__":
    log_memory_usage()
    logger.info("~~~Send any message to a bot to start chatting~~~")
    # Create the application and add the conversation handler
    app = ApplicationBuilder().token(app_settings.TELEGRAM_BOT_TOKEN).build()

    # Add admin command handlers
    app.add_handler(CommandHandler("health", health_check))
    app.add_handler(CommandHandler("send_logs", send_today_logs))
    app.add_handler(CommandHandler("send_all_logs", send_all_logs))

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
            # EXECUTE_SCENARIO: [
            #     MessageHandler(filters.TEXT & ~filters.COMMAND, execute_scenario)
            # ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conversation_handler)
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message)
    )
    app.add_handler(
        MessageHandler(
            filters.VOICE & ~filters.COMMAND, VoiceHandler().handle_voice_message
        )
    )

    logger.info("Starting bot...")
    app.run_polling()
