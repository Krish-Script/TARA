import logging
import os

# 1. Define the Tier 1 Exception
class ToolExpectedError(Exception):
    """
    Tier 1 Expected Failure. 
    Raised when a tool encounters a known, predictable edge case 
    (e.g., file not found, battery missing).
    """
    pass

# 2. Configure the silent file logger (Tiers 2 & 3)
def setup_error_logger():
    # Guarantee the logs directory exists
    os.makedirs('logs', exist_ok=True)
    
    # Create a specific logger for TARA errors
    logger = logging.getLogger('tara_errors')
    logger.setLevel(logging.ERROR)
    
    # CRITICAL: Prevent logs from bubbling up to the root logger and printing to the terminal
    logger.propagate = False 
    
    # Route only to the file
    file_handler = logging.FileHandler('logs/errors.log')
    file_handler.setLevel(logging.ERROR)
    
    # Format: Timestamp - Component - Level - Message
    formatter = logging.Formatter('%(asctime)s - [%(name)s] - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    return logger

# Expose the logger instance to be imported by other modules
error_logger = setup_error_logger()