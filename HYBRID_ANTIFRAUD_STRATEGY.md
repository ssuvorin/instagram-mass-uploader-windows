# Надежная Гибридная Антифрод Система

## Текущая архитектура

У вас правильный подход - два метода загрузки:
- **Browser (Playwright)**: `start_bulk_upload` - полная браузерная автоматизация
- **API (instagrapi)**: `start_bulk_upload_api` - мобильный API

## Цель: Максимальная надежность независимо от выбора оператора

### 1. Устранение критических проблем (Core Issues)

**Проблема 1**: Несинхронизированные fingerprints между браузером и API
**Проблема 2**: Потеря сессий при переключении методов  
**Проблема 3**: Неправильная обработка ошибок
**Проблема 4**: Нестабильное поведение при сбоях

```python
# New: uploader/robust_execution_manager.py
class RobustExecutionManager:
    """Обеспечивает надежность любого выбранного метода"""
    
    def __init__(self):
        self.session_sync = SessionSyncManager()
        self.fingerprint_sync = FingerprintSyncManager()
        self.error_handler = UniversalErrorHandler()
        self.fallback_manager = FallbackManager()
    
    def execute_upload_method(self, account: InstagramAccount, method: str, videos: List) -> bool:
        """Выполнить загрузку выбранным методом с максимальной надежностью"""
        
        try:
            # 1. Подготовка к выполнению
            self._prepare_account_for_method(account, method)
            
            # 2. Выполнение с retry логикой
            result = self._execute_with_retries(account, method, videos)
            
            # 3. Обработка результата
            return self._process_result(account, method, result)
            
        except Exception as e:
            # 4. Обработка критических ошибок
            return self._handle_critical_error(account, method, e, videos)
    
    def _prepare_account_for_method(self, account: InstagramAccount, method: str):
        """Подготовить аккаунт для выбранного метода"""
        
        # Синхронизация fingerprints
        self.fingerprint_sync.ensure_consistency(account, method)
        
        # Подготовка сессий
        if method == 'browser':
            self.session_sync.prepare_for_browser(account)
        elif method == 'api':
            self.session_sync.prepare_for_api(account)
        
        # Проверка готовности прокси
        self._verify_proxy_readiness(account)
        
        # Проверка device consistency
        self._verify_device_consistency(account)
    
    def _execute_with_retries(self, account: InstagramAccount, method: str, videos: List) -> Dict:
        """Выполнение с умными retry попытками"""
        
        max_retries = 3
        retry_delays = [30, 120, 300]  # 30 сек, 2 мин, 5 мин
        
        for attempt in range(max_retries):
            try:
                # Выполнение метода
                if method == 'browser':
                    result = self._execute_browser_upload(account, videos)
                elif method == 'api':
                    result = self._execute_api_upload(account, videos)
                else:
                    raise ValueError(f"Unknown method: {method}")
                
                # Если успешно - возвращаем результат
                if result['success']:
                    return result
                
                # Анализ ошибки для retry
                if not self._should_retry(result['error'], attempt):
                    break
                
                # Подготовка к retry
                if attempt < max_retries - 1:
                    self._prepare_for_retry(account, method, result['error'])
                    time.sleep(retry_delays[attempt])
                
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                time.sleep(retry_delays[attempt])
        
        return {'success': False, 'error': 'Max retries exceeded'}
```

### 2. Универсальное управление сессиями

**Проблема**: Потеря сессий, несинхронизированные cookies, session drift
**Решение**: Bulletproof session management

