"""Views module: accounts (split from monolith)."""
from .common import *


def account_list(request):
    """List all Instagram accounts"""
    status_filter = request.GET.get('status', '')
    search_query = request.GET.get('q', '')
    
    # Sort by creation date descending (newest first) for consistency
    accounts = (
        InstagramAccount.objects.order_by('-created_at')
        .annotate(
            uploaded_success_total=Coalesce(Sum('bulk_uploads__uploaded_success_count'), Value(0)),
            uploaded_failed_total=Coalesce(Sum('bulk_uploads__uploaded_failed_count'), Value(0)),
        )
    )
    
    if status_filter:
        accounts = accounts.filter(status=status_filter)
    
    if search_query:
        accounts = accounts.filter(
            Q(username__icontains=search_query) |
            Q(email_username__icontains=search_query) |
            Q(notes__icontains=search_query)
        )
    
    context = {
        'accounts': accounts,
        'status_filter': status_filter,
        'search_query': search_query,
        'active_tab': 'accounts'
    }
    return render(request, 'uploader/account_list.html', context)

def account_detail(request, account_id):
    """View details of a specific account"""
    account = get_object_or_404(
        InstagramAccount.objects.annotate(
            uploaded_success_total=Coalesce(Sum('bulk_uploads__uploaded_success_count'), Value(0)),
            uploaded_failed_total=Coalesce(Sum('bulk_uploads__uploaded_failed_count'), Value(0)),
        ),
        id=account_id,
    )
    tasks = account.tasks.order_by('-created_at')

    # Build compact cookie summary for UI
    def _build_cookie_summary() -> dict:
        try:
            cookies_obj = getattr(account, 'cookies', None)
            cookies_list = list(getattr(cookies_obj, 'cookies_data', []) or [])
            total = len(cookies_list)
            # Aggregate by normalized domain
            from collections import Counter, defaultdict
            domain_counter: Counter = Counter()
            domain_to_names: dict = defaultdict(set)
            for c in cookies_list:
                try:
                    dom = str(c.get('domain') or '').strip()
                    if not dom:
                        continue
                    dom = dom.lstrip('.')
                    domain_counter[dom] += 1
                    nm = str(c.get('name') or '')
                    if nm:
                        domain_to_names[dom].add(nm)
                except Exception:
                    continue
            unique_domains = len(domain_counter)
            # Top domains compact list
            top_pairs = domain_counter.most_common(12)
            domains_compact = [
                {
                    'domain': d,
                    'count': n
                } for d, n in top_pairs
            ]
            # Instagram session detection
            insta_names_present = set()
            instagram_session_active = False
            important_names = {
                'sessionid', 'csrftoken', 'ds_user_id', 'Authorization',
                'IG-U-DS-USER-ID', 'IG-INTENDED-USER-ID', 'IG-U-RUR', 'rur',
                'mid', 'X-MID', 'X-IG-WWW-Claim'
            }
            for c in cookies_list:
                dom = str(c.get('domain') or '').lstrip('.')
                if dom.endswith('instagram.com'):
                    nm = str(c.get('name') or '')
                    if nm:
                        insta_names_present.add(nm)
                    if nm == 'sessionid':
                        val = (c.get('value') or '')
                        if isinstance(val, str) and len(val) >= 10:
                            instagram_session_active = True
            return {
                'total_cookies': total,
                'unique_domains': unique_domains,
                'domains_compact': domains_compact,
                'instagram_cookie_names': sorted(list(important_names.intersection(insta_names_present))),
                'instagram_session_active': instagram_session_active,
                'is_valid': bool(getattr(cookies_obj, 'is_valid', True)),
                'last_updated': getattr(cookies_obj, 'last_updated', None),
            }
        except Exception:
            return {
                'total_cookies': 0,
                'unique_domains': 0,
                'domains_compact': [],
                'instagram_cookie_names': [],
                'instagram_session_active': False,
                'is_valid': False,
                'last_updated': None,
            }

    # Build mobile session summary (instagrapi settings presence)
    def _build_session_summary() -> dict:
        try:
            device = getattr(account, 'device', None)
            settings = getattr(device, 'session_settings', None) or {}
            has_session = bool(settings)
            auth = settings.get('authorization_data', {}) if isinstance(settings, dict) else {}
            ds_user_id = auth.get('ds_user_id') or settings.get('ds_user_id')
            sessionid = auth.get('sessionid') or settings.get('sessionid')
            uuids = settings.get('uuids') if isinstance(settings, dict) else None
            last_login_ts = settings.get('last_login') if isinstance(settings, dict) else None
            return {
                'present': has_session,
                'ds_user_id': ds_user_id,
                'has_sessionid': bool(sessionid),
                'uuids': uuids or {},
                'last_login_ts': last_login_ts,
                'last_login_at': getattr(device, 'last_login_at', None),
            }
        except Exception:
            return {
                'present': False,
                'ds_user_id': None,
                'has_sessionid': False,
                'uuids': {},
                'last_login_ts': None,
                'last_login_at': None,
            }

    cookie_summary = _build_cookie_summary()
    session_summary = _build_session_summary()
    
    context = {
        'account': account,
        'tasks': tasks,
        'active_tab': 'accounts',
        'cookie_summary': cookie_summary,
        'session_summary': session_summary,
    }
    return render(request, 'uploader/account_detail.html', context)

