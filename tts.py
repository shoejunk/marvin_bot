from pydub import AudioSegment
from pydub.playback import play
import os
import edge_tts
import asyncio
import tempfile
import time
import aiohttp
# Import the new logger configuration
from logger_config import get_logger

# Configure logging using the new thread-specific logger
logger = get_logger(__name__)

default_voice = "en-GB-RyanNeural"
fallback_voice = "en-US-ChristopherNeural"  # Fallback voice if primary fails

async def speak_text(text: str, voice=default_voice, gain_db=5, max_retries=2):
    """
    Convert text to speech and play it with volume adjustment.
    Includes error handling and retry logic for Edge TTS service issues.
    
    Args:
        text: The text to convert to speech
        voice: The voice to use (defaults to en-GB-RyanNeural)
        gain_db: Volume adjustment in decibels
        max_retries: Maximum number of retry attempts for TTS service
    """
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
                
                communicate = edge_tts.Communicate(text, voice=current_voice)
                
                # Set timeout for the TTS request
                timeout = aiohttp.ClientTimeout(total=10)  # 10 second timeout
                
                # Try to save the speech with timeout
                try:
                    await asyncio.wait_for(communicate.save(tts_file), timeout=10)
                    success = True
                    logger.debug(f"TTS generation successful with {current_voice}")
                    break  # Exit the retry loop if successful
                except asyncio.TimeoutError:
                    logger.warning(f"TTS request timed out with voice {current_voice}")
                    continue  # Try next attempt
                
            except aiohttp.ClientConnectorError as e:
                logger.error(f"Network connection error with Edge TTS: {e}")
                await asyncio.sleep(1)  # Wait before retry
            except aiohttp.WSServerHandshakeError as e:
                logger.error(f"Edge TTS service error (HTTP {e.status}): {e.message}")
                await asyncio.sleep(1)  # Wait before retry
            except Exception as e:
                logger.error(f"Unexpected error with Edge TTS: {e}")
                await asyncio.sleep(1)  # Wait before retry
        
        # If we couldn't generate speech after all retries, use a fallback message
        if not success:
            logger.warning("All TTS attempts failed, using text output only")
            print(f"Marvin says: {text}")
            return
        
        # Load and play the audio file if we successfully generated it
        try:
            # Load the audio file
            audio = AudioSegment.from_file(tts_file, format="mp3")
            
            # Increase volume by gain_db decibels
            louder_audio = audio + gain_db

            # Play the louder audio
            play(louder_audio)
            
            # Small delay to ensure file is not in use
            time.sleep(0.1)
        except Exception as e:
            logger.error(f"Error playing audio: {e}")
            # Still show the text as fallback
            print(f"Marvin says: {text}")
            
    finally:
        # Always try to clean up the file, but don't crash if we can't
        try:
            if os.path.exists(tts_file):
                os.remove(tts_file)
        except (FileNotFoundError, PermissionError) as e:
            logger.debug(f"Could not remove temporary file: {e}")
