from datetime import datetime, timedelta
import tkinter as tk
from display_gui import DisplayGUI
from logger_config import get_logger
from settings_manager import get_active_personality
from personalities import get_personality

# Get a logger for this module
logger = get_logger(__name__)

class Display:
    def __init__(self):
        self.gui = DisplayGUI()
        self.conversation = []
        self.timers = {}
        self.paused_timers = {}  # Store paused timers and their remaining time
        logger.debug("Display initialized")
        logger.debug(f"Initial timers: {self.timers}")
        logger.debug(f"Initial paused_timers: {self.paused_timers}")
        
        # Initialize GUI with timer dictionaries
        self.gui.timers = self.timers
        self.gui.paused_timers = self.paused_timers
        logger.debug(f"GUI timers initialized: {self.gui.timers}")
        logger.debug(f"GUI paused_timers initialized: {self.gui.paused_timers}")
        
    def add_conversation(self, message, speaker=None):
        """
        Add a message to the conversation history.
        
        Args:
            message: The message text
            speaker: Who is speaking - 'user', 'assistant', or None for actions/system messages
        """
        if speaker == 'user':
            formatted_message = f"User: {message}"
        elif speaker == 'assistant' or speaker == 'marvin':
            # Get the active personality name
            active_personality = get_active_personality()
            personality = get_personality(active_personality)
            formatted_message = f"{personality.name}: {message}"
        elif speaker == 'action':
            formatted_message = f"Action: {message}"
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
        
        # Also remove from paused timers if it exists there
        if name in self.paused_timers:
            del self.paused_timers[name]
            
            # Update the GUI paused timers dictionary
            self.gui.paused_timers = self.paused_timers

    def pause_timer(self, name):
        """
        Pause a timer by name.
        
        Args:
            name: The name of the timer to pause
            
        Returns:
            bool: True if timer was paused, False if timer not found
        """
        if name in self.timers:
            # Calculate remaining time
            remaining_time = self.timers[name] - datetime.now()
            # Store the remaining time
            self.paused_timers[name] = max(remaining_time, timedelta(0))
            # Remove from active timers
            del self.timers[name]
            # Update the GUI timers dictionary
            self.gui.timers = self.timers
            # Update the GUI paused timers dictionary
            self.gui.paused_timers = self.paused_timers
            logger.debug(f"Timer {name} paused with {self.paused_timers[name]} remaining")
            logger.debug(f"Display paused_timers: {self.paused_timers}")
            logger.debug(f"GUI paused_timers: {self.gui.paused_timers}")
            return True
        return False
    
    def pause_all_timers(self):
        """
        Pause all active timers.
        
        Returns:
            int: Number of timers paused
        """
        active_timers = list(self.timers.keys())
        count = 0
        for timer_name in active_timers:
            if self.pause_timer(timer_name):
                count += 1
        logger.debug(f"Paused {count} timers. Display paused_timers: {self.paused_timers}")
        return count
    
    def resume_timer(self, name):
        """
        Resume a paused timer by name.
        
        Args:
            name: The name of the timer to resume
            
        Returns:
            bool: True if timer was resumed, False if timer not found in paused timers
        """
        if name in self.paused_timers:
            # Calculate new end time based on remaining time
            new_end_time = datetime.now() + self.paused_timers[name]
            # Add back to active timers
            self.timers[name] = new_end_time
            # Remove from paused timers
            del self.paused_timers[name]
            # Update the GUI timers dictionary
            self.gui.timers = self.timers
            # Update the GUI paused timers dictionary
            self.gui.paused_timers = self.paused_timers
            # Ensure timer updates are scheduled
            self._schedule_timer_updates()
            logger.debug(f"Timer {name} resumed, will end at {new_end_time}")
            logger.debug(f"Display paused_timers after resume: {self.paused_timers}")
            logger.debug(f"GUI paused_timers after resume: {self.gui.paused_timers}")
            return True
        return False
    
    def resume_all_timers(self):
        """
        Resume all paused timers.
        
        Returns:
            int: Number of timers resumed
        """
        paused_timers = list(self.paused_timers.keys())
        logger.debug(f"Attempting to resume all paused timers: {paused_timers}")
        count = 0
        for timer_name in paused_timers:
            if self.resume_timer(timer_name):
                count += 1
        logger.debug(f"Resumed {count} timers")
        logger.debug(f"After resuming all timers - Active: {self.timers}, Paused: {self.paused_timers}")
        logger.debug(f"GUI timers after resuming all: {self.gui.timers}")
        logger.debug(f"GUI paused_timers after resuming all: {self.gui.paused_timers}")
        return count

    def update_timers(self):
        # This method is no longer needed as the GUI handles display updates
        pass

    def get_time_left(self, name):
        if name in self.timers:
            time_left = self.timers[name] - datetime.now()
            return max(time_left, timedelta(0))
        elif name in self.paused_timers:
            return self.paused_timers[name]
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
