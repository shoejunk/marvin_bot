from pydub import AudioSegment
from pydub.playback import play
import os
import tempfile
import time
import asyncio
import aiohttp
from openai import OpenAI
import dotenv
# Import the new logger configuration
from logger_config import get_logger
from personalities import get_personality

# Load environment variables
dotenv.load_dotenv()

# Configure logging using the thread-specific logger
logger = get_logger(__name__)

# Initialize OpenAI client
client = OpenAI()

# Default voice settings (will be overridden by personality settings)
default_voice = "alloy"  # Default OpenAI voice
fallback_voice = "echo"  # Fallback OpenAI voice

async def speak_text(text: str, voice=None, personality_name=None, max_retries=2):
    """
    Convert text to speech using OpenAI's TTS API and play it with volume adjustment.
    Includes error handling and retry logic.
    
    Args:
        text: The text to convert to speech
        voice: The voice to use (overrides personality voice if provided)
        personality_name: Name of the personality to use for voice selection
        max_retries: Maximum number of retry attempts for TTS service
    """
    # Determine which voice to use
    if voice is None:
        # Get voice from personality if specified
        personality = get_personality(personality_name)
        voice = personality.voice
        logger.debug(f"Using voice '{voice}' from personality '{personality.name}'")
    
    # Create a unique temporary file for each TTS request
    with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
        tts_file = temp_file.name
    
    # Track if we've successfully generated speech
    success = False
    
    try:
        # Try with primary voice first
        for attempt in range(max_retries + 1):
            try:
                current_voice = voice if attempt == 0 else fallback_voice
                logger.debug(f"TTS attempt {attempt+1}/{max_retries+1} using voice: {current_voice}")
                
                # Use OpenAI's TTS API
                try:
                    # Run in a separate thread to avoid blocking
                    loop = asyncio.get_event_loop()
                    response = await loop.run_in_executor(
                        None,
                        lambda: client.audio.speech.create(
                            model="gpt-4o-mini-tts",
                            voice=current_voice,
                            input=text,
                            instructions=personality.description
                        )
                    )
                    
                    # Save the audio file
                    response.stream_to_file(tts_file)
                    success = True
                    logger.debug(f"TTS generation successful with {current_voice}")
                    break  # Exit the retry loop if successful
                    
                except asyncio.TimeoutError:
                    logger.warning(f"TTS request timed out with voice {current_voice}")
                    continue  # Try next attempt
                
            except aiohttp.ClientConnectorError as e:
                logger.error(f"Network connection error with OpenAI TTS: {e}")
                await asyncio.sleep(1)  # Wait before retry
            except Exception as e:
                logger.error(f"Unexpected error with OpenAI TTS: {e}")
                await asyncio.sleep(1)  # Wait before retry
        
        # If we couldn't generate speech after all retries, use a fallback message
        if not success:
            logger.warning("All TTS attempts failed, using text output only")
            print(f"Assistant says: {text}")
            return
        
        # Load and play the audio file if we successfully generated it
        try:
            # Load the audio file
            audio = AudioSegment.from_file(tts_file, format="mp3")
            
            # Increase volume by volume decibels
            louder_audio = audio + personality.volume

            # Play the louder audio
            play(louder_audio)
            
        except Exception as e:
            logger.error(f"Error playing audio: {e}")
            # Still show the text as fallback
            print(f"Assistant says: {text}")
            
    finally:
        # Always try to clean up the file, but don't crash if we can't
        try:
            if os.path.exists(tts_file):
                os.remove(tts_file)
        except (FileNotFoundError, PermissionError) as e:
            logger.debug(f"Could not remove temporary file: {e}")
