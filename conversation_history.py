# conversation_history.py
import json
import os
import logging

HISTORY_FILE = "conversation_history.json"
MAX_TURNS = 50

def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        logging.error("Error loading conversation history: %s", e)
        return []

def save_history(history):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)

def update_history(user_input, assistant_response):
    history = load_history()
    history.append({"user": user_input, "assistant": assistant_response})
    # Keep only the last MAX_TURNS turns.
    if len(history) > MAX_TURNS:
        history = history[-MAX_TURNS:]
    save_history(history)
    return history
