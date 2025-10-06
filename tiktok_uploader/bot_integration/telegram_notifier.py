import os

import requests

from . import logger

TOKEN = os.environ.get('TELEGRAM_TOKEN')
ADMINS_ENV = os.environ.get('ADMINS', '')
ADMINS = ADMINS_ENV.split(',') if ADMINS_ENV else []
SERVER_NAME = os.environ.get('SERVER_NAME', 'TikTok Bot')


def send_message(message):
    """
    Отправляет сообщение всем администраторам через Telegram.
    
    Args:
        message (str): Текст сообщения
    """
    if not TOKEN or not ADMINS:
        logger.warning('[TELEGRAM] Telegram notifications not configured')
        return
    
    send_message_url = f'https://api.telegram.org/bot{TOKEN}/sendMessage'
    for id in ADMINS:
        if not id.strip():
            continue
        payload = {
            'chat_id': id.strip(),
            'text': f'[{SERVER_NAME}]: {message}'
        }
        try:
            response = requests.post(send_message_url, data=payload, timeout=10)
            if response.status_code == 200:
                logger.info(f'[TELEGRAM] Message to id {id} successfully sent')
            else:
                logger.warning(f'[TELEGRAM] Failed to send message to {id}: {response.text}')
        except Exception as e:
            logger.error(f'[TELEGRAM] Error sending message: {str(e)}')


