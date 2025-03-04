from pydub import AudioSegment
from pydub.playback import play
import os
import edge_tts

default_voice = "en-GB-RyanNeural"

async def speak_text(text: str, voice=default_voice, gain_db=10):
    import tempfile
    import time
    
    # Create a unique temporary file for each TTS request
    with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
        tts_file = temp_file.name
    
    try:
        communicate = edge_tts.Communicate(text, voice=voice)
        await communicate.save(tts_file)

        # Load the audio file
        audio = AudioSegment.from_file(tts_file, format="mp3")
        
        # Increase volume by gain_db decibels
        louder_audio = audio + gain_db

        # Play the louder audio
        play(louder_audio)
        
        # Small delay to ensure file is not in use
        time.sleep(0.1)
    finally:
        # Always try to clean up the file, but don't crash if we can't
        try:
            os.remove(tts_file)
        except (FileNotFoundError, PermissionError):
            pass  # Ignore if the file doesn't exist or is still in use
