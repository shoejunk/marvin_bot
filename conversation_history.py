# conversation_history.py
import json
import os
from logger_config import get_logger

# Get a logger for this module
logger = get_logger(__name__)

HISTORY_FILE = "conversation_history.json"
MAX_TURNS = 50

def load_history():
    if not os.path.exists(HISTORY_FILE):
        logger.debug(f"History file {HISTORY_FILE} does not exist, creating new history")
        return []
    try:
        with open(HISTORY_FILE, "r") as f:
            history = json.load(f)
            logger.debug(f"Loaded {len(history)} conversation turns from history")
            return history
    except Exception as e:
        logger.error("Error loading conversation history: %s", e)
        return []

def save_history(history):
    try:
        with open(HISTORY_FILE, "w") as f:
            json.dump(history, f, indent=2)
        logger.debug(f"Saved {len(history)} conversation turns to history")
    except Exception as e:
        logger.error("Error saving conversation history: %s", e)

def update_history(user_input, assistant_response):
    history = load_history()
    history.append({"user": user_input, "assistant": assistant_response})
    # Keep only the last MAX_TURNS turns.
    if len(history) > MAX_TURNS:
        history = history[-MAX_TURNS:]
        logger.debug(f"Trimmed history to {MAX_TURNS} turns")
    save_history(history)
    return history
