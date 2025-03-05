import datetime as dt
import time
import gc
from logging import getLogger
from typing import List, Union, Dict
import re

from openai import OpenAI

from src.config import app_settings
from src.dal import MessagesRepository, UsersRepository

logger = getLogger(__name__)


def clean_llm_response(text: str) -> str:
    """Remove problematic markdown formatting from LLM responses."""
    # Remove markdown headers (e.g., #### Title)
    text = re.sub(r"^#{1,6}\s+(.+?)$", r"\1", text, flags=re.MULTILINE)
    # Remove double asterisks (bold)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    # Remove single asterisks (italic)
    text = re.sub(r"\*([^*]+?)\*", r"\1", text)
    # Remove triple backticks (code blocks)
    text = re.sub(r"```[^\n]*\n(.+?)```", r"\1", text, flags=re.DOTALL)
    # Remove single backticks (inline code)
    text = re.sub(r"`([^`]+?)`", r"\1", text)
    return text


def load_history_and_generate_answer(
    user_id: int,
    user_input: str,
    assistant_prompt: str = None,
) -> str:
    """
    Loads message history from DB, prepares the system prompt by enriching it with full message history
    or summarized message history and calls LLM.
    """
    start_time = time.time()
    try:
        if not user_input and not assistant_prompt:
            logger.info("User input and assistant prompt are empty. SKIPPING")
            return ""

        # Get user data and recent messages
        user_data = UsersRepository.get_user_by_id(user_id)
        messages_history = MessagesRepository.get_recent_messages(
            user_id, limit=10
        )  # Reduced from 50 to save memory

        # Update system prompt
        system_prompt_updated = update_system_prompt(
            messages_history, app_settings.SYSTEM_PROMPT, user_data
        )

        # Generate response
        output = generate_answer(user_input, system_prompt_updated, assistant_prompt)

        processing_time = time.time() - start_time
        logger.info(f"Total message processing took {processing_time:.2f}s")
        return output

    except Exception as e:
        logger.error(f"Error generating response: {e}", exc_info=True)
        return "I'm having trouble processing your message right now. Please try again in a moment."
    finally:
        gc.collect()  # Force garbage collection


def generate_answer(
    user_input: str, system_prompt: str = None, assistant_prompt: str = None
) -> str:
    """
    Calls LLM using system prompt and user's text message.
    Language model and system prompt are specified in .env configuration file.
    """
    start_time = time.time()
    try:
        if not user_input and not assistant_prompt:
            logger.info("User input is empty. SKIPPING")
            return ""

        model = app_settings.LANGUAGE_MODEL
        system_prompt = system_prompt if system_prompt else app_settings.SYSTEM_PROMPT

        # Update system prompt with current time and formatting instructions
        system_prompt_updated = (
            f"Just in case someone asks you about what day is it today, "
            f"you know that current time is {start_time} and you answer the name "
            f"of a day of a week initially and say full date only "
            f"if you are explicitly asked to do this.\n\n"
            f"IMPORTANT: Do not use any markdown formatting in your responses. "
            f"Specifically:\n"
            f"- Do not use asterisks (*) or backticks (`) for emphasis\n"
            f"- Do not use hashtags (#) for headers\n"
            f"- Do not use any other special formatting characters\n"
            f"Just write plain text.\n\n" + system_prompt
        )

        if assistant_prompt:
            user_input = assistant_prompt + user_input
            logger.info(
                f"ASSISTANT PROMPT is specified (user_input is going "
                f"to be substituted by it): '{user_input}'"
            )

        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=app_settings.OPENROUTER_API_KEY,
        )

        logger.info(
            f"USER PROMPT (user input, the message that is sent to LLM): '{user_input}'"
        )
        messages = [
            {"role": "system", "content": system_prompt_updated},
            {"role": "user", "content": user_input},
        ]

        logger.info("Generating LLM response... ")

        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.7,  # Lower temperature for more focused responses
            max_tokens=500,  # Limit response length
        )
        output = response.choices[0].message.content

        # Clean any markdown formatting from the response
        output = clean_llm_response(output)

        usage = response.usage
        logger.info(
            f"NUMBER OF TOKENS used per OpenAI API request: {usage.total_tokens}. "
            f"System prompt (+ conversation history): {usage.prompt_tokens}. "
            f"Generated response: {usage.completion_tokens}."
        )

        processing_time = time.time() - start_time
        logger.info(f"LLM response generation took {processing_time:.2f}s")
        logger.info(f"LLM's output: {output}")

        return output

    except Exception as e:
        logger.error(f"Error in LLM call: {e}", exc_info=True)
        return "I'm having trouble generating a response right now. Please try again in a moment."
    finally:
        gc.collect()  # Force garbage collection


def update_system_prompt(
    messages: List[Dict[str, Union[str, dt.datetime]]],
    system_prompt: str = app_settings.SYSTEM_PROMPT,
    user_data=None,
) -> str:
    """Adds context (previous messages from the chat) to the system prompt."""

    logger.info(
        "Enriching system prompt with chat history for adding 'context knowledge' to model."
    )
    system_prompt = system_prompt.format(
        native_language=user_data["native_language"],
        target_language=user_data["target_language"],
        current_level=user_data["current_level"],
        learning_goal=user_data["learning_goal"],
    )

    summarized_history = summarize_history(messages)
    updated_prompt = f"{system_prompt}\n{summarized_history}"

    return updated_prompt


def summarize_history(
    messages: List[Dict[str, Union[str, dt.datetime]]], n_last_messages: int = None
) -> str:
    """
    Condense older messages to reduce token usage. Returns a string summary.
    """
    if n_last_messages and len(messages) > n_last_messages:
        prefix = f"Latest messages in the conversation are: "

        # TODO: add summarization with AI for cases when history of dialogue is too long
        summary = "Summary of previous conversations: " + " ".join(
            msg["content"] for msg in messages[:-n_last_messages]
        )

        recent_messages = messages[-n_last_messages:]
    else:
        summary = ""
        prefix = "The history of your conversation with user:"
        recent_messages = messages

    messages_str = MessagesRepository.join_messages_to_string(recent_messages)

    previous_dialogue = f"{summary}\n{prefix}\n{messages_str}"
    logger.info(
        "Format SYSTEM PROMPT with the conversation history:\n"
        + previous_dialogue
        + "\n\n"
    )
    return previous_dialogue


def transcribe_audio(file_path):
    # model = whisper.load_model("base")  # models: base, small, medium, large)
    # result = model.transcribe(file_path)  #  language="en"
    # return result["text"]
    return "stub_text"
