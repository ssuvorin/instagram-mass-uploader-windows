import email
import imaplib
import poplib
import re
import logging
from email.header import decode_header
from email.policy import default
from datetime import datetime

# Настройка логирования для email клиента
logger = logging.getLogger(__name__)

class Email:
    IMAP_SERVER = "imap.rambler.ru"
    IMAP_PORT = 993
    # Конфигурация сервера
    POP3_SERVER = "imap.firstmail.ltd"
    POP3_PORT = 995 # Стандартный порт для POP3 over SSL
    NOTLETTERS_SERVER = 'imap.notletters.com'
    NOTLETTERS_PORT = 993

    def __init__(self, login, password):
        logger.info(f"📧 Инициализация Email клиента для: {login}")
        self.login = login
        self.password = password
        logger.info("✅ Email клиент инициализирован")

    def test_connection(self):
        """Тест подключения к почте с подробным логированием"""
        try:
            logger.info(f"🔍 Тестируем подключение к {self.login}")
            logger.info(f"🌐 Сервер: {Email.IMAP_SERVER}:{Email.IMAP_PORT}")
            
            mail = imaplib.IMAP4_SSL(Email.IMAP_SERVER, Email.IMAP_PORT)
            logger.info("🔐 SSL подключение установлено")
            
            logger.info("🔑 Выполняем аутентификацию...")
            mail.login(self.login, self.password)
            logger.info("✅ Аутентификация успешна")
            
            # Выбираем папку входящих
            logger.info("📂 Выбираем папку 'inbox'...")
            mail.select("inbox")
            
            # Получаем количество писем
            logger.info("🔍 Получаем список писем...")
            status, messages = mail.search(None, "ALL")
            if status == "OK":
                message_count = len(messages[0].split()) if messages[0] else 0
                logger.info(f"✅ Подключение успешно! Найдено {message_count} писем")
                print(f"✅ Подключение успешно! Найдено {message_count} писем")
            else:
                logger.warning(f"⚠️ Статус поиска: {status}")
            
            mail.logout()
            logger.info("🔌 Подключение закрыто")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка подключения: {e}")
            print(f"❌ Ошибка подключения: {e}")
            return False

    def get_verification_code(self):
        logger.info("🔍 Начинаем поиск кода подтверждения...")
        logger.info("📋 Порядок попыток:")
        logger.info("  1. NotLetters IMAP")
        logger.info("  2. Hotmail/Outlook IMAP") 
        logger.info("  3. FirstMail POP3")
        logger.info("  4. Rambler IMAP")
        
        # Пробуем разные методы по порядку
        methods = [
            ("NotLetters IMAP", self.get_verification_imap_notletters),
            ("Hotmail IMAP", self.get_verification_code_hotmail),
            ("FirstMail POP3", self.get_verification_code_pop3),
            ("Rambler IMAP", self.get_verification_imap)
        ]
        
        for method_name, method_func in methods:
            logger.info(f"🔄 Пробуем метод: {method_name}")
            try:
                res = method_func()
                if res:
                    logger.info(f"✅ Код найден методом {method_name}: {res}")
                    return res
                else:
                    logger.info(f"❌ Код не найден методом {method_name}")
            except Exception as e:
                logger.error(f"❌ Ошибка в методе {method_name}: {e}")
        
        logger.error('❌ Код не найден ни одним методом')
        return None

    def get_verification_imap(self):
        method_name = "Rambler IMAP"
        logger.info(f"📧 {method_name}: Начинаем подключение...")
        
        try:
            # Подключение к IMAP
            logger.info(f"🌐 Подключаемся к {Email.IMAP_SERVER}:{Email.IMAP_PORT}")
            mail = imaplib.IMAP4_SSL(Email.IMAP_SERVER, Email.IMAP_PORT)
            
            logger.info("🔑 Выполняем вход...")
            mail.login(self.login, self.password)
            
            logger.info("📂 Выбираем папку inbox...")
            mail.select("inbox")
            
            # Поиск последних писем (за последний час)
            import datetime
            since_date = (datetime.datetime.now() - datetime.timedelta(hours=1)).strftime("%d-%b-%Y")
            logger.info(f"🔍 Ищем письма с {since_date}...")
            
            status, messages = mail.search(None, f'SINCE {since_date}')
            if status != "OK":
                logger.error(f"❌ Ошибка поиска писем: {status}")
                return None
            
            # Получаем ID писем
            message_ids = messages[0].split() if messages[0] else []
            logger.info(f"📧 Найдено писем: {len(message_ids)}")
            
            if not message_ids:
                logger.warning("❌ Писем не найдено")
                return None
            
            # Проверяем последние 5 писем
            check_count = min(5, len(message_ids))
            logger.info(f"🔍 Проверяем последние {check_count} писем...")
            
            for i in range(check_count):
                email_id = message_ids[-(i+1)]  # Берем с конца (самые новые)
                logger.info(f"📧 Проверяем письмо {i+1}/{check_count} (ID: {email_id.decode()})")
                
                # Получаем письмо
                status, msg_data = mail.fetch(email_id, "(RFC822)")
                if status != "OK":
                    logger.warning(f"⚠️ Не удалось получить письмо {i+1}")
                    continue
                
                # Парсим письмо
                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)
                
                # Получаем отправителя
                from_header = msg.get("From", "")
                logger.info(f"👤 От: {from_header}")
                
                # Декодируем заголовок
                subject = decode_header(msg["Subject"])[0][0]
                if isinstance(subject, bytes):
                    subject = subject.decode()
                
                logger.info(f"📋 Тема: {subject}")
                
                # Ищем код в теме
                patterns = [
                    r"(\d{6})",  # 6 цифр подряд
                    r"(\d+) is your verification code",  # Стандартный формат Instagram
                    r"код.*?(\d{6})",  # "код" + 6 цифр
                    r"verification.*?(\d{6})"  # "verification" + 6 цифр
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, subject, re.IGNORECASE)
                    if match:
                        code = match.group(1)
                        if len(code) == 6:
                            logger.info(f"✅ Код найден в теме письма {i+1}: {code}")
                            return code
                
                # Если в теме не нашли, ищем в тексте
                try:
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/plain":
                                body = part.get_payload(decode=True).decode()
                                break
                    else:
                        body = msg.get_payload(decode=True).decode()
                    
                    logger.info(f"📄 Текст письма {i+1} (первые 200 символов): {body[:200]}...")
                    
                    for pattern in patterns:
                        match = re.search(pattern, body, re.IGNORECASE)
                        if match:
                            code = match.group(1)
                            if len(code) == 6:
                                logger.info(f"✅ Код найден в тексте письма {i+1}: {code}")
                                return code
                except Exception as e:
                    logger.warning(f"⚠️ Ошибка чтения тела письма {i+1}: {e}")
            
            logger.warning(f"❌ Код не найден в {check_count} проверенных письмах")
            return None
        
        except Exception as e:
            logger.error(f"❌ Ошибка в {method_name}: {e}")
            return None
        finally:
            try:
                mail.logout()
                logger.info(f"🔌 {method_name}: Подключение закрыто")
            except:
                pass

    def get_verification_code_pop3(self):
        method_name = "FirstMail POP3"
        logger.info(f"📧 {method_name}: Начинаем подключение...")
        
        try:
            # Подключение к серверу
            logger.info(f"🌐 Подключаемся к {Email.POP3_SERVER}:{Email.POP3_PORT}")
            mail = poplib.POP3_SSL(Email.POP3_SERVER, Email.POP3_PORT)
            
            # Аутентификация
            logger.info("🔑 Выполняем аутентификацию...")
            mail.user(self.login)
            mail.pass_(self.password)
            
            # Получаем статистику почтового ящика
            logger.info("📊 Получаем статистику ящика...")
            num_messages = len(mail.list()[1])
            logger.info(f"📧 Всего писем: {num_messages}")
            
            if num_messages == 0:
                logger.warning("❌ Почтовый ящик пуст")
                mail.quit()
                return None
            
            # Проверяем последние 3 письма
            check_count = min(3, num_messages)
            logger.info(f"🔍 Проверяем последние {check_count} писем...")
            
            for i in range(check_count):
                msg_num = num_messages - i  # Начинаем с последнего
                logger.info(f"📧 Проверяем письмо {i+1}/{check_count} (номер {msg_num})")
                
                response, lines, octets = mail.retr(msg_num)
                
                # Преобразуем строки в байты и парсим письмо
                raw_email = b'\r\n'.join(lines)
                msg = email.message_from_bytes(raw_email, policy=default)
                
                # Декодирование заголовков
                subject, encoding = decode_header(msg["Subject"])[0]
                if isinstance(subject, bytes):
                    subject = subject.decode(encoding or "utf-8")
                
                from_, encoding = decode_header(msg.get("From"))[0]
                if isinstance(from_, bytes):
                    from_ = from_.decode(encoding or "utf-8")
                
                logger.info(f"👤 От: {from_}")
                logger.info(f"📋 Тема: {subject}")
                
                # Извлечение текстового содержимого
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_content()
                            break
                else:
                    body = msg.get_content()
                
                logger.info(f"📄 Текст (первые 200 символов): {str(body)[:200]}...")
                
                # Ищем 6-значный код
                patterns = [r'(\d{6})', r'код.*?(\d{6})', r'verification.*?(\d{6})']
                full_text = subject + " " + str(body)
                
                for pattern in patterns:
                    match = re.search(pattern, full_text, re.IGNORECASE)
                    if match:
                        code = match.group(1)
                        if len(code) == 6:
                            logger.info(f"✅ Код найден в письме {i+1}: {code}")
                            mail.quit()
                            return code
            
            mail.quit()
            logger.warning(f"❌ Код не найден в {check_count} проверенных письмах")
            return None
        
        except Exception as e:
            logger.error(f"❌ Ошибка в {method_name}: {e}")
            if 'mail' in locals():
                try:
                    mail.quit()
                except:
                    pass
            return None

    def get_verification_code_hotmail(self):
        method_name = "Hotmail IMAP"
        logger.info(f"📧 {method_name}: Начинаем подключение...")
        
        try:
            # Подключение к IMAP
            logger.info(f"🌐 Подключаемся к imap-mail.outlook.com:{Email.IMAP_PORT}")
            mail = imaplib.IMAP4_SSL('imap-mail.outlook.com', Email.IMAP_PORT)
            
            logger.info("🔑 Выполняем вход...")
            mail.login(self.login, self.password)
            
            logger.info("📂 Выбираем папку inbox...")
            mail.select("inbox")
            
            # Поиск последних писем
            logger.info("🔍 Ищем письма...")
            status, messages = mail.search(None, "ALL")
            if status != "OK":
                logger.error(f"❌ Ошибка поиска: {status}")
                return None
            
            # Получаем ID последних писем
            message_ids = messages[0].split() if messages[0] else []
            logger.info(f"📧 Найдено писем: {len(message_ids)}")
            
            if not message_ids:
                logger.warning("❌ Писем не найдено")
                return None
            
            # Проверяем последние 3 письма
            check_count = min(3, len(message_ids))
            logger.info(f"🔍 Проверяем последние {check_count} писем...")
            
            for i in range(check_count):
                email_id = message_ids[-(i+1)]  # Берем с конца
                logger.info(f"📧 Проверяем письмо {i+1}/{check_count}")
                
                # Получаем письмо
                status, msg_data = mail.fetch(email_id, "(RFC822)")
                if status != "OK":
                    logger.warning(f"⚠️ Не удалось получить письмо {i+1}")
                    continue
                
                # Парсим письмо
                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)
                
                # Декодируем заголовок
                subject = decode_header(msg["Subject"])[0][0]
                if isinstance(subject, bytes):
                    subject = subject.decode()
                
                from_header = msg.get("From", "")
                logger.info(f"👤 От: {from_header}")
                logger.info(f"📋 Тема: {subject}")
                
                # Ищем код
                patterns = [
                    r"(\d{6})",
                    r"(\d+) is your verification code",
                    r"код.*?(\d{6})",
                    r"verification.*?(\d{6})"
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, subject, re.IGNORECASE)
                    if match:
                        code = match.group(1)
                        if len(code) == 6:
                            logger.info(f"✅ Код найден: {code}")
                            return code
            
            logger.warning(f"❌ Код не найден в {check_count} письмах")
            return None
        
        except Exception as e:
            logger.error(f"❌ Ошибка в {method_name}: {e}")
            return None
        finally:
            try:
                mail.logout()
                logger.info(f"🔌 {method_name}: Подключение закрыто")
            except:
                pass

    def get_verification_imap_notletters(self):
        method_name = "NotLetters IMAP"
        logger.info(f"📧 {method_name}: Начинаем подключение...")
        
        try:
            # Подключение к IMAP
            logger.info(f"🌐 Подключаемся к {Email.NOTLETTERS_SERVER}:{Email.NOTLETTERS_PORT}")
            mail = imaplib.IMAP4_SSL(Email.NOTLETTERS_SERVER, Email.NOTLETTERS_PORT)
            
            logger.info("🔑 Выполняем вход...")
            mail.login(self.login, self.password)
            
            logger.info("📂 Выбираем папку inbox...")
            mail.select("inbox")
            
            # Поиск писем
            logger.info("🔍 Ищем письма...")
            status, messages = mail.search(None, "ALL")
            if status != "OK":
                logger.error(f"❌ Ошибка поиска: {status}")
                return None
            
            # Получаем ID последних писем
            message_ids = messages[0].split() if messages[0] else []
            logger.info(f"📧 Найдено писем: {len(message_ids)}")
            
            if not message_ids:
                logger.warning("❌ Писем не найдено")
                return None
            
            # Проверяем последние 3 письма
            check_count = min(3, len(message_ids))
            logger.info(f"🔍 Проверяем последние {check_count} писем...")
            
            for i in range(check_count):
                email_id = message_ids[-(i+1)]  # Берем с конца
                logger.info(f"📧 Проверяем письмо {i+1}/{check_count}")
                
                # Получаем письмо
                status, msg_data = mail.fetch(email_id, "(RFC822)")
                if status != "OK":
                    logger.warning(f"⚠️ Не удалось получить письмо {i+1}")
                    continue
                
                # Парсим письмо
                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)
                
                # Декодируем заголовок
                subject = decode_header(msg["Subject"])[0][0]
                if isinstance(subject, bytes):
                    subject = subject.decode()
                
                from_header = msg.get("From", "")
                logger.info(f"👤 От: {from_header}")
                logger.info(f"📋 Тема: {subject}")
                
                # Ищем код в теме
                match = re.search(r"(\d{6})", subject)
                if match:
                    code = match.group(1)
                    logger.info(f"✅ Код найден в теме: {code}")
                    return code
                else:
                    # Ищем в тексте письма
                    logger.info("🔍 Ищем в тексте письма...")
                    pattern = r'(\d{6})'
                    result = re.search(pattern, str(msg))
                    if result:
                        code = result.group(1)
                        logger.info(f"✅ Код найден в тексте: {code}")
                        return code
            
            logger.warning(f"❌ Код не найден в {check_count} письмах")
            return None
        
        except Exception as e:
            logger.error(f"❌ Ошибка в {method_name}: {e}")
            return None
        finally:
            try:
                mail.logout()
                logger.info(f"🔌 {method_name}: Подключение закрыто")
            except:
                pass
