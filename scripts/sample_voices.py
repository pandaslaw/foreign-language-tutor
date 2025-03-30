import os
import time
from elevenlabs import generate, voices, set_api_key, Voice
from dotenv import load_dotenv

load_dotenv()

# Initialize API key
api_key = os.getenv("ELEVENLABS_API_KEY")
if not api_key:
    raise ValueError("Please set ELEVENLABS_API_KEY in your .env file")
set_api_key(api_key)

# Test text in both English and Turkish
test_texts = [
    "Merhaba! Nasılsın? Bugün seninle Türkçe pratik yapalım.",  # Turkish
    "Hello! How are you? Let's practice Turkish together today.",  # English
    "Kendine iyi bak, görüşürüz!",  # Warm goodbye in Turkish
]

def get_voice_description(voice):
    """Safely get voice description in lowercase."""
    try:
        if hasattr(voice, 'description') and voice.description:
            return voice.description.lower()
        return ''
    except:
        return ''

def preview_voice(voice: Voice):
    """Generate and play sample audio for a voice"""
    print(f"\nTesting voice: {voice.name}")
    
    for text in test_texts:
        print(f"\nGenerating: {text}")
        try:
            # Generate audio
            audio = generate(
                text=text,
                voice=voice.name,
                model="eleven_multilingual_v2"
            )
            
            # Save audio to temp file and play
            temp_file = f"temp_{voice.name}_{int(time.time())}.mp3"
            with open(temp_file, "wb") as f:
                f.write(audio)
            
            # On Windows, use the default media player
            os.system(f'start {temp_file}')
            
            response = input("\nRate this voice (1-5) or press Enter to continue, 'q' to quit: ")
            
            # Clean up temp file
            try:
                os.remove(temp_file)
            except:
                pass
                
            if response.lower() == 'q':
                return False
            elif response.strip() and response.isdigit():
                rating = int(response)
                if 1 <= rating <= 5:
                    print(f"You rated {voice.name} as {rating}/5")
                    
        except Exception as e:
            print(f"Error generating audio: {e}")
            continue
    
    return True

def main():
    print("Fetching available voices...")
    try:
        all_voices = voices()
        if not all_voices:
            raise ValueError("No voices found. Please check your API key.")
    except Exception as e:
        print(f"Error fetching voices: {e}")
        return
    
    # Filter for female voices with warm/soft characteristics
    female_voices = []
    for voice in all_voices:
        description = get_voice_description(voice)
        
        # Check if voice matches our criteria for Leyla's character
        if any(word in description for word in ['warm', 'soft', 'gentle', 'natural', 'female', 'professional']):
            # Exclude voices that don't match Leyla's character
            if not any(word in description for word in ['robotic', 'artificial', 'child', 'old']):
                female_voices.append(voice)
    
    # Sort voices by suitability (those with more matching keywords come first)
    positive_keywords = ['warm', 'soft', 'gentle', 'natural', 'professional', 'clear', 'friendly']
    female_voices.sort(
        key=lambda v: sum(
            kw in get_voice_description(v)
            for kw in positive_keywords
        ),
        reverse=True
    )
    
    if not female_voices:
        print("No suitable voices found. Showing all voices instead.")
        female_voices = all_voices
    
    print("\nAvailable voices (sorted by suitability for Leyla's character):")
    for i, voice in enumerate(female_voices):
        print(f"\n{i+1}. {voice.name}")
        description = get_voice_description(voice)
        if description:
            print(f"   Description: {description}")
        if hasattr(voice, 'labels'):
            print(f"   Labels: {voice.labels}")
    
    while True:
        try:
            choice = input("\nEnter voice number to preview (or 'q' to quit): ")
            if choice.lower() == 'q':
                break
            
            idx = int(choice) - 1
            if 0 <= idx < len(female_voices):
                if not preview_voice(female_voices[idx]):
                    break
            else:
                print("Invalid choice. Please try again.")
        except ValueError:
            print("Please enter a valid number.")
        except Exception as e:
            print(f"Error: {e}")
            break

if __name__ == "__main__":
    main()