def delete_account(request, account_id):
    """Delete an Instagram account"""
    account = get_object_or_404(InstagramAccount, id=account_id)
    
    if request.method == 'POST':
        # Store account info for message
        account_name = account.username
        dolphin_profile_id = account.dolphin_profile_id
        
        try:
            # Delete Dolphin profile if it exists
            if dolphin_profile_id:
                try:
                    logger.info(f"[DELETE ACCOUNT] Attempting to delete Dolphin profile {dolphin_profile_id} for account {account_name}")
                    api_key = os.environ.get("DOLPHIN_API_TOKEN", "")
                    if api_key:
                        # Get Dolphin API host from environment (critical for Docker Windows deployment)
                        dolphin_api_host = os.environ.get("DOLPHIN_API_HOST", "http://localhost:3001/v1.0")
                        if not dolphin_api_host.endswith("/v1.0"):
                            dolphin_api_host = dolphin_api_host.rstrip("/") + "/v1.0"
                        
                        dolphin = DolphinAnty(api_key=api_key, local_api_base=dolphin_api_host)
                        if dolphin.authenticate():
                            delete_result = dolphin.delete_profile(dolphin_profile_id)
                            if delete_result:
                                logger.info(f"[DELETE ACCOUNT] Successfully deleted Dolphin profile {dolphin_profile_id}")
                            else:
                                logger.warning(f"[DELETE ACCOUNT] Failed to delete Dolphin profile {dolphin_profile_id}, but continuing with account deletion")
                        else:
                            logger.error("[DELETE ACCOUNT] Failed to authenticate with Dolphin API")
                    else:
                        logger.warning("[DELETE ACCOUNT] No Dolphin API token found, skipping profile deletion")
                except Exception as e:
                    logger.error(f"[DELETE ACCOUNT] Error deleting Dolphin profile {dolphin_profile_id}: {str(e)}")
                    # Continue with account deletion even if Dolphin profile deletion fails
            
            # Release proxy if assigned
            if account.proxy:
                proxy = account.proxy
                proxy.assigned_account = None
                proxy.save(update_fields=['assigned_account'])
                logger.info(f"[DELETE ACCOUNT] Released proxy {proxy} from account {account_name}")
            
            # Delete the account
            account.delete()
            logger.info(f"[DELETE ACCOUNT] Successfully deleted account {account_name}")
            
            if dolphin_profile_id:
                messages.success(request, f'Account {account_name} and Dolphin profile {dolphin_profile_id} deleted successfully.')
            else:
                messages.success(request, f'Account {account_name} deleted successfully.')
        except Exception as e:
            logger.error(f"Error deleting account {account_id}: {str(e)}")
            messages.error(request, f'Error deleting account: {str(e)}')
        
        return redirect('account_list')
    
    # Confirm deletion
    context = {
        'account': account,
        'active_tab': 'accounts'
    }
    return render(request, 'uploader/delete_account.html', context)

