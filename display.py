from datetime import datetime, timedelta
import tkinter as tk
from display_gui import DisplayGUI
from logger_config import get_logger

# Get a logger for this module
logger = get_logger(__name__)

class Display:
    def __init__(self):
        self.gui = DisplayGUI()
        self.conversation = []
        self.timers = {}
        logger.debug("Display initialized")
        
    def add_conversation(self, message, speaker=None):
        """
        Add a message to the conversation history.
        
        Args:
            message: The message text
            speaker: Who is speaking - 'user', 'marvin', or None for actions/system messages
        """
        if speaker == 'user':
            formatted_message = f"User: {message}"
        elif speaker == 'marvin':
            formatted_message = f"Marvin: {message}"
        else:
            # For actions or system messages
            formatted_message = message
            
        self.conversation.append(formatted_message)
        
        # Use after method for thread-safe updates
        if hasattr(self.gui, 'root') and self.gui.root:
            self.gui.root.after(0, self._update_conversation, formatted_message)
        else:
            logger.warning("GUI not available for conversation update")
    
    def _update_conversation(self, message):
        self.gui.conversation_text.insert(tk.END, f'{message}\n')
        self.gui.conversation_text.see(tk.END)

    def add_timer(self, name, duration):
        if name in self.timers:
            self.remove_timer(name)
        
        # Store the end time
        self.timers[name] = datetime.now() + duration
        
        # Update the GUI timers dictionary to match
        self.gui.timers = self.timers
        
        # Let the GUI's update loop handle the display refresh
        self._schedule_timer_updates()

    def _schedule_timer_updates(self):
        """Schedule periodic updates to keep the timer display current"""
        if hasattr(self.gui, 'root') and self.gui.root and self.timers:
            self.gui.root.after(1000, self._schedule_timer_updates)  # Update every second

    def remove_timer(self, name):
        if name in self.timers:
            del self.timers[name]
            
            # Update the GUI timers dictionary to match
            self.gui.timers = self.timers

    def update_timers(self):
        # This method is no longer needed as the GUI handles display updates
        pass

    def get_time_left(self, name):
        if name in self.timers:
            time_left = self.timers[name] - datetime.now()
            return max(time_left, timedelta(0))
        return None

    def run(self):
        # Make the window visible before entering the mainloop
        if hasattr(self.gui, 'root') and self.gui.root:
            self.gui.root.deiconify()
        self.gui.run()

    def show(self):
        """Make the GUI window visible if it's not already."""
        # This method is kept for compatibility but should only be called from the main thread
        # or through the after() method if the mainloop is running
        if hasattr(self.gui, 'root') and self.gui.root:
            try:
                self.gui.root.deiconify()  # Make the window visible if it was iconified
                self.gui.root.lift()  # Bring window to front
            except RuntimeError as e:
                logger.error(f"Error showing window: {e}")
