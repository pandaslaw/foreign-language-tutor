import os
import sys
import asyncio
import codecs

from pathlib import Path

# Set up UTF-8 output for Turkish characters
if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.voice_handler import VoiceHandler
from src.config import app_settings
from elevenlabs import ElevenLabs


async def gen_voice():
    handler = VoiceHandler()

    test_texts = [
        # Morning greeting (warm and energetic)
        "Günaydın! Nasılsın? Umarım güzel bir gün geçiriyorsun. Bugün seninle Türkçe pratik yapalım!",

        # Midday conversation (natural and friendly)
        "Öğle yemeğinde ne yedin? Ben genellikle Türk mutfağından mercimek çorbası ve köfte tercih ediyorum.",

        # Evening reflection (warm and soulful)
        "Bugün çok iyi çalıştın! Yeni kelimeler öğrendin ve güzel cümleler kurdun. Seninle gurur duyuyorum!"
    ]

    # Initialize ElevenLabs client
    client = ElevenLabs(api_key=app_settings.ELEVENLABS_API_KEY)

    # List available voices
    print("\nAvailable voices:")
    voices_response = client.voices.get_all()

    # Find a suitable voice for our needs
    target_voice = None
    for voice in voices_response.voices:
        print(f"\nVoice: {voice.name}")
        print(f"ID: {voice.voice_id}")
        print(f"Description: {voice.description if hasattr(voice, 'description') else 'N/A'}")
        print(f"Labels: {voice.labels if hasattr(voice, 'labels') else {} }")

        # Look for a warm, friendly female voice
        if hasattr(voice, 'labels') and voice.labels.get('gender') == 'female':
            target_voice = voice
            print("*** This voice matches our criteria! ***")

    if not target_voice:
        print("\nNo ideal voice found. Using the first available voice.")
        target_voice = voices_response.voices[0]

    print(f"\nUsing voice: {target_voice.name}")
    print("Voice settings:", handler.VOICE_SETTINGS)
    print("\nTesting voice generation with different contexts...")

    for text in test_texts:
        print(f"\nGenerating voice for text:\n{text}")
        success, result = await handler.text_to_voice(text, voice_name=target_voice.name)

        if success:
            print("Playing audio...")
            os.system(f'start {result}')

            response = input("\nRate this sample (1-5) or press Enter to continue, 'q' to quit: ")
            if response.lower() == 'q':
                break
            elif response.strip() and response.isdigit():
                rating = int(response)
                if 1 <= rating <= 5:
                    print(f"You rated this sample: {rating}/5")
        else:
            print(f"Error generating voice: {result}")

        print("\nPress Enter to continue to next sample...")
        input()


if __name__ == "__main__":
    asyncio.run(gen_voice())