def create_account(request):
    """Create a new Instagram account"""
    if request.method == 'POST':
        form = InstagramAccountForm(request.POST)
        if form.is_valid():
            # Save the account first to get an ID
            account = form.save()
            
            logger.info(f"[CREATE ACCOUNT] Account {account.username} created successfully. Attempting to assign proxy and create Dolphin profile.")
            
            assigned_proxy = None
            dolphin_available = False

            # Step 1: Assign an available proxy according to selection
            try:
                proxy_selection = request.POST.get('proxy_selection', 'locale_only')
                selected_locale = request.POST.get('profile_locale', 'ru_BY')
                if selected_locale != 'ru_BY':
                    selected_locale = 'ru_BY'

                base_qs = Proxy.objects.filter(is_active=True, assigned_account__isnull=True)
                if proxy_selection == 'locale_only':
                    # Prefer proxies matching BY
                    by_qs = base_qs.filter(
                        models.Q(country__iexact='BY') | models.Q(country__icontains='Belarus') | models.Q(city__icontains='Belarus')
                    )
                    candidate_qs = by_qs if by_qs.exists() else base_qs
                else:
                    candidate_qs = base_qs

                if candidate_qs.exists():
                    assigned_proxy = candidate_qs.order_by('?').first()
                    account.proxy = assigned_proxy
                    account.current_proxy = assigned_proxy
                    account.save(update_fields=['proxy', 'current_proxy'])
                    assigned_proxy.assigned_account = account
                    assigned_proxy.save(update_fields=['assigned_account'])
                    logger.info(f"[CREATE ACCOUNT] Assigned proxy {assigned_proxy} to account {account.username} (selection={proxy_selection})")
                else:
                    logger.warning(f"[CREATE ACCOUNT] No available proxies found for account {account.username}. Skipping proxy assignment.")
                    messages.warning(request, f'Account {account.username} created, but no available proxy could be assigned. Please assign manually.')

            except Exception as e:
                logger.error(f"[CREATE ACCOUNT] Error assigning proxy to account {account.username}: {str(e)}")
                messages.error(request, f'Account {account.username} created, but an error occurred while assigning a proxy: {str(e)}')
            
            # Step 2: Create Dolphin profile if proxy was assigned
            if assigned_proxy:
                try:
                    logger.info(f"[CREATE ACCOUNT] Initializing Dolphin Anty API client for account {account.username}")
                    api_key = os.environ.get("DOLPHIN_API_TOKEN", "")
                    if not api_key:
                        logger.error("[CREATE ACCOUNT] Dolphin API token not found in environment variables")
                        messages.warning(request, f'Account {account.username} created and proxy assigned, but Dolphin API token not configured.')
                        return redirect('account_detail', account_id=account.id)
                    
                    # Get Dolphin API host from environment (critical for Docker Windows deployment)
                    dolphin_api_host = os.environ.get("DOLPHIN_API_HOST", "http://localhost:3001/v1.0")
                    if not dolphin_api_host.endswith("/v1.0"):
                        dolphin_api_host = dolphin_api_host.rstrip("/") + "/v1.0"
                    
                    dolphin = DolphinAnty(api_key=api_key, local_api_base=dolphin_api_host)
                    dolphin_available = dolphin.authenticate()

                    if dolphin_available:
                        logger.info(f"[CREATE ACCOUNT] Authenticated with Dolphin Anty API.")
                        
                        # Create profile name with account username and random suffix
                        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
                        profile_name = f"instagram_{account.username}_{random_suffix}"
                        logger.info(f"[CREATE ACCOUNT] Creating Dolphin profile '{profile_name}' for account {account.username}")

                        proxy_data = assigned_proxy.to_dict()
                        logger.info(f"[CREATE ACCOUNT] Using proxy for profile: {proxy_data.get('host')}:{proxy_data.get('port')}")

                        # Using updated create_profile with locale (ru_BY only)
                        selected_locale = request.POST.get('profile_locale', 'ru_BY')
                        if selected_locale != 'ru_BY':
                            selected_locale = 'ru_BY'
                        response = dolphin.create_profile(
                            name=profile_name,
                            proxy=proxy_data,
                            tags=["instagram", "auto-created", "single-account-created"],
                            locale=selected_locale
                        )

                        # Extract profile ID from response
                        profile_id = None
                        if response and isinstance(response, dict):
                            profile_id = response.get("browserProfileId")
                            if not profile_id and isinstance(response.get("data"), dict):
                                profile_id = response["data"].get("id")
                                
                        if profile_id:
                            account.dolphin_profile_id = profile_id
                            account.save(update_fields=['dolphin_profile_id'])
                            # Persist full snapshot for 1:1 recreation later
                            try:
                                from uploader.models import DolphinProfileSnapshot
                                DolphinProfileSnapshot.objects.update_or_create(
                                    account=account,
                                    defaults={
                                        'profile_id': str(profile_id),
                                        'payload_json': response.get('_payload_used') or {},
                                        'response_json': response,
                                        'meta_json': response.get('_meta') or {}
                                    }
                                )
                            except Exception as snap_err:
                                logger.warning(f"[CREATE ACCOUNT] Could not save Dolphin snapshot: {snap_err}")
                            logger.info(f"[CREATE ACCOUNT] Created Dolphin profile {profile_id} for account {account.username}")
                            messages.success(request, f'Account {account.username} created and Dolphin profile {profile_id} created successfully!')
                        else:
                            error_message = "Unknown error" if not isinstance(response, dict) else response.get("error", "Unknown error during Dolphin profile creation")
                            logger.error(f"[CREATE ACCOUNT] Failed to create Dolphin profile for account {account.username}: {error_message}")
                            messages.warning(request, f'Account {account.username} created and proxy assigned, but failed to create Dolphin profile: {error_message}')
                    else:
                         logger.error(f"[CREATE ACCOUNT] Failed to authenticate with Dolphin Anty API for account {account.username}")
                         messages.warning(request, f'Account {account.username} created and proxy assigned, but could not connect to Dolphin Anty API to create profile. Check API token.')

                except Exception as e:
                    logger.error(f"[CREATE ACCOUNT] Error creating Dolphin profile for account {account.username}: {str(e)}")
                    messages.warning(request, f'Account {account.username} created and proxy assigned, but an error occurred while creating Dolphin profile: {str(e)}')

            messages.success(request, f'Account {account.username} created successfully!')
            return redirect('account_detail', account_id=account.id)
    else:
        form = InstagramAccountForm()
    
    context = {
        'form': form,
        'active_tab': 'accounts'
    }
    return render(request, 'uploader/create_account.html', context)

