from logging import getLogger

from telegram import ReplyKeyboardMarkup
from telegram import Update
from telegram.ext import (
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    CallbackContext,
    ApplicationBuilder,
)

from src.config import app_settings, SCENARIO_PROMPTS
from src.dal import MessagesRepository, UsersRepository
from src.utils import load_history_and_generate_answer

logger = getLogger(__name__)

ASK_NATIVE_LANGUAGE = 0
ASK_TARGET_LANGUAGE = 1
ASK_CURRENT_LEVEL = 2
ASK_GOAL = 3

ASK_SCENARIO = 4
EXECUTE_SCENARIO = 5


# @bot.message_handler(commands=["daily_phrase"])
# def send_daily_phrase(message: Message):
#     phrase, translation = random.choice(phrases)
#     bot.send_message(
#         message.chat.id, f"📚 Сегодняшняя фраза:\n\n{phrase} – {translation}"
#     )
#
#
# @bot.message_handler(commands=["quiz"])
# def ask_question(message: Message):
#     question, correct_answer = random.choice(questions)
#     bot.send_message(message.chat.id, question)
#     bot.register_next_step_handler(
#         message, lambda msg: check_answer(msg, correct_answer)
#     )
#
#
# def check_answer(message: Message, correct_answer: str):
#     if message.text.strip().lower() == correct_answer.lower():
#         bot.send_message(message.chat.id, "✅ Правильно! Молодец!")
#     else:
#         bot.send_message(
#             message.chat.id, f"❌ Неправильно. Правильный ответ: {correct_answer}"
#         )
#
#
# def remind_task(chat_id):
#     while True:
#         time.sleep(24 * 60 * 60)  # 24 часа
#         bot.send_message(
#             chat_id,
#             "🕐 Пора немного позаниматься турецким! Введи /quiz или /daily_phrase.",
#         )
#
#
# def start_reminder(chat_id):
#     reminder_thread = Thread(target=remind_task, args=(chat_id,))
#     reminder_thread.start()
#
#
# @bot.message_handler(commands=["start_reminder"])
# def start_reminder_handler(message: Message):
#     bot.send_message(message.chat.id, "Запускаю ежедневные напоминания.")
#     start_reminder(message.chat.id)


async def start(update: Update, context: CallbackContext) -> int:
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
    return ASK_SCENARIO


async def ask_scenario(update: Update, context: CallbackContext) -> int:
    """Function to handle user's scenario choice"""
    # await update.message.reply_text(
    #     "Welcome to your language learning session! From where would you like to start today?",
    #     reply_markup=ReplyKeyboardMarkup([list(SCENARIO_PROMPTS.keys())], one_time_keyboard=True)
    # )
    tg_id = update.message.from_user.id
    scenario = update.message.text
    context.user_data["current_scenario"] = (
        scenario  # Store selected scenario in user data
    )

    # Call the LLM for the first prompt in the selected scenario
    llm_response = load_history_and_generate_answer(tg_id, SCENARIO_PROMPTS[scenario])
    await update.message.reply_text(llm_response)

    MessagesRepository.save_message(tg_id, scenario)
    MessagesRepository.save_message(tg_id, llm_response, is_llm=True)

    # Continue in the scenario
    return EXECUTE_SCENARIO


async def execute_scenario(update: Update, context: CallbackContext) -> int:
    """Function to continue scenario execution until the user opts to stop or switch"""
    tg_id = update.message.from_user.id
    user_input = update.message.text.lower()

    if user_input in ["stop", "switch"]:
        await update.message.reply_text(
            "Would you like to continue with another scenario?",
            reply_markup=ReplyKeyboardMarkup(
                [list(SCENARIO_PROMPTS.keys())], one_time_keyboard=True
            ),
        )
        return ASK_SCENARIO  # Go back to ask scenario

    current_scenario = context.user_data["current_scenario"]
    llm_response = load_history_and_generate_answer(
        tg_id, user_input, SCENARIO_PROMPTS[current_scenario]
    )
    await update.message.reply_text(llm_response)

    MessagesRepository.save_message(tg_id, user_input)
    MessagesRepository.save_message(tg_id, llm_response, is_llm=True)

    return EXECUTE_SCENARIO


async def cancel(update: Update, context: CallbackContext) -> int:
    """Function to stop conversation"""
    await update.message.reply_text(
        "Goodbye! Feel free to come back anytime for more practice."
    )
    return ConversationHandler.END


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
        ASK_SCENARIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_scenario)],
        EXECUTE_SCENARIO: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, execute_scenario)
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

# Create the application and add the conversation handler
app = ApplicationBuilder().token(app_settings.TELEGRAM_BOT_TOKEN).build()

app.add_handler(conversation_handler)

if __name__ == "__main__":
    logger.info("~~~Send any message to a bot to start chatting~~~")
    app.run_polling()
