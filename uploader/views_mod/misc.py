"""Misc views."""
from .common import *
from django.conf import settings
from django.views.decorators.clickjacking import xframe_options_exempt

from django.views.decorators.csrf import csrf_exempt
import threading
import re
import ast
import time
import random
import os
import json
import logging

# Global top sites list (~500). Consider moving to JSON config if you want to customize without code edits.
_TOP_SITES_CACHE: list | None = None

# Logger for this module
logger = logging.getLogger(__name__)

def _load_top_sites_from_json() -> list:
    """Load top sites list from JSON. Path can be overridden via COOKIE_ROBOT_TOP_SITES_JSON env var."""
    try:
        # Compute default path: <project_root>/uploader/config/top_sites_500.json
        base_dir = getattr(settings, 'BASE_DIR', os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        default_path = os.path.join(base_dir, 'uploader', 'config', 'top_sites_500.json')
        json_path = os.environ.get('COOKIE_ROBOT_TOP_SITES_JSON', default_path)
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # Normalize and filter
        sites = [str(u).strip() for u in data if isinstance(u, str) and u.strip().startswith('http')]
        # Deduplicate while preserving order
        seen = set()
        uniq_sites = []
        for u in sites:
            if u not in seen:
                seen.add(u)
                uniq_sites.append(u)
        return uniq_sites
    except Exception as e:
        # Minimal fallback to avoid breaking tasks
        return [
            'https://google.com','https://youtube.com','https://facebook.com','https://twitter.com','https://instagram.com',
            'https://wikipedia.org','https://amazon.com','https://reddit.com','https://yahoo.com','https://bing.com'
        ]

def _get_top_sites() -> list:
    global _TOP_SITES_CACHE
    if _TOP_SITES_CACHE is None:
        _TOP_SITES_CACHE = _load_top_sites_from_json()
    return _TOP_SITES_CACHE

def _generate_urls_for_account(account_username: str, base_list: list, min_count: int = 28, max_count: int = 47) -> list:
    """Deterministically-random subset for per-account URL list to ensure distribution and stability per account."""
    try:
        seed = hash(account_username) & 0xffffffff
        rng = random.Random(seed)
        n = rng.randint(min_count, max_count)
        # Copy to avoid shuffling global list
        pool = list(base_list)
        rng.shuffle(pool)
        return pool[:n]
    except Exception:
        # Fallback to simple random choice
        count = random.randint(min_count, max_count)
        return random.sample(base_list, min(count, len(base_list)))

# Global semaphore for Cookie Robot concurrency (configurable via settings)
_COOKIE_ROBOT_SEMAPHORE = threading.Semaphore(getattr(settings, 'COOKIE_ROBOT_CONCURRENCY', 5))


def _extract_urls_from_log_text(log_text: str) -> list:
    """Robustly extract list of URLs from task log text.

    Supports lines like:
    - "[...timestamp...] [LIST] URLs to visit: ['https://a', 'https://b']"
    - "URLs: ['https://a', 'https://b']"

    Falls back to regex scanning for http(s) links if bracketed list parsing fails.
    """
    try:
        # Scan lines to find the one containing our URL list marker
        candidate_line = None
        for line in log_text.split('\n'):
            if 'URLs to visit:' in line:
                candidate_line = line
                break
        if not candidate_line:
            for line in log_text.split('\n'):
                if re.search(r'\bURLs\s*:', line):
                    candidate_line = line
                    break

        urls: list = []
        if candidate_line:
            # Take substring after the marker phrase, not the first colon (timestamps contain colons)
            if 'URLs to visit:' in candidate_line:
                after = candidate_line.split('URLs to visit:', 1)[1].strip()
            else:
                # Generic "URLs: ..."
                after = candidate_line.split('URLs', 1)[1]
                after = after.split(':', 1)[1].strip() if ':' in after else after.strip()

            # Try to isolate bracketed list [ ... ] on the same line
            lb = after.find('[')
            rb = after.rfind(']')
            bracket = after[lb:rb+1] if lb != -1 and rb != -1 and rb > lb else ''

            # Prefer parsing the bracketed list via ast.literal_eval
            if bracket:
                try:
                    parsed = ast.literal_eval(bracket)
                    if isinstance(parsed, (list, tuple)):
                        urls = [str(u).strip() for u in parsed if str(u).strip()]
                except Exception:
                    urls = []

            # Fallback: regex find all url-like substrings on the line
            if not urls:
                urls = re.findall(r'https?://[^\s\'",\]]+', candidate_line)

        # Final cleanup and dedup preserving order
        seen = set()
        cleaned = []
        for u in urls:
            if u and u not in seen:
                seen.add(u)
                cleaned.append(u)
        return cleaned
    except Exception:
        # Last resort: scan entire text for links
        return re.findall(r'https?://[^\s\'",\]]+', log_text)


def safe_log_message(message):
    """
    Remove or replace emoji characters that cause encoding issues on Windows
    """
    try:
        # Replace common emoji characters with safe alternatives
        emoji_replacements = {
            '[SEARCH]': '[SEARCH]',
            '[OK]': '[SUCCESS]',
            '[FAIL]': '[ERROR]',
            '[START]': '[START]',
            '[RETRY]': '[PROCESS]',
            '[WARN]': '[WARNING]',
            '[TOOL]': '[TOOL]',
            '🖼️': '[IMAGE]',
            '[CLIPBOARD]': '[LIST]',
            '[DELETE]': '[DELETE]',
            '📧': '[EMAIL]'
        }
        
        # Replace emoji characters with safe alternatives
        for emoji, replacement in emoji_replacements.items():
            message = message.replace(emoji, replacement)
        
        # Ensure the message only contains ASCII characters
        return message.encode('ascii', 'ignore').decode('ascii')
    except Exception:
        # If any error occurs, return a safe fallback
        return str(message).encode('ascii', 'ignore').decode('ascii')

def cookie_task_detail(request, task_id):
    """View details of a specific cookie robot task"""
    task = get_object_or_404(UploadTask, id=task_id)
    logger.info(f"Viewing Cookie Robot task detail for task ID: {task_id}")
    
    # Extract URLs from the log (robust against timestamps/colons)
    urls = _extract_urls_from_log_text(task.log)
    logger.info(f"Extracted {len(urls)} URLs from task {task_id} log")
    
    # Extract headless and imageless settings
    headless = 'Headless: True' in task.log
    imageless = 'Imageless: True' in task.log
    logger.info(f"Task {task_id} settings - Headless: {headless}, Imageless: {imageless}")
    
    context = {
        'task': task,
        'urls': urls,
        'headless': headless,
        'imageless': imageless,
        'active_tab': 'cookies'
    }
    return render(request, 'uploader/cookies/task_detail.html', context)

def cookie_dashboard(request):
    """Dashboard for cookie robot tasks"""
    # Get recent cookie tasks
    tasks = UploadTask.objects.filter(log__contains='Cookie Robot').order_by('-created_at')[:10]
    
    # Get all cookie robot tasks for statistics
    all_cookie_tasks = UploadTask.objects.filter(log__contains='Cookie Robot')
    
    # Get accounts with Dolphin profiles
    accounts_with_profiles = InstagramAccount.objects.filter(dolphin_profile_id__isnull=False).count()
    total_accounts = InstagramAccount.objects.count()
    
    # Task statistics by status
    task_stats = {
        'total': all_cookie_tasks.count(),
        'pending': all_cookie_tasks.filter(status='PENDING').count(),
        'running': all_cookie_tasks.filter(status='RUNNING').count(),
        'completed': all_cookie_tasks.filter(status='COMPLETED').count(),
        'failed': all_cookie_tasks.filter(status='FAILED').count(),
        'cancelled': all_cookie_tasks.filter(status='CANCELLED').count(),
    }
    
    # Calculate success rate
    finished_tasks = task_stats['completed'] + task_stats['failed'] + task_stats['cancelled']
    task_stats['success_rate'] = round((task_stats['completed'] / finished_tasks * 100) if finished_tasks > 0 else 0, 1)
    
    # Recent activity (last 24 hours)
    yesterday = timezone.now() - timedelta(days=1)
    recent_tasks = all_cookie_tasks.filter(created_at__gte=yesterday)
    
    recent_stats = {
        'total_24h': recent_tasks.count(),
        'completed_24h': recent_tasks.filter(status='COMPLETED').count(),
        'failed_24h': recent_tasks.filter(status='FAILED').count(),
        'running_24h': recent_tasks.filter(status='RUNNING').count(),
    }
    
    # Accounts usage statistics
    accounts_with_tasks = all_cookie_tasks.values('account').distinct().count()
    accounts_stats = {
        'with_tasks': accounts_with_tasks,
        'without_tasks': total_accounts - accounts_with_tasks,
        'usage_rate': round((accounts_with_tasks / total_accounts * 100) if total_accounts > 0 else 0, 1)
    }
    
    context = {
        'tasks': tasks,
        'accounts_with_profiles': accounts_with_profiles,
        'total_accounts': total_accounts,
        'task_stats': task_stats,
        'recent_stats': recent_stats,
        'accounts_stats': accounts_stats,
        'active_tab': 'cookies'
    }
    return render(request, 'uploader/cookies/dashboard.html', context)
def cookie_task_list(request):
    """List all cookie robot tasks"""
    tasks = UploadTask.objects.filter(log__contains='Cookie Robot').order_by('-created_at')
    
    context = {
        'tasks': tasks,
        'active_tab': 'cookies'
    }
    return render(request, 'uploader/cookies/task_list.html', context)
def start_cookie_task(request, task_id):
    """Start a cookie robot task"""
    task = get_object_or_404(UploadTask, id=task_id)
    
    if task.status != 'PENDING':
        messages.error(request, f'Task {task.id} is already {task.status}')
        return redirect('cookie_task_detail', task_id=task.id)
    
    # Extract URLs from the log (robust)
    urls = _extract_urls_from_log_text(task.log)
    
    # Extract headless and imageless settings
    headless = 'Headless: True' in task.log
    imageless = 'Imageless: True' in task.log
    
    # Start task in background thread
    thread = threading.Thread(target=run_cookie_robot_task, args=(task.id, urls, headless, imageless))
    thread.daemon = True
    thread.start()
    
    messages.success(request, f'Cookie Robot task {task.id} started!')
    return redirect('cookie_task_detail', task_id=task.id)
def account_cookies(request, account_id):
    """View cookies for a specific account"""
    account = get_object_or_404(InstagramAccount, id=account_id)
    
    # Get cookies from database
    cookies = InstagramCookies.objects.filter(account=account).order_by('-created_at').first()
    
    # Format cookies for display
    formatted_cookies = None
    if cookies and cookies.cookies_data:
        try:
            cookie_data = json.loads(cookies.cookies_data)
            formatted_cookies = json.dumps(cookie_data, indent=2)
        except Exception as e:
            logger.error(f"Error formatting cookies for account {account.username}: {str(e)}")
            formatted_cookies = cookies.cookies_data
    
    context = {
        'account': account,
        'cookies': cookies,
        'formatted_cookies': formatted_cookies,
        'active_tab': 'cookies'
    }
    return render(request, 'uploader/cookies/account_cookies.html', context)
def get_cookie_task_logs(request, task_id):
    """Get logs for a cookie robot task as JSON for AJAX updates"""
    task = get_object_or_404(UploadTask, id=task_id)
    
    # Extract URLs from the log for additional context (robust)
    urls = _extract_urls_from_log_text(task.log)
    
    # Extract headless and imageless settings
    headless = 'Headless: True' in task.log
    imageless = 'Imageless: True' in task.log
    
    response_data = {
        'status': task.status,
        'log': task.log,
        'updated_at': task.updated_at.isoformat() if task.updated_at else None,
        'urls': urls,
        'headless': headless,
        'imageless': imageless
    }
    
    return JsonResponse(response_data)
def stop_cookie_task(request, task_id):
    """Stop a running cookie robot task"""
    task = get_object_or_404(UploadTask, id=task_id)
    
    # Check if task is in a stoppable state
    if task.status not in ['RUNNING', 'PENDING']:
        messages.error(request, f'Cannot stop task {task.id} - it is {task.status}')
        # Return to referring page or task list if no referrer
        referrer = request.META.get('HTTP_REFERER')
        if referrer:
            return redirect(referrer)
        else:
            return redirect('cookie_task_list')
    
    try:
        # Update task status
        task.status = 'CANCELLED'
        
        # Add cancellation log entry
        cancellation_log = f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] 🛑 Task manually stopped by user\n"
        task.log += cancellation_log
        logger.info(f"Cookie Robot task {task.id} manually stopped by user")
        
        task.save()
        
        messages.success(request, f'Cookie Robot task {task.id} has been stopped')
        
    except Exception as e:
        logger.error(f"Error stopping Cookie Robot task {task.id}: {str(e)}")
        messages.error(request, f'Error stopping task: {str(e)}')
    
    # Return to referring page (task list, dashboard, etc.) or task detail if no referrer
    referrer = request.META.get('HTTP_REFERER')
    if referrer:
        return redirect(referrer)
    else:
        return redirect('cookie_task_detail', task_id=task.id)
