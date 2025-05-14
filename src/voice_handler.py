import asyncio
import gc
import logging
import os
import tempfile
import time
from functools import wraps
from typing import Optional, Tuple

import openai
from google.cloud import texttospeech
from telegram import Update
from telegram.ext import CallbackContext

from src.config import app_settings
from src.message_processor import process_text_message, get_last_bot_response
from src.language_detection import detect_language, get_voice_for_language

# Disable symlinks warning
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

logger = logging.getLogger(__name__)

# Initialize API keys
# openai.api_key = app_settings.OPENAI_API_KEY

# Initialize Google Cloud TTS client
# Google credentials are loaded from the path specified in environment variable
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = app_settings.GOOGLE_APPLICATION_CREDENTIALS
client = texttospeech.TextToSpeechClient()

# Initialize Whisper model (download happens only once)
from faster_whisper import WhisperModel

logger.info("Downloading of base whisper model started.")
whisper_model = WhisperModel(
    "base",
    device="cpu",
    compute_type="int8",
    download_root=os.path.join(os.path.dirname(__file__), "..", "models"),
)
logger.info("Downloading of base whisper model completed.")

# Google TTS voice settings for a warm, moderately slow Turkish female voice
GOOGLE_TTS_VOICE = "tr-TR-Standard-D"  # or "tr-TR-Wavenet-D" for higher quality
GOOGLE_TTS_SPEAKING_RATE = 0.85  # Slightly slower than default
GOOGLE_TTS_PITCH = 0.0  # Neutral pitch


def get_voice_by_name(name: str = None) -> Optional[str]:
    """Get ElevenLabs voice by name with caching."""
    global VOICE_CACHE
    try:
        if VOICE_CACHE is None:
            voices_response = client.voices.get_all()
            VOICE_CACHE = {
                voice.name: voice.voice_id for voice in voices_response.voices
            }

        if name and name in VOICE_CACHE:
            return VOICE_CACHE[name]

        # If no name specified or not found, return first voice
        return list(VOICE_CACHE.values())[0] if VOICE_CACHE else None

    except Exception as e:
        logger.error(f"Error getting ElevenLabs voices: {e}")
        return None


def cleanup_file(func):
    """Decorator to clean up temporary files after use"""

    @wraps(func)
    async def wrapper(*args, **kwargs):
        temp_files = []
        try:
            if "temp_files" in kwargs:
                temp_files = kwargs["temp_files"]
            return await func(*args, **kwargs)
        finally:
            for file in temp_files:
                try:
                    if os.path.exists(file):
                        os.remove(file)
                except Exception as e:
                    logger.error(f"Error cleaning up file {file}: {e}")
            gc.collect()

    return wrapper


class VoiceHandler:
    def __init__(self, temp_dir: Optional[str] = None):
        """Initialize voice handler with optional custom temp directory"""
        self.temp_dir = temp_dir or tempfile.gettempdir()
        os.makedirs(self.temp_dir, exist_ok=True)

    def _get_temp_path(self, prefix: str, suffix: str) -> str:
        """Generate a temporary file path."""
        timestamp = int(time.time() * 1000)
        filename = f"{prefix}_{timestamp}{suffix}"
        return os.path.join(self.temp_dir, filename)

    @cleanup_file
    async def transcribe_voice_message(
        self, update: Update, context: CallbackContext, temp_files: list
    ) -> Tuple[bool, str]:
        """
        Transcribe a voice message using Faster Whisper.
        Returns: Tuple[success: bool, text: str]
        """
        try:
            # Get voice message file
            voice_message = update.message.voice
            if not voice_message:
                return False, "No voice message found"

            # Download voice file
            voice_file = await context.bot.get_file(voice_message.file_id)

            # Save to temporary file
            temp_path = self._get_temp_path("voice_message", ".ogg")
            await voice_file.download_to_drive(temp_path)
            temp_files.append(temp_path)

            # Convert to text using Whisper
            segments, info = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: whisper_model.transcribe(
                    temp_path,
                    # language="tr",  # Specify Turkish for better accuracy
                    beam_size=5,  # Increase beam size for better accuracy
                    vad_filter=True,  # Filter out non-speech
                    word_timestamps=False,  # No need for timestamps
                ),
            )

            # Combine all segments into final text
            text = " ".join(segment.text for segment in segments)

            return True, text.strip()

        except Exception as e:
            logger.error(f"Error in transcribe_voice_message: {e}")
            return False, str(e)

    @cleanup_file
    async def text_to_voice(
        self, text: str, lang: str = None, temp_files=None, voice_name: str = None
    ) -> Tuple[bool, str]:
        """
        Convert text to voice using Google Cloud TTS.
        Returns: Tuple[success: bool, file_path: str]
        """
        temp_files = [] if not temp_files else temp_files
        try:
            # Detect language from text if not specified
            detected_lang = lang or detect_language(text)
            
            # Get appropriate voice model for the detected language
            language_code, tts_voice = get_voice_for_language(detected_lang, app_settings)
            
            logger.info(f"Using voice {tts_voice} for language {detected_lang} (code: {language_code})")

            # Generate audio file with unique name
            voice_path = self._get_temp_path("voice_response", ".mp3")
            temp_files.append(voice_path)

            logger.info(f"Generating voice response to {voice_path}")

            # Add natural pauses for more engaging speech
            text = text.replace("!", "! ... ")
            text = text.replace(".", ". ... ")
            text = text.replace("?", "? ... ")

            synthesis_input = texttospeech.SynthesisInput(text=text)
            voice = texttospeech.VoiceSelectionParams(
                language_code=language_code,
                name=tts_voice,
                ssml_gender=texttospeech.SsmlVoiceGender.FEMALE,
            )
            
            logger.info(f"Synthesizing speech with voice: {tts_voice}, language: {language_code}")
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=GOOGLE_TTS_SPEAKING_RATE,
                pitch=GOOGLE_TTS_PITCH,
            )

            response = client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config,
            )

            with open(voice_path, "wb") as out:
                out.write(response.audio_content)

            return True, voice_path

        except Exception as e:
            logger.error(f"Error in text_to_voice: {e}")
            return False, str(e)


    async def handle_voice_message(self, update: Update, context: CallbackContext):
        """Handle incoming voice messages"""
        chat_id = update.effective_chat.id
        if not chat_id:
            return

        start_time = time.time()

        logger.info(f"Received voice message from user {update.message.from_user.id}")

        try:
            # Send typing indicator
            await context.bot.send_chat_action(chat_id=chat_id, action="typing")

            # Transcribe voice
            success, result = await self.transcribe_voice_message(update, context, [])
            if not success:
                await update.message.reply_text(result)
                return

            # Detect language of the transcribed text
            input_language = detect_language(result)
            logger.info(f"Detected language of voice message: {input_language}")
            
            # Echo what we understood
            await update.message.reply_text(
                f"In your voice message you said:\n'{result}'"
            )

            # Process the transcribed text message through the message processor
            await process_text_message(update, context, result)

            # Generate voice response
            await context.bot.send_chat_action(chat_id=chat_id, action="record_voice")
            await update.message.reply_text("Recording answer for you...")

            # Get the last bot response from the message history
            last_response = await get_last_bot_response(update.message.from_user.id)
            if not last_response:
                logger.warning("No response found in message history")
                return
            
            logger.info("Converting bot response to voice")

            # Convert to voice and send - use the same language as the input
            success, voice_path = await self.text_to_voice(last_response, lang=input_language)
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