def import_accounts(request):
    """
    Import Instagram accounts from a text file, create Dolphin profiles,
    assign one proxy per account, and link everything together.
    """
    if request.method == 'POST' and request.FILES.get('accounts_file'):
        accounts_file = request.FILES['accounts_file']
        
        # Helpers for cookie classification and extraction
        def _detect_mobile_cookies(cookies_str: str, device_info: str | None) -> bool:
            try:
                s = (cookies_str or '').lower()
                if 'authorization=' in s and 'bearer igt:' in s:
                    return True
                if 'x-mid=' in s and 'ig-u-ds-user-id=' in s:
                    return True
                if device_info and device_info.strip().lower().startswith(('android-', 'ios-', 'iphone-', 'mobile-')):
                    return True
            except Exception:
                pass
            return False
        
        def _extract_cookie_value(cookie_list: list, name: str) -> str | None:
            for c in cookie_list or []:
                try:
                    if str(c.get('name') or '').lower() == name.lower():
                        return c.get('value')
                except Exception:
                    continue
            return None

        # UI params
        proxy_selection = request.POST.get('proxy_selection', 'locale_only')
        proxy_locale_strict = request.POST.get('proxy_locale_strict') == '1'
        # Locale: support ru_BY and en_IN
        selected_locale = request.POST.get('profile_locale', 'ru_BY')
        if selected_locale not in ['ru_BY', 'en_IN']:
            selected_locale = 'ru_BY'
        # Derive target country from locale
        locale_country = 'BY' if selected_locale == 'ru_BY' else 'IN'
        
        # Counters for status messages
        created_count = 0
        updated_count = 0
        error_count = 0
        dolphin_created_count = 0
        dolphin_error_count = 0
        
        # Initialize Dolphin Anty API client
        try:
            logger.info("[STEP 1/5] Initializing Dolphin Anty API client")
            api_key = os.environ.get("DOLPHIN_API_TOKEN", "")
            if not api_key:
                logger.error("[ERROR] Dolphin API token not found in environment variables")
                messages.error(request, "Dolphin API token not configured. Please set DOLPHIN_API_TOKEN environment variable.")
                return redirect('import_accounts')
            
            # Get Dolphin API host from environment (critical for Docker Windows deployment)
            dolphin_api_host = os.environ.get("DOLPHIN_API_HOST", "http://localhost:3001/v1.0")
            if not dolphin_api_host.endswith("/v1.0"):
                dolphin_api_host = dolphin_api_host.rstrip("/") + "/v1.0"
            
            dolphin = DolphinAnty(api_key=api_key, local_api_base=dolphin_api_host)
            dolphin_available = dolphin.authenticate()
            if dolphin_available:
                logger.info("[SUCCESS] Successfully authenticated with Dolphin Anty API")
            else:
                logger.error("[FAIL] Failed to authenticate with Dolphin Anty API")
                messages.error(request, "Failed to authenticate with Dolphin Anty API. Check your API token.")
        except Exception as e:
            logger.error(f"[ERROR] Error initializing Dolphin Anty API: {str(e)}")
            dolphin_available = False
            messages.error(request, f"Dolphin Anty API error: {str(e)}")
        
        # Read file content
        logger.info("[STEP 2/5] Reading accounts file content")
        content = accounts_file.read().decode('utf-8')
        lines = content.splitlines()
        total_lines = len(lines)
        logger.info(f"[INFO] Found {total_lines} lines in the accounts file")
        
        # Determine how many proxies are actually needed: only for new accounts or existing accounts without proxy
        # Parse usernames from valid lines (username:password...)
        parsed_usernames = []
        for raw in lines:
            s = (raw or '').strip()
            if not s:
                continue
            parts = s.split(':')
            if len(parts) >= 2 and parts[0]:
                parsed_usernames.append(parts[0])
        unique_usernames = list({u for u in parsed_usernames})
 
        existing_map = {
            acc.username: acc
            for acc in InstagramAccount.objects.filter(username__in=unique_usernames)
        }
        new_usernames = [u for u in unique_usernames if u not in existing_map]
        existing_without_proxy = [
            u for u in unique_usernames
            if u in existing_map and not (getattr(existing_map[u], 'proxy', None) or getattr(existing_map[u], 'current_proxy', None))
        ]
        proxies_needed = len(new_usernames) + len(existing_without_proxy)
 
        available_proxies = Proxy.objects.filter(is_active=True, assigned_account__isnull=True)
        if proxy_selection == 'locale_only':
            by_text = 'Belarus' if locale_country == 'BY' else 'India'
            country_filtered = available_proxies.filter(
                Q(country__iexact=locale_country) | Q(country__icontains=by_text) | Q(city__icontains=by_text)
            )
            if proxy_locale_strict:
                available_proxies = country_filtered
            else:
                if country_filtered.exists() and country_filtered.count() >= proxies_needed:
                    available_proxies = country_filtered
        available_proxy_count = available_proxies.count()
        logger.info(f"[INFO] Proxy requirement: needed={proxies_needed} (new={len(new_usernames)}, existing_without_proxy={len(existing_without_proxy)}), available={available_proxy_count}")
         
        if available_proxy_count < proxies_needed:
            if proxy_selection == 'locale_only' and proxy_locale_strict:
                messages.error(request, f'Not enough {locale_country} proxies to satisfy strict requirement (needed {proxies_needed}, available {available_proxy_count}).')
                return redirect('import_accounts')
            error_message = (
                f"Not enough available proxies. Need {proxies_needed} "
                f"(new: {len(new_usernames)}, missing: {len(existing_without_proxy)}) "
                f"but only have {available_proxy_count}. Please add more proxies before importing accounts."
            )
            logger.error(f"[ERROR] {error_message}")
            messages.error(request, error_message)
            return redirect('import_accounts')
         
        # Process accounts
        logger.info("[STEP 3/5] Processing accounts")
        for line_num, line in enumerate(lines, 1):
            if not line.strip():
                logger.debug(f"[SKIP] Line {line_num}: Empty line, skipping")
                continue  # Skip empty lines
                 
            try:
                # Parse line
                logger.info(f"[ACCOUNT {line_num}/{total_lines}] Processing line {line_num}")
                raw_line = line.strip()
                # Support extended format: username:password||device_info|cookies
                cookies_raw = None
                device_info_raw = None
                if '||' in raw_line:
                    auth_part, rest = raw_line.split('||', 1)
                    parts = auth_part.split(':')
                    # extract cookies part after first '|'
                    try:
                        rest_parts = rest.split('|')
                        if len(rest_parts) >= 1:
                            device_info_raw = (rest_parts[0] or '').strip() or None
                        if len(rest_parts) > 1:
                            cookies_raw = '|'.join(rest_parts[1:]).strip() or None
                    except Exception:
                        cookies_raw = None
                else:
                    parts = raw_line.split(':')
                 
                if len(parts) < 2:
                    logger.warning(f"[ERROR] Line {line_num}: Invalid format. Expected at least username:password")
                    messages.warning(request, f'Line {line_num}: Invalid format. Expected at least username:password')
                    error_count += 1
                    continue
                 
                # Common fields
                username = parts[0]
                password = parts[1]
                logger.info(f"[INFO] Processing account: {username}")
                 
                # Default values
                tfa_secret = None
                email_username = None
                email_password = None
                parsed_cookies_list = []
                is_mobile_cookies = False
                 
                # Determine account type based on number of parts
                if len(parts) == 2:
                    # Basic format: username:password (no 2FA, no email verification)
                    logger.info(f"[INFO] Account {username} identified as basic account (no 2FA, no email)")
                 
                elif len(parts) == 3:
                    # This could be either a 2FA account or an email verification account
                    # Check if the third part looks like a 2FA secret (usually uppercase letters and numbers)
                    # Remove spaces first to properly detect 2FA keys that may contain spaces
                    import re
                    potential_2fa = re.sub(r'\s+', '', parts[2])
                    if potential_2fa.isupper() and any(c.isdigit() for c in potential_2fa):
                        tfa_secret = potential_2fa  # Already has spaces removed
                        logger.info(f"[INFO] Account {username} identified as 2FA account")
                    else:
                        # Assume it's an email without password
                        email_username = parts[2]
                        logger.info(f"[INFO] Account {username} identified with email (no password)")
                 
                elif len(parts) == 4:
                    # This is an email verification account (username:password:email:email_password)
                    email_username = parts[2]
                    email_password = parts[3]
                    logger.info(f"[INFO] Account {username} identified as email verification account")
                 
                elif len(parts) == 5:
                    # This is a TFA account (username:password:email:email_password:tfa_secret)
                    email_username = parts[2]
                    email_password = parts[3]
                    import re
                    tfa_secret = re.sub(r'\s+', '', parts[4])  # Remove all whitespace from 2FA key
                    logger.info(f"[INFO] Account {username} identified as TFA account with email")
                 
                elif len(parts) > 5:
                    # Extended format with additional fields
                    email_username = parts[2]
                    email_password = parts[3]
                    import re
                    tfa_secret = re.sub(r'\s+', '', parts[4])  # Remove all whitespace from 2FA key
                    logger.info(f"[INFO] Account {username} identified as TFA account with extended format")
 
                # If cookies string provided, convert raw string of 'name=value; name2=value...' to list of dicts
                if cookies_raw:
                    try:
                        logger.info(f"[COOKIES] Raw cookies string detected for {username} (length={len(cookies_raw)})")
                        cookie_pairs = [c.strip() for c in cookies_raw.split(';') if c.strip()]
                        for pair in cookie_pairs:
                            if '=' not in pair:
                                continue
                            name, value = pair.split('=', 1)
                            # Default cookie skeleton for Instagram domain
                            parsed_cookies_list.append({
                                'domain': '.instagram.com',
                                'name': name.strip(),
                                'value': value.strip(),
                                'path': '/',
                                'httpOnly': False,
                                'secure': True,
                                'session': True,
                                'sameSite': 'no_restriction',
                            })
                        # Classify cookies type
                        is_mobile_cookies = _detect_mobile_cookies(cookies_raw, device_info_raw)
                    except Exception as ce:
                        logger.warning(f"[COOKIES] Failed to parse raw cookies for {username}: {ce}")
                        parsed_cookies_list = []

                # Decide proxy assignment strategy
                logger.info(f"[STEP 4/5] Deciding proxy for account: {username}")
                assigned_proxy = None
                try:
                    existing_acc = existing_map.get(username)
                    if existing_acc and (existing_acc.current_proxy or existing_acc.proxy):
                        # Reuse existing proxy assignment, do not grab a new proxy
                        assigned_proxy = existing_acc.current_proxy or existing_acc.proxy
                        logger.info(f"[INFO] Reusing existing proxy for {username}: {assigned_proxy}")
                    else:
                        # Get an unused active proxy from filtered set
                        available_proxies = Proxy.objects.filter(is_active=True, assigned_account__isnull=True)
                        if proxy_selection == 'locale_only':
                            country_text = 'Belarus' if locale_country == 'BY' else 'India'
                            country_proxies = available_proxies.filter(
                                Q(country__iexact=locale_country) | Q(country__icontains=country_text) | Q(city__icontains=country_text)
                            )
                            available_proxies = country_proxies if country_proxies.exists() else available_proxies
                        if not available_proxies.exists():
                            error_message = f"No available proxies left for account {username}. Please add more proxies."
                            logger.error(f"[ERROR] {error_message}")
                            messages.error(request, error_message)
                            return redirect('import_accounts')
                        assigned_proxy = available_proxies.order_by('?').first()
                        logger.info(f"[SUCCESS] Assigned new proxy {assigned_proxy} to account {username}")
                except Exception as e:
                    error_message = f"Error assigning proxy to account {username}: {str(e)}"
                    logger.error(f"[ERROR] {error_message}")
                    messages.error(request, error_message)
                    error_count += 1
                    continue
                 
                # Check if account already exists
                logger.info(f"[STEP 5/5] Creating or updating account: {username}")
                # Build defaults without overwriting existing proxy unless we actually selected one
                defaults = {
                    'password': password,
                    'tfa_secret': tfa_secret,
                    'email_username': email_username,
                    'email_password': email_password,
                    'status': 'ACTIVE',
                }
                if assigned_proxy and (not existing_map.get(username) or not (existing_map[username].proxy or existing_map[username].current_proxy)):
                    defaults['proxy'] = assigned_proxy
 
                account, created = InstagramAccount.objects.update_or_create(
                    username=username,
                    defaults=defaults
                )
                 
                if created:
                    logger.info(f"[SUCCESS] Created new account: {username}")
                    created_count += 1
                else:
                    logger.info(f"[SUCCESS] Updated existing account: {username}")
                    updated_count += 1
                 
                # If cookies were parsed, save/update appropriate storage (mobile vs desktop)
                try:
                    if parsed_cookies_list:
                        if is_mobile_cookies:
                            from uploader.models import InstagramDevice
                            # Build session payload for later instagrapi usage
                            ds_user_id = _extract_cookie_value(parsed_cookies_list, 'ds_user_id')
                            sessionid = _extract_cookie_value(parsed_cookies_list, 'sessionid')
                            # Optional headers/cookies that map into settings
                            mid_val = _extract_cookie_value(parsed_cookies_list, 'mid') or _extract_cookie_value(parsed_cookies_list, 'X-MID')
                            ig_u_rur_val = _extract_cookie_value(parsed_cookies_list, 'IG-U-RUR') or _extract_cookie_value(parsed_cookies_list, 'rur')
                            ig_www_claim_val = _extract_cookie_value(parsed_cookies_list, 'X-IG-WWW-Claim')
                            # Derive UUIDs from device_info if present: android-<id>;phone_id;uuid;client_session_id
                            uuids_dict = {}
                            try:
                                if device_info_raw:
                                    di_parts = [p for p in device_info_raw.split(';') if p]
                                    if di_parts:
                                        # android_device_id is first token (may start with android-)
                                        uuids_dict['android_device_id'] = di_parts[0]
                                    if len(di_parts) >= 2:
                                        uuids_dict['phone_id'] = di_parts[1]
                                    if len(di_parts) >= 3:
                                        uuids_dict['uuid'] = di_parts[2]
                                    if len(di_parts) >= 4:
                                        uuids_dict['client_session_id'] = di_parts[3]
                            except Exception:
                                uuids_dict = {}
                            # Minimal instagrapi settings dict
                            session_settings = {
                                'uuids': uuids_dict,
                                'mid': mid_val,
                                'ig_u_rur': ig_u_rur_val,
                                'ig_www_claim': ig_www_claim_val,
                                'authorization_data': {
                                    'ds_user_id': ds_user_id,
                                    'sessionid': sessionid,
                                },
                                'cookies': {},
                                # Optional timestamp for reference
                                'last_login': int(time.time()),
                            }
                            dev_obj, _ = InstagramDevice.objects.get_or_create(account=account)
                            # Preserve existing device_settings; store session in session_settings in instagrapi format
                            dev_obj.session_settings = session_settings
                            dev_obj.save(update_fields=['session_settings', 'updated_at'])
                            logger.info(f"[COOKIES] Saved mobile session ({len(parsed_cookies_list)} cookies) for {username} into InstagramDevice.session_settings")
                        else:
                            from uploader.models import InstagramCookies
                            InstagramCookies.objects.update_or_create(
                                account=account,
                                defaults={
                                    'cookies_data': parsed_cookies_list,
                                    'is_valid': True,
                                }
                            )
                            logger.info(f"[COOKIES] Saved desktop cookies ({len(parsed_cookies_list)}) for {username}")
                except Exception as e:
                    logger.warning(f"[COOKIES] Failed to save cookies for {username}: {e}")

                # Update proxy assignment only if we assigned a new proxy from pool
                if assigned_proxy and (not existing_map.get(username) or not (existing_map[username].proxy or existing_map[username].current_proxy)):
                    assigned_proxy.assigned_account = account
                    assigned_proxy.save()
                    logger.info(f"[INFO] Updated proxy assignment for account {username}")
                 
                # Create Dolphin profile if API is available
                if dolphin_available and (created or not account.dolphin_profile_id):
                    try:
                        # Create profile name with account username and random suffix
                        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
                        profile_name = f"instagram_{username}_{random_suffix}"
                        logger.info(f"[DOLPHIN] Creating Dolphin profile for account {username}")
                         
                        # Prepare proxy data if available
                        proxy_data = None
                        if assigned_proxy:
                            proxy_data = assigned_proxy.to_dict()
                            logger.info(f"[DOLPHIN] Using proxy for profile: {assigned_proxy.host}:{assigned_proxy.port}")
                        else:
                            logger.warning(f"[DOLPHIN] No proxy available for profile creation")
                            # This should never happen as we check for proxy availability earlier
                            continue
                         
                        # Add a significant delay between creating each profile to prevent rate limiting
                        # This is especially important since we're generating unique fingerprints
                        if dolphin_created_count > 0:
                            delay_time = random.uniform(4.0, 7.0)  # Random delay between 4-7 seconds
                            logger.info(f"[DOLPHIN] Adding a {delay_time:.1f}-second delay before creating the next profile")
                            time.sleep(delay_time)
                         
                        # Create Dolphin profile with proper fingerprint generation
                        response = dolphin.create_profile(
                            name=profile_name,
                            proxy=proxy_data,
                            tags=["instagram", "auto-created"],
                            locale=selected_locale
                        )
                         
                        # Extract profile ID from response
                        profile_id = None
                        if response and isinstance(response, dict):
                            profile_id = response.get("browserProfileId")
                            if not profile_id and isinstance(response.get("data"), dict):
                                profile_id = response["data"].get("id")
                             
                        if profile_id:
                            account.dolphin_profile_id = profile_id
                            account.save(update_fields=['dolphin_profile_id'])
                            dolphin_created_count += 1
                            logger.info(f"[SUCCESS] Created Dolphin profile {profile_id} for account {username}")

                            # Import cookies into the newly created profile if we have DESKTOP cookies
                            try:
                                if parsed_cookies_list and not is_mobile_cookies:
                                    # Prefer Local API import; if not available (free plan), fall back to Remote PATCH
                                    imp = dolphin.import_cookies_local(profile_id, parsed_cookies_list)
                                    if not (isinstance(imp, dict) and imp.get('success')):
                                        logger.info(f"[DOLPHIN] Local import failed or unsupported, trying Remote PATCH for {username}")
                                        dolphin.update_cookies(profile_id, parsed_cookies_list)
                                    logger.info(f"[COOKIES] Imported cookies into Dolphin profile {profile_id} for {username}")
                                elif parsed_cookies_list and is_mobile_cookies:
                                    logger.info(f"[COOKIES] Skipped importing mobile cookies into Dolphin (desktop) profile for {username}")
                            except Exception as ice:
                                logger.warning(f"[COOKIES] Failed to import cookies into profile {profile_id} for {username}: {ice}")
                        else:
                            error_message = response.get("error", "Unknown error")
                            detailed_error = ""
                             
                            # Extract detailed validation errors
                            if isinstance(error_message, dict):
                                if "fields" in error_message:
                                    validation_errors = []
                                    for field_error in error_message.get("fields", []):
                                        field = field_error.get("field", "unknown")
                                        error = field_error.get("error", "unknown error")
                                        values = field_error.get("values", [])
                                        validation_errors.append(f"{field}: {error} (expected: {', '.join(map(str, values))})")
                                     
                                    detailed_error = " | ".join(validation_errors)
                                else:
                                    detailed_error = str(error_message)
                            else:
                                detailed_error = str(error_message)
                             
                            full_error = f"Failed to create Dolphin profile for account {username}: {detailed_error}"
                            logger.error(f"[ERROR] {full_error}")
                            messages.error(request, full_error)
                            dolphin_error_count += 1
                    except Exception as e:
                        dolphin_error_count += 1
                        error_message = f"Error creating Dolphin profile for account {username}: {str(e)}"
                        logger.error(f"[ERROR] {error_message}")
                        messages.error(request, error_message)
                 
            except Exception as e:
                error_message = f"Error importing account at line {line_num}: {str(e)}"
                logger.error(f"[ERROR] {error_message}")
                messages.error(request, error_message)
                error_count += 1
         
        # Show summary message
        logger.info(f"[SUMMARY] Import completed - Created: {created_count}, Updated: {updated_count}, Errors: {error_count}")
        if dolphin_available:
            logger.info(f"[SUMMARY] Dolphin profiles - Created: {dolphin_created_count}, Errors: {dolphin_error_count}")
             
        if created_count > 0 or updated_count > 0:
            success_msg = f'Import completed! Created: {created_count}, Updated: {updated_count}, Errors: {error_count}'
            if dolphin_available:
                success_msg += f', Dolphin profiles created: {dolphin_created_count}, Dolphin errors: {dolphin_error_count}'
            messages.success(request, success_msg)
        else:
            messages.warning(request, f'No accounts were imported. Errors: {error_count}')
         
        return redirect('account_list')
     
    context = {
        'active_tab': 'import_accounts'
    }
    return render(request, 'uploader/import_accounts.html', context)

