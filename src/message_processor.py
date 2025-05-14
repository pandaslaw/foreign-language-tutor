"""
Message processing module that handles both text and voice messages.
This module serves as a central point for processing messages to avoid circular imports.
"""

import time
import logging
from typing import Optional

from telegram import Update
from telegram.ext import CallbackContext

from src.dal import MessagesRepository
from src.utils import load_history_and_generate_answer, log_memory_usage

logger = logging.getLogger(__name__)


def get_current_scenario(user_data):
    """Get the current scenario from user data or default to General Conversation."""
    if not user_data.get("current_scenario"):
        user_data["current_scenario"] = "General Conversation"
    current_scenario = user_data["current_scenario"]
    logger.info(f"Current scenario is '{current_scenario}'.")
    return current_scenario


async def process_text_message(
    update: Update, context: CallbackContext, transcribed_text: Optional[str] = None
):
    """
    Process a text message or transcribed voice message.
    
    Args:
        update: The Telegram update object
        context: The callback context
        transcribed_text: Optional transcribed text from a voice message
    """
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
        
        return response

    except Exception as e:
        logger.error(f"Error processing message: {e}", exc_info=True)
        error_response = "I'm having trouble processing your message right now. Please try again in a moment."
        await update.message.reply_text(error_response)
        return error_response


async def get_last_bot_response(user_id: int) -> Optional[str]:
    """
    Get the last bot response from the message history.
    
    Args:
        user_id: The Telegram user ID
        
    Returns:
        The last bot response or None if not found
    """
    last_messages = MessagesRepository.get_recent_messages(user_id, limit=1)
    if not last_messages:
        logger.warning("No response found in message history")
        return None
    
    return last_messages[0]["content"]
