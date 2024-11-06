import datetime as dt
from logging import getLogger
from typing import List, Union, Dict

from openai import OpenAI

from src.config import app_settings
from src.dal import MessagesRepository, UsersRepository

logger = getLogger(__name__)


def load_history_and_generate_answer(
    user_id: int,
    user_input: str,
    assistant_prompt: str = None,
) -> str:
    """
    Loads message history from DB, prepares the system prompt by enriching it with full message history
    or summarized message history and calls LLM.
    """
    if not user_input and not assistant_prompt:
        logger.info("User input and assistant prompt are empty. SKIPPING")
        return ""

    messages_history = MessagesRepository.get_recent_messages(user_id)

    user_data = UsersRepository.get_user_by_id(user_id)
    system_prompt_updated = update_system_prompt(
        messages_history, app_settings.SYSTEM_PROMPT, user_data
    )

    output = generate_answer(user_input, system_prompt_updated, assistant_prompt)

    return output


def update_system_prompt(
    messages: List[Dict[str, Union[str, dt.datetime]]],
    system_prompt: str = app_settings.SYSTEM_PROMPT,
    user_data=None,
) -> str:
    """Adds context (previous messages from the chat) to the system prompt."""

    logger.info(
        "Enriching system prompt with chat history for adding 'context knowledge' to model."
    )
    native_language = user_data[3]
    target_language = user_data[4]
    current_level = user_data[5]
    learning_goal = user_data[7]
    system_prompt = system_prompt.format(
        native_language=native_language,
        target_language=target_language,
        current_level=current_level,
        learning_goal=learning_goal,
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


def generate_answer(
    user_input: str, system_prompt: str = None, assistant_prompt: str = None
) -> str:
    """
    Calls LLM using system prompt and user's text message.
    Language model and system prompt are specified in .env configuration file.
    """
    if not user_input:
        logger.info("User input is empty. SKIPPING")
        return ""

    model = app_settings.LANGUAGE_MODEL

    start_time = dt.datetime.now()

    system_prompt = system_prompt if system_prompt else app_settings.SYSTEM_PROMPT
    system_prompt_updated = (
        f"Just in case someone asks you about what day is it today, "
        f"you know that current time is {start_time} and you answer the name "
        f"of a day of a week initially and say full date only "
        f"if you are explicitly asked to do this.\n\n" + system_prompt
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

    response = client.chat.completions.create(model=model, messages=messages)
    output = response.choices[0].message.content

    usage = response.usage
    logger.info(
        f"NUMBER OF TOKENS used per OpenAI API request: {usage.total_tokens}. "
        f"System prompt (+ conversation history): {usage.prompt_tokens}. "
        f"Generated response: {usage.completion_tokens}."
    )

    running_secs = (dt.datetime.now() - start_time).microseconds
    logger.info(f"Answer generation took {running_secs / 100000:.2f} seconds.")
    logger.info(f"LLM's output: {output}")

    return output