def warm_account(request, account_id):
    """Warm up an Instagram account to get fresh cookies"""
    account = get_object_or_404(InstagramAccount, id=account_id)
    
    # In a real implementation, this would start a Playwright process to log in
    # and browse Instagram to warm up the account
    
    # For now, just mark it as warmed
    account.last_warmed = timezone.now()
    account.save(update_fields=['last_warmed'])
    
    messages.success(request, f'Account {account.username} has been warmed up.')
    return redirect('account_detail', account_id=account.id)

def edit_account(request, account_id):
    """Edit an existing Instagram account"""
    account = get_object_or_404(InstagramAccount, id=account_id)
    
    if request.method == 'POST':
        form = InstagramAccountForm(request.POST, instance=account)
        if form.is_valid():
            # Preserve Dolphin profile ID explicitly to avoid clearing
            preserved_profile_id = account.dolphin_profile_id
            account = form.save()
            if preserved_profile_id and account.dolphin_profile_id != preserved_profile_id:
                account.dolphin_profile_id = preserved_profile_id
                account.save(update_fields=['dolphin_profile_id'])
            
            # Synchronize proxy and current_proxy fields
            if account.proxy != account.current_proxy:
                account.current_proxy = account.proxy
                account.save(update_fields=['current_proxy'])
                logger.info(f"[EDIT ACCOUNT] Synchronized proxy fields for account {account.username}")
            
            messages.success(request, f'Account {account.username} updated successfully!')
            return redirect('account_detail', account_id=account.id)
    else:
        form = InstagramAccountForm(instance=account)
    
    context = {
        'form': form,
        'account': account,
        'active_tab': 'accounts'
    }
    return render(request, 'uploader/edit_account.html', context)