def delete_cookie_task(request, task_id):
    """Delete a cookie robot task"""
    task = get_object_or_404(UploadTask, id=task_id)
    
    # Check if this is a Cookie Robot task
    if 'Cookie Robot' not in task.log:
        messages.error(request, 'This is not a Cookie Robot task')
        return redirect('cookie_task_list')
    
    if request.method == 'POST':
        # Check for force parameter
        force = request.POST.get('force') == '1'
        
        # If task is running and force is not set, show warning
        if task.status == 'RUNNING' and not force:
            messages.warning(request, 
                f'Task {task.id} is currently running. Are you sure you want to delete it?'
            )
            
            context = {
                'task': task,
                'confirm_delete': True,
                'active_tab': 'cookies'
            }
            return render(request, 'uploader/cookies/delete_task.html', context)
        
        try:
            # Store task info for message
            task_account = task.account.username if task.account else 'Unknown'
            task_number = task.id
            
            # Update status if running
            if task.status == 'RUNNING':
                task.status = 'CANCELLED'
                log_message = f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] [DELETE] Task deleted while running"
                safe_message = safe_log_message(log_message)
                task.log += safe_message + "\n"
                task.save()
            
            # Delete the task
            task.delete()
            
            logger.info(f"Cookie Robot task {task_number} for account {task_account} deleted")
            messages.success(request, f'Cookie Robot task {task_number} for account {task_account} deleted successfully')
            
        except Exception as e:
            logger.error(f"Error deleting Cookie Robot task {task_id}: {str(e)}")
            messages.error(request, f'Error deleting task: {str(e)}')
        
        return redirect('cookie_task_list')
    
    # GET request - show confirmation page
    context = {
        'task': task,
        'confirm_delete': False,
        'active_tab': 'cookies'
    }
    return render(request, 'uploader/cookies/delete_task.html', context)
def run_cookie_robot_task(task_id, urls, headless, imageless):
    """
    Run cookie robot task in background thread
    """
    from django.utils import timezone
    from uploader.models import InstagramAccount
    
    # Concurrency control: ensure not more than N tasks run simultaneously
    acquired = _COOKIE_ROBOT_SEMAPHORE.acquire(timeout=5)
    if not acquired:
        _COOKIE_ROBOT_SEMAPHORE.acquire()
    
    try:
        # Debug information
        logger.info(f"[COOKIE ROBOT TASK] Starting task {task_id}")
        logger.info(f"[COOKIE ROBOT TASK] URLs received: {urls}")
        logger.info(f"[COOKIE ROBOT TASK] Headless: {headless}")
        logger.info(f"[COOKIE ROBOT TASK] Imageless: {imageless}")
        
        # Get the task object
        task = UploadTask.objects.get(id=task_id)
        
        # Check if task was cancelled before starting
        if task.status == 'CANCELLED':
            logger.info(f"Cookie Robot task {task_id} was cancelled before execution")
            return
        
        # Get the associated account
        try:
            account = InstagramAccount.objects.get(id=task.account.id)
        except InstagramAccount.DoesNotExist:
            logger.error(f"Instagram account not found for task {task_id}")
            task.status = 'FAILED'
            task.log += "[ERROR] Instagram account not found\n"
            task.save()
            return
        
        # Check if account has a Dolphin profile
        if not account.dolphin_profile_id:
            error_msg = f"Account {account.username} does not have a Dolphin profile"
            logger.error(f"[COOKIE_ROBOT] {error_msg}")
            task.status = 'FAILED'
            task.log += f"[ERROR] {error_msg}\n"
            task.save()
            return
        
        # Get API token
        api_key = os.environ.get("DOLPHIN_API_TOKEN", "")
        if not api_key:
            error_msg = "Dolphin API token not found in environment variables"
            logger.error(f"[COOKIE_ROBOT] {error_msg}")
            task.status = 'FAILED'
            task.log += f"[ERROR] {error_msg}\n"
            task.save()
            return
        
        # Initialize Dolphin API client
        from bot.src.instagram_uploader.dolphin_anty import DolphinAnty
        
        # Get Dolphin API host from environment (critical for Docker Windows deployment)
        dolphin_api_host = os.environ.get("DOLPHIN_API_HOST", "http://localhost:3001/v1.0")
        if not dolphin_api_host.endswith("/v1.0"):
            dolphin_api_host = dolphin_api_host.rstrip("/") + "/v1.0"
        
        dolphin = DolphinAnty(api_key=api_key, local_api_base=dolphin_api_host)
        
        # Check Dolphin status before proceeding
        dolphin_status = dolphin.check_dolphin_status()
        if not dolphin_status.get("authenticated", False):
            error_msg = f"Dolphin Anty API not available: {dolphin_status.get('error', 'Unknown error')}"
            logger.error(f"[COOKIE_ROBOT] {error_msg}")
            task.status = 'FAILED'
            task.log += f"[ERROR] {error_msg}\n"
            task.log += f"[INFO] Please ensure Dolphin Anty is running and Local API is enabled on port 3001\n"
            task.save()
            return
        
        # Define logging function for the task
        def task_logger_func(message):
            try:
                # Обновляем статус задачи в реальном времени
                task.refresh_from_db()
                if task.status != 'CANCELLED':
                    task.log += f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}\n"
                    task.save()
                    logger.info(f"[TASK {task_id}] {message}")
            except Exception as e:
                logger.error(f"Error in task_logger_func: {str(e)}")
        
        # Ensure URLs: if none provided, generate per-account from top sites JSON
        try:
            if not urls:
                top_sites = _get_top_sites()
                if top_sites and len(top_sites) >= 100:
                    urls = _generate_urls_for_account(account.username, top_sites, 28, 47)
                    task_logger_func(f"[LIST] Auto-generated {len(urls)} URLs from top sites for account {account.username}")
        except Exception as gen_err:
            task_logger_func(f"[WARNING] URL auto-generation failed: {gen_err}")

        # Run the cookie robot
        log_message = f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] [START] Starting Cookie Robot on Dolphin profile {account.dolphin_profile_id}..."
        safe_message = safe_log_message(log_message)
        task.log += safe_message + "\n"
        logger.info(safe_message)
        
        # Обновляем статус на RUNNING
        task.status = 'RUNNING'
        task.save()
        
        # Добавляем информацию о параметрах
        task_logger_func(f"[INFO] Processing {len(urls)} URLs")
        task_logger_func(f"[INFO] Headless mode: {headless}")
        task_logger_func(f"[INFO] Disable images: {imageless}")
        task_logger_func(f"[INFO] Account: {account.username}")
        
        # Execute with internal retries for more robustness on profile start/connect failures
        result = None
        backoffs = [0, 2, 5]  # seconds
        for attempt, delay in enumerate(backoffs, start=1):
            if delay:
                time.sleep(delay)
            result = dolphin.run_cookie_robot_sync(
                profile_id=account.dolphin_profile_id,
                urls=urls,
                headless=headless,
                imageless=imageless,
                task_logger=task_logger_func
            )
            err = (result or {}).get('error') or ''
            # Break out if error is not start/connect related
            if not err or (
                'Failed to start profile' not in err and
                'Missing port or wsEndpoint' not in err and
                'connect_over_cdp' not in err
            ):
                break
            task_logger_func(f"[RETRY] Attempt {attempt} failed: {err}")
            # Best-effort stop profile between retries
            try:
                dolphin.stop_profile(account.dolphin_profile_id)
            except Exception:
                pass
        
        # Refresh task from database to get latest logs and check for cancellation
        task = UploadTask.objects.get(id=task_id)
        
        # If task was cancelled during execution, don't update status
        if task.status == 'CANCELLED':
            logger.info(f"Cookie Robot task {task_id} was cancelled during execution")
            return
        
        # Update task with result
        if result.get('success', False):
            task.status = 'COMPLETED'
            log_message = f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] [SUCCESS] Cookie Robot completed successfully!"
            safe_message = safe_log_message(log_message)
            task.log += safe_message + "\n"
            logger.info(safe_message)
            
            log_message = f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] Response details:"
            task.log += log_message + "\n"
            logger.info(log_message)
            
            response_json = json.dumps(result.get('data', {}), indent=2)
            task.log += response_json + "\n"
            logger.info(f"Response JSON: {response_json}")
            
            # Export cookies to database after successful cookie robot execution
            try:
                cookies_list = dolphin.get_cookies(account.dolphin_profile_id) or []
                if cookies_list:
                    from uploader.models import InstagramCookies
                    InstagramCookies.objects.update_or_create(
                        account=account,
                        defaults={
                            'cookies_data': cookies_list,
                            'is_valid': True,
                        }
                    )
                    log_message = f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] [COOKIES] Exported {len(cookies_list)} cookies to database for {account.username}"
                    safe_message = safe_log_message(log_message)
                    task.log += safe_message + "\n"
                    logger.info(safe_message)
                else:
                    log_message = f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] [COOKIES] No cookies found for {account.username}"
                    safe_message = safe_log_message(log_message)
                    task.log += safe_message + "\n"
                    logger.warning(safe_message)
            except Exception as e:
                log_message = f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] [COOKIES] Failed to export cookies for {account.username}: {e}"
                safe_message = safe_log_message(log_message)
                task.log += safe_message + "\n"
                logger.error(safe_message)
        else:
            error_details = result.get('error', 'Unknown error')
            
            # Check if it's a human verification error
            if error_details == 'HUMAN_VERIFICATION_REQUIRED':
                task.status = 'FAILED'
                log_message = f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] Human verification required for this account"
                safe_message = safe_log_message(log_message)
                task.log += safe_message + "\n"
                logger.error(safe_message)
                
                # Update the Instagram account status
                try:
                    instagram_account = InstagramAccount.objects.get(username=account.username)
                    instagram_account.status = 'HUMAN_VERIFICATION_REQUIRED'
                    instagram_account.save()
                    
                    log_message = f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] Updated account {account.username} status to HUMAN_VERIFICATION_REQUIRED"
                    safe_message = safe_log_message(log_message)
                    task.log += safe_message + "\n"
                    logger.info(safe_message)
                except Exception as update_error:
                    log_message = f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] [WARNING] Could not update account status: {str(update_error)}"
                    safe_message = safe_log_message(log_message)
                    task.log += safe_message + "\n"
                    logger.warning(safe_message)
            else:
                task.status = 'FAILED'
                log_message = f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] Cookie Robot failed: {error_details}"
                safe_message = safe_log_message(log_message)
                task.log += safe_message + "\n"
                logger.error(safe_message)
                
                # Add full error details if available
                if isinstance(error_details, dict):
                    error_json = json.dumps(error_details, indent=2)
                    task.log += f"Full error details:\n{error_json}\n"
                    logger.error(f"Full API error: {error_json}")
        
        task.save()
        
    except Exception as e:
        # Check if task was cancelled
        task.refresh_from_db()
        if task.status == 'CANCELLED':
            logger.info(f"Cookie Robot task {task_id} was cancelled during exception handling")
            return
            
        task.status = 'FAILED'
        log_message = f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] Exception occurred: {str(e)}"
        safe_message = safe_log_message(log_message)
        task.log += safe_message + "\n"
        logger.error(safe_message)
        
        stack_trace = traceback.format_exc()
        task.log += stack_trace
        logger.error(f"Stack trace: {stack_trace}")
        
        task.save()
    finally:
        # Release semaphore to allow next task to start
        try:
            _COOKIE_ROBOT_SEMAPHORE.release()
        except Exception:
            pass
