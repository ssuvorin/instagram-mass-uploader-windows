"""Views module: proxies (split from monolith)."""
from .common import *


def proxy_list(request):
    """List all proxies"""
    status_filter = request.GET.get('status', '')
    search_query = request.GET.get('q', '')
    
    proxies = Proxy.objects.all()
    
    if status_filter:
        is_active = status_filter == 'active'
        proxies = proxies.filter(is_active=is_active)
    
    if search_query:
        proxies = proxies.filter(
            Q(host__icontains=search_query) |
            Q(username__icontains=search_query)
        )
    
    # Get total count before pagination
    total_proxies = proxies.count()
    
    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(proxies.order_by('-last_verified', 'host', 'port'), 25)  # 25 proxies per page
    page_number = request.GET.get('page', 1)
    proxies = paginator.get_page(page_number)
    
    context = {
        'proxies': proxies,
        'status_filter': status_filter,
        'search_query': search_query,
        'total_proxies': total_proxies,
        'active_tab': 'proxies'
    }
    return render(request, 'uploader/proxy_list.html', context)


def create_proxy(request):
    """Create a new proxy"""
    if request.method == 'POST':
        form = ProxyForm(request.POST)
        if form.is_valid():
            # Create but don't save the proxy instance yet
            proxy = form.save(commit=False)
            
            # Validate the proxy before saving
            is_valid, message, geo_info = validate_proxy(
                host=proxy.host,
                port=proxy.port,
                username=proxy.username,
                password=proxy.password,
                timeout=15,
                proxy_type=proxy.proxy_type
            )
            
            if not is_valid:
                messages.error(request, f'Proxy validation failed: {message}')
                context = {
                    'form': form,
                    'active_tab': 'proxies',
                    'validation_error': message
                }
                return render(request, 'uploader/create_proxy.html', context)
            
            # Set status based on validation result
            proxy.status = 'active' if is_valid else 'inactive'
            proxy.is_active = is_valid
            
            # Update country and city information if available
            if geo_info:
                if geo_info.get('country'):
                    proxy.country = geo_info.get('country')
                if geo_info.get('city'):
                    proxy.city = geo_info.get('city')
            
            # Set verification timestamps
            proxy.last_verified = timezone.now()
            proxy.last_checked = timezone.now()
            
            # Save the valid proxy
            proxy.save()
            messages.success(request, f'Proxy {proxy.host}:{proxy.port} created and validated successfully!')
            return redirect('proxy_list')
    else:
        form = ProxyForm()
    
    context = {
        'form': form,
        'active_tab': 'proxies'
    }
    return render(request, 'uploader/create_proxy.html', context)


def edit_proxy(request, proxy_id):
    """Edit an existing proxy"""
    proxy = get_object_or_404(Proxy, id=proxy_id)
    
    if request.method == 'POST':
        form = ProxyForm(request.POST, instance=proxy)
        if form.is_valid():
            # Create but don't save the proxy instance yet
            updated_proxy = form.save(commit=False)
            
            # Validate only if connectivity details have changed
            if (proxy.host != updated_proxy.host or 
                proxy.port != updated_proxy.port or 
                proxy.username != updated_proxy.username or 
                proxy.password != updated_proxy.password or
                proxy.proxy_type != updated_proxy.proxy_type):
                
                # Validate the proxy before saving
                is_valid, message, geo_info = validate_proxy(
                    host=updated_proxy.host,
                    port=updated_proxy.port,
                    username=updated_proxy.username,
                    password=updated_proxy.password,
                    timeout=15,
                    proxy_type=updated_proxy.proxy_type
                )
                
                if not is_valid:
                    messages.error(request, f'Proxy validation failed: {message}')
                    context = {
                        'form': form,
                        'proxy': proxy,
                        'active_tab': 'proxies',
                        'validation_error': message
                    }
                    return render(request, 'uploader/edit_proxy.html', context)
                
                # Set status based on validation result
                updated_proxy.status = 'active' if is_valid else 'inactive'
                updated_proxy.is_active = is_valid
                
                # Set verification timestamps
                updated_proxy.last_verified = timezone.now()
                updated_proxy.last_checked = timezone.now()
                
                # Update country and city information if available
                if geo_info:
                    if geo_info.get('country'):
                        updated_proxy.country = geo_info.get('country')
                    if geo_info.get('city'):
                        updated_proxy.city = geo_info.get('city')
            
            # Save the valid proxy
            updated_proxy.save()
            messages.success(request, f'Proxy {updated_proxy.host}:{updated_proxy.port} updated successfully!')
            return redirect('proxy_list')
    else:
        form = ProxyForm(instance=proxy)
    
    context = {
        'form': form,
        'proxy': proxy,
        'active_tab': 'proxies'
    }
    return render(request, 'uploader/edit_proxy.html', context)