def change_account_proxy(request, account_id):
    """Change the proxy for an Instagram account and update Dolphin profile if exists"""
    account = get_object_or_404(InstagramAccount, id=account_id)
    
    if request.method == 'POST':
        proxy_id = request.POST.get('proxy_id')
        
        try:
            if proxy_id:
                # Assign the selected proxy
                new_proxy = get_object_or_404(Proxy, id=proxy_id)
                
                # If this proxy is assigned to another account, unassign it
                if new_proxy.assigned_account and new_proxy.assigned_account != account:
                    old_account = new_proxy.assigned_account
                    old_account.proxy = None
                    old_account.current_proxy = None
                    old_account.save(update_fields=['proxy', 'current_proxy'])
                
                # Update the current account's proxy - update both proxy and current_proxy fields
                old_proxy = account.proxy
                account.proxy = new_proxy
                account.current_proxy = new_proxy  # Ensure both fields are updated
                account.save(update_fields=['proxy', 'current_proxy'])
                
                # Update the proxy's assigned account
                new_proxy.assigned_account = account
                new_proxy.save(update_fields=['assigned_account'])
                
                # If the old proxy exists, clear its assignment
                if old_proxy:
                    old_proxy.assigned_account = None
                    old_proxy.save(update_fields=['assigned_account'])
                
                # Update Dolphin profile proxy if profile exists
                if account.dolphin_profile_id:
                    try:
                        logger.info(f"[CHANGE PROXY] Updating Dolphin profile {account.dolphin_profile_id} proxy for account {account.username}")
                        
                        # Initialize Dolphin API
                        api_key = os.environ.get("DOLPHIN_API_TOKEN", "")
                        if not api_key:
                            logger.warning("[CHANGE PROXY] Dolphin API token not found in environment variables")
                            messages.warning(request, f'Proxy changed for account {account.username}, but could not update Dolphin profile: API token not configured.')
                        else:
                            # Get Dolphin API host from environment (critical for Docker Windows deployment)
                            dolphin_api_host = os.environ.get("DOLPHIN_API_HOST", "http://localhost:3001/v1.0")
                            if not dolphin_api_host.endswith("/v1.0"):
                                dolphin_api_host = dolphin_api_host.rstrip("/") + "/v1.0"
                            
                            dolphin = DolphinAnty(api_key=api_key, local_api_base=dolphin_api_host)
                            
                            # Authenticate with Dolphin
                            if dolphin.authenticate():
                                # Prepare proxy data for Dolphin
                                proxy_data = new_proxy.to_dict()
                                
                                # Update proxy in Dolphin profile
                                result = dolphin.update_profile_proxy(account.dolphin_profile_id, proxy_data)
                                
                                if result.get("success"):
                                    logger.info(f"[CHANGE PROXY] Successfully updated Dolphin profile {account.dolphin_profile_id} proxy")
                                    region_msg = ""
                                    if old_proxy and old_proxy.country and new_proxy.country and old_proxy.country != new_proxy.country:
                                        region_msg = f" (Region changed from {old_proxy.country} to {new_proxy.country})"
                                    messages.success(request, f'Proxy changed for account {account.username} and Dolphin profile {account.dolphin_profile_id} updated successfully!{region_msg}')
                                else:
                                    error_msg = result.get("error", "Unknown error")
                                    logger.error(f"[CHANGE PROXY] Failed to update Dolphin profile proxy: {error_msg}")
                                    messages.warning(request, f'Proxy changed for account {account.username}, but failed to update Dolphin profile: {error_msg}')
                            else:
                                logger.error("[CHANGE PROXY] Failed to authenticate with Dolphin Anty API")
                                messages.warning(request, f'Proxy changed for account {account.username}, but could not authenticate with Dolphin Anty API.')
                    
                    except Exception as e:
                        logger.error(f"[CHANGE PROXY] Error updating Dolphin profile proxy: {str(e)}")
                        messages.warning(request, f'Proxy changed for account {account.username}, but an error occurred while updating Dolphin profile: {str(e)}')
                else:
                    region_msg = ""
                    if old_proxy and old_proxy.country and new_proxy.country and old_proxy.country != new_proxy.country:
                        region_msg = f" (Region changed from {old_proxy.country} to {new_proxy.country})"
                    messages.success(request, f'Proxy changed for account {account.username}{region_msg}')
            else:
                # Remove proxy assignment - clear both proxy and current_proxy fields
                old_proxy = account.proxy
                account.proxy = None
                account.current_proxy = None
                account.save(update_fields=['proxy', 'current_proxy'])
                
                if old_proxy:
                    old_proxy.assigned_account = None
                    old_proxy.save(update_fields=['assigned_account'])
                
                # Note: We don't remove proxy from Dolphin profile when removing proxy assignment
                # as this would break the profile. User should manually handle this case.
                if account.dolphin_profile_id:
                    messages.warning(request, f'Proxy removed from account {account.username}. Note: Dolphin profile {account.dolphin_profile_id} still has the old proxy configured.')
                else:
                    messages.success(request, f'Proxy removed from account {account.username}')
                
        except Exception as e:
            logger.error(f"[CHANGE PROXY] Error changing proxy for account {account.username}: {str(e)}")
            messages.error(request, f'Error changing proxy: {str(e)}')
        
        return redirect('account_detail', account_id=account.id)
    
    # Get available proxies - prefer same region if account has a proxy with region info
    if account.proxy and account.proxy.country:
        # First, get proxies from the same region
        same_region_proxies = Proxy.objects.filter(
            Q(assigned_account__isnull=True) | Q(assigned_account=account),
            is_active=True,
            country=account.proxy.country
        ).order_by('host', 'port')
        
        # Then, get all other active proxies
        other_proxies = Proxy.objects.filter(
            Q(assigned_account__isnull=True) | Q(assigned_account=account),
            is_active=True
        ).exclude(country=account.proxy.country).order_by('host', 'port')
        
        # Combine: same region first, then others
        available_proxies = list(same_region_proxies) + list(other_proxies)
    else:
        # No region preference, get all available proxies
        available_proxies = Proxy.objects.filter(
            Q(assigned_account__isnull=True) | Q(assigned_account=account),
            is_active=True
        ).order_by('host', 'port')
    
    context = {
        'account': account,
        'available_proxies': available_proxies,
        'active_tab': 'accounts'
    }
    
    return render(request, 'uploader/change_account_proxy.html', context)
