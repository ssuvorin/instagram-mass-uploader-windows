import email
import imaplib
import poplib
import re
import time
from datetime import datetime, timedelta
from email.header import decode_header
from email.policy import default


class Email:
    # Email server configurations
    EMAIL_SERVERS = {
        # Hotmail/Outlook domains
        'hotmail.com': {'server': 'imap-mail.outlook.com', 'port': 993, 'type': 'imap'},
        'outlook.com': {'server': 'imap-mail.outlook.com', 'port': 993, 'type': 'imap'},
        'live.com': {'server': 'imap-mail.outlook.com', 'port': 993, 'type': 'imap'},
        'msn.com': {'server': 'imap-mail.outlook.com', 'port': 993, 'type': 'imap'},
        
        # Gmail
        'gmail.com': {'server': 'imap.gmail.com', 'port': 993, 'type': 'imap'},
        
        # Yahoo
        'yahoo.com': {'server': 'imap.mail.yahoo.com', 'port': 993, 'type': 'imap'},
        'yahoo.ru': {'server': 'imap.mail.yahoo.com', 'port': 993, 'type': 'imap'},
        
        # Rambler
        'rambler.ru': {'server': 'imap.rambler.ru', 'port': 993, 'type': 'imap'},
        
        # Mail.ru
        'mail.ru': {'server': 'imap.mail.ru', 'port': 993, 'type': 'imap'},
        'inbox.ru': {'server': 'imap.mail.ru', 'port': 993, 'type': 'imap'},
        'list.ru': {'server': 'imap.mail.ru', 'port': 993, 'type': 'imap'},
        'bk.ru': {'server': 'imap.mail.ru', 'port': 993, 'type': 'imap'},
        
        # Yandex
        'yandex.ru': {'server': 'imap.yandex.ru', 'port': 993, 'type': 'imap'},
        'yandex.com': {'server': 'imap.yandex.ru', 'port': 993, 'type': 'imap'},
        'ya.ru': {'server': 'imap.yandex.ru', 'port': 993, 'type': 'imap'},
        
        # FirstMail - расширенная поддержка различных доменов
        'firstmail.ltd': {'server': 'imap.firstmail.ltd', 'port': 995, 'type': 'pop3'},
        'firstmail.org': {'server': 'imap.firstmail.ltd', 'port': 995, 'type': 'pop3'},
        'firstmail.com': {'server': 'imap.firstmail.ltd', 'port': 995, 'type': 'pop3'},
        'firstmail.net': {'server': 'imap.firstmail.ltd', 'port': 995, 'type': 'pop3'},
        'firstmail.co': {'server': 'imap.firstmail.ltd', 'port': 995, 'type': 'pop3'},
        'firstmail.io': {'server': 'imap.firstmail.ltd', 'port': 995, 'type': 'pop3'},
        'firstmail.me': {'server': 'imap.firstmail.ltd', 'port': 995, 'type': 'pop3'},
        'firstmail.xyz': {'server': 'imap.firstmail.ltd', 'port': 995, 'type': 'pop3'},
        'firstmail.site': {'server': 'imap.firstmail.ltd', 'port': 995, 'type': 'pop3'},
        'firstmail.online': {'server': 'imap.firstmail.ltd', 'port': 995, 'type': 'pop3'},
        
        # NotLetters and temporary email providers - расширенная поддержка
        'notletters.com': {'server': 'imap.notletters.com', 'port': 993, 'type': 'imap'},
        'notletters.org': {'server': 'imap.notletters.com', 'port': 993, 'type': 'imap'},
        'notletters.net': {'server': 'imap.notletters.com', 'port': 993, 'type': 'imap'},
        'notletters.co': {'server': 'imap.notletters.com', 'port': 993, 'type': 'imap'},
        
        # Другие временные email провайдеры
        'tempmail.org': {'server': 'imap.tempmail.org', 'port': 993, 'type': 'imap'},
        'tempmail.com': {'server': 'imap.tempmail.org', 'port': 993, 'type': 'imap'},
        'tempmail.net': {'server': 'imap.tempmail.org', 'port': 993, 'type': 'imap'},
        
        '10minutemail.com': {'server': 'imap.10minutemail.com', 'port': 993, 'type': 'imap'},
        '10minutemail.org': {'server': 'imap.10minutemail.com', 'port': 993, 'type': 'imap'},
        '10minutemail.net': {'server': 'imap.10minutemail.com', 'port': 993, 'type': 'imap'},
        
        'guerrillamail.com': {'server': 'imap.guerrillamail.com', 'port': 993, 'type': 'imap'},
        'guerrillamail.org': {'server': 'imap.guerrillamail.com', 'port': 993, 'type': 'imap'},
        'guerrillamail.net': {'server': 'imap.guerrillamail.com', 'port': 993, 'type': 'imap'},
        
        'mailinator.com': {'server': 'imap.mailinator.com', 'port': 993, 'type': 'imap'},
        'mailinator.org': {'server': 'imap.mailinator.com', 'port': 993, 'type': 'imap'},
        'mailinator.net': {'server': 'imap.mailinator.com', 'port': 993, 'type': 'imap'},
        
        # Дополнительные временные провайдеры
        'temp-mail.org': {'server': 'imap.temp-mail.org', 'port': 993, 'type': 'imap'},
        'temp-mail.com': {'server': 'imap.temp-mail.org', 'port': 993, 'type': 'imap'},
        'temp-mail.net': {'server': 'imap.temp-mail.org', 'port': 993, 'type': 'imap'},
        
        'maildrop.cc': {'server': 'imap.maildrop.cc', 'port': 993, 'type': 'imap'},
        'maildrop.com': {'server': 'imap.maildrop.cc', 'port': 993, 'type': 'imap'},
        'maildrop.org': {'server': 'imap.maildrop.cc', 'port': 993, 'type': 'imap'},
        
        'throwaway.email': {'server': 'imap.throwaway.email', 'port': 993, 'type': 'imap'},
        'throwaway.com': {'server': 'imap.throwaway.email', 'port': 993, 'type': 'imap'},
        'throwaway.org': {'server': 'imap.throwaway.email', 'port': 993, 'type': 'imap'},
        
        # Add more email providers as needed
    }

    # Improved Instagram-specific verification code patterns
    INSTAGRAM_CODE_PATTERNS = [
        # Most specific patterns first
        r"(\d{6})\s+is your Instagram verification code",
        r"(\d{6})\s+is your verification code for Instagram",
        r"Instagram.*?verification.*?code.*?(\d{6})",
        r"verification.*?code.*?Instagram.*?(\d{6})",
        r"код подтверждения.*?Instagram.*?(\d{6})",
        r"Instagram.*?код подтверждения.*?(\d{6})",
        r"Instagram.*?(\d{6})",
        # HTML patterns for Instagram emails
        r'<font size="6">(\d{6})</font>',
        r'<font size=3D"6">(\d{6})</font>',
        r'<span[^>]*>(\d{6})</span>',
        r'<div[^>]*>(\d{6})</div>',
        # Generic patterns (use as last resort)
        r"verification code[:\s]*(\d{6})",
        r"код подтверждения[:\s]*(\d{6})",
        r"security code[:\s]*(\d{6})",
        r"(\d{6})",  # Last resort - 6 digit code only
    ]

    def __init__(self, login, password):
        self.login = login
        self.password = password
        self.domain = self._extract_domain(login)
        self.server_config = self._get_server_config()

    def _extract_domain(self, email_address):
        """Extract domain from email address"""
        try:
            domain = email_address.split('@')[1].lower()
            print(f"📧 [EMAIL_CLIENT] Extracted domain: {domain}")
            return domain
        except IndexError:
            print(f"📧 [EMAIL_CLIENT] [FAIL] Invalid email format: {email_address}")
            return None

    def _get_server_config(self):
        """Get server configuration based on email domain"""
        if not self.domain:
            return None
            
        config = self.EMAIL_SERVERS.get(self.domain)
        if config:
            print(f"📧 [EMAIL_CLIENT] Found server config for {self.domain}: {config['server']}:{config['port']} ({config['type']})")
            return config
        else:
            print(f"📧 [EMAIL_CLIENT] [WARN] No specific config for {self.domain}, will try common servers")
            return None

    def get_verification_code(self, max_retries=3, retry_delay=30):
        """Get verification code with retry logic and time filtering"""
        print(f"📧 [EMAIL_CLIENT] Starting verification code retrieval for: {self.login}")
        
        for retry in range(max_retries):
            if retry > 0:
                print(f"📧 [EMAIL_CLIENT] Retry attempt {retry + 1}/{max_retries}")
                time.sleep(retry_delay)
            
            code = self._attempt_get_verification_code()
            if code:
                print(f"📧 [EMAIL_CLIENT] [OK] Successfully retrieved code: {code}")
                return code
        
        print(f'📧 [EMAIL_CLIENT] [FAIL] Failed to get verification code after {max_retries} attempts')
        return None

    def _attempt_get_verification_code(self):
        """Single attempt to get verification code"""
        # If we have a specific server config, try it first
        if self.server_config:
            print(f"📧 [EMAIL_CLIENT] Using specific server for {self.domain}")
            
            if self.server_config['type'] == 'imap':
                code = self._get_verification_imap(
                    self.server_config['server'], 
                    self.server_config['port']
                )
                if code:
                    return code
            elif self.server_config['type'] == 'pop3':
                code = self._get_verification_pop3(
                    self.server_config['server'], 
                    self.server_config['port']
                )
                if code:
                    return code
        
        # Fallback: try common servers if specific config failed or not found
        print(f"📧 [EMAIL_CLIENT] Trying fallback servers...")
        
        # Расширенный список fallback серверов с приоритетом для временных email провайдеров
        fallback_servers = [
            # FirstMail серверы (высокий приоритет для временных email)
            ('imap.firstmail.ltd', 995, 'pop3'),
            ('imap.firstmail.ltd', 993, 'imap'),  # Попробуем и IMAP
            
            # NotLetters серверы
            ('imap.notletters.com', 993, 'imap'),
            ('imap.notletters.com', 995, 'pop3'),  # Попробуем и POP3
            
            # Другие временные email провайдеры
            ('imap.tempmail.org', 993, 'imap'),
            ('imap.10minutemail.com', 993, 'imap'),
            ('imap.guerrillamail.com', 993, 'imap'),
            ('imap.mailinator.com', 993, 'imap'),
            ('imap.temp-mail.org', 993, 'imap'),
            ('imap.maildrop.cc', 993, 'imap'),
            ('imap.throwaway.email', 993, 'imap'),
            
            # Основные email провайдеры
            ('imap-mail.outlook.com', 993, 'imap'),
            ('imap.rambler.ru', 993, 'imap'),
            ('imap.mail.ru', 993, 'imap'),
            ('imap.yandex.ru', 993, 'imap'),
            ('imap.gmail.com', 993, 'imap'),
            ('imap.mail.yahoo.com', 993, 'imap'),
        ]
        
        for server, port, server_type in fallback_servers:
            print(f"📧 [EMAIL_CLIENT] Trying {server_type.upper()}: {server}:{port}")
            try:
                if server_type == 'imap':
                    code = self._get_verification_imap(server, port)
                else:
                    code = self._get_verification_pop3(server, port)
                
                if code:
                    print(f"📧 [EMAIL_CLIENT] [OK] Success with {server}:{port}")
                    return code
                else:
                    print(f"📧 [EMAIL_CLIENT] [WARN] No code found with {server}:{port}")
            except Exception as e:
                print(f"📧 [EMAIL_CLIENT] [FAIL] {server}:{port} failed: {str(e)}")
                continue
        
        return None

    def _is_recent_email(self, date_str):
        """Check if email is recent (within last 15 minutes)"""
        try:
            # Parse email date
            email_date = email.utils.parsedate_to_datetime(date_str)
            current_time = datetime.now(email_date.tzinfo)
            time_diff = current_time - email_date
            
            # Consider email recent if it's within 15 minutes
            return time_diff.total_seconds() <= 900  # 15 minutes
        except Exception as e:
            print(f"📧 [DATE_CHECK] Could not parse date {date_str}: {str(e)}")
            return True  # If we can't parse date, assume it's recent

    def _extract_code_with_patterns(self, text, source="unknown"):
        """Extract verification code using improved patterns"""
        print(f"📧 [CODE_EXTRACT] Searching for code in {source}")
        
        for i, pattern in enumerate(self.INSTAGRAM_CODE_PATTERNS):
            try:
                match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
                if match:
                    code = match.group(1)
                    # Validate code (should be 6 digits for Instagram)
                    if len(code) == 6 and code.isdigit():
                        print(f"📧 [CODE_EXTRACT] [OK] Found valid code with pattern {i+1}: {code}")
                        return code
                    else:
                        print(f"📧 [CODE_EXTRACT] Invalid code format: {code} (pattern {i+1})")
            except Exception as e:
                print(f"📧 [CODE_EXTRACT] Pattern {i+1} failed: {str(e)}")
                continue
        
        print(f"📧 [CODE_EXTRACT] [FAIL] No valid code found in {source}")
        return None

    def _get_verification_imap(self, server, port):
        """Generic IMAP verification code retrieval with improved filtering"""
        print(f"📧 [IMAP] Connecting to IMAP server: {server}:{port}")
        try:
            # Подключение к IMAP
            print(f"📧 [IMAP] Establishing SSL connection...")
            mail = imaplib.IMAP4_SSL(server, port)
            print(f"📧 [IMAP] SSL connection established")
            
            print(f"📧 [IMAP] Logging in with user: {self.login}")
            mail.login(self.login, self.password)
            print(f"📧 [IMAP] [OK] Login successful")
            
            print(f"📧 [IMAP] Selecting inbox...")
            mail.select("inbox")

            # Search for recent emails from Instagram
            print(f"📧 [IMAP] Searching for recent emails...")
            
            # Search for emails from the last hour
            since_date = (datetime.now() - timedelta(hours=1)).strftime("%d-%b-%Y")
            status, messages = mail.search(None, f'(SINCE "{since_date}")')
            
            if status != "OK":
                print(f"📧 [IMAP] [FAIL] Search failed with status: {status}")
                return None

            message_ids = messages[0].split()
            if not message_ids:
                print(f"📧 [IMAP] [FAIL] No recent emails found")
                return None

            print(f"📧 [IMAP] Found {len(message_ids)} recent emails")
            
            # Process emails from newest to oldest
            for email_id in reversed(message_ids[-10:]):  # Check last 10 emails
                print(f"📧 [IMAP] Processing email ID: {email_id}")
                
                # Получаем письмо
                status, msg_data = mail.fetch(email_id, "(RFC822)")
                if status != "OK":
                    continue

                # Парсим письмо
                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)

                # Check email date
                date_str = msg.get("Date", "")
                if not self._is_recent_email(date_str):
                    print(f"📧 [IMAP] Skipping old email: {date_str}")
                    continue

                # Check if email is from Instagram
                from_address = msg.get("From", "").lower()
                subject = decode_header(msg["Subject"])[0][0]
                if isinstance(subject, bytes):
                    subject = subject.decode()
                
                print(f"📧 [IMAP] Email from: {from_address}")
                print(f"📧 [IMAP] Subject: {subject}")
                
                # Check if this looks like an Instagram email
                if not any(keyword in from_address for keyword in ['instagram', 'facebook', 'meta']) and \
                   not any(keyword in subject.lower() for keyword in ['instagram', 'verification', 'код']):
                    print(f"📧 [IMAP] Skipping non-Instagram email")
                    continue
                
                # Try to extract code from subject first
                code = self._extract_code_with_patterns(subject, "subject")
                if code:
                    return code
                
                # Extract email body content
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body += part.get_payload(decode=True).decode('utf-8', errors='ignore')
                        elif part.get_content_type() == "text/html":
                            body += part.get_payload(decode=True).decode('utf-8', errors='ignore')
                else:
                    body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
                
                # Try to extract code from body
                code = self._extract_code_with_patterns(body, "body")
                if code:
                    return code
            
            print(f"📧 [IMAP] [FAIL] No verification code found in recent emails")
            return None

        except Exception as e:
            print(f"📧 [IMAP] [FAIL] Error: {str(e)}")
            return None
        finally:
            try:
                mail.logout()
                print(f"📧 [IMAP] Logged out successfully")
            except:
                print(f"📧 [IMAP] Warning: Could not logout cleanly")
                pass

    def _get_verification_pop3(self, server, port):
        """Generic POP3 verification code retrieval with improved filtering"""
        print(f"📧 [POP3] Connecting to POP3 server: {server}:{port}")
        try:
            # Подключение к серверу
            print(f"📧 [POP3] Establishing SSL connection...")
            mail = poplib.POP3_SSL(server, port)
            print(f"📧 [POP3] SSL connection established")

            # Аутентификация
            print(f"📧 [POP3] Authenticating user: {self.login}")
            mail.user(self.login)
            mail.pass_(self.password)
            print(f"📧 [POP3] [OK] Authentication successful")

            # Получаем статистику почтового ящика
            print(f"📧 [POP3] Getting mailbox statistics...")
            num_messages = len(mail.list()[1])
            print(f"📧 [POP3] Found {num_messages} messages in mailbox")
            
            if num_messages == 0:
                print("📧 [POP3] [FAIL] Mailbox is empty")
                mail.quit()
                return None

            # Check last few messages (up to 5)
            messages_to_check = min(5, num_messages)
            for i in range(messages_to_check):
                message_num = num_messages - i  # Start from newest
                
                print(f"📧 [POP3] Retrieving message #{message_num}...")
                response, lines, octets = mail.retr(message_num)
                
                # Преобразуем строки в байты и парсим письмо
                raw_email = b'\r\n'.join(lines)
                msg = email.message_from_bytes(raw_email, policy=default)

                # Check email date
                date_str = msg.get("Date", "")
                if not self._is_recent_email(date_str):
                    print(f"📧 [POP3] Skipping old email: {date_str}")
                    continue

                # Check if email is from Instagram
                from_address = msg.get("From", "").lower()
                subject, encoding = decode_header(msg["Subject"])[0]
                if isinstance(subject, bytes):
                    subject = subject.decode(encoding or "utf-8")
                
                print(f"📧 [POP3] Email from: {from_address}")
                print(f"📧 [POP3] Subject: {subject}")
                
                # Check if this looks like an Instagram email
                if not any(keyword in from_address for keyword in ['instagram', 'facebook', 'meta']) and \
                   not any(keyword in subject.lower() for keyword in ['instagram', 'verification', 'код']):
                    print(f"📧 [POP3] Skipping non-Instagram email")
                    continue

                # Try to extract code from subject first
                code = self._extract_code_with_patterns(subject, "subject")
                if code:
                    mail.quit()
                    return code
                
                # Извлечение текстового содержимого
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_content()
                            break
                else:
                    body = msg.get_content()

                # Try to extract code from body
                code = self._extract_code_with_patterns(body, "body")
                if code:
                    mail.quit()
                    return code

            mail.quit()
            print(f"📧 [POP3] [FAIL] No verification code found in recent messages")
            return None

        except Exception as e:
            print(f"📧 [POP3] [FAIL] Error: {str(e)}")
            if 'mail' in locals():
                try:
                    mail.quit()
                    print(f"📧 [POP3] Cleaned up connection")
                except:
                    print(f"📧 [POP3] Warning: Could not clean up connection")
            return None

    def test_connection(self):
        """Test email connection without retrieving verification code"""
        print(f"📧 [TEST] Testing email connection for: {self.login}")
        print(f"📧 [TEST] Domain: {self.domain}")
        
        if self.server_config:
            print(f"📧 [TEST] Using specific server config: {self.server_config}")
            
            if self.server_config['type'] == 'imap':
                return self._test_imap_connection(
                    self.server_config['server'], 
                    self.server_config['port']
                )
            elif self.server_config['type'] == 'pop3':
                return self._test_pop3_connection(
                    self.server_config['server'], 
                    self.server_config['port']
                )
        else:
            print(f"📧 [TEST] No specific config found, testing common servers...")
            
            # Test common servers
            test_servers = [
                ('imap.notletters.com', 993, 'imap'),
                ('imap-mail.outlook.com', 993, 'imap'),
                ('imap.firstmail.ltd', 995, 'pop3'),
                ('imap.rambler.ru', 993, 'imap'),
            ]
            
            for server, port, server_type in test_servers:
                print(f"📧 [TEST] Testing {server_type.upper()} server: {server}:{port}")
                
                if server_type == 'imap':
                    if self._test_imap_connection(server, port):
                        return True
                elif server_type == 'pop3':
                    if self._test_pop3_connection(server, port):
                        return True
            
            print(f"📧 [TEST] [FAIL] All server tests failed")
            return False

    def _test_imap_connection(self, server, port):
        """Test IMAP connection"""
        try:
            print(f"📧 [TEST_IMAP] Testing connection to {server}:{port}")
            mail = imaplib.IMAP4_SSL(server, port)
            print(f"📧 [TEST_IMAP] SSL connection established")
            
            mail.login(self.login, self.password)
            print(f"📧 [TEST_IMAP] [OK] Login successful")
            
            mail.select("inbox")
            print(f"📧 [TEST_IMAP] [OK] Inbox selected")
            
            status, messages = mail.search(None, "ALL")
            if status == "OK":
                message_count = len(messages[0].split()) if messages[0] else 0
                print(f"📧 [TEST_IMAP] [OK] Found {message_count} emails in inbox")
            
            mail.logout()
            print(f"📧 [TEST_IMAP] [OK] Connection test successful")
            return True
            
        except Exception as e:
            print(f"📧 [TEST_IMAP] [FAIL] Connection test failed: {str(e)}")
            return False

    def _test_pop3_connection(self, server, port):
        """Test POP3 connection"""
        try:
            print(f"📧 [TEST_POP3] Testing connection to {server}:{port}")
            mail = poplib.POP3_SSL(server, port)
            print(f"📧 [TEST_POP3] SSL connection established")
            
            mail.user(self.login)
            mail.pass_(self.password)
            print(f"📧 [TEST_POP3] [OK] Authentication successful")
            
            num_messages = len(mail.list()[1])
            print(f"📧 [TEST_POP3] [OK] Found {num_messages} messages in mailbox")
            
            mail.quit()
            print(f"📧 [TEST_POP3] [OK] Connection test successful")
            return True
            
        except Exception as e:
            print(f"📧 [TEST_POP3] [FAIL] Connection test failed: {str(e)}")
            return False
