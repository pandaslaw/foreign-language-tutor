import os
import time
import tempfile
from functools import wraps
from typing import Optional, Tuple
import logging
from pathlib import Path
import gc

# import whisper
# from gtts import gTTS
from telegram import Update
from telegram.ext import CallbackContext

logger = logging.getLogger(__name__)

# Initialize Whisper model globally to avoid reloading
MODEL = None


def init_whisper_model():
    """Initialize the Whisper model lazily"""
    global MODEL
    if MODEL is None:
        logger.info("Initializing Whisper model...")
        # MODEL = whisper.load_model("tiny")  # Only ~150MB
        logger.info("Whisper model initialized")


def cleanup_file(func):
    """Decorator to clean up temporary files after use"""

    @wraps(func)
    async def wrapper(*args, **kwargs):
        temp_files = []
        try:
            result = await func(*args, temp_files=temp_files, **kwargs)
            return result
        finally:
            for file in temp_files:
                try:
                    if os.path.exists(file):
                        os.remove(file)
                        logger.debug(f"Cleaned up temporary file: {file}")
                except Exception as e:
                    logger.error(f"Error cleaning up file {file}: {e}")
            # Force garbage collection after file operations
            gc.collect()

    return wrapper


class VoiceHandler:
    def __init__(self, temp_dir: Optional[str] = None):
        """Initialize voice handler with optional custom temp directory"""
        # Use a subdirectory in the temp directory for better organization
        self.temp_dir = os.path.join(
            temp_dir or tempfile.gettempdir(), "foreign_language_tutor"
        )
        try:
            # Create directory with full permissions if it doesn't exist
            if not os.path.exists(self.temp_dir):
                os.makedirs(self.temp_dir, mode=0o777, exist_ok=True)
            else:
                # Ensure directory has proper permissions
                os.chmod(self.temp_dir, 0o777)
            logger.info(f"Using temporary directory: {self.temp_dir}")
        except Exception as e:
            logger.error(f"Error creating/accessing temp directory: {e}")
            # Fallback to a directory in the current working directory
            self.temp_dir = os.path.join(os.getcwd(), "temp", "foreign_language_tutor")
            os.makedirs(self.temp_dir, mode=0o777, exist_ok=True)
            logger.info(f"Using fallback temporary directory: {self.temp_dir}")

        # Clean any leftover files from previous runs
        self._cleanup_temp_dir()

        # Initialize model
        init_whisper_model()

    def _cleanup_temp_dir(self):
        """Clean up old temporary files"""
        try:
            current_time = time.time()
            for file in os.listdir(self.temp_dir):
                file_path = os.path.join(self.temp_dir, file)
                try:
                    # Remove files older than 1 hour
                    if os.path.getctime(file_path) < current_time - 3600:
                        try:
                            os.remove(file_path)
                            logger.debug(f"Cleaned up old file: {file_path}")
                        except PermissionError:
                            logger.warning(f"Permission denied when cleaning up {file_path}")
                        except Exception as e:
                            logger.error(f"Error cleaning up old file {file_path}: {e}")
                except OSError as e:
                    logger.error(f"Error accessing file {file_path}: {e}")
        except Exception as e:
            logger.error(f"Error cleaning temp directory: {e}")

    @cleanup_file
    async def transcribe_voice_message(
        self, update: Update, context: CallbackContext, temp_files: list
    ) -> Tuple[bool, str]:
        """
        Transcribe a voice message from Telegram.
        Returns (success, text/error_message)
        """
        start_time = time.time()
        try:
            # Download voice message
            voice = update.message.voice
            file = await context.bot.get_file(voice.file_id)

            # Ensure unique filename with microsecond precision
            timestamp = update.message.date.timestamp()
            microsecond = int(time.time() * 1000000) % 1000000
            voice_path = os.path.join(
                self.temp_dir,
                f"voice_{voice.file_id}_{timestamp}_{microsecond}.ogg",
            )
            temp_files.append(voice_path)

            # Ensure parent directory exists with proper permissions
            os.makedirs(os.path.dirname(voice_path), mode=0o777, exist_ok=True)

            logger.info(f"Downloading voice message to {voice_path}")
            try:
                await file.download_to_drive(voice_path)
                # Set file permissions
                os.chmod(voice_path, 0o666)
            except Exception as e:
                logger.error(f"Error downloading voice file: {e}")
                raise

            if not os.path.exists(voice_path):
                raise FileNotFoundError(
                    f"Voice file was not downloaded to {voice_path}"
                )

            logger.info("Starting transcription...")
            # Transcribe
            result = MODEL.transcribe(
                voice_path, fp16=False
            )  # Force FP32 to avoid warnings
            transcribed_text = result["text"].strip()

            if not transcribed_text:
                return (
                    False,
                    "Sorry, I couldn't understand the audio. Please try speaking clearly and avoid background noise.",
                )

            processing_time = time.time() - start_time
            logger.info(
                f"Successfully transcribed in {processing_time:.2f}s: {transcribed_text}"
            )
            return True, transcribed_text

        except FileNotFoundError as e:
            logger.error(f"File not found error: {e}")
            return (
                False,
                "Sorry, there was an error saving your voice message. Please try again.",
            )
        except Exception as e:
            logger.error(f"Error transcribing voice message: {e}", exc_info=True)
            return (
                False,
                "Sorry, there was an error processing your voice message. Please try again.",
            )
        finally:
            # Force garbage collection after heavy processing
            gc.collect()

    @cleanup_file
    async def text_to_voice(
        self, text: str, lang: str = "tr", temp_files=None
    ) -> Tuple[bool, str]:
        """
        Convert text to voice using gTTS.
        Returns (success, file_path/error_message)
        """
        start_time = time.time()
        temp_files = [] if not temp_files else temp_files
        try:
            # Generate audio file with unique name
            voice_path = os.path.join(
                self.temp_dir, f"response_{hash(text)}_{int(time.time())}.mp3"
            )
            temp_files.append(voice_path)

            logger.info(f"Generating voice response to {voice_path}")
            tts = gTTS(text=text, lang=lang, slow=False)
            tts.save(voice_path)

            if not os.path.exists(voice_path):
                raise FileNotFoundError(
                    f"Voice response file was not created at {voice_path}"
                )

            processing_time = time.time() - start_time
            logger.info(f"Generated voice response in {processing_time:.2f}s")
            return True, voice_path

        except Exception as e:
            logger.error(f"Error converting text to voice: {e}", exc_info=True)
            return False, "Sorry, there was an error generating the voice message."
        finally:
            # Force garbage collection after processing
            gc.collect()

    async def handle_voice_message(self, update: Update, context: CallbackContext):
        """Handle incoming voice messages"""
        chat_id = update.message.chat_id
        start_time = time.time()

        logger.info(f"Received voice message from user {update.message.from_user.id}")

        try:
            # Send typing indicator
            await context.bot.send_chat_action(chat_id=chat_id, action="typing")

            # Transcribe voice
            success, result = await self.transcribe_voice_message(update, context)
            if not success:
                await update.message.reply_text(result)
                return

            # Echo what we understood
            await update.message.reply_text(
                f"In your voice message you said:\n'{result}'"
            )

            # Process the text message normally using the existing handler
            from src.run_bot import handle_text_message

            await handle_text_message(update, context, result)

            # Generate voice response
            await context.bot.send_chat_action(chat_id=chat_id, action="record_voice")
            await update.message.reply_text("Recording answer for you...")

            # Get the last bot response from the message history
            from src.dal import MessagesRepository

            last_messages = MessagesRepository.get_recent_messages(
                update.message.from_user.id, limit=1
            )
            if not last_messages:
                logger.warning("No response found in message history")
                return

            last_response = last_messages[0]["message_text"]
            logger.info("Converting bot response to voice")

            # Convert to voice and send
            success, voice_path = await self.text_to_voice(last_response)
            if success:
                # Send voice response
                try:
                    with open(voice_path, "rb") as audio:
                        await update.message.reply_voice(voice=audio)
                    # Send text version
                    await update.message.reply_text(
                        f"Text version of my response:\n{last_response}"
                    )
                except Exception as e:
                    logger.error(f"Error sending voice response: {e}", exc_info=True)
                    await update.message.reply_text(
                        "Sorry, I couldn't send the voice message, but here's my text response:\n{last_response}"
                    )
            else:
                logger.error(f"Failed to generate voice response: {voice_path}")
                await update.message.reply_text(
                    "Sorry, I couldn't generate a voice message, but here's my text response:\n{last_response}"
                )

        except Exception as e:
            logger.error(f"Error in voice message handler: {e}", exc_info=True)
            await update.message.reply_text(
                "Sorry, I encountered an error processing your voice message. Please try again."
            )
        finally:
            processing_time = time.time() - start_time
            logger.info(f"Total voice message processing took {processing_time:.2f}s")
            gc.collect()  # Final garbage collection

    def analyze_pronunciation(self, text: str, target_language: str) -> str:
        """Analyze pronunciation and provide feedback"""
        # This uses your existing OpenAI integration
        from src.utils import generate_answer

        prompt = f"""
        Act as a {target_language} language tutor. The user provided the following transcribed speech:
        "{text}"
        
        Provide concise feedback on:
        1. Pronunciation issues (if any can be inferred from text)
        2. Grammar mistakes and corrections
        3. One quick tip for improvement
        
        Keep the response brief and friendly.
        """

        return generate_answer(prompt)
