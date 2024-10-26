import random
import time
from logging import getLogger
from threading import Thread

import telebot
from telebot.types import Message

from src.config import app_settings
from src.dal import MessagesRepository, UsersRepository
from src.utils import generate_answer

logger = getLogger(__name__)

bot = telebot.TeleBot(app_settings.TELEGRAM_BOT_TOKEN)

phrases = [
    ("Merhaba", "Привет"),
    ("Teşekkür ederim", "Спасибо"),
    ("Nasılsın?", "Как дела?"),
]

questions = [
    ("Как на турецком 'Привет'?", "Merhaba"),
    ("Как на турецком 'Спасибо'?", "Teşekkür ederim"),
]


@bot.message_handler(commands=["start"])
def send_welcome(message: Message):
    bot.send_message(message.chat.id, "Merhaba! Меня зовут Лейла. Давай начнем учить турецкий вместе! Как тебя зовут?")
    bot.register_next_step_handler(message, save_name)


def save_name(message: Message):
    name = message.text
    user_id = message.from_user.id

    UsersRepository.create_user(name, user_id)

    bot.send_message(message.chat.id,
                     f"Очень приятно, {name}! Почему ты хочешь выучить турецкий? Что ожидаешь от обучения?")
    bot.register_next_step_handler(message, save_goal)


def save_goal(message: Message):
    goal = message.text
    user_id = message.from_user.id

    UsersRepository.update_goal(user_id, goal)

    bot.send_message(message.chat.id, "Отлично! Я подготовила план, чтобы помочь тебе достигнуть твоих целей.")


@bot.message_handler(commands=["daily_phrase"])
def send_daily_phrase(message: Message):
    phrase, translation = random.choice(phrases)
    bot.send_message(message.chat.id, f"📚 Сегодняшняя фраза:\n\n{phrase} – {translation}")


@bot.message_handler(commands=["quiz"])
def ask_question(message: Message):
    question, correct_answer = random.choice(questions)
    bot.send_message(message.chat.id, question)
    bot.register_next_step_handler(message, lambda msg: check_answer(msg, correct_answer))


def check_answer(message: Message, correct_answer: str):
    if message.text.strip().lower() == correct_answer.lower():
        bot.send_message(message.chat.id, "✅ Правильно! Молодец!")
    else:
        bot.send_message(message.chat.id, f"❌ Неправильно. Правильный ответ: {correct_answer}")


def remind_task(chat_id):
    while True:
        time.sleep(24 * 60 * 60)  # 24 часа
        bot.send_message(chat_id, "🕐 Пора немного позаниматься турецким! Введи /quiz или /daily_phrase.")


def start_reminder(chat_id):
    reminder_thread = Thread(target=remind_task, args=(chat_id,))
    reminder_thread.start()


@bot.message_handler(commands=["start_reminder"])
def start_reminder_handler(message: Message):
    bot.send_message(message.chat.id, "Запускаю ежедневные напоминания.")
    start_reminder(message.chat.id)


# @bot.message_handler(func=lambda msg: True)
# def log_and_respond(message: Message):
#     MessagesRepository.save_message(message.from_user.id, message.text)
#     bot.send_message(message.chat.id, "Сообщение записано!")


@bot.message_handler(commands=["exercise"])
def start_exercise(message):
    bot.send_message(message.chat.id, "📚 Давай начнем упражнение. Привет, как ты на турецком?")
    user_id = message.from_user.id
    chat_history = []

    bot.register_next_step_handler(message, lambda msg: handle_exercise(msg, user_id, chat_history))


def handle_exercise(message, user_id, chat_history):
    user_message = message.text

    llm_response = generate_answer(user_message, chat_history=chat_history)
    chat_history.append({"role": "user", "content": user_message})

    bot.send_message(message.chat.id, llm_response)

    MessagesRepository.save_message(user_id, user_message)
    MessagesRepository.save_message(user_id, llm_response, is_llm=True)

    bot.register_next_step_handler(message, lambda msg: handle_exercise(msg, user_id, chat_history))


if __name__ == "__main__":
    logger.info("~~~Send any message to a bot to start chatting~~~")
    bot.infinity_polling()
