"""
logger_config.py - Configures logging for the Marvin bot with thread-specific log files.
This module provides a centralized logging configuration that creates separate log files
for different components to avoid file contention issues.
"""

import os
import logging
import threading
from logging.handlers import RotatingFileHandler
import time

# Base directory for logs
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')

# Create logs directory if it doesn't exist
os.makedirs(LOG_DIR, exist_ok=True)

# Dictionary to track handlers created for each thread
thread_handlers = {}

def get_logger(name):
    """
    Get a logger with a thread-specific log file.
    
    Args:
        name: The name of the logger (usually __name__ from the calling module)
        
    Returns:
        A configured logger instance
    """
    # Create a unique logger for this module
    logger = logging.getLogger(name)
    
    # Only configure if it hasn't been configured yet
    if not logger.handlers:
        # Set the logging level
        logger.setLevel(logging.DEBUG)
        
        # Get current thread ID for the log filename
        thread_id = threading.get_ident()
        thread_name = threading.current_thread().name.replace(' ', '_')
        
        # Create a unique filename based on the module name and thread
        log_filename = f"marvin_{name.split('.')[-1]}_{thread_name}.log"
        log_path = os.path.join(LOG_DIR, log_filename)
        
        try:
            # Create a rotating file handler (10 MB max size, keep 3 backups)
            file_handler = RotatingFileHandler(
                log_path,
                maxBytes=10*1024*1024,  # 10 MB
                backupCount=3,
                delay=True  # Don't open the file until first log
            )
            
            # Set formatter
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(threadName)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(formatter)
            
            # Add the handler to the logger
            logger.addHandler(file_handler)
            
            # Also add a console handler for immediate feedback
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
            
            # Track this handler
            thread_handlers[thread_id] = file_handler
            
            logger.debug(f"Logger initialized for {name} in thread {thread_name}")
            
        except Exception as e:
            # If we can't set up the file handler, fall back to console only
            print(f"Error setting up log file for {name}: {e}")
            console_handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
            logger.warning(f"Falling back to console logging due to error: {e}")
    
    return logger

def shutdown_logging():
    """
    Properly shut down all loggers to ensure files are closed.
    Call this function before application exit.
    """
    logging.shutdown()
    print("Logging shutdown complete")
