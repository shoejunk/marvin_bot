#!/usr/bin/env python3
"""
voice_processor.py - Processes voice input for Marvin.
Handles wake word detection and speech transcription.
"""

import logging
import json
from typing import Optional, List, Tuple

# Import the logger configuration
from logger_config import get_logger
from settings_manager import get_active_personality
from personalities import get_personality

# Get a logger for this module
logger = get_logger(__name__)

class VoiceProcessor:
    def __init__(self, transcribe_function, display, update_history_function):
        """
        Initialize the VoiceProcessor.
        
        Args:
            transcribe_function: Function to transcribe speech to text
            display: Display interface for UI updates
            update_history_function: Function to update conversation history
        """
        self.transcribe = transcribe_function
        self.display = display
        self.update_history = update_history_function
        self.wake_word_required = True
        
        # Define wake words - will be dynamically updated based on active personality
        self.update_wake_words()
        
    def update_wake_words(self):
        """Update wake words based on the active personality."""
        # Get the active personality
        active_personality = get_active_personality()
        personality = get_personality(active_personality)
        
        # Base wake words that work for any personality
        base_wake_words = [
            "computer", "hey computer", "ok computer", "okay computer", "hi computer",
            "PC", "hey PC", "ok PC", "okay PC", "hi PC"
        ]
        
        # Add personality-specific wake words
        personality_name = personality.name.lower()
        personality_wake_words = [
            f"{personality_name}", f"hey {personality_name}", f"ok {personality_name}", 
            f"okay {personality_name}", f"hi {personality_name}"
        ]
        
        # Combine all wake words
        self.wake_words = base_wake_words + personality_wake_words
        
        logger.debug(f"Updated wake words for {personality.name}: {self.wake_words}")
        
    def set_wake_word_required(self, required: bool):
        """Set whether wake word is required."""
        self.wake_word_required = required
        logger.info(f"Wake word requirement is now {'ON' if required else 'OFF'}")
        
    def get_wake_word_required(self) -> bool:
        """Get whether wake word is required."""
        return self.wake_word_required
        
    async def process_voice_input(self) -> Tuple[Optional[str], bool]:
        """
        Process voice input, handling wake word detection if required.
        
        Returns:
            Tuple of (command, wake_word_detected)
            - command: The processed command, or None if no valid input
            - wake_word_detected: Whether a wake word was detected
        """
        try:
            # Update wake words based on current personality
            self.update_wake_words()
            
            # Get user input from speech transcription
            user_input = await self.transcribe()
            
            if not user_input:
                return None, False
                
            logger.info(f"Wake word requirement is currently {'ON' if self.wake_word_required else 'OFF'}")
            
            user_input_lower = user_input.lower()
            matched_wake_word = None
            
            # Check for wake word if required
            if self.wake_word_required:
                for wake_word in self.wake_words:
                    if user_input_lower.startswith(wake_word):
                        matched_wake_word = wake_word
                        break
                        
                if not matched_wake_word:
                    logger.info("Waiting for wake word...")
                    return None, False
                    
                # Remove the detected wake word from the beginning of the input
                command = user_input[len(matched_wake_word):].strip()
                logger.debug(f"Wake word detected: '{matched_wake_word}', command: '{command}'")
                return command, True
            else:
                # Wake word not required, process the entire input
                command = user_input
                logger.info(f"Wake word OFF - Processing input without wake word: '{command}'")
                return command, False
                
        except TimeoutError:
            logger.error("Error: Connection timed out while transcribing speech.")
            return None, False
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            return None, False
            
    def add_to_conversation(self, user_input: str, ai_response: str):
        """
        Add the conversation exchange to the display and history.
        
        Args:
            user_input: The user's input
            ai_response: The AI's response
        """
        try:
            # Parse the JSON response
            response_data = json.loads(ai_response)
            
            # Extract the text response to speak
            text_to_speak = response_data.get("response", "")
            
            # Update conversation history with the current turn
            self.display.add_conversation(user_input, speaker='user')
            self.display.add_conversation(text_to_speak, speaker='assistant')
            
            # Update the conversation history
            self.update_history(user_input, ai_response)
            
            return text_to_speak
            
        except json.JSONDecodeError:
            logger.error("Failed to parse response as JSON")
            self.display.add_conversation("Error: Failed to parse response as JSON", speaker='assistant')
            return "I encountered an error processing your request."
        except Exception as e:
            logger.error(f"Error processing response: {e}")
            self.display.add_conversation(f"Error: {str(e)}", speaker='assistant')
            return "I encountered an error processing your request."
