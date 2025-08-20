import os

from dotenv import load_dotenv

from src.logger import Logger

load_dotenv()

logger = Logger(debug=bool(os.environ.get('DEBUG')))
