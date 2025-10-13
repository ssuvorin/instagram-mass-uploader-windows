"""Views module: accounts (split from monolith)."""
from .common import *
from django.db import models
from django.db.models import Q
from cabinet.models import Client as CabinetClient


def account_list(request):
    """List all Instagram accounts"""
    status_filter = request.GET.get('status', '')
    search_query = request.GET.get('q', '')
    tag_filter = request.GET.get('tag', '')
    client_id = request.GET.get('client_id')
    client_name = request.GET.get('client_name')
    agency_id = request.GET.get('agency_id')
    
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

    # Tag filtering
    if tag_filter:
        if tag_filter == 'no_tag':
            accounts = accounts.filter(tag__isnull=True)
        else:
            accounts = accounts.filter(tag_id=tag_filter)

    # Optional filtering by client/agency for cabinet deep links
    try:
        if client_id:
            accounts = accounts.filter(client_id=int(client_id))
    except Exception:
        pass
    if client_name:
        accounts = accounts.filter(client__name__iexact=client_name)
    try:
        if agency_id:
            accounts = accounts.filter(client__agency_id=int(agency_id))
    except Exception:
        pass

    # Role-based visibility restrictions
    if not request.user.is_superuser:
        try:
            from cabinet.models import Client as CabinetClient, Agency as CabinetAgency
            my_client = CabinetClient.objects.filter(user=request.user).first()
            if my_client:
                accounts = accounts.filter(client_id=my_client.id)
            else:
                my_agency = CabinetAgency.objects.filter(owner=request.user).first()
                if my_agency:
                    accounts = accounts.filter(client__agency_id=my_agency.id)
                else:
                    accounts = accounts.none()
        except Exception:
            accounts = accounts.none()
    
    # Get tags for filter dropdown
    from uploader.models import Tag
    tags = Tag.objects.all().order_by('name')
    
    context = {
        'accounts': accounts,
        'status_filter': status_filter,
        'search_query': search_query,
        'tag_filter': tag_filter,
        'tags': tags,
        'client_id': client_id or '',
        'client_name': client_name or '',
        'agency_id': agency_id or '',
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
                if selected_locale not in ['ru_BY', 'en_IN', 'es_CL', 'es_MX', 'pt_BR', 'el_GR', 'de_DE']:
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
            
            # Persist selected locale on account regardless of Dolphin availability
            try:
                _sel = request.POST.get('profile_locale', 'ru_BY')
                if _sel not in ['ru_BY', 'en_IN', 'es_CL', 'es_MX', 'pt_BR']:
                    _sel = 'ru_BY'
                if getattr(account, 'locale', None) != _sel:
                    account.locale = _sel
                    account.save(update_fields=['locale'])
            except Exception:
                pass

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

                        # Using updated create_profile with multiple locales
                        selected_locale = request.POST.get('profile_locale', 'ru_BY')
                        if selected_locale not in ['ru_BY', 'en_IN', 'es_CL', 'es_MX', 'pt_BR', 'el_GR', 'de_DE']:
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
                            account.locale = selected_locale
                            account.save(update_fields=['dolphin_profile_id', 'locale'])
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
        # Optional client selection
        selected_client = None
        try:
            client_id_str = request.POST.get('client_id')
            if client_id_str:
                selected_client = CabinetClient.objects.filter(id=int(client_id_str)).first()
        except Exception:
            selected_client = None
        
        # Optional tags selection
        selected_tag = None
        try:
            tag_id = request.POST.get('tags')
            if tag_id:
                from uploader.models import Tag
                selected_tag = Tag.objects.filter(id=int(tag_id)).first()
        except Exception:
            selected_tag = None
        
        # Helpers for cookie classification and extraction
        def _detect_mobile_cookies(cookies_str: str, device_info: str | None) -> bool:
            """
            Heuristic classification:
            - Count mobile markers (Authorization=Bearer IGT, X-MID, IG-U-*, device_info android/ios)
            - Count web markers (sessionid, csrftoken, ds_user_id)
            - Treat as mobile only if mobile markers clearly dominate (diff >= 2)
            """
            try:
                raw = cookies_str or ''
                s_lower = raw.lower()
                parts = [p.strip() for p in raw.split(';') if p.strip()]
                names = set()
                for p in parts:
                    try:
                        if '=' in p:
                            nm = p.split('=', 1)[0].strip().lower()
                            if nm:
                                names.add(nm)
                    except Exception:
                        continue

                mobile_score = 0
                web_score = 0

                if 'authorization=' in s_lower and 'bearer igt:' in s_lower:
                    mobile_score += 1
                if 'x-mid' in names:
                    mobile_score += 1
                if 'ig-u-ds-user-id' in names:
                    mobile_score += 1
                if 'ig-u-rur' in names or 'ig-intended-user-id' in names:
                    mobile_score += 1
                if device_info and device_info.strip().lower().startswith(('android-', 'ios-', 'iphone-', 'mobile-')):
                    mobile_score += 1

                if 'sessionid' in names:
                    web_score += 2
                if 'csrftoken' in names:
                    web_score += 1
                if 'ds_user_id' in names:
                    web_score += 1

                if mobile_score <= 0:
                    return False
                return (mobile_score - web_score) >= 2
            except Exception:
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
        profile_mode = request.POST.get('profile_mode', 'create_profiles')
        # Locale: support ru_BY, en_IN, es_CL, es_MX, pt_BR, el_GR, de_DE
        selected_locale = request.POST.get('profile_locale', 'ru_BY')
        allowed_locales = ['ru_BY', 'en_IN', 'es_CL', 'es_MX', 'pt_BR', 'el_GR', 'de_DE']
        if selected_locale not in allowed_locales:
            selected_locale = 'ru_BY'
        # Derive target country from locale
        if selected_locale == 'ru_BY':
            locale_country = 'BY'
            country_text = 'Belarus'
        elif selected_locale == 'en_IN':
            locale_country = 'IN'
            country_text = 'India'
        elif selected_locale == 'es_CL':
            locale_country = 'CL'
            country_text = 'Chile'
        elif selected_locale == 'es_MX':
            locale_country = 'MX'
            country_text = 'Mexico'
        elif selected_locale == 'pt_BR':
            locale_country = 'BR'
            country_text = 'Brazil'
        elif selected_locale == 'el_GR':
            locale_country = 'GR'
            country_text = 'Greece'
        elif selected_locale == 'de_DE':
            locale_country = 'DE'
            country_text = 'Germany'
        else:
            locale_country = 'BY'
            country_text = 'Belarus'
        
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
            country_filtered = available_proxies.filter(
                Q(country__iexact=locale_country) | Q(country__icontains=country_text) | Q(city__icontains=country_text)
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
                web_format_hint = False
                explicit_no_device_info_hint = False
                if '||' in raw_line:
                    auth_part, rest = raw_line.split('||', 1)
                    parts = auth_part.split(':')
                    # Robustly detect cookies segment from the rightmost 'segment containing ='
                    try:
                        segments = rest.split('|')
                        cookies_idx = None
                        for idx in range(len(segments) - 1, -1, -1):
                            seg = (segments[idx] or '').strip()
                            if not seg:
                                continue
                            if '=' in seg or 'sessionid=' in seg or 'ds_user_id=' in seg:
                                cookies_idx = idx
                                break
                        if cookies_idx is not None:
                            cookies_raw = '|'.join(segments[cookies_idx:]).strip() or None
                            device_seg = [x for x in segments[:cookies_idx] if (x or '').strip()]
                            device_info_raw = ('|'.join(device_seg).strip() or None) if device_seg else None
                        else:
                            # Fallback: assume first segment is device, no cookies
                            device_info_raw = (segments[0] or '').strip() or None if segments else None
                    except Exception:
                        cookies_raw = None
                elif '|' in raw_line:
                    # Support web cookies format: username:password|cookie1=value1; cookie2=value2; ...
                    left, right = raw_line.split('|', 1)
                    parts = left.split(':')
                    try:
                        cookies_raw = (right or '').strip() or None
                        web_format_hint = True
                    except Exception:
                        cookies_raw = None
                else:
                    # Default split by ':'; but if the line ends with a JSON cookies array
                    # username:password:email:email_pass:[json_cookies_array]
                    # we must not split inside JSON (which may contain ':').
                    if ('[' in raw_line and raw_line.rstrip().endswith(']')):
                        parts = raw_line.split(':', 4)
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
                    # Either TFA or JSON cookies array in 5th segment
                    email_username = parts[2]
                    email_password = parts[3]
                    tail = (parts[4] or '').strip()
                    if tail.startswith('[') and tail.endswith(']'):
                        # Parse JSON cookies array
                        try:
                            import json
                            cookies_json = json.loads(tail)
                            if isinstance(cookies_json, list):
                                parsed_cookies_list = []
                                for c in cookies_json:
                                    try:
                                        # Normalize common cookie dict formats
                                        name = (c.get('name') if isinstance(c, dict) else None) or ''
                                        value = (c.get('value') if isinstance(c, dict) else None) or ''
                                        domain = (c.get('domain') if isinstance(c, dict) else None) or '.instagram.com'
                                        path = (c.get('path') if isinstance(c, dict) else None) or '/'
                                        http_only = bool((c.get('httpOnly') if isinstance(c, dict) else c.get('http_only')) if isinstance(c, dict) else False)
                                        secure = bool(c.get('secure')) if isinstance(c, dict) else True
                                        if name:
                                            parsed_cookies_list.append({
                                                'domain': domain,
                                                'name': name,
                                                'value': value,
                                                'path': path,
                                                'httpOnly': http_only,
                                                'secure': secure,
                                                'session': True,
                                                'sameSite': 'no_restriction',
                                            })
                                    except Exception:
                                        # Skip malformed cookie objects
                                        continue
                                # Treat JSON cookies array as WEB cookies
                                is_mobile_cookies = False
                                logger.info(f"[INFO] Account {username} provided JSON cookies array with {len(parsed_cookies_list)} items")
                            else:
                                logger.warning(f"[COOKIES] JSON in 5th segment is not a list for {username}")
                        except Exception as je:
                            logger.warning(f"[COOKIES] Failed to parse JSON cookies array for {username}: {je}")
                    else:
                        # TFA secret in 5th segment
                        import re
                        tfa_secret = re.sub(r'\s+', '', tail)  # Remove all whitespace from 2FA key
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
                        classification = _detect_mobile_cookies(cookies_raw, device_info_raw)
                        is_mobile_cookies = False if (web_format_hint or explicit_no_device_info_hint) else classification
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
                if selected_client is not None:
                    defaults['client'] = selected_client
 
                account, created = InstagramAccount.objects.update_or_create(
                    username=username,
                    defaults=defaults
                )
                # Persist locale selection on account
                try:
                    if account.locale != selected_locale:
                        account.locale = selected_locale
                        account.save(update_fields=['locale'])
                except Exception:
                    pass
                
                # Assign tag to account
                if selected_tag:
                    account.tag = selected_tag
                    account.save(update_fields=['tag'])
                 
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
                            
                            # CRITICAL: Add device_settings if we have device info
                            if device_info_raw:
                                try:
                                    device_settings = {}
                                    # Extract device info from device_info_raw
                                    di_parts = [p for p in device_info_raw.split(';') if p]
                                    if di_parts:
                                        device_settings['android_device_id'] = di_parts[0]
                                    if len(di_parts) >= 2:
                                        device_settings['phone_id'] = di_parts[1]
                                    if len(di_parts) >= 3:
                                        device_settings['uuid'] = di_parts[2]
                                    if len(di_parts) >= 4:
                                        device_settings['client_session_id'] = di_parts[3]
                                    
                                    if device_settings:
                                        session_settings['device_settings'] = device_settings
                                except Exception:
                                    pass
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
                 
                # Create Dolphin profile if API is available and profile_mode requires it
                if profile_mode == 'create_profiles' and dolphin_available and (created or not account.dolphin_profile_id):
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
                            account.locale = selected_locale
                            account.save(update_fields=['dolphin_profile_id', 'locale'])
                            dolphin_created_count += 1
                            logger.info(f"[SUCCESS] Created Dolphin profile {profile_id} for account {username}")
                            
                            # Save Dolphin profile snapshot for 1:1 recreation
                            try:
                                from uploader.services.dolphin_snapshot import save_dolphin_snapshot
                                save_dolphin_snapshot(account, profile_id, response)
                            except Exception as snap_err:
                                logger.warning(f"[IMPORT] Could not save Dolphin snapshot for {username}: {snap_err}")

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
     
    clients = CabinetClient.objects.select_related('agency').all()
    from uploader.models import Tag
    tags = Tag.objects.all().order_by('name')
    context = {
        'active_tab': 'import_accounts',
        'clients': clients,
        'tags': tags,
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

def import_accounts_ua_cookies(request):
	"""
	Import accounts in the UA+Cookies format on a separate page.
	Supported lines:
	- username:password|UA|cookies
	- username:password|UA|device_info|cookies
	Device info (if present) is expected as: android-<device>;phone_id;uuid;client_session_id
	All provided cookies are treated as WEB cookies and imported into Dolphin profile.
	"""
	if request.method == 'POST' and request.FILES.get('accounts_file'):
		accounts_file = request.FILES['accounts_file']

		# Helpers for extraction
		def _extract_cookie_value(cookie_list: list, name: str) -> str | None:
			for c in cookie_list or []:
				try:
					if str(c.get('name') or '').lower() == name.lower():
						return c.get('value')
				except Exception:
					continue
			return None

		# UI params (reuse existing semantics)
		proxy_selection = request.POST.get('proxy_selection', 'locale_only')
		proxy_locale_strict = request.POST.get('proxy_locale_strict') == '1'
		profile_mode = request.POST.get('profile_mode', 'create_profiles')
		selected_locale = request.POST.get('profile_locale', 'ru_BY')
		allowed_locales = ['ru_BY', 'en_IN', 'es_CL', 'es_MX', 'pt_BR', 'el_GR', 'de_DE']
		if selected_locale not in allowed_locales:
			selected_locale = 'ru_BY'
		locale_country = (
			'BY' if selected_locale == 'ru_BY' else (
				'IN' if selected_locale == 'en_IN' else (
					'CL' if selected_locale == 'es_CL' else (
						'MX' if selected_locale == 'es_MX' else (
							'BR' if selected_locale == 'pt_BR' else (
								'GR' if selected_locale == 'el_GR' else (
									'DE' if selected_locale == 'de_DE' else 'BY'
								)
							)
						)
					)
				)
			)
		)

		created_count = 0
		updated_count = 0
		error_count = 0
		dolphin_created_count = 0
		dolphin_error_count = 0

		# Initialize Dolphin Anty API client
		try:
			logger.info("[UA+COOKIES][STEP 1/5] Initializing Dolphin Anty API client")
			api_key = os.environ.get("DOLPHIN_API_TOKEN", "")
			if not api_key:
				logger.error("[UA+COOKIES][ERROR] Dolphin API token not found in environment variables")
				messages.error(request, "Dolphin API token not configured. Please set DOLPHIN_API_TOKEN environment variable.")
				return redirect('import_ua_cookies')
			# Get Dolphin API host
			dolphin_api_host = os.environ.get("DOLPHIN_API_HOST", "http://localhost:3001/v1.0")
			if not dolphin_api_host.endswith("/v1.0"):
				dolphin_api_host = dolphin_api_host.rstrip("/") + "/v1.0"
			dolphin = DolphinAnty(api_key=api_key, local_api_base=dolphin_api_host)
			dolphin_available = dolphin.authenticate()
			if dolphin_available:
				logger.info("[UA+COOKIES][SUCCESS] Authenticated with Dolphin Anty API")
			else:
				logger.error("[UA+COOKIES][FAIL] Failed to authenticate with Dolphin Anty API")
				messages.error(request, "Failed to authenticate with Dolphin Anty API. Check your API token.")
		except Exception as e:
			logger.error(f"[UA+COOKIES][ERROR] Error initializing Dolphin Anty API: {str(e)}")
			dolphin_available = False
			messages.error(request, f"Dolphin Anty API error: {str(e)}")
			return redirect('import_ua_cookies')

		# Read file content
		logger.info("[UA+COOKIES][STEP 2/5] Reading accounts file content")
		content = accounts_file.read().decode('utf-8')
		lines = content.splitlines()
		total_lines = len(lines)
		logger.info(f"[UA+COOKIES][INFO] Found {total_lines} lines in the accounts file")

		# Determine proxies needed for new accounts or existing accounts without proxy
		parsed_usernames = []
		for raw in lines:
			s = (raw or '').strip()
			if not s:
				continue
			left = s.split('|', 1)[0]
			parts = left.split(':')
			if len(parts) >= 2 and parts[0]:
				parsed_usernames.append(parts[0])
		unique_usernames = list({u for u in parsed_usernames})
		existing_map = {acc.username: acc for acc in InstagramAccount.objects.filter(username__in=unique_usernames)}
		new_usernames = [u for u in unique_usernames if u not in existing_map]
		existing_without_proxy = [u for u in unique_usernames if u in existing_map and not (getattr(existing_map[u], 'proxy', None) or getattr(existing_map[u], 'current_proxy', None))]
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
		logger.info(f"[UA+COOKIES][INFO] Proxy requirement: needed={proxies_needed}, available={available_proxy_count}")
		if available_proxy_count < proxies_needed:
			if proxy_selection == 'locale_only' and proxy_locale_strict:
				messages.error(request, f'Not enough {locale_country} proxies to satisfy strict requirement (needed {proxies_needed}, available {available_proxy_count}).')
				return redirect('import_ua_cookies')
			error_message = (
				f"Not enough available proxies. Need {proxies_needed} (new: {len(new_usernames)}, missing: {len(existing_without_proxy)}) "
				f"but only have {available_proxy_count}. Please add more proxies before importing accounts."
			)
			logger.error(f"[UA+COOKIES][ERROR] {error_message}")
			messages.error(request, error_message)
			return redirect('import_ua_cookies')

		# Process accounts
		logger.info("[UA+COOKIES][STEP 3/5] Processing accounts")
		for line_num, raw in enumerate(lines, 1):
			if not (raw or '').strip():
				logger.debug(f"[UA+COOKIES][SKIP] Line {line_num}: Empty line, skipping")
				continue
			try:
				logger.info(f"[UA+COOKIES][ACCOUNT {line_num}/{total_lines}] Processing line {line_num}")
				s = raw.strip()
				segments = s.split('|')
				left = (segments[0] or '').strip() if len(segments) >= 1 else ''
				ua_string = (segments[1] or '').strip() if len(segments) >= 2 else None

				# Determine cookies segment: search from the end for first segment containing '=' (name=value pattern)
				cookies_idx = None
				for idx in range(len(segments) - 1, -1, -1):
					seg = (segments[idx] or '').strip()
					if not seg:
						continue
					if '=' in seg or 'sessionid=' in seg or 'ds_user_id=' in seg:
						cookies_idx = idx
						break
				cookies_raw = None
				if cookies_idx is not None:
					cookies_raw = '|'.join(segments[cookies_idx:]).strip() or None

				# Device info: if there are segments between UA and cookies, join them; otherwise None
				device_info_raw = None
				if ua_string is not None and cookies_idx is not None and (cookies_idx - 2) >= 1:
					mid_parts = segments[2:cookies_idx]
					joined = '|'.join([p for p in mid_parts if p is not None])
					device_info_raw = joined.strip() or None

				parts = left.split(':', 1)
				if len(parts) < 2:
					logger.warning(f"[UA+COOKIES][ERROR] Line {line_num}: Invalid format. Expected username:password|UA|cookies")
					messages.warning(request, f'Line {line_num}: Invalid format. Expected username:password|UA|cookies')
					error_count += 1
					continue
				username = parts[0].strip()
				password = parts[1].strip()

				# Parse cookies into list of dicts for Dolphin
				parsed_cookies_list = []
				if cookies_raw:
					try:
						cookie_pairs = [c.strip() for c in cookies_raw.split(';') if c.strip()]
						for pair in cookie_pairs:
							if '=' not in pair:
								continue
							name, value = pair.split('=', 1)
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
					except Exception as ce:
						logger.warning(f"[UA+COOKIES][COOKIES] Failed to parse cookies for {username}: {ce}")
						parsed_cookies_list = []

				# Assign proxy (reuse existing if present)
				assigned_proxy = None
				try:
					existing_acc = existing_map.get(username)
					if existing_acc and (existing_acc.current_proxy or existing_acc.proxy):
						assigned_proxy = existing_acc.current_proxy or existing_acc.proxy
						logger.info(f"[UA+COOKIES][INFO] Reusing existing proxy for {username}: {assigned_proxy}")
					else:
						avail = Proxy.objects.filter(is_active=True, assigned_account__isnull=True)
						if proxy_selection == 'locale_only':
							country_text = 'Belarus' if locale_country == 'BY' else 'India'
							country_proxies = avail.filter(
								Q(country__iexact=locale_country) | Q(country__icontains=country_text) | Q(city__icontains=country_text)
							)
							avail = country_proxies if country_proxies.exists() else avail
						if not avail.exists():
							error_message = f"No available proxies left for account {username}. Please add more proxies."
							logger.error(f"[UA+COOKIES][ERROR] {error_message}")
							messages.error(request, error_message)
							return redirect('import_ua_cookies')
						assigned_proxy = avail.order_by('?').first()
						logger.info(f"[UA+COOKIES][SUCCESS] Assigned new proxy {assigned_proxy} to account {username}")
				except Exception as e:
					error_message = f"Error assigning proxy to account {username}: {str(e)}"
					logger.error(f"[UA+COOKIES][ERROR] {error_message}")
					messages.error(request, error_message)
					error_count += 1
					continue

				# Create or update account
				defaults = {
					'password': password,
					'notes': (f"UA: {ua_string[:200]}" if ua_string else "")
				}
				if assigned_proxy and (not existing_map.get(username) or not (existing_map[username].proxy or existing_map[username].current_proxy)):
					defaults['proxy'] = assigned_proxy
				# Optional client assignment
				try:
					client_id_str = request.POST.get('client_id')
					if client_id_str:
						sel_client = CabinetClient.objects.filter(id=int(client_id_str)).first()
						if sel_client:
							defaults['client'] = sel_client
				except Exception:
					pass
				account, created = InstagramAccount.objects.update_or_create(
					username=username,
					defaults=defaults
				)
				if created:
					logger.info(f"[UA+COOKIES][SUCCESS] Created new account: {username}")
					created_count += 1
				else:
					logger.info(f"[UA+COOKIES][SUCCESS] Updated existing account: {username}")
					updated_count += 1

				# Persist UA/device session snapshot for reference
				try:
					from uploader.models import InstagramDevice
					dev_obj, _ = InstagramDevice.objects.get_or_create(account=account)
					# Derive UUIDs from device_info if present
					uuids_dict = {}
					try:
						if device_info_raw:
							di_parts = [p for p in device_info_raw.split(';') if p]
							if di_parts:
								uuids_dict['android_device_id'] = di_parts[0]
							if len(di_parts) >= 2:
								uuids_dict['phone_id'] = di_parts[1]
							if len(di_parts) >= 3:
								uuids_dict['uuid'] = di_parts[2]
							if len(di_parts) >= 4:
								uuids_dict['client_session_id'] = di_parts[3]
					except Exception:
						uuids_dict = {}
					# Extract some key values from cookies if available
					ds_user_id = _extract_cookie_value(parsed_cookies_list, 'ds_user_id')
					sessionid = _extract_cookie_value(parsed_cookies_list, 'sessionid')
					mid_val = _extract_cookie_value(parsed_cookies_list, 'mid') or _extract_cookie_value(parsed_cookies_list, 'X-MID')
					ig_u_rur_val = _extract_cookie_value(parsed_cookies_list, 'IG-U-RUR') or _extract_cookie_value(parsed_cookies_list, 'rur')
					ig_www_claim_val = _extract_cookie_value(parsed_cookies_list, 'X-IG-WWW-Claim')
					settings_snapshot = {
						'uuids': uuids_dict,
						'mobile_user_agent': ua_string,
						'mid': mid_val,
						'ig_u_rur': ig_u_rur_val,
						'ig_www_claim': ig_www_claim_val,
						'authorization_data': {
							'ds_user_id': ds_user_id,
							'sessionid': sessionid,
						},
						'last_login': int(time.time()),
					}
					
					# CRITICAL: Also save device_settings if we have UA to derive device info
					if ua_string:
						try:
							# Extract device settings from UA for ensure_persistent_device
							device_settings = {}
							import re as _re
							
							# Extract app_version from UA
							m = _re.search(r'Instagram\s+([0-9.]+)', ua_string, flags=_re.I)
							if m:
								device_settings['app_version'] = m.group(1)
							
							# Extract resolution and DPI from UA
							m_res = _re.search(r'(\d{3,5})x(\d{3,5})', ua_string)
							if m_res:
								device_settings['resolution'] = f"{m_res.group(1)}x{m_res.group(2)}"
							
							m_scale = _re.search(r'scale\s*=\s*([\d\.]+)', ua_string, flags=_re.I)
							if m_scale:
								try:
									scale_val = float(m_scale.group(1))
									approx_dpi = int(round(scale_val * 160))
									device_settings['dpi'] = f"{approx_dpi}dpi"
								except Exception:
									pass
							
							# Extract device info from UA parentheses
							inside = _re.search(r'\(([^)]*)\)', ua_string)
							if inside:
								ua_tokens = [p.strip() for p in inside.group(1).split(';') if p.strip()]
								if ua_tokens:
									device_settings['ios_model'] = ua_tokens[0]
									for tok in ua_tokens[1:]:
										if tok.lower().startswith('ios'):
											device_settings['ios_version'] = tok.split(' ', 1)[-1]
											break
									for tok in reversed(ua_tokens):
										if tok.isdigit() and len(tok) >= 6:
											device_settings['version_code'] = tok
											break
							
							# Convert iPhone to Android if needed
							if 'iphone' in ua_string.lower() or 'ipad' in ua_string.lower():
								from instgrapi_func.services.device_service import generate_random_device_settings
								android_device = generate_random_device_settings()
								device_settings.update(android_device)
							
							if device_settings:
								settings_snapshot['device_settings'] = device_settings
								settings_snapshot['user_agent'] = ua_string
						except Exception:
							pass
					
					dev_obj.session_settings = settings_snapshot
					dev_obj.save(update_fields=['session_settings', 'updated_at'])
				except Exception as se:
					logger.warning(f"[UA+COOKIES][WARN] Could not persist device session snapshot for {username}: {se}")

				# Update proxy assignment linkage
				if assigned_proxy and (not existing_map.get(username) or not (existing_map[username].proxy or existing_map[username].current_proxy)):
					assigned_proxy.assigned_account = account
					assigned_proxy.save()

				# Create Dolphin profile and import cookies (always as WEB cookies) if requested
				if profile_mode == 'create_profiles' and dolphin_available and (created or not account.dolphin_profile_id):
					try:
						# Throttle between profile creations
						if dolphin_created_count > 0:
							delay_time = random.uniform(1, 2)
							logger.info(f"[UA+COOKIES][DOLPHIN] Delay {delay_time:.1f}s before creating next profile")
							time.sleep(delay_time)

						profile_name = f"instagram_{username}_" + ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
						logger.info(f"[UA+COOKIES][DOLPHIN] Creating Dolphin profile for account {username}")
						proxy_data = assigned_proxy.to_dict() if assigned_proxy else None
						response = dolphin.create_profile(
							name=profile_name,
							proxy=proxy_data,
							tags=["instagram", "ua-cookies"],
							locale=selected_locale
						)
						profile_id = None
						if response and isinstance(response, dict):
							profile_id = response.get("browserProfileId")
							if not profile_id and isinstance(response.get("data"), dict):
								profile_id = response["data"].get("id")
						if profile_id:
							account.dolphin_profile_id = profile_id
							try:
								if account.locale != selected_locale:
									account.locale = selected_locale
									account.save(update_fields=['dolphin_profile_id', 'locale'])
								else:
									account.save(update_fields=['dolphin_profile_id'])
							except Exception:
								account.save(update_fields=['dolphin_profile_id'])
							dolphin_created_count += 1
							logger.info(f"[UA+COOKIES][SUCCESS] Created Dolphin profile {profile_id} for account {username}")
							
							# Save Dolphin profile snapshot for 1:1 recreation
							try:
								from uploader.services.dolphin_snapshot import save_dolphin_snapshot
								save_dolphin_snapshot(account, profile_id, response)
							except Exception as snap_err:
								logger.warning(f"[UA+COOKIES] Could not save Dolphin snapshot for {username}: {snap_err}")
							# Import cookies to Dolphin (prefer Local API)
							try:
								if parsed_cookies_list:
									imp = dolphin.import_cookies_local(profile_id, parsed_cookies_list)
									if not (isinstance(imp, dict) and imp.get('success')):
										logger.info(f"[UA+COOKIES][DOLPHIN] Local import failed/unsupported, trying Remote PATCH for {username}")
										dolphin.update_cookies(profile_id, parsed_cookies_list)
									logger.info(f"[UA+COOKIES][COOKIES] Imported cookies into Dolphin profile {profile_id} for {username}")
								else:
									logger.info(f"[UA+COOKIES][COOKIES] No cookies parsed for {username}, skipping import")
							except Exception as ice:
								logger.warning(f"[UA+COOKIES][COOKIES] Failed to import cookies into profile {profile_id} for {username}: {ice}")
						else:
							error_message = response.get("error", "Unknown error") if isinstance(response, dict) else "Unknown error"
							logger.error(f"[UA+COOKIES][ERROR] Failed to create Dolphin profile for account {username}: {error_message}")
							messages.error(request, f"Failed to create Dolphin profile for account {username}: {error_message}")
							dolphin_error_count += 1
					except Exception as e:
						dolphin_error_count += 1
						logger.error(f"[UA+COOKIES][ERROR] Error creating Dolphin profile for account {username}: {str(e)}")
						messages.error(request, f"Error creating Dolphin profile for account {username}: {str(e)}")

				# Persist cookies in DB for reference
				try:
					from uploader.models import InstagramCookies
					if parsed_cookies_list:
						InstagramCookies.objects.update_or_create(
							account=account,
							defaults={'cookies_data': parsed_cookies_list, 'is_valid': True}
						)
						logger.info(f"[UA+COOKIES][COOKIES] Saved {len(parsed_cookies_list)} cookies for {username}")
				except Exception as ce:
					logger.warning(f"[UA+COOKIES][WARN] Failed to persist cookies in DB for {username}: {ce}")

			except Exception as e:
				error_message = f"[UA+COOKIES][ERROR] Error importing account at line {line_num}: {str(e)}"
				logger.error(error_message)
				messages.error(request, error_message)
				error_count += 1

		# Summary
		logger.info(f"[UA+COOKIES][SUMMARY] Import completed - Created: {created_count}, Updated: {updated_count}, Errors: {error_count}")
		if dolphin_available:
			logger.info(f"[UA+COOKIES][SUMMARY] Dolphin profiles - Created: {dolphin_created_count}, Errors: {dolphin_error_count}")
		if created_count > 0 or updated_count > 0:
			msg = f'Import completed! Created: {created_count}, Updated: {updated_count}, Errors: {error_count}'
			if dolphin_available:
				msg += f', Dolphin profiles created: {dolphin_created_count}, Dolphin errors: {dolphin_error_count}'
			messages.success(request, msg)
		else:
			messages.warning(request, f'No accounts were imported. Errors: {error_count}')
		return redirect('account_list')

	# GET: render page
	clients = CabinetClient.objects.select_related('agency').all()
	context = {
		'active_tab': 'accounts',
		'clients': clients,
	}
	return render(request, 'uploader/import_accounts_ua_cookies.html', context)


def import_accounts_bundle(request):
	"""
	Import accounts in the single-line bundle format.

	Supported formats (sections separated by |):
	1) New (preferred):
	   login:password:email:email_password | user_agent | proxy | ip | locale
	   - proxy examples:
	     user:pass@host:port
	     http:host:port:user:pass
	     host:port:user:pass
	   - ip: external IP of proxy (optional)
	   - locale: e.g. es-CL / es_CL (will be normalized to underscore)

		2) Legacy (still accepted):
	   creds | UA | device_ids | cookies/headers | proxy
	   Where cookies may include Authorization=Bearer IGT:2:...

		3) Enhanced UA+Cookies with 2FA and optional email (cookies-first workflow):
		   login:password:2FA | User Agent | [device_ids] | Cookies [| proxy] [|| email:password]
	   - Example email segment at the end: name@example.com:mail_password
		   - Works strictly via cookies; password is stored but login flows should use cookies.
		   - Proxies embedded in this format are ignored (we assign our own proxies later).

	Parser is resilient and will attempt to auto-detect provided structure.
	"""
	if request.method == 'POST' and request.FILES.get('accounts_file'):
		accounts_file = request.FILES['accounts_file']
		
		# Get selected locale and profile mode
		selected_locale = request.POST.get('profile_locale', 'ru_BY')
		profile_mode = request.POST.get('profile_mode', 'create_profiles')
		
		# Validate locale
		valid_locales = ['ru_BY', 'en_IN', 'es_CL', 'es_MX', 'pt_BR', 'el_GR', 'de_DE']
		if selected_locale not in valid_locales:
			selected_locale = 'ru_BY'

		# Optional tags selection
		selected_tag = None
		try:
			tag_id = request.POST.get('tags')
			if tag_id:
				from uploader.models import Tag
				selected_tag = Tag.objects.filter(id=int(tag_id)).first()
		except Exception:
			selected_tag = None

		# Helpers
		def _extract_cookie_value(cookie_list: list, name: str) -> str | None:
			for c in cookie_list or []:
				try:
					if str(c.get('name') or '').lower() == name.lower():
						return c.get('value')
				except Exception:
					continue
			return None

		def _is_proxy_segment(seg: str) -> bool:
			try:
				s = (seg or '').strip()
				if not s:
					return False
				# Expect at least host:port or scheme:host:port
				colon_count = s.count(':')
				if colon_count < 1:
					return False
				# Heuristics: if contains scheme and 3+ colons -> likely proxy with auth
				low = s.lower()
				# Accept scheme + host:port (2 colons) and scheme + host:port:user:pass (>=3)
				if low.startswith(('http:', 'https:', 'socks5:')) and colon_count >= 2:
					return True
				# Or host:port:login:pass without scheme
				if colon_count >= 3 and '=' not in s and ' ' not in s:
					return True
				# Or user:pass@host:port form (at least one '@' and a colon in host:port)
				if '@' in s:
					try:
						creds, hp = s.rsplit('@', 1)
						if ':' in hp and creds:
							return True
					except Exception:
						return False
				return False
			except Exception:
				return False

		def _parse_proxy(seg: str):
			"""Return dict or None: {host, port, username, password, proxy_type}
			Resolves domain to IP for DB storage.
			"""
			import socket
			try:
				s = (seg or '').strip()
				parts = s.split(':')
				proxy_type = 'HTTP'
				host = ''
				port = None
				username = None
				password = None
				# user:pass@host:port
				if '@' in s and not s.lower().startswith(('http@', 'https@', 'socks5@')):
					try:
						cred_part, hostpart = s.rsplit('@', 1)
						# cred_part could itself contain ':' multiple times; split only on first
						if ':' in cred_part:
							username, password = cred_part.split(':', 1)
						else:
							username = cred_part
							password = None
						# hostpart: host:port
						if ':' in hostpart:
							host, port = hostpart.split(':', 1)
						else:
							return None
					except Exception:
						return None
				elif s.lower().startswith(('http:', 'https:', 'socks5:')):
					scheme = parts[0].lower()
					if scheme == 'https':
						proxy_type = 'HTTPS'
					elif scheme == 'socks5':
						proxy_type = 'SOCKS5'
					else:
						proxy_type = 'HTTP'
					# scheme:host:port[:user][:pass]
					if len(parts) >= 3:
						host = parts[1]
						port = parts[2]
						if len(parts) >= 5:
							username = parts[3] or None
							password = parts[4] or None
					elif len(parts) == 4:
						host = parts[1]
						port = parts[2]
						username = parts[3] or None
					else:
						return None
				else:
					# host:port[:user][:pass]
					if len(parts) < 2:
						return None
					host = parts[0]
					port = parts[1]
					if len(parts) >= 4:
						username = parts[2] or None
						password = parts[3] or None
				# Resolve domain to IP if needed for DB model GenericIPAddressField
				resolved_host = host
				try:
					# If host is already an IP, this will return it; if domain, resolve to first IP
					resolved_host = socket.gethostbyname(host)
				except Exception:
					pass
				return {
					'host': resolved_host,
					'port': int(port) if port is not None else None,
					'username': username,
					'password': password,
					'proxy_type': proxy_type,
					'_original_host': host,
				}
			except Exception:
				return None

		def _parse_cookies(raw: str) -> list[dict]:
			cookies: list[dict] = []
			for pair in [c.strip() for c in (raw or '').split(';') if c.strip()]:
				if '=' not in pair:
					continue
				name, value = pair.split('=', 1)
				cookies.append({
					'domain': '.instagram.com',
					'name': name.strip(),
					'value': value.strip(),
					'path': '/',
					'httpOnly': False,
					'secure': True,
					'session': True,
					'sameSite': 'no_restriction',
				})
			return cookies

		def _decode_igt_bearer(raw: str) -> dict:
			"""Extract ds_user_id/sessionid from Authorization=Bearer IGT:2:<b64> if present."""
			import base64, json
			try:
				marker = 'Authorization=Bearer IGT:2:'
				idx = raw.find(marker)
				if idx == -1:
					return {}
				b64 = raw[idx + len(marker):].split(';', 1)[0].strip()
				# Pad base64 if needed
				padding = '=' * (-len(b64) % 4)
				decoded = base64.b64decode(b64 + padding).decode('utf-8')
				data = json.loads(decoded)
				return {
					'ds_user_id': data.get('ds_user_id'),
					'sessionid': data.get('sessionid'),
				}
			except Exception:
				return {}

		# Read and split
		content = accounts_file.read().decode('utf-8')
		lines = content.splitlines()

		# Precompute existing accounts map to reuse proxies if already assigned
		parsed_usernames: list[str] = []
		for _raw in lines:
			s = (_raw or '').strip()
			if not s:
				continue
			try:
				left = s.split('|', 1)[0]
				uname = left.split(':', 1)[0].strip()
				if uname:
					parsed_usernames.append(uname)
			except Exception:
				continue
		unique_usernames = list({u for u in parsed_usernames})
		existing_map = {acc.username: acc for acc in InstagramAccount.objects.filter(username__in=unique_usernames)}

		created_count = 0
		updated_count = 0
		error_count = 0

		for line_num, raw in enumerate(lines, 1):
			if not (raw or '').strip():
				continue
			try:
				raw_line = raw.strip()
				# Extract optional email suffix, prefer explicit '||email:pass', fallback to last '|email:pass'
				s = raw_line
				email_username = None
				email_password = None
				if '||' in s:
					main_part, email_part = s.split('||', 1)
					s = (main_part or '').strip()
					e = (email_part or '').strip()
					if e and ':' in e:
						eml, epw = e.split(':', 1)
						if '@' in eml:
							email_username = eml.strip()
							email_password = epw.strip()
				else:
					# Fallback: if the last segment looks like email:pass, peel it off
					_tmp_segments = [p.strip() for p in s.split('|')]
					if _tmp_segments and '@' in _tmp_segments[-1] and ':' in _tmp_segments[-1] and '=' not in _tmp_segments[-1]:
						try:
							eml, epw = _tmp_segments[-1].split(':', 1)
							if '@' in eml:
								email_username = eml.strip()
								email_password = epw.strip()
								# remove the last segment from parsing target
								s = s.rsplit('|', 1)[0].strip()
						except Exception:
							pass

				segments = [p.strip() for p in s.split('|')]
				# creds: always left part before first |
				left = segments[0] if segments else ''
				cred_parts = left.split(':')
				if len(cred_parts) < 2:
					messages.warning(request, f'Line {line_num}: Invalid creds, expected username:password')
					error_count += 1
					continue
				username = cred_parts[0].strip()
				password = cred_parts[1].strip()
				# Determine 2FA vs email in cred_parts[2..]
				tfa_secret = None
				if len(cred_parts) >= 4 and ('@' in (cred_parts[2] or '')):
					# Preferred new format with email embedded in creds
					if email_username is None:
						email_username = cred_parts[2].strip()
					if email_password is None:
						email_password = cred_parts[3].strip()
				elif len(cred_parts) == 3:
					third = cred_parts[2].strip()
					if '@' in third:
						# Some bundles might provide only email here without password
						if email_username is None:
							email_username = third
					else:
						# Treat as TOTP secret
						tfa_secret = third
				# Try NEW format first: creds | ua | proxy | ip | locale
				ua_string = ''
				proxy_data = None
				ip_value = None
				locale_value = None
				new_format_ok = False
				if len(segments) >= 4:
					# quick heuristics: second seg looks like UA; third looks like proxy; last 1-2 look like ip/locale
					ua_candidate = segments[1] if len(segments) > 1 else ''
					proxy_candidate = segments[2] if len(segments) > 2 else ''
					last_seg = segments[-1] if segments else ''
					prev_last_seg = segments[-2] if len(segments) >= 2 else ''
					# IP detector
					def _is_ip(sval: str) -> bool:
						try:
							parts = sval.split('.')
							if len(parts) != 4:
								return False
							for p in parts:
								iv = int(p)
								if iv < 0 or iv > 255:
									return False
							return True
						except Exception:
							return False
					# locale detector: xx-YY or xx_YY
					def _is_locale(sval: str) -> bool:
						import re as _re
						return bool(_re.match(r'^[a-z]{2}[-_][A-Z]{2}$', sval or ''))
					if ua_candidate and _is_proxy_segment(proxy_candidate):
						# Determine positions of ip/locale
						if _is_locale(last_seg) and _is_ip(prev_last_seg):
							ua_string = ua_candidate
							proxy_data = _parse_proxy(proxy_candidate)
							ip_value = prev_last_seg
							locale_value = last_seg
							new_format_ok = True
						elif _is_ip(last_seg) and _is_locale(prev_last_seg):
							ua_string = ua_candidate
							proxy_data = _parse_proxy(proxy_candidate)
							ip_value = last_seg
							locale_value = prev_last_seg
							new_format_ok = True

				device_info_raw = None
				parsed_cookies_list: list[dict] = []
				ds_user_id = None
				sessionid = None
				mid_val = None
				ig_u_rur_val = None
				ig_www_claim_val = None

				if not new_format_ok:
					# Legacy format autodetection
					# detect proxy segment (prefer last matching)
					proxy_idx = None
					for idx in range(len(segments) - 1, -1, -1):
						if _is_proxy_segment(segments[idx]):
							proxy_idx = idx
							break

					# detect cookies start: from left to right, first seg containing '=' (name=value)
					cookies_idx = None
					for idx in range(1, len(segments)):
						seg = (segments[idx] or '').strip()
						if '=' in seg:
							cookies_idx = idx
							break

					# UA: first segment with "Instagram" word
					ua_idx = None
					for idx in range(1, len(segments)):
						if 'instagram' in (segments[idx] or '').lower():
							ua_idx = idx
							break

					ua_string = (segments[ua_idx].strip() if ua_idx is not None else '') or ''
					if ua_idx is not None and cookies_idx is not None and (cookies_idx - ua_idx) > 1:
						# Device info should be strictly between UA and cookies
						mid_parts = segments[ua_idx + 1:cookies_idx]
						joined = '|'.join([p for p in mid_parts if p is not None]).strip()
						device_info_raw = joined or None

					cookies_raw = None
					if cookies_idx is not None:
						end_idx = proxy_idx if proxy_idx is not None else len(segments)
						cookies_raw = '|'.join(segments[cookies_idx:end_idx]).strip() or None

					proxy_data = None
					if proxy_idx is not None:
						proxy_data = _parse_proxy(segments[proxy_idx])

					# Parse cookies list and extract useful values
					parsed_cookies_list = _parse_cookies(cookies_raw or '') if cookies_raw else []
					ds_user_id = _extract_cookie_value(parsed_cookies_list, 'ds_user_id')
					sessionid = _extract_cookie_value(parsed_cookies_list, 'sessionid')
					mid_val = _extract_cookie_value(parsed_cookies_list, 'mid') or _extract_cookie_value(parsed_cookies_list, 'X-MID')
					ig_u_rur_val = _extract_cookie_value(parsed_cookies_list, 'IG-U-RUR') or _extract_cookie_value(parsed_cookies_list, 'rur')
					ig_www_claim_val = _extract_cookie_value(parsed_cookies_list, 'X-IG-WWW-Claim')
					# If Authorization bearer present, try decode to enrich
					cookies_raw = '|'.join(segments[cookies_idx:]) if cookies_idx is not None else ''
					if cookies_raw and 'Authorization=Bearer IGT:2:' in cookies_raw:
						dec = _decode_igt_bearer(cookies_raw)
						ds_user_id = ds_user_id or dec.get('ds_user_id')
						sessionid = sessionid or dec.get('sessionid')

				# Flag: cookies-first workflow (strictly by cookies). We will ignore bundle proxies in this mode.
				cookies_first_mode = bool((tfa_secret or '||' in raw_line) and (parsed_cookies_list or sessionid))

				# Create/update account
				defaults = {
					'password': password,
					'email_username': email_username,
					'email_password': email_password,
					'status': 'ACTIVE',
					'notes': (f"UA: {ua_string[:200]}" if ua_string else ""),
				}
				# Persist TFA secret if provided in creds (login:password:2FA)
				if tfa_secret:
					defaults['tfa_secret'] = tfa_secret
				# Set locale from selected locale or from new format
				if locale_value:
					try:
						loc = (locale_value or '').strip()
						loc = loc.replace('-', '_')
						defaults['locale'] = loc
					except Exception:
						pass
				else:
					# Use selected locale from form
					defaults['locale'] = selected_locale
				# Optional client assignment
				try:
					client_id_str = request.POST.get('client_id')
					if client_id_str:
						sel_client = CabinetClient.objects.filter(id=int(client_id_str)).first()
						if sel_client:
							defaults['client'] = sel_client
				except Exception:
					pass
				account, created = InstagramAccount.objects.update_or_create(
					username=username,
					defaults=defaults
				)
				if created:
					created_count += 1
				else:
					updated_count += 1

				# Persist device/session snapshot for instagrapi usage
				try:
					from uploader.models import InstagramDevice
					dev_obj, _ = InstagramDevice.objects.get_or_create(account=account)
					# Build device_settings to lock API app_version and locale
					device_settings = dict(getattr(dev_obj, 'device_settings', {}) or {})
					# Extract app_version from UA if present (Instagram x.y.z...)
					try:
						import re as _re
						m = _re.search(r'Instagram\s+([0-9.]+)', ua_string or '', flags=_re.I)
						if m:
							device_settings['app_version'] = m.group(1)
					except Exception:
						pass
					# Extract resolution and DPI from UA if present (e.g., scale=3.66; 1284x2778)
					try:
						import re as _re
						m_res = _re.search(r'(\d{3,5})x(\d{3,5})', ua_string or '')
						if m_res:
							device_settings['resolution'] = f"{m_res.group(1)}x{m_res.group(2)}"
						m_scale = _re.search(r'scale\s*=\s*([\d\.]+)', (ua_string or ''), flags=_re.I)
						if m_scale:
							try:
								scale_val = float(m_scale.group(1))
								approx_dpi = int(round(scale_val * 160))
								device_settings['dpi'] = f"{approx_dpi}dpi"
							except Exception:
								pass
						# Extract device info from UA parentheses
						inside = _re.search(r'\(([^)]*)\)', ua_string or '')
						if inside:
							ua_tokens = [p.strip() for p in inside.group(1).split(';') if p.strip()]
							if ua_tokens:
								# Check if Android or iOS
								if 'android' in ua_string.lower():
									# Android format: (24/7.0; 640dpi; 720x1280; Lenovo; mi_350; Spice Mi-350; h1; en_US; 671551996)
									if len(ua_tokens) >= 4:
										device_settings['manufacturer'] = ua_tokens[3]  # Lenovo
									if len(ua_tokens) >= 5:
										device_settings['model'] = ua_tokens[4]  # mi_350
									if len(ua_tokens) >= 6:
										device_settings['device'] = ua_tokens[5]  # Spice Mi-350
									if len(ua_tokens) >= 7:
										device_settings['cpu'] = ua_tokens[6]  # h1
									# Extract Android version
									if len(ua_tokens) >= 1:
										android_ver = ua_tokens[0]  # 24/7.0
										if '/' in android_ver:
											ver_parts = android_ver.split('/')
											if len(ver_parts) >= 2:
												device_settings['android_version'] = int(ver_parts[0])
												device_settings['android_release'] = ver_parts[1]
									# Extract DPI
									if len(ua_tokens) >= 2:
										dpi_val = ua_tokens[1]  # 640dpi
										device_settings['dpi'] = dpi_val
									# Extract version code from end
									for tok in reversed(ua_tokens):
										if tok.isdigit() and len(tok) >= 6:
											device_settings['version_code'] = tok
											break
								else:
									# iOS format
									device_settings['ios_model'] = ua_tokens[0]
									# iOS version token like "iOS 12_5_4"
									for tok in ua_tokens[1:]:
										if tok.lower().startswith('ios'):
											device_settings['ios_version'] = tok.split(' ', 1)[-1]
											break
									# trailing numeric token may be version_code-like
									for tok in reversed(ua_tokens):
										if tok.isdigit() and len(tok) >= 6:
											device_settings['version_code'] = tok
											break
					except Exception:
						pass
					# Persist locale/country if provided
					if locale_value:
						try:
							loc_norm = (locale_value or '').replace('-', '_')
							device_settings['locale'] = loc_norm
							# country code: part after underscore
							cc = loc_norm.split('_')[-1]
							device_settings['country'] = cc
							# language code (first part)
							lang_code = loc_norm.split('_', 1)[0].lower()
							device_settings['language'] = lang_code
						except Exception:
							pass
					else:
						# Fallback: try to extract locale from UA parentheses: e.g. (...; es_CL; es-CL; ...)
						try:
							import re as _re
							inside = _re.search(r'\(([^)]*)\)', ua_string or '')
							if inside:
								parts = [p.strip() for p in inside.group(1).split(';')]
								for tok in parts:
									if _re.match(r'^[a-z]{2}[-_][A-Z]{2}$', tok):
										loc_norm = tok.replace('-', '_')
										device_settings['locale'] = loc_norm
										cc = loc_norm.split('_')[-1]
										device_settings['country'] = cc
										device_settings['language'] = loc_norm.split('_', 1)[0].lower()
										# Also update account locale below after device save
										locale_value = tok
										break
						except Exception:
							pass
					# Extract Apple device model (iPhone/iPad) and mark manufacturer
					# BUT CONVERT TO ANDROID - iPhone is not supported by instagrapi
					try:
						import re as _re
						inside = _re.search(r'\(([^)]*)\)', ua_string or '')
						if inside:
							first_tok = inside.group(1).split(';')[0].strip()
							if first_tok.lower().startswith(('iphone', 'ipad', 'ipod')):
								# CONVERT iPhone to Android instead of marking as Apple
								print(f"[CONVERT] Detected iPhone/iPad in account data: {first_tok}, converting to Android")
								
								# Generate Android device settings
								from instgrapi_func.services.device_service import generate_random_device_settings
								android_device = generate_random_device_settings()
								
								# Preserve UUIDs from original if available
								preserved_uuids = {}
								for key in ("uuid", "android_device_id", "phone_id", "client_session_id"):
									if device_settings.get(key):
										preserved_uuids[key] = device_settings[key]
								
								# Merge preserved UUIDs into Android device
								from instgrapi_func.services.device_service import _merge_uuids
								android_device = _merge_uuids(android_device, preserved_uuids)
								
								# Update device_settings with Android values
								device_settings.update(android_device)
								
								print(f"[CONVERT] iPhone converted to Android: {android_device.get('model')} {android_device.get('manufacturer')}")
					except Exception as e:
						print(f"[CONVERT] Failed to convert iPhone to Android: {e}")
						pass

					# Capture network segment like "NW/1" if present in the line segments
					try:
						for _seg in segments[1:]:
							_s = (_seg or '').strip()
							if _s.upper().startswith('NW/') and len(_s) <= 6:
								device_settings['network'] = _s.upper()
								break
					except Exception:
						pass

					# Ensure stable device UUIDs (uuid/phone_id/client_session_id/android_device_id)
					try:
						import hashlib, uuid as _uuid
						need_ids = not all([
							device_settings.get('uuid'),
							device_settings.get('phone_id'),
							device_settings.get('client_session_id'),
							device_settings.get('android_device_id'),
						])
						if need_ids:
							seed_parts = [username or '', ua_string or '']
							try:
								seed_parts.append(proxy_data.get('username') or '')
							except Exception:
								pass
							seed = '|'.join(seed_parts)
							h = hashlib.sha1(seed.encode('utf-8')).hexdigest()
							# Build deterministic UUIDs
							uid = str(_uuid.UUID(h[0:32]))
							pid = str(_uuid.uuid5(_uuid.NAMESPACE_DNS, h[8:]))
							csid = str(_uuid.uuid5(_uuid.NAMESPACE_URL, h[16:]))
							adid = 'android-' + h[0:16]
							device_settings.setdefault('uuid', uid)
							device_settings.setdefault('phone_id', pid)
							device_settings.setdefault('client_session_id', csid)
							device_settings.setdefault('android_device_id', adid)
					except Exception:
						pass

					# If UA looks like Apple/iOS – convert to Android UA for instagrapi
					try:
						def _is_apple_ua(s: str) -> bool:
							ls = (s or '').lower()
							return ('iphone' in ls) or ('ipad' in ls) or ('ipod' in ls) or ('ios' in ls)
						is_apple = _is_apple_ua(ua_string)
						if is_apple:
							# Choose Android defaults if missing
							app_ver = device_settings.get('app_version') or '269.0.0.18.75'
							android_version = str(device_settings.get('android_version') or 29)
							android_release = device_settings.get('android_release') or '10'
							dpi_val = device_settings.get('dpi') or '640dpi'
							res_val = device_settings.get('resolution') or '1440x3040'
							man = device_settings.get('manufacturer') or 'samsung'
							model = device_settings.get('model') or 'SM-G973F'
							dev = device_settings.get('device') or 'beyond1'
							cpu = device_settings.get('cpu') or 'exynos9820'
							loc = device_settings.get('locale') or (locale_value or 'en_US')
							ver_code = device_settings.get('version_code') or '314665256'
							# Normalize locale formatting to underscore
							loc = str(loc).replace('-', '_')
							android_ua = (
								f"Instagram {app_ver} "
								f"Android ({android_version}/{android_release}; {dpi_val}; {res_val}; {man}; {model}; {dev}; {cpu}; {loc}; {ver_code})"
							)
							# Overwrite device settings to Android profile
							device_settings['app_version'] = app_ver
							device_settings['android_version'] = int(android_version) if str(android_version).isdigit() else 29
							device_settings['android_release'] = android_release
							device_settings['dpi'] = dpi_val
							device_settings['resolution'] = res_val
							device_settings['manufacturer'] = man
							device_settings['model'] = model
							device_settings['device'] = dev
							device_settings['cpu'] = cpu
							device_settings['locale'] = loc
							device_settings['version_code'] = ver_code
							device_settings['user_agent'] = android_ua
							# Persist UA replacement: keep original for reference
							ua_replaced = android_ua
						else:
							ua_replaced = None
					except Exception:
						ua_replaced = None
					# Backfill UUIDs if present from legacy device_info_raw
					if device_info_raw:
						try:
							di_parts = [p for p in device_info_raw.split(';') if p]
							if di_parts:
								device_settings.setdefault('android_device_id', di_parts[0])
							if len(di_parts) >= 2:
								device_settings.setdefault('phone_id', di_parts[1])
							if len(di_parts) >= 3:
								device_settings.setdefault('uuid', di_parts[2])
							if len(di_parts) >= 4:
								device_settings.setdefault('client_session_id', di_parts[3])
						except Exception:
							pass
					# Save device and session snapshot (minimal in new format)
					if ua_string:
						# Pick UA for API: converted Android UA if we built it, else original
						ua_for_api = (ua_replaced or ua_string)
						dev_obj.user_agent = dev_obj.user_agent or ua_for_api
					if device_settings:
						dev_obj.device_settings = device_settings
						logger.info(f"[BUNDLE] Saved device_settings for {username}: {list(device_settings.keys())}")
						logger.info(f"[BUNDLE] Device details: manufacturer={device_settings.get('manufacturer')}, model={device_settings.get('model')}, resolution={device_settings.get('resolution')}")
					# Minimal session_settings to carry UA for API-only flows
					sess = dict(getattr(dev_obj, 'session_settings', {}) or {})
					if ua_string:
						# keep both original and effective UA
						sess['user_agent'] = (ua_replaced or ua_string)
						if ua_replaced:
							sess['original_user_agent'] = ua_string
					
					# CRITICAL: Save device_settings in session_settings for ensure_persistent_device
					if device_settings:
						sess['device_settings'] = device_settings
					
					# Inject authorization_data from cookies for instagrapi session login
					if (ds_user_id or sessionid):
						try:
							sess['authorization_data'] = {
								'ds_user_id': ds_user_id,
								'sessionid': sessionid,
								'should_use_header_over_cookies': True,
							}
						except Exception:
							pass
					dev_obj.session_settings = sess
					dev_obj.save(update_fields=['device_settings', 'session_settings', 'user_agent', 'updated_at'])
					# If we auto-derived locale from UA and account lacks it, persist to account
					try:
						if locale_value and (not account.locale or account.locale.strip() == ''):
							loc_norm = locale_value.replace('-', '_')
							account.locale = loc_norm
							account.save(update_fields=['locale'])
					except Exception:
						pass
				except Exception as se:
					logger.warning(f"[BUNDLE] Could not persist device session for {username}: {se}")

				# Persist cookies for reference and instagrapi session restoration
				if parsed_cookies_list:
					try:
						from uploader.models import InstagramCookies
						# Convert cookies list to dict format for instagrapi
						cookies_dict = {cookie['name']: cookie['value'] for cookie in parsed_cookies_list}
						
						InstagramCookies.objects.update_or_create(
							account=account,
							defaults={'cookies_data': cookies_dict, 'is_valid': True}
						)
						
						# Also save cookies in session_settings for instagrapi
						if not sess.get('cookies'):
							sess['cookies'] = cookies_dict
							dev_obj.session_settings = sess
							dev_obj.save(update_fields=['session_settings'])
						
						logger.info(f"[BUNDLE] Saved {len(cookies_dict)} cookies for {username}")
					except Exception as ce:
						logger.warning(f"[BUNDLE] Failed to persist cookies for {username}: {ce}")

				# Attach proxy from bundle unless we're in cookies-first mode (skip proxies in this format)
				try:
					assigned_proxy = None
					if (not cookies_first_mode) and proxy_data and proxy_data.get('host') and proxy_data.get('port'):
						# Normalize country from locale if present
						proxy_country = None
						try:
							if locale_value:
								proxy_country = locale_value.replace('-', '_').split('_')[-1]
						except Exception:
							proxy_country = None
						assigned_proxy, _ = Proxy.objects.get_or_create(
							host=proxy_data['host'],
							port=int(proxy_data['port']),
							username=proxy_data.get('username') or None,
							password=proxy_data.get('password') or None,
							defaults={
								'proxy_type': proxy_data.get('proxy_type') or 'HTTP',
								'status': 'active',
								'is_active': True,
								'external_ip': ip_value,
								'country': proxy_country,
							}
						)
						# Update mutable fields if existing
						updates = []
						if ip_value and assigned_proxy.external_ip != ip_value:
							assigned_proxy.external_ip = ip_value
							updates.append('external_ip')
						if proxy_country and assigned_proxy.country != proxy_country:
							assigned_proxy.country = proxy_country
							updates.append('country')
						if assigned_proxy.status != 'active':
							assigned_proxy.status = 'active'
							updates.append('status')
						if assigned_proxy.is_active is False:
							assigned_proxy.is_active = True
							updates.append('is_active')
						if assigned_proxy.assigned_account_id != account.id:
							assigned_proxy.assigned_account = account
							updates.append('assigned_account')
						if updates:
							assigned_proxy.save(update_fields=updates)
						# Bind to account
						account.proxy = assigned_proxy
						account.current_proxy = assigned_proxy
						account.save(update_fields=['proxy', 'current_proxy'])
					else:
						# Fallback: reuse previous or assign free
						prev_acc = existing_map.get(username)
						if prev_acc and (prev_acc.current_proxy or prev_acc.proxy):
							assigned_proxy = prev_acc.current_proxy or prev_acc.proxy
							account.proxy = assigned_proxy
							account.current_proxy = assigned_proxy
							account.save(update_fields=['proxy', 'current_proxy'])
							logger.info(f"[BUNDLE] Reusing existing proxy for {username}: {assigned_proxy}")
						elif not (account.current_proxy or account.proxy):
							# Assign proxy by selected locale
							avail = Proxy.objects.filter(is_active=True, assigned_account__isnull=True)
							
							# Filter by locale country if available
							locale_country = selected_locale.split('_')[-1] if '_' in selected_locale else selected_locale
							country_text = {
								'BY': 'Belarus', 'IN': 'India', 'CL': 'Chile', 
								'MX': 'Mexico', 'BR': 'Brazil', 'GR': 'Greece', 'DE': 'Germany'
							}.get(locale_country, locale_country)
							
							locale_proxies = avail.filter(
								Q(country__iexact=locale_country) | 
								Q(country__icontains=country_text) | 
								Q(city__icontains=country_text)
							)
							
							if locale_proxies.exists():
								assigned_proxy = locale_proxies.order_by('?').first()
								logger.info(f"[BUNDLE] Assigned locale proxy {assigned_proxy} to {username} (locale: {selected_locale})")
							elif avail.exists():
								assigned_proxy = avail.order_by('?').first()
								logger.info(f"[BUNDLE] Assigned fallback proxy {assigned_proxy} to {username} (no locale match)")
							else:
								logger.warning(f"[BUNDLE] No free proxies available to assign for {username}")
							
							if assigned_proxy:
								account.proxy = assigned_proxy
								account.current_proxy = assigned_proxy
								account.save(update_fields=['proxy', 'current_proxy'])
								assigned_proxy.assigned_account = account
								assigned_proxy.save(update_fields=['assigned_account'])
				except Exception as pe:
					logger.warning(f"[BUNDLE] Proxy assignment failed for {username}: {pe}")

				# Assign tag to account
				if selected_tag:
					account.tag = selected_tag
					account.save(update_fields=['tag'])
					logger.info(f"[BUNDLE] Assigned tag '{selected_tag.name}' to {username}")

				# Create Dolphin profile if requested and proxy is available
				if profile_mode == 'create_profiles' and assigned_proxy and (created or not account.dolphin_profile_id):
					try:
						# Initialize Dolphin API
						api_key = os.environ.get("DOLPHIN_API_TOKEN", "")
						if api_key:
							dolphin_api_host = os.environ.get("DOLPHIN_API_HOST", "http://localhost:3001/v1.0")
							if not dolphin_api_host.endswith("/v1.0"):
								dolphin_api_host = dolphin_api_host.rstrip("/") + "/v1.0"
							
							from bot.src.instagram_uploader.dolphin_anty import DolphinAnty
							dolphin = DolphinAnty(api_key=api_key, local_api_base=dolphin_api_host)
							
							if dolphin.authenticate():
								# Create profile name
								random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
								profile_name = f"instagram_{username}_{random_suffix}"
								logger.info(f"[BUNDLE][DOLPHIN] Creating Dolphin profile for account {username}")
								
								# Create profile
								response = dolphin.create_profile(
									name=profile_name,
									proxy=assigned_proxy.to_dict(),
									tags=["instagram", "bundle"],
									locale=selected_locale
								)
								
								# Extract profile ID
								profile_id = None
								if response and isinstance(response, dict):
									profile_id = response.get("browserProfileId")
									if not profile_id and isinstance(response.get("data"), dict):
										profile_id = response["data"].get("id")
								
								if profile_id:
									account.dolphin_profile_id = profile_id
									account.save(update_fields=['dolphin_profile_id'])
									
									# Import cookies if available
									if parsed_cookies_list:
										try:
											# Convert cookies to list format for Dolphin
											cookies_for_dolphin = []
											if isinstance(parsed_cookies_list, list):
												cookies_for_dolphin = parsed_cookies_list
											elif isinstance(parsed_cookies_list, dict):
												cookies_for_dolphin = [{'name': k, 'value': v, 'domain': '.instagram.com', 'path': '/'} for k, v in parsed_cookies_list.items()]
											
											# Import cookies
											imp = dolphin.import_cookies_local(profile_id, cookies_for_dolphin)
											if not (isinstance(imp, dict) and imp.get('success')):
												logger.info(f"[BUNDLE][DOLPHIN] Local import failed, trying Remote PATCH for {username}")
												dolphin.update_cookies(profile_id, cookies_for_dolphin)
											logger.info(f"[BUNDLE][DOLPHIN] Imported {len(cookies_for_dolphin)} cookies into profile {profile_id} for {username}")
										except Exception as cookie_err:
											logger.warning(f"[BUNDLE][DOLPHIN] Failed to import cookies for {username}: {cookie_err}")
									
									logger.info(f"[BUNDLE][DOLPHIN] Successfully created profile {profile_id} for {username}")
								else:
									logger.error(f"[BUNDLE][DOLPHIN] Failed to create profile for {username}: {response}")
							else:
								logger.warning(f"[BUNDLE][DOLPHIN] Failed to authenticate with Dolphin API")
						else:
							logger.warning(f"[BUNDLE][DOLPHIN] Dolphin API token not configured")
					except Exception as dolphin_err:
						logger.warning(f"[BUNDLE][DOLPHIN] Error creating Dolphin profile for {username}: {dolphin_err}")

			except Exception as e:
				logger.error(f"[BUNDLE] Error at line {line_num}: {e}")
				messages.error(request, f'Line {line_num}: {e}')
				error_count += 1

		# Summary
		if created_count or updated_count:
			messages.success(request, f'Bundle import done. Created: {created_count}, Updated: {updated_count}, Errors: {error_count}')
		else:
			messages.warning(request, f'No accounts imported. Errors: {error_count}')
		return redirect('account_list')

	# GET: render page
	clients = CabinetClient.objects.select_related('agency').all()
	from uploader.models import Tag
	tags = Tag.objects.all().order_by('name')
	context = {
		'active_tab': 'accounts',
		'clients': clients,
		'tags': tags,
	}
	return render(request, 'uploader/import_accounts_bundle.html', context)


@login_required
def bulk_save_snapshots(request):
	"""Bulk save Dolphin profile snapshots for selected accounts"""
	if request.method != 'POST':
		return redirect('account_list')
	
	account_ids = request.POST.getlist('account_ids')
	if not account_ids:
		messages.warning(request, 'No accounts selected!')
		return redirect('account_list')
	
	try:
		# Initialize Dolphin API
		dolphin_token = os.environ.get('DOLPHIN_API_TOKEN')
		if not dolphin_token:
			messages.error(request, 'Dolphin API token not configured!')
			return redirect('account_list')
		
		from bot.src.instagram_uploader.dolphin_anty import DolphinAnty
		dolphin = DolphinAnty(dolphin_token)
		
		if not dolphin.authenticate():
			messages.error(request, 'Failed to authenticate with Dolphin Anty API!')
			return redirect('account_list')
		
		from uploader.services.dolphin_snapshot import save_existing_profile_snapshot
		
		success_count = 0
		error_count = 0
		skipped_count = 0
		
		accounts = InstagramAccount.objects.filter(id__in=account_ids)
		
		for account in accounts:
			if not account.dolphin_profile_id:
				skipped_count += 1
				logger.warning(f"[BULK SNAPSHOT] Account {account.username} has no Dolphin profile, skipped")
				continue
			
			try:
				if save_existing_profile_snapshot(account, dolphin):
					success_count += 1
					logger.info(f"[BULK SNAPSHOT] Successfully saved snapshot for {account.username}")
				else:
					error_count += 1
					logger.error(f"[BULK SNAPSHOT] Failed to save snapshot for {account.username}")
			except Exception as e:
				error_count += 1
				logger.error(f"[BULK SNAPSHOT] Error saving snapshot for {account.username}: {str(e)}")
		
		# Show summary
		if success_count > 0:
			messages.success(request, f'Successfully saved {success_count} snapshot(s)!')
		if error_count > 0:
			messages.error(request, f'Failed to save {error_count} snapshot(s). Check logs for details.')
		if skipped_count > 0:
			messages.warning(request, f'Skipped {skipped_count} account(s) without Dolphin profiles.')
	
	except Exception as e:
		logger.error(f"[BULK SNAPSHOT] Bulk save snapshots error: {str(e)}")
		messages.error(request, f'Error during bulk snapshot save: {str(e)}')
	
	return redirect('account_list')


@login_required
def bulk_change_status(request):
	"""Bulk change status for selected accounts"""
	if request.method != 'POST':
		return redirect('account_list')
	
	account_ids = request.POST.getlist('account_ids')
	new_status = request.POST.get('status', '').upper()
	
	if not account_ids:
		messages.warning(request, 'No accounts selected!')
		return redirect('account_list')
	
	valid_statuses = ['ACTIVE', 'BLOCKED', 'LIMITED', 'INACTIVE', 'PHONE_VERIFICATION_REQUIRED', 'HUMAN_VERIFICATION_REQUIRED', 'SUSPENDED']
	if new_status not in valid_statuses:
		messages.error(request, f'Invalid status! Valid options: {", ".join(valid_statuses)}')
		return redirect('account_list')
	
	try:
		accounts = InstagramAccount.objects.filter(id__in=account_ids)
		count = accounts.update(status=new_status)
		
		logger.info(f"[BULK STATUS] Changed status to {new_status} for {count} account(s)")
		messages.success(request, f'Successfully changed status to {new_status} for {count} account(s)!')
	
	except Exception as e:
		logger.error(f"[BULK STATUS] Error changing status: {str(e)}")
		messages.error(request, f'Error changing status: {str(e)}')
	
	return redirect('account_list')


@login_required
def bulk_delete_accounts(request):
	"""Bulk delete selected accounts"""
	if request.method != 'POST':
		return redirect('account_list')
	
	account_ids = request.POST.getlist('account_ids')
	
	if not account_ids:
		messages.warning(request, 'No accounts selected!')
		return redirect('account_list')
	
	try:
		accounts = InstagramAccount.objects.filter(id__in=account_ids)
		count = accounts.count()
		usernames = [acc.username for acc in accounts[:10]]  # Show first 10
		
		# Initialize Dolphin API for profile deletion
		dolphin = None
		api_key = os.environ.get("DOLPHIN_API_TOKEN", "")
		if api_key:
			try:
				dolphin_api_host = os.environ.get("DOLPHIN_API_HOST", "http://localhost:3001/v1.0")
				if not dolphin_api_host.endswith("/v1.0"):
					dolphin_api_host = dolphin_api_host.rstrip("/") + "/v1.0"
				
				from bot.src.instagram_uploader.dolphin_anty import DolphinAnty
				dolphin = DolphinAnty(api_key=api_key, local_api_base=dolphin_api_host)
				if not dolphin.authenticate():
					logger.warning("[BULK DELETE] Failed to authenticate with Dolphin API")
					dolphin = None
			except Exception as e:
				logger.error(f"[BULK DELETE] Error initializing Dolphin API: {str(e)}")
				dolphin = None
		
		# Delete Dolphin profiles and release proxies
		dolphin_deleted_count = 0
		dolphin_failed_count = 0
		proxy_released_count = 0
		
		for account in accounts:
			# Delete Dolphin profile if exists
			if account.dolphin_profile_id and dolphin:
				try:
					delete_result = dolphin.delete_profile(account.dolphin_profile_id)
					if delete_result:
						dolphin_deleted_count += 1
						logger.info(f"[BULK DELETE] Deleted Dolphin profile {account.dolphin_profile_id} for {account.username}")
					else:
						dolphin_failed_count += 1
						logger.warning(f"[BULK DELETE] Failed to delete Dolphin profile {account.dolphin_profile_id} for {account.username}")
				except Exception as e:
					dolphin_failed_count += 1
					logger.error(f"[BULK DELETE] Error deleting Dolphin profile {account.dolphin_profile_id} for {account.username}: {str(e)}")
			
			# Release proxy if assigned
			if account.proxy:
				try:
					proxy = account.proxy
					proxy.assigned_account = None
					proxy.save(update_fields=['assigned_account'])
					proxy_released_count += 1
					logger.info(f"[BULK DELETE] Released proxy {proxy} from account {account.username}")
				except Exception as e:
					logger.error(f"[BULK DELETE] Error releasing proxy for {account.username}: {str(e)}")
		
		# Delete accounts from database
		accounts.delete()
		
		# Prepare summary message
		summary_parts = [f'Successfully deleted {count} account(s)']
		if dolphin_deleted_count > 0:
			summary_parts.append(f'{dolphin_deleted_count} Dolphin profile(s) deleted')
		if dolphin_failed_count > 0:
			summary_parts.append(f'{dolphin_failed_count} Dolphin profile(s) failed to delete')
		if proxy_released_count > 0:
			summary_parts.append(f'{proxy_released_count} proxy(ies) released')
		
		logger.info(f"[BULK DELETE] Deleted {count} account(s): {', '.join(usernames)}")
		messages.success(request, '. '.join(summary_parts) + '.')
		
		if dolphin_failed_count > 0:
			messages.warning(request, f'{dolphin_failed_count} Dolphin profile(s) could not be deleted. They may need to be cleaned up manually.')
	
	except Exception as e:
		logger.error(f"[BULK DELETE] Error deleting accounts: {str(e)}")
		messages.error(request, f'Error deleting accounts: {str(e)}')
	
	return redirect('account_list')