def bulk_cookie_robot(request):
    """Create and run Cookie Robot tasks on multiple accounts"""
    if request.method == 'POST':
        # Get selected accounts
        account_ids = request.POST.getlist('accounts')
        # URLs field deprecated in bulk UI; keep parsing if present for API compatibility
        urls_text = request.POST.get('urls', '')
        headless = request.POST.get('headless', '') == 'on'
        imageless = request.POST.get('imageless', '') == 'on'
        
        # Parse URLs
        urls = [url.strip() for url in urls_text.split('\n') if url.strip()]
        
        # Debug information
        logger.info(f"[BULK COOKIE ROBOT] Received request:")
        logger.info(f"[BULK COOKIE ROBOT] Account IDs: {account_ids}")
        logger.info(f"[BULK COOKIE ROBOT] URLs text length: {len(urls_text)}")
        logger.info(f"[BULK COOKIE ROBOT] Parsed URLs: {urls}")
        logger.info(f"[BULK COOKIE ROBOT] Headless: {headless}")
        logger.info(f"[BULK COOKIE ROBOT] Imageless: {imageless}")
        
        if not account_ids:
            messages.error(request, 'Please select at least one account')
            return redirect('bulk_cookie_robot')
        
        # If URLs empty, per-account lists will be auto-generated later in run_cookie_robot_task
        
        # Create tasks for each account
        created_tasks = []
        for account_id in account_ids:
            try:
                account = InstagramAccount.objects.get(id=account_id)
                
                # Skip accounts without Dolphin profile
                if not account.dolphin_profile_id:
                    messages.warning(request, f'Account {account.username} skipped: No Dolphin profile')
                    continue
                
                # Create task
                initial_log = f"Cookie Robot Task\n"
                log_message = f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] [SUCCESS] Task created for account: {account.username}"
                safe_message = safe_log_message(log_message)
                initial_log += safe_message + "\n"
                logger.info(safe_message)
                
                if urls:
                    log_message = f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] [LIST] URLs to visit: {urls}"
                else:
                    log_message = f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] [LIST] URLs: auto-generate per account from global top sites (28–47)"
                safe_message = safe_log_message(log_message)
                initial_log += safe_message + "\n"
                logger.info(safe_message)
                
                log_message = f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] [TOOL] Headless mode: {headless}"
                safe_message = safe_log_message(log_message)
                initial_log += safe_message + "\n"
                logger.info(safe_message)
                
                log_message = f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] [IMAGE] Disable images: {imageless}"
                safe_message = safe_log_message(log_message)
                initial_log += safe_message + "\n"
                logger.info(safe_message)
                
                task = UploadTask.objects.create(
                    account=account,
                    status='PENDING',
                    log=initial_log
                )
                
                created_tasks.append(task)
                
            except InstagramAccount.DoesNotExist:
                messages.error(request, f'Account with ID {account_id} not found')
            except Exception as e:
                messages.error(request, f'Error creating task: {str(e)}')
        
        # Start tasks in background (concurrency limited by semaphore)
        if created_tasks:
            messages.success(request, f'Created {len(created_tasks)} Cookie Robot tasks')
            
            # Start tasks in background
            for task in created_tasks:
                thread = threading.Thread(target=run_cookie_robot_task, args=(task.id, urls, headless, imageless))
                thread.daemon = True
                thread.start()
                logger.info(f"Started Cookie Robot task {task.id} for account {task.account.username}")
                
            return redirect('cookie_task_list')
        else:
            messages.error(request, 'No tasks were created')
            return redirect('bulk_cookie_robot')
    
    # GET request - show form
    # Get accounts with Dolphin profiles - sort by creation date descending (newest first)
    accounts = InstagramAccount.objects.filter(dolphin_profile_id__isnull=False).order_by('-created_at')
    # Enrich accounts with proxy/cookies summaries for UI
    try:
        for acc in accounts:
            # Proxy flags (prefer current_proxy if present)
            proxy = getattr(acc, 'current_proxy', None) or getattr(acc, 'proxy', None)
            acc.ui_has_proxy = bool(proxy)
            acc.ui_proxy_active = bool(getattr(proxy, 'is_active', False))
            acc.ui_proxy_status = getattr(proxy, 'status', '') or ''
            try:
                acc.ui_proxy_host_port = f"{getattr(proxy, 'host', '')}:{getattr(proxy, 'port', '')}" if proxy else ''
            except Exception:
                acc.ui_proxy_host_port = ''
            # Cookies summary
            cookies_obj = getattr(acc, 'cookies', None)
            cookies_list = list(getattr(cookies_obj, 'cookies_data', []) or [])
            domain_set = set()
            instagram_session_active = False
            for c in cookies_list:
                try:
                    dom = str(c.get('domain') or '').lstrip('.')
                    if dom:
                        domain_set.add(dom)
                    if dom.endswith('instagram.com') and (c.get('name') or '').lower() == 'sessionid':
                        val = c.get('value') or ''
                        if isinstance(val, str) and len(val) >= 10:
                            instagram_session_active = True
                except Exception:
                    continue
            acc.ui_cookie_domains = len(domain_set)
            acc.ui_cookie_total = len(cookies_list)
            acc.ui_instagram_session = instagram_session_active
            # Mobile session (instagrapi settings) presence
            try:
                device = getattr(acc, 'device', None)
                acc.ui_mobile_session_present = bool(getattr(device, 'session_settings', None))
            except Exception:
                acc.ui_mobile_session_present = False
    except Exception as _enrich_err:
        logger.warning(f"[BULK COOKIE ROBOT] Could not enrich accounts with cookie summaries: {_enrich_err}")
    
    # Default URLs for the form
    default_urls = [
        "https://google.com",
        "https://yandex.ru",
        "https://vk.com",
        "https://twitter.com",
        "https://t.me",
        "https://youtube.com",
        "https://twitch.tv",
        "https://amazon.com",
        "https://ozon.ru",
        "https://wildberries.ru",
        "https://aliexpress.com",
        "https://ebay.com",
        "https://walmart.com",
        "https://etsy.com",
        "https://booking.com",
        "https://airbnb.com",
        "https://netflix.com",
        "https://hulu.com",
        "https://spotify.com",
        "https://apple.com",
        "https://microsoft.com",
        "https://github.com",
        "https://gitlab.com",
        "https://stackoverflow.com",
        "https://medium.com",
        "https://reddit.com",
        "https://quora.com",
        "https://cnn.com",
        "https://bbc.com",
        "https://theguardian.com",
        "https://forbes.com",
        "https://bloomberg.com",
        "https://techcrunch.com",
        "https://cnet.com",
        "https://w3schools.com",
        "https://udemy.com",
        "https://coursera.org",
        "https://linkedin.com",
        "https://wikipedia.org"
    ]
    
    context = {
        'accounts': accounts,
        'default_urls': '\n'.join(default_urls),
        'active_tab': 'cookies'
    }
    return render(request, 'uploader/cookies/bulk_cookie_robot.html', context)

