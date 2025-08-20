import os

import requests

from src import logger

TOKEN = os.environ.get('TELEGRAM_TOKEN')
ADMINS = os.environ.get('ADMINS').split(',')
SERVER_NAME = os.environ.get('SERVER_NAME')


def send_message(message):
    send_message_url = f'https://api.telegram.org/bot{TOKEN}/sendMessage'
    for id in ADMINS:
        payload = {
            'chat_id': id,
            'text': f'[{SERVER_NAME}]: {message}'
        }
        response = requests.post(send_message_url, data=payload)
        if response.status_code == 200:
            logger.info(f'[TELEGRAM] Message to id {id} succesfully sended')
