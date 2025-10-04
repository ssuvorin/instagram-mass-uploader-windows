import email
import imaplib
import re
from email.header import decode_header

from tiktok_uploader.bot_integration import logger


class Email:

    def __init__(self, login, password):
        self.login = login
        self.password = password

    def get_code(self):
        servers = ['imap', 'imap-mail']
        domains = ['notletters', 'rambler', 'hotmail', 'firstmail', 'outlook']
        prefixes = ['com', 'ru', 'ltd']
        ports = [993, 995]
        for server in servers:
            for domain in domains:
                for prefix in prefixes:
                    for port in ports:
                        code = self._get_code(imap_server=f'{server}.{domain}.{prefix}', port=port)
                        if code:
                            return code
        return None


    def _get_code(self, imap_server=None, port=None):
        try:
            imap = imaplib.IMAP4_SSL(imap_server, port, timeout=15)
            imap.login(self.login, self.password)
            imap.select('INBOX')

            status, messages = imap.search(None, 'ALL')
            if status != 'OK':
                return None
            message_ids = messages[0].split()
            if not message_ids:
                return None
            latest_message_id = message_ids[-1]
            status, msg_data = imap.fetch(latest_message_id, "(RFC822)")
            if status != 'OK':
                return None
            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)
            subject = decode_header(msg['Subject'])[0][0]
            match = re.search(r"(\d{6}) is your verification code", subject)
            if match:
                logger.info(f'Got verification code: {match.group(1)}')
                return str(match.group(1))  # Возвращаем только цифры кода
            return None
        except:
            pass
        finally:
            try:
                imap.logout()
            except:
                pass