def refresh_cookies_from_profiles(request):
    """Fetch and persist cookies from Dolphin profiles into DB and return to bulk page."""
    if request.method != 'POST':
        return redirect('bulk_cookie_robot')

    try:
        from bot.src.instagram_uploader.dolphin_anty import DolphinAnty
    except Exception as e:
        messages.error(request, f'Dolphin API client not available: {e}')
        return redirect('bulk_cookie_robot')

    # Read Dolphin API settings
    # Accept both env var names to match different setups
    api_key = os.environ.get('DOLPHIN_API_TOKEN') or os.environ.get('TOKEN') or ''
    if not api_key:
        messages.error(request, 'DOLPHIN_API_TOKEN is not configured. Cannot refresh cookies.')
        return redirect('bulk_cookie_robot')
    dolphin_api_host = os.environ.get('DOLPHIN_API_HOST', 'http://localhost:3001/v1.0')
    if not dolphin_api_host.endswith('/v1.0'):
        dolphin_api_host = dolphin_api_host.rstrip('/') + '/v1.0'

    # Determine target accounts: selected IDs if provided, otherwise all with profiles
    selected_ids = request.POST.getlist('accounts')
    qs = InstagramAccount.objects.filter(dolphin_profile_id__isnull=False)
    if selected_ids:
        qs = qs.filter(id__in=selected_ids)
    accounts = list(qs)
    if not accounts:
        messages.warning(request, 'No accounts with Dolphin profiles selected/found.')
        return redirect('bulk_cookie_robot')

    # Initialize client with working Sync API
    dolphin_local = DolphinAnty(api_key=api_key, local_api_base=dolphin_api_host)

    refreshed = 0
    errors = 0
    total_cookies = 0

    for acc in accounts:
        pid = acc.dolphin_profile_id
        try:
            # Use only the working Sync API method
            cookies_list = dolphin_local.get_cookies(pid) or []
            # Persist only if list is a list of dicts
            if isinstance(cookies_list, list):
                InstagramCookies.objects.update_or_create(
                    account=acc,
                    defaults={'cookies_data': cookies_list, 'is_valid': True}
                )
                refreshed += 1
                total_cookies += len(cookies_list)
            else:
                errors += 1
        except Exception as e:
            logger.warning(f"[COOKIES][REFRESH] Failed for {acc.username}/{pid}: {e}")
            errors += 1

    if refreshed:
        messages.success(request, f'Refreshed cookies for {refreshed} accounts (total cookies: {total_cookies}).')
    if errors:
        messages.warning(request, f'Failed to refresh {errors} accounts. Check logs and Dolphin API connectivity.')

    return redirect('bulk_cookie_robot')
def create_dolphin_profile(request, account_id):
    """Create a Dolphin profile for an existing account"""
    account = get_object_or_404(InstagramAccount, id=account_id)
    
    # Check if account already has a Dolphin profile
    if account.dolphin_profile_id:
        messages.warning(request, f'Account {account.username} already has a Dolphin profile: {account.dolphin_profile_id}')
        return redirect('account_detail', account_id=account.id)
    
    # Check if account has a proxy
    if not account.proxy:
        messages.error(request, f'Account {account.username} needs a proxy before creating a Dolphin profile. Please assign a proxy first.')
        return redirect('change_account_proxy', account_id=account.id)
    
    # Read UI params
    proxy_selection = request.POST.get('proxy_selection', 'locale_only') if request.method == 'POST' else 'locale_only'
    selected_locale = request.POST.get('profile_locale', 'ru_BY') if request.method == 'POST' else 'ru_BY'
    if selected_locale != 'ru_BY':
        selected_locale = 'ru_BY'
    
    try:
        logger.info(f"[CREATE PROFILE] Creating Dolphin profile for account {account.username}")
        
        # Initialize Dolphin API
        api_key = os.environ.get("DOLPHIN_API_TOKEN", "")
        if not api_key:
            logger.error("[CREATE PROFILE] Dolphin API token not found in environment variables")
            messages.error(request, "Dolphin API token not configured. Please set DOLPHIN_API_TOKEN environment variable.")
            return redirect('account_detail', account_id=account.id)
        
        # Get Dolphin API host from environment (critical for Docker Windows deployment)
        dolphin_api_host = os.environ.get("DOLPHIN_API_HOST", "http://localhost:3001/v1.0")
        if not dolphin_api_host.endswith("/v1.0"):
            dolphin_api_host = dolphin_api_host.rstrip("/") + "/v1.0"
        
        dolphin = DolphinAnty(api_key=api_key, local_api_base=dolphin_api_host)
        
        # Authenticate with Dolphin
        if not dolphin.authenticate():
            logger.error("[CREATE PROFILE] Failed to authenticate with Dolphin Anty API")
            messages.error(request, "Failed to authenticate with Dolphin Anty API. Check your API token.")
            return redirect('account_detail', account_id=account.id)
        
        # Optionally reassign proxy to locale-only BY
        if request.method == 'POST' and proxy_selection == 'locale_only':
            proxy_country = (account.proxy.country or '').strip() if account.proxy else ''
            is_by = proxy_country.upper() == 'BY' or 'belarus' in proxy_country.lower()
            if not is_by:
                available_proxies = Proxy.objects.filter(is_active=True, assigned_account__isnull=True)
                by_proxies = available_proxies.filter(
                    Q(country__iexact='BY') | Q(country__icontains='Belarus') | Q(city__icontains='Belarus')
                )
                if by_proxies.exists():
                    new_proxy = by_proxies.order_by('?').first()
                    # Assign
                    account.proxy = new_proxy
                    account.current_proxy = new_proxy
                    account.save(update_fields=['proxy', 'current_proxy'])
                    new_proxy.assigned_account = account
                    new_proxy.save(update_fields=['assigned_account'])
                    logger.info(f"[CREATE PROFILE] Reassigned proxy to BY-only {new_proxy} for account {account.username}")
                else:
                    messages.warning(request, 'No available BY proxies found; using current proxy.')
        
        # Create profile name
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
        profile_name = f"instagram_{account.username}_{random_suffix}"
        logger.info(f"[CREATE PROFILE] Creating Dolphin profile '{profile_name}'")
        
        # Get proxy data
        proxy_data = account.proxy.to_dict()
        logger.info(f"[CREATE PROFILE] Using proxy: {proxy_data.get('host')}:{proxy_data.get('port')}")
        
        # Create Dolphin profile
        response = dolphin.create_profile(
            name=profile_name,
            proxy=proxy_data,
            tags=["instagram", "manual-created"],
            locale=selected_locale
        )
        
        # Extract profile ID from response
        profile_id = None
        if response and isinstance(response, dict):
            profile_id = response.get("browserProfileId")
            if not profile_id and isinstance(response.get("data"), dict):
                profile_id = response["data"].get("id")
        
        if profile_id:
            # Save profile ID to account
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
                logger.warning(f"[CREATE PROFILE] Could not save Dolphin snapshot: {snap_err}")
            
            logger.info(f"[CREATE PROFILE] Successfully created Dolphin profile {profile_id} for account {account.username}")
            messages.success(request, f'Dolphin profile {profile_id} created successfully for account {account.username}!')
        else:
            error_message = response.get("error", "Unknown error") if isinstance(response, dict) else "Unknown error"
            logger.error(f"[CREATE PROFILE] Failed to create Dolphin profile: {error_message}")
            messages.error(request, f'Failed to create Dolphin profile: {error_message}')
    
    except Exception as e:
        logger.error(f"[CREATE PROFILE] Error creating Dolphin profile for account {account.username}: {str(e)}")
        messages.error(request, f'Error creating Dolphin profile: {str(e)}')
    
    return redirect('account_detail', account_id=account.id)
def edit_video_location_mentions(request, video_id):
    """Edit location and mentions for a specific video"""
    video = get_object_or_404(BulkVideo, id=video_id)
    task = video.bulk_task
    
    # Check if task is still editable
    if task.status not in ['PENDING']:
        messages.error(request, f'Cannot edit video in task "{task.name}" as it is already {task.status}')
        return redirect('bulk_upload_detail', task_id=task.id)
    
    if request.method == 'POST':
        form = BulkVideoLocationMentionsForm(request.POST, instance=video)
        if form.is_valid():
            form.save()
            messages.success(request, f'Location and mentions updated for video {video.id}')
            return redirect('bulk_upload_detail', task_id=task.id)
    else:
        form = BulkVideoLocationMentionsForm(instance=video)
    
    context = {
        'form': form,
        'video': video,
        'task': task,
        'active_tab': 'bulk_upload'
    }
    return render(request, 'uploader/bulk_upload/edit_video_location_mentions.html', context)
