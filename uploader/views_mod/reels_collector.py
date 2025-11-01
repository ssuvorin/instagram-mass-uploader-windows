from .common import *

from django.views.decorators.http import require_http_methods
from django.core.files.uploadedfile import InMemoryUploadedFile
import threading
import django

from instgrapi_func.services.reels_collector_service import ReelsCollectorService
from instgrapi_func.services.code_providers import CompositeProvider, TOTPProvider, AutoIMAPEmailProvider


@login_required
@require_http_methods(["GET", "POST"])
def reels_collector(request):
    """UI: Select account and upload file with Instagram account URLs to collect reels links."""
    # Only superusers can access reels collector
    if not request.user.is_superuser:
        messages.error(request, 'Доступ запрещен. Только администраторы могут использовать сборщик reels.')
        return redirect('dashboard')
    
    accounts = InstagramAccount.objects.all().order_by('username')
    context = {
        'accounts': accounts,
        'active_tab': 'tools',
    }

    if request.method == 'GET':
        return render(request, 'uploader/reels_collector/collector.html', context)

    account_id = request.POST.get('account_id')
    uploaded_file = request.FILES.get('accounts_file')
    max_reels_per_account = request.POST.get('max_reels_per_account', '0')
    fast_mode = request.POST.get('fast_mode') == 'on'  # Checkbox for fast mode

    if not account_id:
        messages.error(request, 'Выберите аккаунт для аутентификации')
        return render(request, 'uploader/reels_collector/collector.html', context)

    if not uploaded_file:
        messages.error(request, 'Загрузите файл со ссылками на аккаунты')
        context['form_account_id'] = account_id
        return render(request, 'uploader/reels_collector/collector.html', context)

    account = get_object_or_404(InstagramAccount, id=account_id)

    # Parse uploaded file
    try:
        # Read file content
        if isinstance(uploaded_file, InMemoryUploadedFile):
            content = uploaded_file.read().decode('utf-8')
        else:
            content = uploaded_file.read().decode('utf-8')
        
        # Parse lines (one URL/username per line)
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        
        if not lines:
            messages.error(request, 'Файл пуст или не содержит валидных ссылок')
            context['form_account_id'] = account_id
            return render(request, 'uploader/reels_collector/collector.html', context)

    except Exception as e:
        messages.error(request, f'Ошибка чтения файла: {e}')
        context['form_account_id'] = account_id
        return render(request, 'uploader/reels_collector/collector.html', context)

    # Parse max_reels_per_account
    try:
        max_reels_per_account = int(max_reels_per_account) if max_reels_per_account else 0
    except ValueError:
        max_reels_per_account = 0

    # Generate output file paths before starting background task
    from datetime import datetime
    import os
    timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    output_file_path = os.path.join(project_root, f"reels_links_{timestamp_str}.txt")
    accounts_with_reels_file_path = os.path.join(project_root, f"accounts_with_reels_{timestamp_str}.txt")

    # Prepare data for background thread
    proxy_dict = None
    proxy = getattr(account, 'current_proxy', None) or getattr(account, 'proxy', None)
    if proxy:
        proxy_dict = proxy.to_dict()

    # Store account data for background thread (avoid passing Django model objects)
    account_username = account.username
    account_password = account.password
    account_tfa_secret = getattr(account, 'tfa_secret', None)
    account_email_username = getattr(account, 'email_username', None)
    account_email_password = getattr(account, 'email_password', None)

    # Run collection in background thread to avoid session timeout
    def run_collection_in_background():
        """Run collection in background thread"""
        try:
            # Ensure Django is configured for this thread
            import django
            from django.conf import settings
            if not settings.configured:
                os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'instagram_uploader.settings')
                django.setup()
            
            # Re-create provider in background thread
            provider = CompositeProvider([
                TOTPProvider(account_tfa_secret),
                AutoIMAPEmailProvider(account_email_username, account_email_password, on_log=None),
            ])
            
            # Re-create service in background thread
            service = ReelsCollectorService(provider=provider)
            logs: list[str] = []
            console = logging.getLogger('uploader.reels_collector')

            def on_log(msg: str):
                logs.append(msg)
                try:
                    console.info(msg)
                except Exception:
                    pass

            try:
                result = service.collect_reels_from_accounts(
                    account_username=account_username,
                    account_password=account_password,
                    target_usernames=lines,
                    proxy=proxy_dict,
                    on_log=on_log,
                    max_reels_per_account=max_reels_per_account,
                    fast_mode=fast_mode,
                )
                print(f"\n✅ Background collection completed successfully!")
                print(f"   📹 Total reels: {result.total_reels_links}")
                print(f"   ✅ Processed: {result.processed_accounts}")
                print(f"   ❌ Failed: {result.failed_accounts}")
            except Exception as e:
                print(f"\n❌ Background collection failed: {e}")
                console.error(f"Background collection failed: {e}", exc_info=True)
        except Exception as e:
            print(f"\n❌ Background thread error: {e}")
            logging.error(f"Background thread error: {e}", exc_info=True)

    # Start background thread
    thread = threading.Thread(target=run_collection_in_background, daemon=True)
    thread.start()

    # Return immediately with information about started task
    messages.success(request, f'Сбор reels запущен в фоновом режиме для {len(lines)} аккаунтов!')
    context.update({
        'task_started': True,
        'total_accounts': len(lines),
        'max_reels_per_account': max_reels_per_account,
        'fast_mode': fast_mode,
        'selected_account': account,
        'output_file_path': output_file_path,
        'accounts_with_reels_file_path': accounts_with_reels_file_path,
        'files_info': f"""
Файлы будут сохраняться в реальном времени:
• Ссылки на reels: {output_file_path}
• Аккаунты с reels: {accounts_with_reels_file_path}

Следите за выводом в консоли сервера для отслеживания прогресса.
        """.strip(),
    })
    return render(request, 'uploader/reels_collector/result.html', context)

