import logging
import sys
import os

# Determine stream based on environment to avoid polluting stdout in isolated subprocesses
# If FORCE_LOG_TO_STDERR or COOKIE_ROBOT_ISOLATED is set, redirect stream logs to stderr
_stream = sys.stderr if os.environ.get('FORCE_LOG_TO_STDERR') == '1' or os.environ.get('COOKIE_ROBOT_ISOLATED') == '1' else sys.stdout

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(_stream),
        logging.FileHandler('bot/log.txt', encoding='utf-8')
    ]
)

# Create logger to be imported by other modules
logger = logging.getLogger('bot')
logger.setLevel(logging.INFO)

# Make sure we don't duplicate log messages
if not logger.handlers:
    # Add stream handler (to selected stream)
    console_handler = logging.StreamHandler(_stream)
    console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(console_handler)
    
    # Add file handler
    file_handler = logging.FileHandler('bot/log.txt', encoding='utf-8')
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler) 