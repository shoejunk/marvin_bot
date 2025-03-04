from datetime import datetime, timedelta
import logging
import tkinter as tk
from display_gui import DisplayGUI

class Display:
    def __init__(self):
        self.gui = DisplayGUI()
        self.conversation = []
        self.actions = []
        self.timers = {}

    def add_conversation(self, message):
        self.conversation.append(message)
        
        # Use after method for thread-safe updates
        if hasattr(self.gui, 'root') and self.gui.root:
            self.gui.root.after(0, self._update_conversation, message)
    
    def _update_conversation(self, message):
        self.gui.conversation_text.insert(tk.END, f'{message}\n')
        self.gui.conversation_text.see(tk.END)

    def add_action(self, action):
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.actions.append((timestamp, action))
        
        # Use after method for thread-safe updates
        if hasattr(self.gui, 'root') and self.gui.root:
            self.gui.root.after(0, self._update_action, timestamp, action)
    
    def _update_action(self, timestamp, action):
        self.gui.actions_tree.insert('', tk.END, values=(timestamp, action))

    def add_timer(self, name, duration):
        if name in self.timers:
            self.remove_timer(name)
        self.timers[name] = datetime.now() + duration
        
        # Use after method for thread-safe updates
        if hasattr(self.gui, 'root') and self.gui.root:
            self.gui.root.after(0, self.update_timers)

    def remove_timer(self, name):
        if name in self.timers:
            del self.timers[name]
            
            # Use after method for thread-safe updates
            if hasattr(self.gui, 'root') and self.gui.root:
                self.gui.root.after(0, self.update_timers)

    def update_timers(self):
        # Use after method for thread-safe updates if not already in the main thread
        if hasattr(self.gui, 'root') and self.gui.root:
            try:
                self.gui.timers_tree.delete(*self.gui.timers_tree.get_children())
                for name, end_time in self.timers.items():
                    time_left = end_time - datetime.now()
                    self.gui.timers_tree.insert('', tk.END, values=(name, str(time_left)))
            except Exception as e:
                import logging
                logging.error(f"Error updating timers: {e}")

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
                import logging
                logging.error(f"Error showing window: {e}")
