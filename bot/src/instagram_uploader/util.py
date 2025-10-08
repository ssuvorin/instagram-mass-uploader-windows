import time
import random
import logging
import tomli
import os
import sys

# Setup basic logging
# Get the project root directory for django.log
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
django_log_path = os.path.join(project_root, 'django.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(django_log_path, encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# Load config from TOML file
config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.toml")
with open(config_path, "rb") as f:
    config = tomli.load(f)

def random_delay(action_type="normal"):
    """
    Executes a random delay based on config settings
    
    Args:
        action_type: Type of action ("normal", "major", or custom min/max tuple)
    """
    if isinstance(action_type, tuple) and len(action_type) == 2:
        min_delay, max_delay = action_type
    elif action_type == "major":
        min_delay = config['delays']['major_action_min']
        max_delay = config['delays']['major_action_max']
    else:  # normal action
        min_delay = config['delays']['action_min']
        max_delay = config['delays']['action_max']
    
    delay = random.uniform(min_delay, max_delay)
    logger.info(f"[WAIT] Ожидание {delay:.2f} секунд...")
    time.sleep(delay)
    return delay

def realistic_type(page, selector, text, log_message=None):
    """
    Simulates realistic typing with random delays between keystrokes
    
    Args:
        page: Playwright page object
        selector: Element selector (xpath or css)
        text: Text to type
        log_message: Optional message to log before typing
    """
    if log_message:
        logger.info(log_message)
    
    min_delay = config['delays']['typing_min']
    max_delay = config['delays']['typing_max']
    
    # First click on the field to focus it
    try:
        if selector.startswith('//'):
            element = page.locator(f"xpath={selector}")
        else:
            element = page.locator(selector)
        
        element.click()
        random_delay((0.2, 0.5))  # Short delay after click
        
        # Type text with random delays between characters
        logger.info(f"⌨️ Ввод текста с имитацией человеческого набора...")
        element.type(text, delay=random.uniform(min_delay, max_delay))
        
        # Small delay after typing is complete
        random_delay((0.5, 1.0))
        return True
    except Exception as e:
        logger.error(f"[FAIL] Ошибка при вводе текста: {str(e)}")
        return False

def human_action(page, action_type, selector=None, value=None, log_message=None):
    """
    Performs a human-like action with appropriate delays
    
    Args:
        page: Playwright page object
        action_type: Type of action ("click", "fill", "select", etc)
        selector: Element selector
        value: Value to set (for fill, select actions)
        log_message: Optional message to log before action
    """
    if log_message:
        logger.info(log_message)
    
    try:
        if selector.startswith('//'):
            element = page.locator(f"xpath={selector}")
        else:
            element = page.locator(selector)
        
        # Random delay before action
        random_delay()
        
        # Perform the requested action
        if action_type == "click":
            element.click()
        elif action_type == "fill":
            if value:
                element.fill(value)
        elif action_type == "type":
            if value:
                return realistic_type(page, selector, value)
        elif action_type == "select":
            if value:
                element.select_option(value)
        
        # Random delay after action
        random_delay()
        return True
    except Exception as e:
        logger.error(f"[FAIL] Ошибка при выполнении действия {action_type}: {str(e)}")
        return False 