def test_proxy(request, proxy_id):
    """Test if a proxy server is working"""
    proxy = get_object_or_404(Proxy, id=proxy_id)
    
    # Test proxy functionality using the validation utility
    is_valid, message, geo_info = validate_proxy(
        host=proxy.host,
        port=proxy.port,
        username=proxy.username,
        password=proxy.password,
        timeout=15,  # Increase timeout for more reliable testing
        proxy_type=proxy.proxy_type
    )
    
    # Update proxy verification timestamp and location data
    proxy.last_verified = timezone.now()
    proxy.last_checked = timezone.now()
    
    # Update status based on validation result
    if is_valid:
        proxy.status = 'active'
        proxy.is_active = True
    else:
        proxy.status = 'inactive'
        proxy.is_active = False
    
    # Update country and city information if available
    if geo_info and is_valid:
        if geo_info.get('country'):
            proxy.country = geo_info.get('country')
        if geo_info.get('city'):
            proxy.city = geo_info.get('city')
    
    proxy.save()
    
    if is_valid:
        messages.success(request, f'Proxy {proxy.host}:{proxy.port} is working! {message}')
    else:
        messages.error(request, f'Proxy {proxy.host}:{proxy.port} failed validation: {message}')
        
    return redirect('proxy_list')


def import_proxies(request):
    """Import proxies from a text file"""
    if request.method == 'POST' and request.FILES.get('proxies_file'):
        proxies_file = request.FILES['proxies_file']
        
        # Counters for status messages
        created_count = 0
        updated_count = 0
        error_count = 0
        invalid_count = 0
        
        # Read file content
        content = proxies_file.read().decode('utf-8')
        
        for line_num, line in enumerate(content.splitlines(), 1):
            if not line.strip():
                continue  # Skip empty lines
            
            try:
                # Parse line in format host:port:username:password
                parts = line.strip().split(':')
                
                if len(parts) < 2:
                    messages.warning(request, f'Line {line_num}: Invalid format. Expected at least host:port')
                    error_count += 1
                    continue
                
                host = parts[0]
                port = parts[1]
                username = parts[2] if len(parts) > 2 else None
                password = parts[3] if len(parts) > 3 else None
                
                # Validate the proxy before importing
                is_valid, validation_message, geo_info = validate_proxy(
                    host=host,
                    port=port,
                    username=username,
                    password=password,
                    timeout=10,
                    proxy_type='HTTP'  # Default to HTTP for imported proxies
                )
                
                if not is_valid:
                    logger.warning(f"Line {line_num}: Proxy validation failed - {validation_message}")
                    messages.warning(request, f'Line {line_num}: Proxy validation failed - {validation_message}')
                    invalid_count += 1
                    continue
                
                # Check if an identical proxy already exists (same host, port, username, password)
                identical_proxy = Proxy.objects.filter(
                    host=host,
                    port=port,
                    username=username,
                    password=password
                ).first()
                
                if identical_proxy:
                    # Update existing proxy
                    identical_proxy.status = 'active' if is_valid else 'inactive'
                    identical_proxy.is_active = is_valid
                    identical_proxy.last_verified = timezone.now()
                    identical_proxy.last_checked = timezone.now()
                    
                    # Update country and city information if available
                    if geo_info:
                        if geo_info.get('country'):
                            identical_proxy.country = geo_info.get('country')
                        if geo_info.get('city'):
                            identical_proxy.city = geo_info.get('city')
                    
                    identical_proxy.save()
                    updated_count += 1
                else:
                    # Create new proxy
                    new_proxy = Proxy(
                        host=host,
                        port=port,
                        username=username,
                        password=password,
                        status='active' if is_valid else 'inactive',
                        is_active=is_valid,
                        last_verified=timezone.now(),
                        last_checked=timezone.now()
                    )
                    
                    # Add country and city information if available
                    if geo_info:
                        if geo_info.get('country'):
                            new_proxy.country = geo_info.get('country')
                        if geo_info.get('city'):
                            new_proxy.city = geo_info.get('city')
                    
                    new_proxy.save()
                    created_count += 1
                
            except Exception as e:
                logger.error(f"Error importing proxy at line {line_num}: {str(e)}")
                messages.error(request, f'Line {line_num}: Error importing proxy - {str(e)}')
                error_count += 1
        
        # Show summary message
        if created_count > 0 or updated_count > 0:
            messages.success(
                request, 
                f'Import completed! Created: {created_count}, Updated: {updated_count}, Invalid: {invalid_count}, Errors: {error_count}'
            )
        else:
            messages.warning(request, f'No valid proxies were imported. Invalid: {invalid_count}, Errors: {error_count}')
            
        return redirect('proxy_list')
        
    context = {
        'active_tab': 'import_proxies'
    }
    return render(request, 'uploader/import_proxies.html', context)


