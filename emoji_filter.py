#!/usr/bin/env python3
"""
emoji_filter.py - Utility for detecting and filtering emojis from text.
"""

import re
import unicodedata

# Import the logger configuration
from logger_config import get_logger

# Get a logger for this module
logger = get_logger(__name__)

def is_emoji(char):
    """
    Check if a character is an emoji.
    
    Args:
        char: The character to check
        
    Returns:
        bool: True if the character is an emoji, False otherwise
    """
    # Check for emoji using unicode category
    if unicodedata.category(char) in ('So', 'Sk'):
        return True
    
    # Check for emoji variation selectors
    if char in ['\uFE0F', '\uFE0E']:
        return True
    
    # Check for emoji modifiers (skin tones, etc.)
    if 0x1F3FB <= ord(char) <= 0x1F3FF:
        return True
    
    return False

def contains_emoji(text):
    """
    Check if text contains any emojis.
    
    Args:
        text: The text to check
        
    Returns:
        bool: True if the text contains emojis, False otherwise
    """
    if not text:
        return False
    
    for char in text:
        if is_emoji(char):
            return True
    
    return False

def remove_emojis(text):
    """
    Remove all emojis from text.
    
    Args:
        text: The text to process
        
    Returns:
        str: The text with all emojis removed
    """
    if not text:
        return text
    
    # Remove emoji characters
    filtered_chars = [char for char in text if not is_emoji(char)]
    
    # Remove zero-width joiners that might be part of emoji sequences
    filtered_text = ''.join(filtered_chars).replace('\u200D', '')
    
    # Clean up any double spaces that might have been created
    cleaned_text = re.sub(r'\s+', ' ', filtered_text).strip()
    
    # Log if emojis were removed
    if cleaned_text != text:
        logger.debug(f"Removed emojis from text: '{text}' -> '{cleaned_text}'")
    
    return cleaned_text

def filter_for_tts(text):
    """
    Filter text for text-to-speech, removing emojis.
    
    Args:
        text: The text to filter
        
    Returns:
        str: The filtered text suitable for TTS
    """
    return remove_emojis(text)