```python
# Enhanced: uploader/bulletproof_session_manager.py
class BulletproofSessionManager:
    """Гарантированно надежное управление сессиями"""
    
    def __init__(self):
        self.session_backup = SessionBackupManager()
        self.session_validator = SessionValidator()
        self.session_restorer = SessionRestorer()
    
    def prepare_for_browser(self, account: InstagramAccount) -> bool:
        """Подготовить аккаунт для браузерной загрузки"""
        try:
            # 1. Проверить текущее состояние browser profile
            if not self._verify_dolphin_profile_health(account):
                self._repair_dolphin_profile(account)
            
            # 2. Синхронизировать API sessions в browser cookies
            if hasattr(account, 'device') and account.device.session_settings:
                self._sync_api_to_browser_cookies(account)
            
            # 3. Проверить валидность cookies
            if not self._validate_browser_cookies(account):
                return self._recover_browser_session(account)
            
            # 4. Backup текущего состояния
            self.session_backup.backup_browser_state(account)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to prepare browser session for {account.username}: {e}")
            return self._emergency_browser_recovery(account)
    
    def prepare_for_api(self, account: InstagramAccount) -> bool:
        """Подготовить аккаунт для API загрузки"""
        try:
            # 1. Проверить device settings
            device = self._ensure_device_exists(account)
            
            # 2. Синхронизировать browser cookies в API session
            if account.dolphin_profile_id:
                self._sync_browser_to_api_session(account)
            
            # 3. Проверить валидность API session
            if not self._validate_api_session(account):
                return self._recover_api_session(account)
            
            # 4. Backup текущего состояния
            self.session_backup.backup_api_state(account)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to prepare API session for {account.username}: {e}")
            return self._emergency_api_recovery(account)
    
    def _sync_api_to_browser_cookies(self, account: InstagramAccount):
        """Синхронизировать API session в browser cookies"""
        device = account.device
        if not device or not device.session_settings:
            return
        
        # Конвертировать instagrapi session в browser cookies
        browser_cookies = self._convert_api_session_to_cookies(device.session_settings)
        
        # Импортировать в Dolphin profile
        if account.dolphin_profile_id:
            self._import_cookies_to_dolphin(account.dolphin_profile_id, browser_cookies)
    
    def _sync_browser_to_api_session(self, account: InstagramAccount):
        """Синхронизировать browser cookies в API session"""
        if not account.dolphin_profile_id:
            return
        
        # Экспортировать cookies из Dolphin
        browser_cookies = self._export_cookies_from_dolphin(account.dolphin_profile_id)
        
        # Конвертировать в API session
        api_session = self._convert_cookies_to_api_session(browser_cookies)
        
        # Сохранить в device
        device = self._ensure_device_exists(account)
        device.session_settings = api_session
        device.save()
    
    def _emergency_recovery(self, account: InstagramAccount, method: str) -> bool:
        """Экстренное восстановление сессии"""
        try:
            # 1. Попробовать восстановить из backup
            if self.session_backup.has_recent_backup(account, method):
                return self.session_backup.restore_backup(account, method)
            
            # 2. Попробовать cross-sync (browser -> API или API -> browser)
            if method == 'browser' and self._has_valid_api_session(account):
                return self._force_sync_api_to_browser(account)
            elif method == 'api' and self._has_valid_browser_session(account):
                return self._force_sync_browser_to_api(account)
            
            # 3. Сбросить сессии и начать заново
            return self._reset_and_recreate_sessions(account)
            
        except Exception as e:
            logger.error(f"Emergency recovery failed for {account.username}: {e}")
            return False

class SessionValidator:
    """Валидация сессий перед использованием"""
    
    def validate_browser_session(self, account: InstagramAccount) -> bool:
        """Проверить валидность browser session"""
        if not account.dolphin_profile_id:
            return False
        
        try:
            # Экспорт cookies для проверки
            cookies = self._export_cookies_from_dolphin(account.dolphin_profile_id)
            
            # Проверить ключевые cookies
            required_cookies = ['sessionid', 'ds_user_id', 'csrftoken']
            for cookie_name in required_cookies:
                if not any(c['name'] == cookie_name for c in cookies):
                    return False
            
            # Проверить срок действия sessionid
            sessionid_cookie = next((c for c in cookies if c['name'] == 'sessionid'), None)
            if sessionid_cookie and self._is_session_expired(sessionid_cookie):
                return False
            
            return True
            
        except Exception:
            return False
    
    def validate_api_session(self, account: InstagramAccount) -> bool:
        """Проверить валидность API session"""
        device = getattr(account, 'device', None)
        if not device or not device.session_settings:
            return False
        
        session = device.session_settings
        
        # Проверить обязательные поля
        required_fields = ['sessionid', 'ds_user_id']
        for field in required_fields:
            if field not in session or not session[field]:
                return False
        
        # Проверить формат ds_user_id
        try:
            int(session['ds_user_id'])
        except (ValueError, TypeError):
            return False
        
        return True
```

