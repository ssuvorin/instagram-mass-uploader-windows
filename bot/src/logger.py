import logging
import sys

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot/log.txt', encoding='utf-8')
    ]
)

# Create logger to be imported by other modules
logger = logging.getLogger('bot')
logger.setLevel(logging.INFO)

# Make sure we don't duplicate log messages
if not logger.handlers:
    # Add stdout handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(console_handler)
    
    # Add file handler
    file_handler = logging.FileHandler('bot/log.txt', encoding='utf-8')
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler) 