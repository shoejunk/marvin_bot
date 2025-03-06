import tkinter as tk
from tkinter import ttk
import json
from datetime import datetime
import threading

class DisplayGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title('Marvin Display')
        self.root.geometry('800x600')
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)  # Handle window close event
        
        # Ensure the window is visible initially
        self.root.deiconify()
        
        # Create main container with a vertical split
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Configure row weights to achieve 3/4 to 1/4 ratio
        self.main_frame.grid_rowconfigure(0, weight=3)  # 3/4 for conversation
        self.main_frame.grid_rowconfigure(1, weight=1)  # 1/4 for timers
        self.main_frame.grid_columnconfigure(0, weight=1)
        
        # Create conversation frame (top section - 3/4 of the space)
        self.conversation_frame = ttk.LabelFrame(self.main_frame, text='Conversation History')
        self.conversation_frame.grid(row=0, column=0, sticky='nsew', padx=5, pady=5)
        
        # Create conversation text area with scrollbar
        self.conversation_text = tk.Text(self.conversation_frame, wrap=tk.WORD)
        self.conversation_scroll = ttk.Scrollbar(self.conversation_frame, command=self.conversation_text.yview)
        self.conversation_text.configure(yscrollcommand=self.conversation_scroll.set)
        self.conversation_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.conversation_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Create timers frame (bottom section - 1/4 of the space)
        self.timers_frame = ttk.LabelFrame(self.main_frame, text='Active Timers')
        self.timers_frame.grid(row=1, column=0, sticky='nsew', padx=5, pady=5)
        
        # Create timers tree with only time column
        self.timers_tree = ttk.Treeview(self.timers_frame, columns=('time_left'), show='headings', height=5)
        self.timers_tree.heading('time_left', text='Time Remaining')
        self.timers_tree.column('time_left', width=150)
        self.timers_scroll = ttk.Scrollbar(self.timers_frame, command=self.timers_tree.yview)
        self.timers_tree.configure(yscrollcommand=self.timers_scroll.set)
        self.timers_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.timers_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Initialize timers dictionary
        self.timers = {}
        
        # Start update loop
        self.update_interval = 1000  # 1 second
        self.update_lock = threading.Lock()
        self.update_display()
    
    def update_display(self):
        # Schedule next update
        self.root.after(self.update_interval, self.update_display)
        self.update_timers()

    def update_timers(self):
        with self.update_lock:
            # Clear existing timer entries
            for item in self.timers_tree.get_children():
                self.timers_tree.delete(item)
            
            # Update the display with current timers
            for name, end_time in self.timers.items():
                time_left = end_time - datetime.now()
                if time_left.total_seconds() > 0:
                    minutes, seconds = divmod(int(time_left.total_seconds()), 60)
                    hours, minutes = divmod(minutes, 60)
                    time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                    self.timers_tree.insert('', tk.END, values=(time_str,))
    
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