def validate_all_proxies(request):
    """Validate all active proxies in the system"""
    proxies = Proxy.objects.filter(is_active=True)
    
    if not proxies.exists():
        messages.warning(request, 'No active proxies found in the system.')
        return redirect('proxy_list')
    
    # Require authenticated user to attach messages/session to background thread
    if not getattr(request.user, 'is_authenticated', False):
        messages.error(request, 'You must be logged in to validate proxies.')
        return redirect('proxy_list')
    
    # Start the validation in a background thread to avoid timeout
    thread = threading.Thread(
        target=_validate_proxies_background,
        args=(proxies, request.user.id)
    )
    thread.daemon = True
    thread.start()
    
    messages.info(
        request, 
        f'Validation of {proxies.count()} proxies has been started in the background. Please check back in a moment.'
    )
    return redirect('proxy_list')


def _validate_proxies_background(proxies, user_id):
    """Background task to validate proxies"""
    from django.contrib.auth import get_user_model
    from django.contrib.auth.models import AnonymousUser
    from django.contrib.messages import constants as message_constants
    from django.contrib.messages.storage.fallback import FallbackStorage
    from django.contrib.sessions.backends.db import SessionStore
    from django.http import HttpRequest
    from django.db import connections
    
    # Create a fake request to use for messaging
    request = HttpRequest()
    try:
        if user_id is not None:
            UserModel = get_user_model()
            request.user = UserModel.objects.get(id=user_id)
        else:
            request.user = AnonymousUser()
    except Exception:
        # Fall back to anonymous if user not found
        request.user = AnonymousUser()
    request.session = SessionStore()
    request.session.create()
    request._messages = FallbackStorage(request)
    
    valid_count = 0
    invalid_count = 0
    
    # Use multiple threads to validate proxies in parallel
    thread_count = min(10, proxies.count())  # Max 10 threads
    
    if thread_count <= 0:
        return
    
    from concurrent.futures import ThreadPoolExecutor
    
    def validate_proxy_worker(proxy):
        is_valid, _, geo_info = validate_proxy(
            host=proxy.host,
            port=proxy.port,
            username=proxy.username,
            password=proxy.password,
            timeout=10,
            proxy_type=proxy.proxy_type
        )
        
        # Update proxy verification timestamp and location data
        proxy.last_verified = timezone.now()
        proxy.last_checked = timezone.now()
        
        # Update status based on validation result
        proxy.status = 'active' if is_valid else 'inactive'
        proxy.is_active = is_valid
        
        # Update country and city information if available
        if geo_info and is_valid:
            if geo_info.get('country'):
                proxy.country = geo_info.get('country')
            if geo_info.get('city'):
                proxy.city = geo_info.get('city')
        
        proxy.save()
        
        return is_valid
    
    # Execute validation in parallel
    with ThreadPoolExecutor(max_workers=thread_count) as executor:
        # Evaluate queryset to list in main thread to avoid DB usage across threads during iteration
        proxy_list = list(proxies)
        results = list(executor.map(validate_proxy_worker, proxy_list))
        
    valid_count = sum(1 for r in results if r)
    invalid_count = sum(1 for r in results if not r)
    
    # Add message to the fake request
    # This will be seen on the next page load
    request._messages.add(
        message_constants.SUCCESS,
        f'Proxy validation complete. Valid: {valid_count}, Invalid: {invalid_count}'
    )
    
    # Gently close DB connections opened by this background thread
    try:
        for conn in connections.all():
            if conn.connection is not None:
                conn.close_if_unusable_or_obsolete()
                conn.close()
    except Exception:
        pass


def delete_proxy(request, proxy_id):
    """Delete a proxy server"""
    proxy = get_object_or_404(Proxy, id=proxy_id)
    
    # Store proxy info for message
    proxy_str = str(proxy)
    
    try:
        # Delete the proxy
        proxy.delete()
        messages.success(request, f'Proxy {proxy_str} deleted successfully.')
    except Exception as e:
        logger.error(f"Error deleting proxy {proxy_id}: {str(e)}")
        messages.error(request, f'Error deleting proxy: {str(e)}')
    
    return redirect('proxy_list')
