import tkinter as tk
from tkinter import ttk
import json
from datetime import datetime

class DisplayGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title('Marvin Display')
        self.root.geometry('800x600')
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)  # Handle window close event
        
        # Ensure the window is visible initially
        self.root.deiconify()
        
        # Create main container
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Create conversation tab
        self.conversation_frame = ttk.Frame(self.notebook)
        self.conversation_text = tk.Text(self.conversation_frame, wrap=tk.WORD)
        self.conversation_scroll = ttk.Scrollbar(self.conversation_frame, command=self.conversation_text.yview)
        self.conversation_text.configure(yscrollcommand=self.conversation_scroll.set)
        self.conversation_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.conversation_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.notebook.add(self.conversation_frame, text='Conversation')

        # Create actions tab
        self.actions_frame = ttk.Frame(self.notebook)
        self.actions_tree = ttk.Treeview(self.actions_frame, columns=('time', 'action'), show='headings')
        self.actions_tree.heading('time', text='Time')
        self.actions_tree.heading('action', text='Action')
        self.actions_tree.column('time', width=150)
        self.actions_tree.column('action', stretch=True)
        self.actions_scroll = ttk.Scrollbar(self.actions_frame, command=self.actions_tree.yview)
        self.actions_tree.configure(yscrollcommand=self.actions_scroll.set)
        self.actions_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.actions_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.notebook.add(self.actions_frame, text='Actions')

        # Create timers tab
        self.timers_frame = ttk.Frame(self.notebook)
        self.timers_tree = ttk.Treeview(self.timers_frame, columns=('name', 'time_left'), show='headings')
        self.timers_tree.heading('name', text='Timer Name')
        self.timers_tree.heading('time_left', text='Time Left')
        self.timers_tree.column('name', width=150)
        self.timers_tree.column('time_left', stretch=True)
        self.timers_scroll = ttk.Scrollbar(self.timers_frame, command=self.timers_tree.yview)
        self.timers_tree.configure(yscrollcommand=self.timers_scroll.set)
        self.timers_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.timers_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.notebook.add(self.timers_frame, text='Timers')

        # Initialize timers dictionary
        self.timers = {}

        # Start update loop
        self.update_interval = 1000  # 1 second
        self.update_display()

    def update_display(self):
        # Schedule next update
        self.root.after(self.update_interval, self.update_display)
        self.update_timers()

    def update_timers(self):
        # Clear existing timer entries
        for item in self.timers_tree.get_children():
            self.timers_tree.delete(item)
        # Update the display with current timers
        for name, end_time in self.timers.items():
            time_left = end_time - datetime.now()
            self.timers_tree.insert('', tk.END, values=(name, str(time_left)))

    def on_close(self):
        # Instead of destroying the window, just hide it
        self.root.withdraw()
        # The window can be shown again with root.deiconify()

    def run(self):
        try:
            self.root.mainloop()
        except Exception as e:
            import logging
            logging.error(f"Error in display GUI mainloop: {e}")

if __name__ == "__main__":
    gui = DisplayGUI()
    gui.run()