def bulk_edit_location_mentions(request, task_id):
    """Bulk edit location and mentions for all videos in a task"""
    task = get_object_or_404(BulkUploadTask, id=task_id)
    
    # Check if task is still editable
    if task.status not in ['PENDING']:
        messages.error(request, f'Cannot edit videos in task "{task.name}" as it is already {task.status}')
        return redirect('bulk_upload_detail', task_id=task.id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        location = request.POST.get('location', '').strip()
        mentions = request.POST.get('mentions', '').strip()
        
        if action == 'apply_to_all':
            # Apply to all videos
            videos = task.videos.all()
            updated_count = 0
            for video in videos:
                video.location = location
                video.mentions = mentions
                video.save(update_fields=['location', 'mentions'])
                updated_count += 1
            
            messages.success(request, f'Location and mentions updated for {updated_count} videos')
            
        elif action == 'apply_to_selected':
            # Apply to selected videos
            selected_video_ids = request.POST.getlist('selected_videos')
            if selected_video_ids:
                videos = task.videos.filter(id__in=selected_video_ids)
                updated_count = 0
                for video in videos:
                    video.location = location
                    video.mentions = mentions
                    video.save(update_fields=['location', 'mentions'])
                    updated_count += 1
                
                messages.success(request, f'Location and mentions updated for {updated_count} selected videos')
            else:
                messages.warning(request, 'No videos selected')
        
        return redirect('bulk_upload_detail', task_id=task.id)
    
    videos = task.videos.all()
    
    context = {
        'task': task,
        'videos': videos,
        'active_tab': 'bulk_upload'
    }
    return render(request, 'uploader/bulk_upload/bulk_edit_location_mentions.html', context)
def bulk_change_proxy(request):
    """Bulk change proxies for multiple accounts"""
    if request.method == 'POST':
        account_ids = request.POST.getlist('account_ids')
        action = request.POST.get('action')
        
        if not account_ids:
            messages.error(request, 'No accounts selected')
            return redirect('account_list')
        
        accounts = InstagramAccount.objects.filter(id__in=account_ids)
        
        if action == 'auto_assign':
            # Auto-assign available proxies to selected accounts
            # Try to match regions when possible
            available_proxies = list(Proxy.objects.filter(
                assigned_account__isnull=True,
                is_active=True
            ).order_by('host', 'port'))
            
            if len(available_proxies) < len(accounts):
                messages.warning(request, f'Only {len(available_proxies)} proxies available for {len(accounts)} accounts. Some accounts will not get a proxy.')
            
            success_count = 0
            error_count = 0
            region_mismatch_count = 0
            
            for account in accounts:
                if not available_proxies:
                    # No more proxies available
                    break
                    
                proxy = None
                old_proxy = account.proxy
                
                # Try to find a proxy from the same region first if account has a proxy with region
                if old_proxy and old_proxy.country:
                    same_region_proxies = [p for p in available_proxies if p.country == old_proxy.country]
                    if same_region_proxies:
                        proxy = same_region_proxies[0]
                        available_proxies.remove(proxy)
                        logger.info(f"[BULK CHANGE] Found same region proxy for {account.username}: {old_proxy.country}")
                    else:
                        # No same region proxy available, use any available proxy (force)
                        proxy = available_proxies.pop(0)
                        region_mismatch_count += 1
                        logger.warning(f"[BULK CHANGE] No same region proxy for {account.username}, using different region: {old_proxy.country} -> {proxy.country if proxy.country else 'Unknown'}")
                else:
                    # Account has no region info or no current proxy, just assign any available proxy
                    proxy = available_proxies.pop(0)
                
                if proxy:
                    try:
                        # Update account proxy - update both proxy and current_proxy fields
                        account.proxy = proxy
                        account.current_proxy = proxy
                        account.save(update_fields=['proxy', 'current_proxy'])
                        
                        # Update proxy assignment
                        proxy.assigned_account = account
                        proxy.save(update_fields=['assigned_account'])
                        
                        # Clear old proxy assignment
                        if old_proxy:
                            old_proxy.assigned_account = None
                            old_proxy.save(update_fields=['assigned_account'])
                        
                        # Update Dolphin profile if exists
                        if account.dolphin_profile_id:
                            try:
                                api_key = os.environ.get("DOLPHIN_API_TOKEN", "")
                                if api_key:
                                    from bot.src.instagram_uploader.dolphin_anty import DolphinAnty
                                    dolphin = DolphinAnty(api_key=api_key)
                                    
                                    if dolphin.authenticate():
                                        proxy_data = proxy.to_dict()
                                        result = dolphin.update_profile_proxy(account.dolphin_profile_id, proxy_data)
                                        
                                        if not result.get("success"):
                                            logger.warning(f"[BULK CHANGE] Failed to update Dolphin profile {account.dolphin_profile_id} for account {account.username}")
                            except Exception as e:
                                logger.error(f"[BULK CHANGE] Error updating Dolphin profile for account {account.username}: {str(e)}")
                        
                        success_count += 1
                        region_info = ""
                        if old_proxy and old_proxy.country and proxy.country:
                            if old_proxy.country != proxy.country:
                                region_info = f" (region changed: {old_proxy.country} -> {proxy.country})"
                            else:
                                region_info = f" (same region: {old_proxy.country})"
                        logger.info(f"[BULK CHANGE] Successfully assigned proxy {proxy} to account {account.username}{region_info}")
                        
                    except Exception as e:
                        error_count += 1
                        logger.error(f"[BULK CHANGE] Error assigning proxy to account {account.username}: {str(e)}")
            
            success_message = f'Successfully assigned proxies to {success_count} accounts'
            if region_mismatch_count > 0:
                success_message += f' ({region_mismatch_count} accounts got different region proxies due to availability)'
            if success_count > 0:
                messages.success(request, success_message)
            if error_count > 0:
                messages.error(request, f'Failed to assign proxies to {error_count} accounts')
                
        elif action == 'remove_all':
            # Remove proxies from all selected accounts - clear both proxy and current_proxy fields
            success_count = 0
            error_count = 0
            
            for account in accounts:
                try:
                    old_proxy = account.proxy
                    account.proxy = None
                    account.current_proxy = None
                    account.save(update_fields=['proxy', 'current_proxy'])
                    
                    if old_proxy:
                        old_proxy.assigned_account = None
                        old_proxy.save(update_fields=['assigned_account'])
                    
                    success_count += 1
                    logger.info(f"[BULK CHANGE] Successfully removed proxy from account {account.username}")
                    
                except Exception as e:
                    error_count += 1
                    logger.error(f"[BULK CHANGE] Error removing proxy from account {account.username}: {str(e)}")
            
            if success_count > 0:
                messages.success(request, f'Successfully removed proxies from {success_count} accounts')
            if error_count > 0:
                messages.error(request, f'Failed to remove proxies from {error_count} accounts')
        
        return redirect('account_list')
    
    # GET request - show form
    accounts = InstagramAccount.objects.all().order_by('username')
    available_proxies_count = Proxy.objects.filter(
        assigned_account__isnull=True,
        is_active=True
    ).count()
    
    context = {
        'accounts': accounts,
        'available_proxies_count': available_proxies_count,
        'active_tab': 'accounts'
    }
    return render(request, 'uploader/bulk_change_proxy.html', context)
def refresh_dolphin_proxies(request):
    """Refresh proxies in all Dolphin profiles to match current account proxy assignments"""
    if request.method == 'POST':
        # Get all accounts with Dolphin profiles and proxies
        accounts_with_profiles = InstagramAccount.objects.filter(
            dolphin_profile_id__isnull=False,
            proxy__isnull=False
        )
        
        if not accounts_with_profiles.exists():
            messages.warning(request, 'No accounts found with both Dolphin profiles and assigned proxies')
            return redirect('account_list')
        
        # Initialize Dolphin API
        api_key = os.environ.get("DOLPHIN_API_TOKEN", "")
        if not api_key:
            messages.error(request, 'Dolphin API token not configured. Please set DOLPHIN_API_TOKEN environment variable.')
            return redirect('account_list')
        
        try:
            from bot.src.instagram_uploader.dolphin_anty import DolphinAnty
            dolphin = DolphinAnty(api_key=api_key)
            
            if not dolphin.authenticate():
                messages.error(request, 'Failed to authenticate with Dolphin Anty API. Check your API token.')
                return redirect('account_list')
            
            success_count = 0
            error_count = 0
            
            for account in accounts_with_profiles:
                try:
                    proxy_data = account.proxy.to_dict()
                    result = dolphin.update_profile_proxy(account.dolphin_profile_id, proxy_data)
                    
                    if result.get("success"):
                        success_count += 1
                        logger.info(f"[REFRESH PROXIES] Successfully updated Dolphin profile {account.dolphin_profile_id} for account {account.username}")
                    else:
                        error_count += 1
                        error_msg = result.get("error", "Unknown error")
                        logger.error(f"[REFRESH PROXIES] Failed to update Dolphin profile {account.dolphin_profile_id} for account {account.username}: {error_msg}")
                        
                except Exception as e:
                    error_count += 1
                    logger.error(f"[REFRESH PROXIES] Error updating Dolphin profile for account {account.username}: {str(e)}")
            
            if success_count > 0:
                messages.success(request, f'Successfully updated {success_count} Dolphin profiles')
            if error_count > 0:
                messages.error(request, f'Failed to update {error_count} Dolphin profiles')
                
        except Exception as e:
            logger.error(f"[REFRESH PROXIES] Error initializing Dolphin API: {str(e)}")
            messages.error(request, f'Error connecting to Dolphin API: {str(e)}')
        
        return redirect('account_list')
    
    # GET request - show confirmation
    accounts_with_profiles = InstagramAccount.objects.filter(
        dolphin_profile_id__isnull=False,
        proxy__isnull=False
    ).order_by('username')
    
    context = {
        'accounts_with_profiles': accounts_with_profiles,
        'active_tab': 'accounts'
    }
    return render(request, 'uploader/refresh_dolphin_proxies.html', context)
def cleanup_inactive_proxies(request):
    """Clean up inactive proxies with options to handle assigned accounts"""
    if request.method == 'POST':
        action = request.POST.get('action')
        
        # Get inactive proxies
        inactive_proxies = Proxy.objects.filter(
            Q(status='inactive') | Q(is_active=False)
        )
        
        if not inactive_proxies.exists():
            messages.info(request, 'No inactive proxies found to clean up')
            return redirect('proxy_list')
        
        # Get accounts that would be affected
        affected_accounts = InstagramAccount.objects.filter(
            proxy__in=inactive_proxies
        )
        
        if action == 'delete_only_unassigned':
            # Delete only unassigned inactive proxies
            unassigned_inactive = inactive_proxies.filter(assigned_account__isnull=True)
            deleted_count = unassigned_inactive.count()
            unassigned_inactive.delete()
            
            messages.success(request, f'Deleted {deleted_count} unassigned inactive proxies')
            if affected_accounts.exists():
                messages.warning(request, f'{affected_accounts.count()} accounts still have inactive proxies assigned')
        
        elif action == 'reassign_and_delete':
            # Try to reassign accounts to active proxies, then delete inactive ones
            # First, try to match regions when possible
            available_active_proxies = list(Proxy.objects.filter(
                status='active',
                is_active=True,
                assigned_account__isnull=True
            ).order_by('host', 'port'))
            
            reassigned_count = 0
            unassigned_count = 0
            region_mismatch_count = 0
            
            # Initialize Dolphin API for updating profiles
            api_key = os.environ.get("DOLPHIN_API_TOKEN", "")
            dolphin = None
            if api_key:
                try:
                    from bot.src.instagram_uploader.dolphin_anty import DolphinAnty
                    dolphin = DolphinAnty(api_key=api_key)
                    if not dolphin.authenticate():
                        dolphin = None
                        logger.warning("[CLEANUP] Failed to authenticate with Dolphin API")
                except Exception as e:
                    logger.error(f"[CLEANUP] Error initializing Dolphin API: {str(e)}")
                    dolphin = None
            
            for account in affected_accounts:
                if not available_active_proxies:
                    # No more active proxies available
                    account.proxy = None
                    account.current_proxy = None
                    account.save(update_fields=['proxy', 'current_proxy'])
                    unassigned_count += 1
                    logger.warning(f"[CLEANUP] No active proxy available for account {account.username}, removed proxy assignment")
                    continue
                
                old_proxy = account.proxy
                new_proxy = None
                
                # Try to find a proxy from the same region first
                if old_proxy and old_proxy.country:
                    same_region_proxies = [p for p in available_active_proxies if p.country == old_proxy.country]
                    if same_region_proxies:
                        new_proxy = same_region_proxies[0]
                        available_active_proxies.remove(new_proxy)
                        logger.info(f"[CLEANUP] Found same region proxy for {account.username}: {old_proxy.country}")
                    else:
                        # No same region proxy available, use any available proxy (force)
                        new_proxy = available_active_proxies.pop(0)
                        region_mismatch_count += 1
                        logger.warning(f"[CLEANUP] No same region proxy for {account.username}, using different region: {old_proxy.country} -> {new_proxy.country if new_proxy.country else 'Unknown'}")
                else:
                    # Account has no region info, just assign any available proxy
                    new_proxy = available_active_proxies.pop(0)
                
                if new_proxy:
                    try:
                        # Update account - update both proxy and current_proxy fields
                        account.proxy = new_proxy
                        account.current_proxy = new_proxy
                        account.save(update_fields=['proxy', 'current_proxy'])
                        
                        # Update proxy assignment
                        new_proxy.assigned_account = account
                        new_proxy.save(update_fields=['assigned_account'])
                        
                        # Update Dolphin profile if exists
                        if account.dolphin_profile_id and dolphin:
                            try:
                                proxy_data = new_proxy.to_dict()
                                result = dolphin.update_profile_proxy(account.dolphin_profile_id, proxy_data)
                                if not result.get("success"):
                                    logger.warning(f"[CLEANUP] Failed to update Dolphin profile {account.dolphin_profile_id}")
                            except Exception as e:
                                logger.error(f"[CLEANUP] Error updating Dolphin profile for {account.username}: {str(e)}")
                        
                        reassigned_count += 1
                        region_info = ""
                        if old_proxy and old_proxy.country and new_proxy.country:
                            if old_proxy.country != new_proxy.country:
                                region_info = f" (region changed: {old_proxy.country} -> {new_proxy.country})"
                            else:
                                region_info = f" (same region: {old_proxy.country})"
                        logger.info(f"[CLEANUP] Reassigned account {account.username} from {old_proxy} to {new_proxy}{region_info}")
                        
                    except Exception as e:
                        logger.error(f"[CLEANUP] Error reassigning proxy for account {account.username}: {str(e)}")
                        unassigned_count += 1
            
            # Now delete all inactive proxies
            deleted_count = inactive_proxies.count()
            inactive_proxies.delete()
            
            success_message = f'Cleanup completed: {deleted_count} inactive proxies deleted, {reassigned_count} accounts reassigned to active proxies'
            if region_mismatch_count > 0:
                success_message += f' ({region_mismatch_count} accounts got different region proxies due to availability)'
            messages.success(request, success_message)
            
            if unassigned_count > 0:
                messages.warning(request, f'{unassigned_count} accounts left without proxies (no active proxies available)')
        
        elif action == 'force_delete':
            # Force delete all inactive proxies, leaving accounts without proxies
            affected_count = affected_accounts.count()
            
            # Remove proxy assignments from accounts - clear both proxy and current_proxy fields
            affected_accounts.update(proxy=None, current_proxy=None)
            
            # Delete inactive proxies
            deleted_count = inactive_proxies.count()
            inactive_proxies.delete()
            
            messages.success(request, f'Force deleted {deleted_count} inactive proxies')
            if affected_count > 0:
                messages.warning(request, f'{affected_count} accounts are now without proxies and may need manual assignment')
        
        return redirect('proxy_list')
    
    # GET request - show cleanup options
    inactive_proxies = Proxy.objects.filter(
        Q(status='inactive') | Q(is_active=False)
    )
    
    # Get statistics
    total_inactive = inactive_proxies.count()
    unassigned_inactive = inactive_proxies.filter(assigned_account__isnull=True).count()
    assigned_inactive = inactive_proxies.filter(assigned_account__isnull=False).count()
    
    # Get affected accounts
    affected_accounts = InstagramAccount.objects.filter(
        proxy__in=inactive_proxies
    ).select_related('proxy')
    
    # Get available active proxies for reassignment
    available_active_proxies = Proxy.objects.filter(
        status='active',
        is_active=True,
        assigned_account__isnull=True
    ).count()
    
    context = {
        'total_inactive': total_inactive,
        'unassigned_inactive': unassigned_inactive,
        'assigned_inactive': assigned_inactive,
        'affected_accounts': affected_accounts,
        'available_active_proxies': available_active_proxies,
        'can_reassign_all': available_active_proxies >= assigned_inactive,
        'active_tab': 'proxies'
    }
    return render(request, 'uploader/cleanup_inactive_proxies.html', context)


@login_required
def tiktok_booster(request):
    """Render the TikTok Booster control page that calls external FastAPI endpoints.

    Supports multiple API servers configured via environment variables.
    Default servers can be configured via TIKTOK_API_SERVERS as JSON.
    Selected server can be overridden via TIKTOK_API_BASE.
    """
    context = _tiktok_api_context(request)
    return render(request, 'uploader/tiktok/booster.html', context)


def _tiktok_api_context(request=None) -> dict:
    """Build context with API servers from environment for TikTok booster pages."""
    # Load servers from environment variable TIKTOK_API_SERVERS
    servers_config = os.environ.get('TIKTOK_API_SERVERS', '')
    if not servers_config:
        # Fallback to default if env var is not set
        servers = [
            {
                'name': 'Primary Server',
                'url': 'http://94.141.161.231:8000',
                'description': 'Основной сервер для TikTok API'
            }
        ]
    else:
        try:
            # Handle both quoted and unquoted JSON strings
            if servers_config.strip().startswith("'") and servers_config.strip().endswith("'"):
                servers_config = servers_config.strip('\'"')
            elif servers_config.strip().startswith('"') and servers_config.strip().endswith('"'):
                servers_config = servers_config.strip('\'"')
            servers = json.loads(servers_config)
        except Exception as e:
            logger.warning(f"Failed to parse TIKTOK_API_SERVERS JSON: {e}. Using fallback server.")
            servers = [
                {
                    'name': 'Primary Server',
                    'url': 'http://94.141.161.231:8000',
                    'description': 'Основной сервер для TikTok API'
                }
            ]

    # Sanitize and normalize server list to avoid NoneType subscripting
    try:
        if not isinstance(servers, list):
            servers = []
        normalized_servers = []
        for idx, srv in enumerate(servers):
            if isinstance(srv, dict):
                url_val = srv.get('url') or srv.get('base') or srv.get('host')
                if isinstance(url_val, str) and url_val.strip():
                    # Ensure minimal required keys
                    normalized_servers.append({
                        'name': srv.get('name') or f'Server {idx+1}',
                        'url': url_val.strip(),
                        'description': srv.get('description') or ''
                    })
                else:
                    logger.debug(f"Skipping server entry without valid url at index {idx}: {srv}")
            else:
                logger.debug(f"Skipping non-dict server entry at index {idx}: {srv}")
        servers = normalized_servers
    except Exception as norm_err:
        logger.warning(f"Failed to normalize TIKTOK_API_SERVERS: {norm_err}. Using empty list and fallback base.")
        servers = []

    # Determine selected API base with precedence: session -> env -> first server
    selected_api_base = None

    # 1) Try to get from session if request is provided
    if request is not None:
        try:
            session_url = request.session.get('selected_tiktok_api_base')
            if session_url:
                selected_api_base = session_url
        except Exception:
            pass

    # 2) Fallback to environment variable TIKTOK_API_BASE
    if not selected_api_base:
        selected_api_base = os.environ.get('TIKTOK_API_BASE', servers[0]['url'] if servers else 'http://94.141.161.231:8000')

    # Find the selected server object
    selected_server = None
    for server in servers:
        try:
            if isinstance(server, dict) and server.get('url') == selected_api_base:
                selected_server = server
                break
        except Exception:
            continue

    # If selected server not found in list, create a custom entry
    if not selected_server:
        selected_server = {
            'name': 'Custom Server',
            'url': selected_api_base,
            'description': 'Пользовательский сервер'
        }
        # Add to servers list if not already there
        if not any((isinstance(s, dict) and s.get('url') == selected_api_base) for s in servers):
            servers.append(selected_server)

    return {
        'active_tab': 'tiktok',
        'api_base': selected_api_base,
        'available_servers': servers,
        'selected_server': selected_server,
        'server_count': len(servers),
    }


@login_required
def tiktok_booster_upload_accounts(request):
    context = _tiktok_api_context(request)
    return render(request, 'uploader/tiktok/booster_upload_accounts.html', context)


@login_required
def tiktok_booster_upload_proxies(request):
    context = _tiktok_api_context(request)
    return render(request, 'uploader/tiktok/booster_upload_proxies.html', context)


@login_required
def tiktok_booster_prepare(request):
    context = _tiktok_api_context(request)
    return render(request, 'uploader/tiktok/booster_prepare.html', context)


@login_required
def tiktok_booster_start(request):
    context = _tiktok_api_context(request)
    return render(request, 'uploader/tiktok/booster_start.html', context)


# ====== Server-side proxy for TikTok Booster API ======

def _get_tiktok_api_base(request=None) -> str:
    """Resolve TikTok API base with precedence: request.POST.server_url -> session -> env/default."""
    try:
        # 1) From current request (form submit)
        if request is not None:
            server_url = None
            if getattr(request, 'method', '').upper() == 'POST':
                server_url = (request.POST.get('server_url') or '').strip()
            if server_url:
                # Persist in session for subsequent requests
                try:
                    request.session['selected_tiktok_api_base'] = server_url
                except Exception:
                    pass
                return server_url
            # 2) From session
            try:
                session_url = request.session.get('selected_tiktok_api_base')
                if session_url:
                    return session_url
            except Exception:
                pass
        # 3) Fallback to env/defaults
        ctx = _tiktok_api_context(request)
        return ctx.get('api_base')
    except Exception:
        ctx = _tiktok_api_context(request)
        return ctx.get('api_base')


def _json_response(data: dict, status: int = 200):
    from django.http import JsonResponse
    return JsonResponse(data, status=status)


@csrf_exempt
@login_required
def tiktok_booster_proxy_upload_accounts(request):
    """Proxy: upload accounts file to external TikTok API from server side."""
    import requests
    if request.method != 'POST':
        return _json_response({'detail': 'Method not allowed'}, status=405)
    api_base = _get_tiktok_api_base(request)
    try:
        file = request.FILES.get('file')
        if not file:
            return _json_response({'detail': 'No file provided'}, status=400)
        files = {'file': (file.name, file.read())}
        resp = requests.post(f"{api_base}/booster/upload_accounts", files=files, timeout=30)
        try:
            data = resp.json()
        except Exception:
            data = {'detail': resp.text}
        if resp.ok:
            return _json_response(data, status=resp.status_code)
        return _json_response(data, status=resp.status_code)
    except requests.exceptions.RequestException as e:
        return _json_response({'detail': f'Upstream error: {str(e)}'}, status=502)


@csrf_exempt
@login_required
def tiktok_booster_proxy_upload_proxies(request):
    """Proxy: upload proxies file to external TikTok API from server side."""
    import requests
    if request.method != 'POST':
        return _json_response({'detail': 'Method not allowed'}, status=405)
    api_base = _get_tiktok_api_base(request)
    try:
        file = request.FILES.get('file')
        if not file:
            return _json_response({'detail': 'No file provided'}, status=400)
        files = {'file': (file.name, file.read())}
        resp = requests.post(f"{api_base}/booster/upload_proxies", files=files, timeout=30)
        try:
            data = resp.json()
        except Exception:
            data = {'detail': resp.text}
        if resp.ok:
            return _json_response(data, status=resp.status_code)
        return _json_response(data, status=resp.status_code)
    except requests.exceptions.RequestException as e:
        return _json_response({'detail': f'Upstream error: {str(e)}'}, status=502)


@csrf_exempt
@login_required
def tiktok_booster_proxy_prepare_accounts(request):
    """Proxy: prepare booster accounts."""
    import requests
    if request.method != 'POST':
        return _json_response({'detail': 'Method not allowed'}, status=405)
    api_base = _get_tiktok_api_base(request)
    try:
        resp = requests.post(f"{api_base}/booster/prepare_accounts", timeout=30)
        try:
            data = resp.json()
        except Exception:
            data = {'detail': resp.text}
        if resp.ok:
            return _json_response(data, status=resp.status_code)
        return _json_response(data, status=resp.status_code)
    except requests.exceptions.RequestException as e:
        return _json_response({'detail': f'Upstream error: {str(e)}'}, status=502)


@csrf_exempt
@login_required
def tiktok_booster_proxy_start(request):
    """Proxy: start booster."""
    import requests
    if request.method != 'POST':
        return _json_response({'detail': 'Method not allowed'}, status=405)
    api_base = _get_tiktok_api_base(request)
    try:
        resp = requests.post(f"{api_base}/booster/start_booster", timeout=60)
        try:
            data = resp.json()
        except Exception:
            data = {'detail': resp.text}
        if resp.ok:
            return _json_response(data, status=resp.status_code)
        return _json_response(data, status=resp.status_code)
    except requests.exceptions.RequestException as e:
        return _json_response({'detail': f'Upstream error: {str(e)}'}, status=502)


@csrf_exempt
@login_required
def tiktok_set_active_server(request):
    """Set selected TikTok API server URL in the user's session."""
    from django.http import JsonResponse
    if request.method != 'POST':
        return JsonResponse({'detail': 'Method not allowed'}, status=405)
    server_url = (request.POST.get('server_url') or '').strip()
    if not server_url:
        return JsonResponse({'detail': 'server_url required'}, status=400)
    try:
        request.session['selected_tiktok_api_base'] = server_url
    except Exception:
        pass
    return JsonResponse({'ok': True, 'server_url': server_url})


@csrf_exempt
@login_required
def tiktok_api_ping(request):
    """Server-side connectivity check to selected TikTok API server."""
    import requests
    from django.http import JsonResponse
    # Allow GET or POST; prefer POST so we can accept server_url
    base = _get_tiktok_api_base(request)
    try:
        # Use /docs as simple reachable endpoint; could be /health if available
        resp = requests.get(f"{base}/docs", timeout=5, headers={"Accept": "text/html"})
        if resp.ok:
            return JsonResponse({"ok": True, "server_url": base, "status_code": resp.status_code})
        return JsonResponse({"ok": False, "server_url": base, "status_code": resp.status_code, "detail": resp.text[:200]}, status=502)
    except requests.exceptions.RequestException as e:
        return JsonResponse({"ok": False, "server_url": base, "detail": str(e)}, status=502)


@csrf_exempt
@login_required
def tiktok_booster_proxy_pipeline(request):
    """Single-call pipeline for Booster: upload accounts, upload proxies, prepare, start."""
    import requests
    if request.method != 'POST':
        return _json_response({'detail': 'Method not allowed'}, status=405)
    api_base = _get_tiktok_api_base(request)
    try:
        # 1) Upload proxies file
        proxies_file = request.FILES.get('proxies') or request.FILES.get('proxies_file') or request.FILES.get('file_proxies')
        if not proxies_file:
            return _json_response({'detail': 'Proxies file is required'}, status=400)
        files_prx = {'file': (proxies_file.name, proxies_file.read())}
        resp_prx = requests.post(f"{api_base}/booster/upload_proxies", files=files_prx, timeout=120)
        try:
            data_prx = resp_prx.json()
        except Exception:
            data_prx = {'detail': resp_prx.text}
        if not resp_prx.ok:
            return _json_response({'step': 'upload_proxies', 'detail': data_prx.get('detail') or data_prx}, status=resp_prx.status_code)

        # 2) Upload accounts file
        accounts_file = request.FILES.get('accounts') or request.FILES.get('accounts_file') or request.FILES.get('file_accounts')
        if not accounts_file:
            return _json_response({'detail': 'Accounts file is required'}, status=400)
        files_acc = {'file': (accounts_file.name, accounts_file.read())}
        resp_acc = requests.post(f"{api_base}/booster/upload_accounts", files=files_acc, timeout=120)
        try:
            data_acc = resp_acc.json()
        except Exception:
            data_acc = {'detail': resp_acc.text}
        if not resp_acc.ok:
            return _json_response({'step': 'upload_accounts', 'detail': data_acc.get('detail') or data_acc}, status=resp_acc.status_code)

        # 3) Prepare accounts
        resp_prep = requests.post(f"{api_base}/booster/prepare_accounts", timeout=60)
        try:
            data_prep = resp_prep.json()
        except Exception:
            data_prep = {'detail': resp_prep.text}
        if not resp_prep.ok:
            return _json_response({'step': 'prepare_accounts', 'detail': data_prep.get('detail') or data_prep}, status=resp_prep.status_code)

        # 4) Start booster
        resp_start = requests.post(f"{api_base}/booster/start_booster", timeout=180)
        try:
            data_start = resp_start.json()
        except Exception:
            data_start = {'detail': resp_start.text}
        if not resp_start.ok:
            return _json_response({'step': 'start_booster', 'detail': data_start.get('detail') or data_start}, status=resp_start.status_code)

        return _json_response({
            'ok': True,
            'results': {
                'upload_proxies': data_prx,
                'upload_accounts': data_acc,
                'prepare_accounts': data_prep,
                'start_booster': data_start,
            }
        })
    except requests.exceptions.RequestException as e:
        return _json_response({'detail': f'Upstream error: {str(e)}'}, status=502)


@login_required
def get_api_server_logs(request):
    """AJAX endpoint to fetch logs from the selected API server."""
    import requests
    import json
    from django.http import JsonResponse

    # Get the selected server from request or environment
    server_url = request.GET.get('server_url') or os.environ.get('TIKTOK_API_BASE')

    if not server_url:
        return JsonResponse({'error': 'No server URL provided', 'logs': []})

    try:
        # Try to get logs from the API server
        # Note: This is a placeholder - the actual API server might not have a logs endpoint
        # We'll need to implement this on the API server side
        logs_endpoint = f"{server_url}/logs"
        response = requests.get(logs_endpoint, timeout=5)

        if response.status_code == 200:
            logs_data = response.json()
            return JsonResponse({
                'logs': logs_data.get('logs', []),
                'server': server_url,
                'status': 'success'
            })
        else:
            return JsonResponse({
                'logs': [],
                'server': server_url,
                'status': 'error',
                'message': f'API server returned status {response.status_code}'
            })

    except requests.exceptions.RequestException as e:
        return JsonResponse({
            'logs': [],
            'server': server_url,
            'status': 'error',
            'message': f'Failed to connect to API server: {str(e)}'
        })
    except Exception as e:
        return JsonResponse({
            'logs': [],
            'server': server_url,
            'status': 'error',
            'message': f'Unexpected error: {str(e)}'
        })


def bulk_upload_logs(request, task_id):
    """Get bulk upload logs for a specific task"""
    try:
        task = get_object_or_404(BulkUploadTask, id=task_id)
        
        # Get logs from cache or file
        logs_key = f"bulk_upload_logs_{task_id}"
        logs = cache.get(logs_key, [])
        
        return JsonResponse({
            'logs': logs,
            'status': task.status,
            'completion_percentage': task.get_completion_percentage,
            'completed_count': task.get_completed_count,
            'total_count': task.get_total_count
        })
        
    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'logs': [],
            'status': 'ERROR'
        })
