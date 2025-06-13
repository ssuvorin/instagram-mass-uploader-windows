import email
import imaplib
import poplib
import re
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
        
        # NotLetters and temporary email providers
        'notletters.com': {'server': 'imap.notletters.com', 'port': 993, 'type': 'imap'},
        'tempmail.org': {'server': 'imap.tempmail.org', 'port': 993, 'type': 'imap'},
        '10minutemail.com': {'server': 'imap.10minutemail.com', 'port': 993, 'type': 'imap'},
        'guerrillamail.com': {'server': 'imap.guerrillamail.com', 'port': 993, 'type': 'imap'},
        'mailinator.com': {'server': 'imap.mailinator.com', 'port': 993, 'type': 'imap'},
        
        # FirstMail (POP3)
        'firstmail.ltd': {'server': 'imap.firstmail.ltd', 'port': 995, 'type': 'pop3'},
        
        # Add more email providers as needed
    }

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
            print(f"📧 [EMAIL_CLIENT] ❌ Invalid email format: {email_address}")
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
            print(f"📧 [EMAIL_CLIENT] ⚠️ No specific config for {self.domain}, will try common servers")
            return None

    def get_verification_code(self):
        print(f"📧 [EMAIL_CLIENT] Starting verification code retrieval for: {self.login}")
        
        # If we have a specific server config, try it first
        if self.server_config:
            print(f"📧 [EMAIL_CLIENT] Using specific server for {self.domain}")
            
            if self.server_config['type'] == 'imap':
                code = self._get_verification_imap(
                    self.server_config['server'], 
                    self.server_config['port']
                )
                if code:
                    print(f"📧 [EMAIL_CLIENT] ✅ Successfully got code from {self.domain}: {code}")
                    return code
            elif self.server_config['type'] == 'pop3':
                code = self._get_verification_pop3(
                    self.server_config['server'], 
                    self.server_config['port']
                )
                if code:
                    print(f"📧 [EMAIL_CLIENT] ✅ Successfully got code from {self.domain}: {code}")
                    return code
        
        # Fallback: try common servers if specific config failed or not found
        print(f"📧 [EMAIL_CLIENT] Trying fallback servers...")
        
        # Try notletters.com first (common for temp emails)
        print(f"📧 [EMAIL_CLIENT] Trying notletters.com IMAP server...")
        res = self.get_verification_imap_notletters()
        if res:
            print(f"📧 [EMAIL_CLIENT] ✅ Successfully got code from notletters.com: {res}")
            return res
            
        # Try hotmail next
        print(f"📧 [EMAIL_CLIENT] Trying Hotmail/Outlook IMAP server...")
        res = self.get_verification_code_hotmail()
        if res:
            print(f"📧 [EMAIL_CLIENT] ✅ Successfully got code from Hotmail: {res}")
            return res
            
        # Try POP3 server
        print(f"📧 [EMAIL_CLIENT] Trying POP3 server...")
        res = self.get_verification_code_pop3()
        if res:
            print(f"📧 [EMAIL_CLIENT] ✅ Successfully got code from POP3: {res}")
            return res
            
        # Try IMAP rambler as fallback
        print(f"📧 [EMAIL_CLIENT] Trying Rambler IMAP server as fallback...")
        res = self.get_verification_imap()
        if res:
            print(f"📧 [EMAIL_CLIENT] ✅ Successfully got code from Rambler: {res}")
            return res
            
        print('📧 [EMAIL_CLIENT] ❌ Failed to get verification code from all email servers')
        return None

    def _get_verification_imap(self, server, port):
        """Generic IMAP verification code retrieval"""
        print(f"📧 [IMAP] Connecting to IMAP server: {server}:{port}")
        try:
            # Подключение к IMAP
            print(f"📧 [IMAP] Establishing SSL connection...")
            mail = imaplib.IMAP4_SSL(server, port)
            print(f"📧 [IMAP] SSL connection established")
            
            print(f"📧 [IMAP] Logging in with user: {self.login}")
            mail.login(self.login, self.password)
            print(f"📧 [IMAP] ✅ Login successful")
            
            print(f"📧 [IMAP] Selecting inbox...")
            mail.select("inbox")

            # Поиск последнего письма
            print(f"📧 [IMAP] Searching for emails...")
            status, messages = mail.search(None, "ALL")
            if status != "OK":
                print(f"📧 [IMAP] ❌ Search failed with status: {status}")
                return None

            # Получаем ID последнего письма
            message_ids = messages[0].split()
            if not message_ids:
                print(f"📧 [IMAP] ❌ No emails found in inbox")
                return None

            print(f"📧 [IMAP] Found {len(message_ids)} emails in inbox")
            latest_email_id = message_ids[-1]
            print(f"📧 [IMAP] Processing latest email ID: {latest_email_id}")

            # Получаем письмо
            status, msg_data = mail.fetch(latest_email_id, "(RFC822)")
            if status != "OK":
                print(f"📧 [IMAP] ❌ Failed to fetch email with status: {status}")
                return None

            print(f"📧 [IMAP] Email fetched successfully, parsing...")
            # Парсим письмо
            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)

            # Декодируем заголовок
            subject = decode_header(msg["Subject"])[0][0]
            if isinstance(subject, bytes):
                subject = subject.decode()
            print(f"📧 [IMAP] Email subject: '{subject}'")
            
            # Ищем код с помощью регулярного выражения в заголовке
            print(f"📧 [IMAP] Searching for verification code in subject...")
            
            # Multiple patterns for verification codes in subject
            subject_patterns = [
                r"(\d+) is your verification code",
                r"verification code[:\s]*(\d+)",
                r"код подтверждения[:\s]*(\d+)",
                r"(\d{4,8})",  # Generic 4-8 digit code
            ]
            
            for pattern in subject_patterns:
                match = re.search(pattern, subject, re.IGNORECASE)
                if match:
                    code = match.group(1)
                    print(f"📧 [IMAP] ✅ Found verification code in subject: {code}")
                    return code
            
            print(f"📧 [IMAP] No verification code found in subject, checking email body...")
            
            # Extract email body content
            body = ""
            if msg.is_multipart():
                print(f"📧 [IMAP] Email is multipart, extracting text content...")
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body += part.get_payload(decode=True).decode('utf-8', errors='ignore')
                    elif part.get_content_type() == "text/html":
                        body += part.get_payload(decode=True).decode('utf-8', errors='ignore')
            else:
                print(f"📧 [IMAP] Email is single part")
                body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
            
            print(f"📧 [IMAP] Body content length: {len(body)} characters")
            
            # Search for verification code patterns in body
            print(f"📧 [IMAP] Searching for verification code patterns in body...")
            body_patterns = [
                r'<font size="6">(\d+)</font>',
                r'<font size=3D"6">(\d+)</font>',
                r'verification code[:\s]*(\d+)',
                r'код подтверждения[:\s]*(\d+)',
                r'(\d{4,8})',  # Generic 4-8 digit code
            ]
            
            for pattern in body_patterns:
                result = re.search(pattern, body, re.IGNORECASE)
                if result:
                    code = result.group(1)
                    print(f"📧 [IMAP] ✅ Found verification code in body: {code}")
                    return code
            
            print(f"📧 [IMAP] ❌ No verification code pattern found in email")
            return None

        except Exception as e:
            print(f"📧 [IMAP] ❌ Error: {str(e)}")
            return None
        finally:
            try:
                mail.logout()
                print(f"📧 [IMAP] Logged out successfully")
            except:
                print(f"📧 [IMAP] Warning: Could not logout cleanly")
                pass

    def _get_verification_pop3(self, server, port):
        """Generic POP3 verification code retrieval"""
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
            print(f"📧 [POP3] ✅ Authentication successful")

            # Получаем статистику почтового ящика
            print(f"📧 [POP3] Getting mailbox statistics...")
            num_messages = len(mail.list()[1])
            print(f"📧 [POP3] Found {num_messages} messages in mailbox")
            
            if num_messages == 0:
                print("📧 [POP3] ❌ Mailbox is empty")
                mail.quit()
                return None

            # Получаем последнее письмо (с наибольшим номером)
            print(f"📧 [POP3] Retrieving latest message (#{num_messages})...")
            response, lines, octets = mail.retr(num_messages)
            print(f"📧 [POP3] Message retrieved, size: {octets} bytes")

            # Преобразуем строки в байты и парсим письмо
            print(f"📧 [POP3] Parsing email message...")
            raw_email = b'\r\n'.join(lines)
            msg = email.message_from_bytes(raw_email, policy=default)

            # Декодирование заголовков
            subject, encoding = decode_header(msg["Subject"])[0]
            if isinstance(subject, bytes):
                subject = subject.decode(encoding or "utf-8")
            print(f"📧 [POP3] Email subject: '{subject}'")

            from_, encoding = decode_header(msg.get("From"))[0]
            if isinstance(from_, bytes):
                from_ = from_.decode(encoding or "utf-8")
            print(f"📧 [POP3] Email from: '{from_}'")

            # Извлечение текстового содержимого
            print(f"📧 [POP3] Extracting email body content...")
            body = ""
            if msg.is_multipart():
                print(f"📧 [POP3] Email is multipart, searching for text/plain part...")
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_content()
                        print(f"📧 [POP3] Found text/plain part")
                        break
            else:
                print(f"📧 [POP3] Email is single part")
                body = msg.get_content()

            print(f"📧 [POP3] Body content length: {len(body)} characters")
            mail.quit()
            print(f"📧 [POP3] Disconnected from server")
            
            # Search for verification code pattern
            print(f"📧 [POP3] Searching for verification code pattern in body...")
            pattern = r'<font size="6">(\d+)</font>'
            result = re.search(pattern, body)
            if result:
                code = result.group(1)
                print(f"📧 [POP3] ✅ Found verification code: {code}")
                return code
            else:
                print(f"📧 [POP3] ❌ No verification code pattern found in email body")
                return None

        except Exception as e:
            print(f"📧 [POP3] ❌ Error: {str(e)}")
            if 'mail' in locals():
                try:
                    mail.quit()
                    print(f"📧 [POP3] Cleaned up connection")
                except:
                    print(f"📧 [POP3] Warning: Could not clean up connection")
            return None

    def get_verification_code_pop3(self):
        """Legacy method for FirstMail POP3 - now uses generic method"""
        return self._get_verification_pop3('imap.firstmail.ltd', 995)

    def get_verification_code_hotmail(self):
        """Legacy method for Hotmail IMAP - now uses generic method"""
        return self._get_verification_imap('imap-mail.outlook.com', 993)

    def get_verification_imap_notletters(self):
        """Legacy method for NotLetters IMAP - now uses generic method"""
        return self._get_verification_imap('imap.notletters.com', 993)

    def get_verification_imap(self):
        """Legacy method for Rambler IMAP - now uses generic method"""
        return self._get_verification_imap('imap.rambler.ru', 993)

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
            
            print(f"📧 [TEST] ❌ All server tests failed")
            return False

    def _test_imap_connection(self, server, port):
        """Test IMAP connection"""
        try:
            print(f"📧 [TEST_IMAP] Testing connection to {server}:{port}")
            mail = imaplib.IMAP4_SSL(server, port)
            print(f"📧 [TEST_IMAP] SSL connection established")
            
            mail.login(self.login, self.password)
            print(f"📧 [TEST_IMAP] ✅ Login successful")
            
            mail.select("inbox")
            print(f"📧 [TEST_IMAP] ✅ Inbox selected")
            
            status, messages = mail.search(None, "ALL")
            if status == "OK":
                message_count = len(messages[0].split()) if messages[0] else 0
                print(f"📧 [TEST_IMAP] ✅ Found {message_count} emails in inbox")
            
            mail.logout()
            print(f"📧 [TEST_IMAP] ✅ Connection test successful")
            return True
            
        except Exception as e:
            print(f"📧 [TEST_IMAP] ❌ Connection test failed: {str(e)}")
            return False

    def _test_pop3_connection(self, server, port):
        """Test POP3 connection"""
        try:
            print(f"📧 [TEST_POP3] Testing connection to {server}:{port}")
            mail = poplib.POP3_SSL(server, port)
            print(f"📧 [TEST_POP3] SSL connection established")
            
            mail.user(self.login)
            mail.pass_(self.password)
            print(f"📧 [TEST_POP3] ✅ Authentication successful")
            
            num_messages = len(mail.list()[1])
            print(f"📧 [TEST_POP3] ✅ Found {num_messages} messages in mailbox")
            
            mail.quit()
            print(f"📧 [TEST_POP3] ✅ Connection test successful")
            return True
            
        except Exception as e:
            print(f"📧 [TEST_POP3] ❌ Connection test failed: {str(e)}")
            return False
