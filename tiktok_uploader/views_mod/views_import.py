"""
TikTok Accounts Bulk Import View
"""
import os
import logging
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q

from tiktok_uploader.models import TikTokAccount, TikTokProxy
from cabinet.models import Client
from tiktok_uploader.bot_integration.dolphin.dolphin import Dolphin

logger = logging.getLogger('tiktok_uploader')


@login_required
def import_accounts(request):
    """
    Массовый импорт TikTok аккаунтов из текстового файла.
    Поддерживаемый формат: username:password:email:email_password
    
    Опции:
    - Автоматическое создание Dolphin профилей
    - Автоматическое назначение прокси (с фильтрацией по локали)
    - Привязка к клиенту
    """
    
    if request.method == 'POST' and request.FILES.get('accounts_file'):
        accounts_file = request.FILES['accounts_file']
        
        # Получаем параметры из формы
        proxy_selection = request.POST.get('proxy_selection', 'locale_only')
        proxy_locale_strict = request.POST.get('proxy_locale_strict') == '1'
        profile_mode = request.POST.get('profile_mode', 'create_profiles')
        selected_locale = request.POST.get('profile_locale', 'en_US')
        
        # Опциональный выбор клиента
        selected_client = None
        try:
            client_id_str = request.POST.get('client_id')
            if client_id_str:
                selected_client = Client.objects.filter(id=int(client_id_str)).first()
        except Exception:
            selected_client = None
        
        # Поддерживаемые локали для TikTok
        allowed_locales = ['en_US', 'ru_RU', 'es_ES', 'pt_BR', 'de_DE', 'fr_FR']
        if selected_locale not in allowed_locales:
            selected_locale = 'en_US'
        
        # Определяем страну по локали для фильтрации прокси
        locale_country_map = {
            'en_US': ('US', 'United States'),
            'ru_RU': ('RU', 'Russia'),
            'es_ES': ('ES', 'Spain'),
            'pt_BR': ('BR', 'Brazil'),
            'de_DE': ('DE', 'Germany'),
            'fr_FR': ('FR', 'France'),
        }
        locale_country, country_text = locale_country_map.get(
            selected_locale, ('US', 'United States')
        )
        
        # Счетчики для статистики
        created_count = 0
        updated_count = 0
        error_count = 0
        dolphin_created_count = 0
        dolphin_error_count = 0
        
        # Инициализация Dolphin API (если нужно создавать профили)
        dolphin = None
        dolphin_available = False
        
        if profile_mode == 'create_profiles':
            try:
                logger.info("[STEP 1/5] Initializing Dolphin Anty API client")
                api_key = os.environ.get("DOLPHIN_API_TOKEN", "")
                if not api_key:
                    logger.error("[ERROR] Dolphin API token not found")
                    messages.error(request, "Dolphin API token not configured. Set DOLPHIN_API_TOKEN.")
                    return redirect('tiktok_uploader:import_accounts')
                
                dolphin = Dolphin()
                dolphin_available = True
                logger.info("[SUCCESS] Dolphin Anty API initialized")
            except Exception as e:
                logger.error(f"[ERROR] Dolphin API init failed: {str(e)}")
                dolphin_available = False
                messages.error(request, f"Dolphin API error: {str(e)}")
        
        # Читаем файл
        logger.info("[STEP 2/5] Reading accounts file")
        content = accounts_file.read().decode('utf-8')
        lines = content.splitlines()
        total_lines = len(lines)
        logger.info(f"[INFO] Found {total_lines} lines in file")
        
        # Парсим usernames для проверки существующих аккаунтов
        parsed_usernames = []
        for raw in lines:
            s = (raw or '').strip()
            if not s or s.startswith('#'):
                continue
            parts = s.split(':')
            if len(parts) >= 2 and parts[0]:
                parsed_usernames.append(parts[0].strip())
        
        unique_usernames = list(set(parsed_usernames))
        
        # Проверяем существующие аккаунты
        existing_map = {
            acc.username: acc
            for acc in TikTokAccount.objects.filter(username__in=unique_usernames)
        }
        
        new_usernames = [u for u in unique_usernames if u not in existing_map]
        existing_without_proxy = [
            u for u in unique_usernames
            if u in existing_map and not existing_map[u].proxy
        ]
        
        proxies_needed = len(new_usernames) + len(existing_without_proxy)
        
        # Получаем доступные прокси
        logger.info("[STEP 3/5] Loading available proxies")
        available_proxies = TikTokProxy.objects.filter(
            is_active=True,
            accounts__isnull=True  # Не назначенные
        )
        
        # Фильтрация по локали
        if proxy_selection == 'locale_only':
            country_filtered = available_proxies.filter(
                Q(country__iexact=locale_country) | 
                Q(country__icontains=country_text) | 
                Q(city__icontains=country_text)
            )
            
            if proxy_locale_strict:
                available_proxies = country_filtered
            else:
                if country_filtered.exists() and country_filtered.count() >= proxies_needed:
                    available_proxies = country_filtered
        
        available_proxy_count = available_proxies.count()
        logger.info(
            f"[INFO] Proxies: needed={proxies_needed}, available={available_proxy_count}"
        )
        
        # Проверка достаточности прокси
        if proxies_needed > available_proxy_count:
            messages.warning(
                request,
                f"Not enough proxies! Need {proxies_needed}, available {available_proxy_count}. "
                f"Some accounts will be created without proxies."
            )
        
        # Преобразуем в список для индексирования
        proxy_list = list(available_proxies)
        proxy_index = 0
        
        # Обработка каждой строки
        logger.info("[STEP 4/5] Processing accounts")
        for line_num, raw in enumerate(lines, 1):
            line = (raw or '').strip()
            
            # Пропускаем пустые и комментарии
            if not line or line.startswith('#'):
                continue
            
            try:
                # Парсинг формата: username:password[:email[:email_password]]
                parts = line.split(':')
                
                if len(parts) < 2:
                    logger.warning(f"[SKIP] Line {line_num}: Invalid format (need at least username:password)")
                    error_count += 1
                    continue
                
                username = parts[0].strip()
                password = parts[1].strip()
                email = parts[2].strip() if len(parts) > 2 else None
                email_password = parts[3].strip() if len(parts) > 3 else None
                
                if not username or not password:
                    logger.warning(f"[SKIP] Line {line_num}: Empty username or password")
                    error_count += 1
                    continue
                
                # Проверяем существует ли аккаунт
                if username in existing_map:
                    account = existing_map[username]
                    logger.info(f"[UPDATE] Account {username} already exists, updating...")
                    
                    # Обновляем данные
                    account.password = password
                    if email:
                        account.email = email
                    if email_password:
                        account.email_password = email_password
                    account.locale = selected_locale
                    if selected_client:
                        account.client = selected_client
                    
                    # Назначаем прокси если еще нет
                    if not account.proxy and proxy_index < len(proxy_list):
                        proxy = proxy_list[proxy_index]
                        account.proxy = proxy
                        account.current_proxy = proxy
                        proxy_index += 1
                        logger.info(f"[PROXY] Assigned proxy {proxy.host}:{proxy.port} to {username}")
                    
                    account.save()
                    updated_count += 1
                    
                else:
                    # Создаем новый аккаунт
                    logger.info(f"[CREATE] Creating new account: {username}")
                    
                    account = TikTokAccount(
                        username=username,
                        password=password,
                        email=email or '',
                        email_password=email_password or '',
                        locale=selected_locale,
                        client=selected_client
                    )
                    
                    # Назначаем прокси
                    if proxy_index < len(proxy_list):
                        proxy = proxy_list[proxy_index]
                        account.proxy = proxy
                        account.current_proxy = proxy
                        proxy_index += 1
                        logger.info(f"[PROXY] Assigned proxy {proxy.host}:{proxy.port} to {username}")
                    
                    account.save()
                    created_count += 1
                
                # Создание Dolphin профиля (если включено)
                if profile_mode == 'create_profiles' and dolphin_available and not account.dolphin_profile_id:
                    try:
                        logger.info(f"[DOLPHIN] Creating profile for {username}")
                        
                        # Проверяем существует ли уже профиль с таким именем
                        existing_profile = dolphin.get_profile_by_name(username)
                        
                        if existing_profile:
                            logger.info(f"[DOLPHIN] Profile already exists for {username}, linking...")
                            account.dolphin_profile_id = existing_profile['id']
                            account.save()
                            dolphin_created_count += 1
                        else:
                            # Создаем новый профиль
                            # Подготавливаем прокси конфиг
                            proxy_config = None
                            if account.proxy:
                                proxy_config = {
                                    'type': account.proxy.proxy_type.lower(),
                                    'host': account.proxy.host,
                                    'port': int(account.proxy.port),
                                }
                                
                                if account.proxy.username:
                                    proxy_config['user'] = account.proxy.username
                                if account.proxy.password:
                                    proxy_config['pass'] = account.proxy.password
                            
                            if not proxy_config:
                                logger.error(f"[DOLPHIN SKIP] No proxy configured for {username}, skipping profile creation")
                                dolphin_error_count += 1
                                continue
                            
                            # Создаем профиль через Dolphin API с правильными аргументами
                            result = dolphin.create_profile(
                                name=username,
                                proxy=proxy_config,
                                tags=['tiktok', 'import'],
                                locale=selected_locale
                            )
                            
                            # Проверяем результат
                            if result.get("success", True) and (result.get('browserProfileId') or result.get('data', {}).get('id')):
                                profile_id = result.get('browserProfileId') or result.get('data', {}).get('id')
                                account.dolphin_profile_id = str(profile_id)
                                account.save()
                                dolphin_created_count += 1
                                logger.info(f"[DOLPHIN SUCCESS] Profile created: ID={profile_id}")
                            else:
                                error_msg = result.get('error', 'Unknown error')
                                logger.error(f"[DOLPHIN FAIL] Failed to create profile for {username}: {error_msg}")
                                dolphin_error_count += 1
                                
                    except Exception as e:
                        logger.error(f"[DOLPHIN ERROR] {username}: {str(e)}")
                        dolphin_error_count += 1
                
            except Exception as e:
                logger.error(f"[ERROR] Line {line_num}: {str(e)}")
                error_count += 1
                continue
        
        # Финальная статистика
        logger.info("[STEP 5/5] Import completed")
        logger.info(f"[STATS] Created: {created_count}, Updated: {updated_count}, Errors: {error_count}")
        logger.info(f"[STATS] Dolphin: Created {dolphin_created_count}, Errors {dolphin_error_count}")
        
        # Сообщения для пользователя
        if created_count > 0:
            messages.success(request, f"✅ Successfully created {created_count} new account(s).")
        if updated_count > 0:
            messages.success(request, f"🔄 Updated {updated_count} existing account(s).")
        if dolphin_created_count > 0:
            messages.success(request, f"🐬 Created {dolphin_created_count} Dolphin profile(s).")
        if error_count > 0:
            messages.warning(request, f"⚠️ {error_count} line(s) skipped due to errors.")
        if dolphin_error_count > 0:
            messages.warning(request, f"⚠️ {dolphin_error_count} Dolphin profile(s) failed to create.")
        
        return redirect('tiktok_uploader:account_list')
    
    # GET request - показываем форму
    clients = Client.objects.all().order_by('name')
    
    # Статистика прокси по странам
    proxy_stats = {}
    for proxy in TikTokProxy.objects.filter(is_active=True, accounts__isnull=True):
        country = proxy.country or 'Unknown'
        proxy_stats[country] = proxy_stats.get(country, 0) + 1
    
    context = {
        'clients': clients,
        'proxy_stats': proxy_stats,
    }
    
    return render(request, 'tiktok_uploader/accounts/import_accounts.html', context)