def captcha_notification(request):
    """API endpoint for captcha notifications"""
    try:
        data = json.loads(request.body)
        bulk_upload_id = data.get('bulk_upload_id')
        message = data.get('message', 'CAPTCHA detected!')
        
        # Store captcha notification in cache
        cache_key = f"captcha_notification_{bulk_upload_id}"
        cache.set(cache_key, {
            'message': message,
            'timestamp': time.time(),
            'active': True
        }, timeout=300)  # 5 minutes timeout
        
        return JsonResponse({
            'status': 'success',
            'message': 'Captcha notification stored'
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)
def get_captcha_status(request, task_id):
    """Get captcha status for a bulk upload task"""
    try:
        cache_key = f"captcha_notification_{task_id}"
        notification = cache.get(cache_key)
        
        if notification and notification.get('active'):
            return JsonResponse({
                'captcha_detected': True,
                'message': notification.get('message'),
                'timestamp': notification.get('timestamp')
            })
        else:
            return JsonResponse({
                'captcha_detected': False
            })
            
    except Exception as e:
        return JsonResponse({
            'captcha_detected': False,
            'error': str(e)
        })
def clear_captcha_notification(request, task_id):
    """Clear captcha notification for a bulk upload task (called after resolution/dismiss)."""
    try:
        cache_key = f"captcha_notification_{task_id}"
        cache.delete(cache_key)
        return JsonResponse({ 'status': 'cleared' })
    except Exception as e:
        return JsonResponse({ 'status': 'error', 'message': str(e) }, status=400)





# ====== TikTok Video Management (Separate Module) ======

@login_required
def tiktok_videos(request):
    """TikTok Video Management - main page"""
    context = _tiktok_api_context(request)
    return render(request, 'uploader/tiktok/videos.html', context)


@login_required
def tiktok_videos_upload(request):
    """TikTok Video Upload page"""
    context = _tiktok_api_context(request)
    return render(request, 'uploader/tiktok/videos_upload.html', context)


@csrf_exempt
@login_required
def tiktok_videos_proxy_upload(request):
    """Proxy: upload videos to external TikTok API from server side."""
    import requests
    if request.method != 'POST':
        return _json_response({'detail': 'Method not allowed'}, status=405)
    api_base = _get_tiktok_api_base(request)
    try:
        files = request.FILES.getlist('files')
        if not files:
            return _json_response({'detail': 'No video files provided'}, status=400)
        
        # Prepare files for upload
        upload_files = []
        for file in files:
            upload_files.append(('files', (file.name, file.read())))
        
        # Upstream upload endpoint (server-side)
        resp = requests.post(f"{api_base}/upload/upload_videos", files=upload_files, timeout=120)
        try:
            data = resp.json()
        except Exception:
            data = {'detail': resp.text}
        if resp.ok:
            return _json_response(data, status=resp.status_code)
        return _json_response(data, status=resp.status_code)
    except requests.exceptions.RequestException as e:
        return _json_response({'detail': f'Upstream error: {str(e)}'}, status=502)

@login_required
def tiktok_videos_titles(request):
    context = _tiktok_api_context(request)
    return render(request, 'uploader/tiktok/videos_titles.html', context)

@csrf_exempt
@login_required
def tiktok_videos_proxy_upload_titles(request):
    """Proxy: upload titles file to external TikTok API from server side."""
    import requests
    if request.method != 'POST':
        return _json_response({'detail': 'Method not allowed'}, status=405)
    api_base = _get_tiktok_api_base(request)
    try:
        file = request.FILES.get('file')
        if not file:
            return _json_response({'detail': 'No titles file provided'}, status=400)
        files = {'file': (file.name, file.read())}
        resp = requests.post(f"{api_base}/upload/upload_titles", files=files, timeout=60)
        try:
            data = resp.json()
        except Exception:
            data = {'detail': resp.text}
        if resp.ok:
            return _json_response(data, status=resp.status_code)
        return _json_response(data, status=resp.status_code)
    except requests.exceptions.RequestException as e:
        return _json_response({'detail': f'Upstream error: {str(e)}'}, status=502)

@login_required
def tiktok_videos_prepare(request):
    context = _tiktok_api_context(request)
    return render(request, 'uploader/tiktok/videos_prepare.html', context)

@csrf_exempt
@login_required
def tiktok_videos_proxy_prepare_config(request):
    """Proxy: prepare upload configuration on upstream server."""
    import requests
    if request.method != 'POST':
        return _json_response({'detail': 'Method not allowed'}, status=405)
    api_base = _get_tiktok_api_base(request)
    try:
        try:
            payload = json.loads(request.body.decode('utf-8')) if request.body else {}
        except Exception:
            payload = {}
        resp = requests.post(
            f"{api_base}/upload/prepare_config",
            json={
                'music_name': payload.get('music_name') or '',
                'location': payload.get('location') or '',
                'mentions': payload.get('mentions') or [],
                'upload_cycles': int(payload.get('upload_cycles') or 5)
            },
            timeout=60
        )
        try:
            data = resp.json()
        except Exception:
            data = {'detail': resp.text}
        if resp.ok:
            return _json_response(data, status=resp.status_code)
        return _json_response(data, status=resp.status_code)
    except requests.exceptions.RequestException as e:
        return _json_response({'detail': f'Upstream error: {str(e)}'}, status=502)

@login_required
def tiktok_videos_start(request):
    context = _tiktok_api_context(request)
    return render(request, 'uploader/tiktok/videos_start.html', context)

@csrf_exempt
@login_required
def tiktok_videos_proxy_start_upload(request):
    """Proxy: start upload pipeline on upstream server."""
    import requests
    if request.method != 'POST':
        return _json_response({'detail': 'Method not allowed'}, status=405)
    api_base = _get_tiktok_api_base(request)
    try:
        resp = requests.post(f"{api_base}/upload/start_upload", timeout=120)
        try:
            data = resp.json()
        except Exception:
            data = {'detail': resp.text}
        if resp.ok:
            return _json_response(data, status=resp.status_code)
        return _json_response(data, status=resp.status_code)
    except requests.exceptions.RequestException as e:
        return _json_response({'detail': f'Upstream error: {str(e)}'}, status=502)


@csrf_exempt
@login_required
def tiktok_videos_proxy_pipeline(request):
    """Single-call pipeline: upload videos, upload titles, prepare config, then start upload."""
    import requests
    if request.method != 'POST':
        return _json_response({'detail': 'Method not allowed'}, status=405)
    api_base = _get_tiktok_api_base(request)
    try:
        # 1) Upload videos (multipart with many files under key 'files')
        videos = request.FILES.getlist('files')
        if not videos:
            return _json_response({'detail': 'Video files are required'}, status=400)
        video_files = [('files', (f.name, f.read())) for f in videos]
        resp_v = requests.post(f"{api_base}/upload/upload_videos", files=video_files, timeout=180)
        try:
            data_v = resp_v.json()
        except Exception:
            data_v = {'detail': resp_v.text}
        if not resp_v.ok:
            return _json_response({'step': 'upload_videos', 'detail': data_v.get('detail') or data_v}, status=resp_v.status_code)

        # 2) Upload titles (single file field name 'titles')
        titles_file = request.FILES.get('titles')
        if not titles_file:
            return _json_response({'detail': 'Titles file is required'}, status=400)
        files_t = {'file': (titles_file.name, titles_file.read())}
        resp_t = requests.post(f"{api_base}/upload/upload_titles", files=files_t, timeout=60)
        try:
            data_t = resp_t.json()
        except Exception:
            data_t = {'detail': resp_t.text}
        if not resp_t.ok:
            return _json_response({'step': 'upload_titles', 'detail': data_t.get('detail') or data_t}, status=resp_t.status_code)

        # 3) Prepare config (json from form fields)
        music_name = (request.POST.get('music_name') or '').strip()
        location = (request.POST.get('location') or '').strip()
        mentions_raw = (request.POST.get('mentions') or '').strip()
        upload_cycles = request.POST.get('upload_cycles') or '5'
        try:
            upload_cycles = int(upload_cycles)
        except Exception:
            upload_cycles = 5
        mentions = [m.strip() for m in mentions_raw.split(',') if m.strip()]
        # All fields required per request
        if not music_name or not location or upload_cycles < 1:
            return _json_response({'detail': 'music_name, location, upload_cycles are required'}, status=400)
        resp_c = requests.post(
            f"{api_base}/upload/prepare_config",
            json={
                'music_name': music_name,
                'location': location,
                'mentions': mentions,
                'upload_cycles': upload_cycles,
            },
            timeout=60,
        )
        try:
            data_c = resp_c.json()
        except Exception:
            data_c = {'detail': resp_c.text}
        if not resp_c.ok:
            return _json_response({'step': 'prepare_config', 'detail': data_c.get('detail') or data_c}, status=resp_c.status_code)

        # 4) Start upload
        resp_s = requests.post(f"{api_base}/upload/start_upload", timeout=180)
        try:
            data_s = resp_s.json()
        except Exception:
            data_s = {'detail': resp_s.text}
        if not resp_s.ok:
            return _json_response({'step': 'start_upload', 'detail': data_s.get('detail') or data_s}, status=resp_s.status_code)

        return _json_response({
            'ok': True,
            'results': {
                'upload_videos': data_v,
                'upload_titles': data_t,
                'prepare_config': data_c,
                'start_upload': data_s,
            }
        })
    except requests.exceptions.RequestException as e:
        return _json_response({'detail': f'Upstream error: {str(e)}'}, status=502)