### 3. Надежная обработка ошибок

**Проблема**: Неправильная обработка ошибок, отсутствие fallback механизмов
**Решение**: Universal Error Handler с автоматическим recovery

```python
# New: uploader/universal_error_handler.py
class UniversalErrorHandler:
    """Универсальная обработка ошибок для любого метода"""
    
    def __init__(self):
        self.session_manager = BulletproofSessionManager()
        self.fingerprint_manager = FingerprintSyncManager()
        self.recovery_strategies = {
            'CHALLENGE_REQUIRED': self._handle_challenge_required,
            'CAPTCHA_REQUIRED': self._handle_captcha_required,
            'RATE_LIMITED': self._handle_rate_limit,
            'SESSION_EXPIRED': self._handle_session_expired,
            'PROXY_ERROR': self._handle_proxy_error,
            'FINGERPRINT_MISMATCH': self._handle_fingerprint_mismatch,
            'NETWORK_ERROR': self._handle_network_error,
            'UPLOAD_FAILED': self._handle_upload_failed
        }
    
    def handle_error(self, account: InstagramAccount, error: Exception, 
                    method: str, context: Dict) -> Dict:
        """Обработать ошибку с автоматическим recovery"""
        
        # 1. Классифицировать ошибку
        error_type = self._classify_error(error)
        
        # 2. Логирование деталей ошибки
        self._log_error_details(account, error, error_type, method, context)
        
        # 3. Попытка автоматического восстановления
        if error_type in self.recovery_strategies:
            recovery_result = self.recovery_strategies[error_type](
                account, error, method, context
            )
            
            if recovery_result['success']:
                return {
                    'recovered': True,
                    'action': recovery_result['action'],
                    'retry_recommended': True,
                    'delay_before_retry': recovery_result.get('delay', 60)
                }
        
        # 4. Если авто-recovery не сработал - fallback стратегии
        fallback_result = self._try_fallback_strategies(account, error_type, method)
        
        return {
            'recovered': fallback_result['success'],
            'action': fallback_result.get('action', 'manual_intervention_required'),
            'retry_recommended': fallback_result.get('retry', False),
            'delay_before_retry': fallback_result.get('delay', 300)
        }
    
    def _classify_error(self, error: Exception) -> str:
        """Классифицировать тип ошибки"""
        error_str = str(error).lower()
        
        # Instagram API ошибки
        if 'challenge_required' in error_str:
            return 'CHALLENGE_REQUIRED'
        elif 'captcha' in error_str:
            return 'CAPTCHA_REQUIRED'
        elif 'rate limit' in error_str or 'too many requests' in error_str:
            return 'RATE_LIMITED'
        elif 'login_required' in error_str or 'session' in error_str:
            return 'SESSION_EXPIRED'
        
        # Proxy ошибки
        elif 'proxy' in error_str or 'connection refused' in error_str:
            return 'PROXY_ERROR'
        
        # Сетевые ошибки
        elif 'timeout' in error_str or 'network' in error_str:
            return 'NETWORK_ERROR'
        
        # Browser ошибки
        elif 'element not found' in error_str or 'selector' in error_str:
            return 'BROWSER_SELECTOR_ERROR'
        
        # Ошибки загрузки
        elif 'upload' in error_str or 'file' in error_str:
            return 'UPLOAD_FAILED'
        
        return 'UNKNOWN_ERROR'
    
    def _handle_challenge_required(self, account: InstagramAccount, error: Exception, 
                                  method: str, context: Dict) -> Dict:
        """Обработка challenge_required"""
        try:
            # 1. Попытка автоматического решения challenge
            if hasattr(account, 'email_username') and account.email_username:
                challenge_resolver = ChallengeResolver()
                if challenge_resolver.auto_resolve_email_challenge(account):
                    return {'success': True, 'action': 'challenge_auto_resolved', 'delay': 30}
            
            # 2. Отметить аккаунт как требующий вручную проверку
            account.status = 'HUMAN_VERIFICATION_REQUIRED'
            account.save()
            
            return {'success': False, 'action': 'manual_challenge_resolution_required'}
            
        except Exception as e:
            logger.error(f"Failed to handle challenge for {account.username}: {e}")
            return {'success': False, 'action': 'challenge_handler_failed'}
    
    def _handle_session_expired(self, account: InstagramAccount, error: Exception,
                               method: str, context: Dict) -> Dict:
        """Обработка сессий, которые стали невалидными"""
        try:
            # 1. Попытка восстановить сессию из backup
            if self.session_manager.session_backup.has_recent_backup(account, method):
                if self.session_manager.session_backup.restore_backup(account, method):
                    return {'success': True, 'action': 'session_restored_from_backup', 'delay': 10}
            
            # 2. Попытка cross-sync (синхронизация с альтернативным методом)
            if method == 'browser':
                if self.session_manager._has_valid_api_session(account):
                    if self.session_manager._force_sync_api_to_browser(account):
                        return {'success': True, 'action': 'session_synced_from_api', 'delay': 15}
            elif method == 'api':
                if self.session_manager._has_valid_browser_session(account):
                    if self.session_manager._force_sync_browser_to_api(account):
                        return {'success': True, 'action': 'session_synced_from_browser', 'delay': 15}
            
            # 3. Полный ресет сессии с перелогином
            if self._attempt_fresh_login(account, method):
                return {'success': True, 'action': 'fresh_login_completed', 'delay': 30}
            
            return {'success': False, 'action': 'session_recovery_failed'}
            
        except Exception as e:
            logger.error(f"Failed to handle session expiry for {account.username}: {e}")
            return {'success': False, 'action': 'session_handler_failed'}
    
    def _handle_proxy_error(self, account: InstagramAccount, error: Exception,
                           method: str, context: Dict) -> Dict:
        """Обработка ошибок прокси"""
        try:
            # 1. Проверить доступность текущего прокси
            proxy_checker = ProxyHealthChecker()
            if account.current_proxy:
                if proxy_checker.test_proxy(account.current_proxy):
                    # Прокси работает, проблема в другом
                    return {'success': True, 'action': 'proxy_confirmed_working', 'delay': 30}
            
            # 2. Попытка переключения на запасной прокси
            backup_proxy = self._find_backup_proxy(account)
            if backup_proxy:
                account.current_proxy = backup_proxy
                account.save()
                return {'success': True, 'action': 'switched_to_backup_proxy', 'delay': 45}
            
            # 3. Отметить прокси как нерабочий
            if account.current_proxy:
                account.current_proxy.status = 'inactive'
                account.current_proxy.save()
            
            return {'success': False, 'action': 'no_working_proxy_available'}
            
        except Exception as e:
            logger.error(f"Failed to handle proxy error for {account.username}: {e}")
            return {'success': False, 'action': 'proxy_handler_failed'}
```

## Преимущества гибридного подхода

### 1. **Максимальная надежность**
- Автоматическое переключение при проблемах
- Синхронизация сессий между методами
- Адаптация к паттернам блокировок Instagram

### 2. **Оптимальная производительность**  
- Выбор лучшего метода для каждого аккаунта
- Параллельное выполнение browser и API операций
- Минимизация времени выполнения задач

### 3. **Естественное поведение**
- Имитация реальных пользователей (кто-то через браузер, кто-то через приложение)
- Консистентные устройства и сессии
- Адаптивные паттерны использования

### 4. **Мониторинг и аналитика**
- Отслеживание успешности каждого метода
- Автоматическая оптимизация выбора
- Детальная статистика по методам

Этот подход позволит максимально эффективно использовать оба метода, автоматически адаптируясь к изменениям в системах защиты Instagram.