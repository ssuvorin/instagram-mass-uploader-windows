"""Views module: cookie_robot (split from monolith)."""
from .common import *
from .misc import run_cookie_robot_task  # ensure available here for background start


def create_cookie_robot_task(request):
    """Create a new cookie robot task"""
    if request.method == 'POST':
        # Get form data manually
        account_id = request.POST.get('account')
        urls_text = request.POST.get('urls', '')
        headless = request.POST.get('headless', '') == 'on'
        imageless = request.POST.get('imageless', '') == 'on'
        
        # Validate data
        if not account_id:
            logger.error("Cookie Robot task creation failed: No account selected")
            messages.error(request, 'Please select an account')
            return redirect('create_cookie_robot_task')
        
        # Parse URLs
        urls = [url.strip() for url in urls_text.split('\n') if url.strip()]
        
        if not urls:
            logger.error("Cookie Robot task creation failed: No URLs provided")
            messages.error(request, 'Please enter at least one URL')
            return redirect('create_cookie_robot_task')
        
        # Get account
        try:
            account = InstagramAccount.objects.get(id=account_id)
            logger.info(f"Creating Cookie Robot task for account: {account.username}")
        except InstagramAccount.DoesNotExist:
            logger.error(f"Cookie Robot task creation failed: Account with ID {account_id} not found")
            messages.error(request, 'Account not found')
            return redirect('create_cookie_robot_task')
        
        # Create task - using UploadTask for now
        initial_log = f"Cookie Robot Task\n"
        
        log_message = f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] Task created"
        initial_log += log_message + "\n"
        logger.info(log_message)
        
        log_message = f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] Account: {account.username}"
        initial_log += log_message + "\n"
        logger.info(log_message)
        
        log_message = f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] URLs: {urls}"
        initial_log += log_message + "\n"
        logger.info(log_message)
        
        log_message = f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] Headless: {headless}"
        initial_log += log_message + "\n"
        logger.info(log_message)
        
        log_message = f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] Imageless: {imageless}"
        initial_log += log_message + "\n"
        logger.info(log_message)
        
        task = UploadTask.objects.create(
            account=account,
            status='PENDING',
            log=initial_log
        )
        
        logger.info(f"Cookie Robot task created successfully! Task ID: {task.id}")
        messages.success(request, f'Cookie Robot task created successfully! Task ID: {task.id}')
        
        # Start task in background thread
        thread = threading.Thread(target=run_cookie_robot_task, args=(task.id, urls, headless, imageless))
        thread.daemon = True
        thread.start()
        logger.info(f"Task {task.id} started in background thread")
        messages.info(request, 'Task started in background.')
        
        return redirect('cookie_task_detail', task_id=task.id)
    else:
        # Get accounts with Dolphin profiles
        accounts = InstagramAccount.objects.filter(dolphin_profile_id__isnull=False)
        logger.info(f"Found {accounts.count()} accounts with Dolphin profiles for Cookie Robot")
        
        # Get account ID from query parameter
        account_id = request.GET.get('account')
        selected_account = None
        if account_id:
            try:
                selected_account = accounts.get(id=account_id)
                logger.info(f"Selected account for Cookie Robot: {selected_account.username}")
            except InstagramAccount.DoesNotExist:
                logger.warning(f"Account with ID {account_id} not found for Cookie Robot")
                pass
        
        context = {
            'accounts': accounts,
            'selected_account': selected_account,
            'active_tab': 'cookies'
        }
        return render(request, 'uploader/cookies/create_task.html', context)
