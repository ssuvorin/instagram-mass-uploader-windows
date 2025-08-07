#!/usr/bin/env python
"""
CLI инструмент для тестирования асинхронной загрузки видео в Instagram
"""

import os
import sys
import django
import asyncio
import time
import argparse
import threading
from datetime import datetime
from dotenv import load_dotenv

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'instagram_uploader.settings')
django.setup()

from uploader.models import BulkUploadTask, InstagramAccount, BulkUploadAccount, BulkVideo, VideoTitle
from uploader.async_bulk_tasks import (
    run_async_bulk_upload_task, run_async_bulk_upload_task_sync,
    set_async_config, get_async_config, test_async_performance,
    monitor_async_task_health, AsyncConfig
)
from django.utils import timezone

# Load environment variables
load_dotenv()

# Force visible mode
os.environ["VISIBLE"] = "1"
os.environ["HEADLESS"] = "0"

# Color constants for output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'
    
    @staticmethod
    def colorize(text, color):
        return f"{color}{text}{Colors.END}"

def print_separator(title="", char="=", width=80):
    """Print a separator line with optional title"""
    if title:
        title_line = f" {title} "
        padding = (width - len(title_line)) // 2
        line = char * padding + title_line + char * padding
        if len(line) < width:
            line += char
        print(Colors.colorize(line, Colors.BLUE))
    else:
        print(char * width)

def format_status(status):
    """Format status with colors"""
    status_colors = {
        'PENDING': Colors.YELLOW,
        'RUNNING': Colors.BLUE,
        'COMPLETED': Colors.GREEN,
        'FAILED': Colors.RED,
        'PARTIALLY_COMPLETED': Colors.CYAN,
        'PHONE_VERIFICATION_REQUIRED': Colors.YELLOW,
        'HUMAN_VERIFICATION_REQUIRED': Colors.YELLOW
    }
    color = status_colors.get(status, Colors.END)
    return Colors.colorize(status, color + Colors.BOLD)

def print_async_config():
    """Print current async configuration"""
    print_separator("ASYNC CONFIGURATION")
    
    config = get_async_config()
    
    print(f"{Colors.BOLD}Current Async Configuration:{Colors.END}")
    print(f"  Max Concurrent Accounts: {Colors.colorize(str(config['max_concurrent_accounts']), Colors.CYAN)}")
    print(f"  Max Concurrent Videos: {Colors.colorize(str(config['max_concurrent_videos']), Colors.CYAN)}")
    print(f"  Account Delay Min: {Colors.colorize(str(config['account_delay_min']), Colors.CYAN)}s")
    print(f"  Account Delay Max: {Colors.colorize(str(config['account_delay_max']), Colors.CYAN)}s")
    print(f"  Retry Attempts: {Colors.colorize(str(config['retry_attempts']), Colors.CYAN)}")
    print(f"  Health Check Interval: {Colors.colorize(str(config['health_check_interval']), Colors.CYAN)}s")

def configure_async_settings(args):
    """Configure async settings from command line arguments"""
    settings_changed = False
    
    if args.max_accounts:
        set_async_config(max_concurrent_accounts=args.max_accounts)
        settings_changed = True
    
    if args.account_delay_min:
        set_async_config(account_delay_min=args.account_delay_min)
        settings_changed = True
    
    if args.account_delay_max:
        set_async_config(account_delay_max=args.account_delay_max)
        settings_changed = True
    
    if args.retry_attempts:
        set_async_config(retry_attempts=args.retry_attempts)
        settings_changed = True
    
    if settings_changed:
        print(f"{Colors.GREEN}[OK] Async configuration updated{Colors.END}")
        print_async_config()
    
    return settings_changed

def print_task_summary(task):
    """Print detailed task summary with status information"""
    print_separator("TASK SUMMARY")
    
    print(f"{Colors.BOLD}Task ID:{Colors.END} {task.id}")
    print(f"{Colors.BOLD}Name:{Colors.END} {task.name}")
    print(f"{Colors.BOLD}Status:{Colors.END} {format_status(task.status)}")
    print(f"{Colors.BOLD}Created:{Colors.END} {task.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{Colors.BOLD}Updated:{Colors.END} {task.updated_at.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Account statistics
    accounts = task.accounts.all()
    print(f"\n{Colors.BOLD}ACCOUNTS SUMMARY:{Colors.END}")
    print(f"  Total accounts: {accounts.count()}")
    
    # Count accounts by status
    status_counts = {}
    for account in accounts:
        status_counts[account.status] = status_counts.get(account.status, 0) + 1
    
    for status, count in status_counts.items():
        print(f"  {format_status(status)}: {count}")
    
    # Video statistics
    videos = task.videos.all()
    print(f"\n{Colors.BOLD}VIDEOS SUMMARY:{Colors.END}")
    print(f"  Total videos: {videos.count()}")
    assigned_videos = videos.filter(assigned_to__isnull=False).count()
    unassigned_videos = videos.filter(assigned_to__isnull=True).count()
    print(f"  Assigned to accounts: {Colors.colorize(str(assigned_videos), Colors.GREEN)}")
    if unassigned_videos > 0:
        print(f"  Unassigned: {Colors.colorize(str(unassigned_videos), Colors.YELLOW)}")
    
    # Progress information
    if task.status in ['RUNNING', 'PARTIALLY_COMPLETED', 'COMPLETED']:
        completed_count = task.get_completed_count()
        total_count = task.get_total_count()
        percentage = task.get_completion_percentage()
        
        print(f"\n{Colors.BOLD}PROGRESS:{Colors.END}")
        print(f"  Completed: {Colors.colorize(str(completed_count), Colors.GREEN)}/{total_count}")
        print(f"  Progress: {Colors.colorize(f'{percentage}%', Colors.CYAN)}")

def print_accounts_table(accounts):
    """Print detailed accounts table with status"""
    if not accounts:
        print(f"{Colors.YELLOW}No accounts found{Colors.END}")
        return
    
    print_separator("ACCOUNTS DETAILS")
    
    # Table header
    print(f"{Colors.BOLD}{'USERNAME':<20} {'STATUS':<25} {'VIDEOS':<8} {'PROXY':<15} {'LAST USED':<12}{Colors.END}")
    print("-" * 80)
    
    for account_task in accounts:
        username = account_task.account.username[:19] if len(account_task.account.username) > 19 else account_task.account.username
        status_display = format_status(account_task.status)
        videos_count = account_task.assigned_videos.count()
        
        # Proxy info
        proxy_info = "None"
        if account_task.proxy:
            proxy_info = f"{account_task.proxy.host[:12]}..."
        elif account_task.account.proxy:
            proxy_info = f"{account_task.account.proxy.host[:12]}..."
        
        # Last used info
        last_used = "Never"
        if account_task.account.last_used:
            last_used = account_task.account.last_used.strftime('%m-%d %H:%M')
        
        print(f"{username:<20} {status_display:<25} {videos_count:<8} {proxy_info:<15} {last_used:<12}")
        
        # Show log if there are any issues
        if account_task.log and account_task.status in ['FAILED', 'PHONE_VERIFICATION_REQUIRED', 'HUMAN_VERIFICATION_REQUIRED']:
            log_lines = account_task.log.split('\n')
            for line in log_lines[-2:]:  # Show last 2 lines
                if line.strip():
                    print(f"    {Colors.YELLOW}└─ {line.strip()[:60]}{Colors.END}")

def monitor_task_progress(task_id, stop_event):
    """Monitor task progress in real-time"""
    last_status = {}
    
    while not stop_event.is_set():
        try:
            task = BulkUploadTask.objects.get(id=task_id)
            accounts = task.accounts.all()
            
            # Check if any status changed
            current_status = {}
            status_changed = False
            
            for account_task in accounts:
                current_status[account_task.id] = account_task.status
                if account_task.id not in last_status or last_status[account_task.id] != account_task.status:
                    status_changed = True
            
            # If status changed, update display
            if status_changed:
                print(f"\n{Colors.CYAN}[{timezone.now().strftime('%H:%M:%S')}] Status Update:{Colors.END}")
                
                # Show quick status summary
                status_counts = {}
                for account_task in accounts:
                    status_counts[account_task.status] = status_counts.get(account_task.status, 0) + 1
                
                status_line = []
                for status, count in status_counts.items():
                    status_line.append(f"{format_status(status)}: {count}")
                
                print("  " + " | ".join(status_line))
                
                # Show individual account changes
                for account_task in accounts:
                    if account_task.id not in last_status:
                        continue
                    
                    if last_status[account_task.id] != account_task.status:
                        old_status = format_status(last_status[account_task.id])
                        new_status = format_status(account_task.status)
                        username = Colors.colorize(account_task.account.username, Colors.CYAN)
                        print(f"  {username}: {old_status} → {new_status}")
                        
                        # Show recent log messages for failures
                        if account_task.status in ['FAILED', 'PHONE_VERIFICATION_REQUIRED', 'HUMAN_VERIFICATION_REQUIRED']:
                            if account_task.log:
                                recent_logs = account_task.log.split('\n')[-3:]
                                for log_line in recent_logs:
                                    if log_line.strip():
                                        print(f"    {Colors.YELLOW}└─ {log_line.strip()}{Colors.END}")
                
                last_status = current_status.copy()
                
                # Check if task is complete
                if task.status in ['COMPLETED', 'FAILED', 'PARTIALLY_COMPLETED']:
                    print(f"\n{Colors.GREEN}Task completed with status: {format_status(task.status)}{Colors.END}")
                    break
            
            time.sleep(5)  # Check every 5 seconds
            
        except Exception as e:
            print(f"\n{Colors.RED}Error monitoring progress: {str(e)}{Colors.END}")
            break

async def run_async_task_with_monitoring(task_id):
    """Run async task with real-time monitoring"""
    print_separator(f"STARTING ASYNC BULK UPLOAD TASK {task_id}")
    
    # Get the task
    try:
        task = BulkUploadTask.objects.get(id=task_id)
    except BulkUploadTask.DoesNotExist:
        print(f"{Colors.RED}Task with ID {task_id} not found{Colors.END}")
        return False
    
    # Print detailed task information
    print_task_summary(task)
    
    # Show accounts table
    accounts = task.accounts.all().select_related('account', 'proxy')
    print_accounts_table(accounts)
    
    # Show current async configuration
    print_async_config()
    
    # Check if videos are assigned
    unassigned_videos = task.videos.filter(assigned_to__isnull=True)
    if unassigned_videos.exists():
        print(f"\n{Colors.YELLOW}Warning: {unassigned_videos.count()} videos are not assigned to accounts{Colors.END}")
        
        # Assign videos to accounts
        from uploader.views import assign_videos_to_accounts
        assign_videos_to_accounts(task)
        print(f"{Colors.GREEN}Assigned videos to accounts{Colors.END}")
    
    # Update task status
    task.status = 'RUNNING'
    task.log += f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] Task started via CLI tool (ASYNC mode)\n"
    task.save()
    
    print_separator("ASYNC EXECUTION STARTING")
    print(f"{Colors.BOLD}{Colors.YELLOW}ВАЖНО: Браузеры будут запускаться ПАРАЛЛЕЛЬНО{Colors.END}")
    print(f"{Colors.BOLD}Максимум {AsyncConfig.MAX_CONCURRENT_ACCOUNTS} аккаунтов одновременно{Colors.END}")
    print(f"{Colors.BOLD}Следите за прогрессом в веб-интерфейсе или в этом терминале{Colors.END}")
    print_separator()
    
    # Force environment variables for visibility
    os.environ["VISIBLE"] = "1"
    os.environ["HEADLESS"] = "0"
    
    # Start monitoring thread
    stop_event = threading.Event()
    monitor_thread = threading.Thread(target=monitor_task_progress, args=(task_id, stop_event))
    monitor_thread.daemon = True
    monitor_thread.start()
    
    # Run the async task
    start_time = time.time()
    try:
        result = await run_async_bulk_upload_task(task_id)
        end_time = time.time()
        
        # Stop monitoring
        stop_event.set()
        monitor_thread.join(timeout=1)
        
        execution_time = end_time - start_time
        
        # Get final status
        task.refresh_from_db()
        print_separator("ASYNC UPLOAD COMPLETED")
        print_task_summary(task)
        
        # Show final accounts status
        accounts = task.accounts.all().select_related('account', 'proxy')
        print_accounts_table(accounts)
        
        print(f"\n{Colors.BOLD}ASYNC EXECUTION SUMMARY:{Colors.END}")
        print(f"  Execution Time: {Colors.colorize(f'{execution_time:.2f}s', Colors.CYAN)}")
        print(f"  Result: {Colors.colorize(str(result), Colors.GREEN if result else Colors.RED)}")
        
        return result
        
    except Exception as e:
        stop_event.set()
        end_time = time.time()
        execution_time = end_time - start_time
        
        print_separator("ASYNC EXECUTION FAILED")
        print(f"{Colors.RED}Error: {str(e)}{Colors.END}")
        print(f"{Colors.BOLD}Execution Time:{Colors.END} {Colors.colorize(f'{execution_time:.2f}s', Colors.CYAN)}")
        return False

def run_sync_vs_async_comparison(task_id):
    """Compare sync vs async performance"""
    print_separator("SYNC VS ASYNC PERFORMANCE COMPARISON")
    
    try:
        task = BulkUploadTask.objects.get(id=task_id)
    except BulkUploadTask.DoesNotExist:
        print(f"{Colors.RED}Task with ID {task_id} not found{Colors.END}")
        return
    
    print(f"{Colors.BOLD}Task:{Colors.END} {task.name}")
    print(f"{Colors.BOLD}Accounts:{Colors.END} {task.accounts.count()}")
    print(f"{Colors.BOLD}Videos:{Colors.END} {task.videos.count()}")
    
    print(f"\n{Colors.YELLOW}[WARN]  ВНИМАНИЕ: Это тест производительности, не реальная загрузка!{Colors.END}")
    print(f"{Colors.YELLOW}[WARN]  Для реального теста используйте отдельные задачи{Colors.END}")
    
    # Run async performance test
    print(f"\n{Colors.BLUE}[START] Running ASYNC performance test...{Colors.END}")
    async_result = asyncio.run(test_async_performance(task_id))
    
    print(f"\n{Colors.BOLD}ASYNC Results:{Colors.END}")
    print(f"  Success: {Colors.colorize(str(async_result['success']), Colors.GREEN if async_result['success'] else Colors.RED)}")
    print(f"  Time: {Colors.colorize(f'{async_result['execution_time']:.2f}s', Colors.CYAN)}")
    print(f"  Accounts Processed: {Colors.colorize(str(async_result['accounts_processed']), Colors.CYAN)}/{async_result['total_accounts']}")
    
    if 'error' in async_result:
        print(f"  Error: {Colors.colorize(async_result['error'], Colors.RED)}")

def list_suitable_tasks():
    """List tasks suitable for async testing"""
    print_separator("TASKS SUITABLE FOR ASYNC TESTING")
    
    tasks = BulkUploadTask.objects.filter(
        status__in=['PENDING', 'FAILED']
    ).order_by('-created_at')
    
    if not tasks:
        print(f"{Colors.YELLOW}No suitable tasks found{Colors.END}")
        print(f"Create a task with multiple accounts to test async functionality")
        return
    
    # Table header
    print(f"{Colors.BOLD}{'ID':<4} {'NAME':<25} {'STATUS':<15} {'ACCOUNTS':<9} {'VIDEOS':<7} {'CREATED':<12}{Colors.END}")
    print("-" * 80)
    
    for task in tasks:
        name = task.name[:24] if len(task.name) > 24 else task.name
        status_display = format_status(task.status)
        
        accounts_count = task.accounts.count()
        videos_count = task.videos.count()
        created = task.created_at.strftime('%m-%d %H:%M')
        
        # Highlight tasks with multiple accounts
        if accounts_count > 1:
            name = Colors.colorize(name, Colors.GREEN)
            accounts_count = Colors.colorize(str(accounts_count), Colors.GREEN)
        
        print(f"{task.id:<4} {name:<25} {status_display:<15} {accounts_count:<9} {videos_count:<7} {created:<12}")

def create_test_bulk_upload(name="Test Async Bulk Upload", add_video=True):
    """Create a test bulk upload task with multiple accounts for async testing"""
    print(f"Creating test async bulk upload task: {name}")
    
    # Check if we have multiple accounts
    accounts = InstagramAccount.objects.filter(status='ACTIVE')[:3]  # Get up to 3 accounts
    if not accounts:
        print(f"{Colors.RED}No active Instagram accounts found. Please create at least one account first.{Colors.END}")
        return None
    
    if len(accounts) < 2:
        print(f"{Colors.YELLOW}Warning: Only {len(accounts)} account(s) found. Async mode works best with multiple accounts.{Colors.END}")
    
    # Create the bulk upload task
    from django.core.files.uploadedfile import SimpleUploadedFile
    import shutil
    
    bulk_task = BulkUploadTask.objects.create(
        name=name,
        status='PENDING',
        log=f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] Task created via CLI tool (ASYNC mode)\n"
    )
    
    # Add accounts to the task
    for i, account in enumerate(accounts):
        print(f"Adding account {Colors.colorize(account.username, Colors.CYAN)} to task")
        
        bulk_account = BulkUploadAccount.objects.create(
            bulk_task=bulk_task,
            account=account,
            proxy=account.proxy,
            status='PENDING'
        )
    
    # Add test video if requested
    if add_video:
        # Create or get test video
        test_video_path = os.path.join("media", "test_video.mp4")
        os.makedirs(os.path.dirname(test_video_path), exist_ok=True)
        
        # Check if we already have a test video
        if not os.path.exists(test_video_path):
            # Check if there are any videos in videos directory
            videos_dir = os.path.join("bot", "videos")
            if os.path.exists(videos_dir) and os.listdir(videos_dir):
                # Take the first video file
                for filename in os.listdir(videos_dir):
                    if filename.endswith(".mp4") or filename.endswith(".mov"):
                        source_path = os.path.join(videos_dir, filename)
                        shutil.copy(source_path, test_video_path)
                        print(f"Copied test video from {source_path} to {test_video_path}")
                        break
            else:
                # Create a very small empty video file if no existing videos
                print("Creating empty test video file")
                with open(test_video_path, 'wb') as f:
                    f.write(b'TEST VIDEO CONTENT')
        
        # Create bulk video entry
        with open(test_video_path, 'rb') as f:
            uploaded_file = SimpleUploadedFile(
                name=os.path.basename(test_video_path),
                content=f.read(),
                content_type='video/mp4'
            )
            
        print(f"Adding test video to task: {os.path.basename(test_video_path)}")
        bulk_video = BulkVideo.objects.create(
            bulk_task=bulk_task,
            video_file=uploaded_file,
            order=1
        )
        
        # Assign video to first account
        first_account = bulk_task.accounts.first()
        if first_account:
            bulk_video.assigned_to = first_account
            bulk_video.save()
        
        # Add a test caption
        title = VideoTitle.objects.create(
            bulk_task=bulk_task,
            title="Test video uploaded via async bulk upload #test #automation #async",
            used=True,
            assigned_to=bulk_video
        )
        
        print(f"Added test video and assigned to account {Colors.colorize(first_account.account.username, Colors.CYAN) if first_account else 'None'}")
    
    print(f"{Colors.GREEN}Created async bulk task {bulk_task.id}: {bulk_task.name} with {len(accounts)} accounts{Colors.END}")
    return bulk_task

def main():
    parser = argparse.ArgumentParser(
        description='Async Bulk Upload CLI Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_async_bulk_upload.py --list                    # List suitable tasks
  python run_async_bulk_upload.py --create                  # Create new test task
  python run_async_bulk_upload.py --create --name "My Task" # Create task with custom name  
  python run_async_bulk_upload.py --run-async 5             # Run task with ID 5 in async mode
  python run_async_bulk_upload.py --run-sync 5              # Run task with ID 5 in sync mode
  python run_async_bulk_upload.py --compare 5               # Compare sync vs async performance
  python run_async_bulk_upload.py --config                  # Show current async configuration
  python run_async_bulk_upload.py --max-accounts 5          # Set max concurrent accounts
        """
    )
    
    # Main actions
    parser.add_argument('--run-async', type=int, metavar='TASK_ID',
                       help='Run task in async mode')
    parser.add_argument('--run-sync', type=int, metavar='TASK_ID',
                       help='Run task in sync mode (for comparison)')
    parser.add_argument('--compare', type=int, metavar='TASK_ID',
                       help='Compare sync vs async performance')
    parser.add_argument('--list', action='store_true',
                       help='List tasks suitable for async testing')
    parser.add_argument('--config', action='store_true',
                       help='Show current async configuration')
    parser.add_argument('--create', action='store_true',
                       help='Create a new test bulk upload task for async testing')
    
    # Configuration options
    parser.add_argument('--max-accounts', type=int,
                       help='Max concurrent accounts (default: 3)')
    parser.add_argument('--account-delay-min', type=int,
                       help='Min delay between accounts in seconds (default: 30)')
    parser.add_argument('--account-delay-max', type=int,
                       help='Max delay between accounts in seconds (default: 120)')
    parser.add_argument('--retry-attempts', type=int,
                       help='Number of retry attempts (default: 2)')
    parser.add_argument('--name', type=str, help='Name for the new task', default="Test Async Bulk Upload")
    parser.add_argument('--no-video', action='store_true', help='Do not add test video to the task')
    
    args = parser.parse_args()
    
    # Check if we have a Dolphin API token
    dolphin_token = os.environ.get("DOLPHIN_API_TOKEN")
    if not dolphin_token and not args.list and not args.config and not args.create:
        print(f"{Colors.YELLOW}[WARN] No DOLPHIN_API_TOKEN found in environment. Please set it in a .env file or enter it now.{Colors.END}")
        dolphin_token = input("Enter your Dolphin API token (or press Enter to proceed anyway): ")
        if dolphin_token:
            # Set it for this session
            os.environ["DOLPHIN_API_TOKEN"] = dolphin_token
    
    # Configure async settings if provided
    configure_async_settings(args)
    
    if args.config:
        print_async_config()
    
    elif args.create:
        task = create_test_bulk_upload(name=args.name, add_video=not args.no_video)
        if task:
            print(f"\n{Colors.GREEN}Created task with ID: {task.id}{Colors.END}")
            
            # Ask if user wants to run it
            run_now = input(f"Do you want to run task {task.id} in async mode now? (y/n): ")
            if run_now.lower() == 'y':
                result = asyncio.run(run_async_task_with_monitoring(task.id))
                if result:
                    print(f"{Colors.GREEN}[OK] Async task completed successfully{Colors.END}")
                else:
                    print(f"{Colors.RED}[FAIL] Async task failed{Colors.END}")
        
    elif args.list:
        list_suitable_tasks()
    
    elif args.run_async:
        print(f"{Colors.BOLD}[START] Starting ASYNC bulk upload task {args.run_async}{Colors.END}")
        result = asyncio.run(run_async_task_with_monitoring(args.run_async))
        if result:
            print(f"{Colors.GREEN}[OK] Async task completed successfully{Colors.END}")
        else:
            print(f"{Colors.RED}[FAIL] Async task failed{Colors.END}")
    
    elif args.run_sync:
        print(f"{Colors.BOLD}[RETRY] Starting SYNC bulk upload task {args.run_sync}{Colors.END}")
        from uploader.bulk_tasks_playwright import run_bulk_upload_task
        
        start_time = time.time()
        result = run_bulk_upload_task(args.run_sync)
        end_time = time.time()
        
        execution_time = end_time - start_time
        print(f"{Colors.BOLD}Sync Execution Time:{Colors.END} {Colors.colorize(f'{execution_time:.2f}s', Colors.CYAN)}")
        
        if result:
            print(f"{Colors.GREEN}[OK] Sync task completed successfully{Colors.END}")
        else:
            print(f"{Colors.RED}[FAIL] Sync task failed{Colors.END}")
    
    elif args.compare:
        run_sync_vs_async_comparison(args.compare)
    
    else:
        # Show help and list tasks by default
        parser.print_help()
        print("\n")
        list_suitable_tasks()
        print("\n")
        print_async_config()

if __name__ == "__main__":
    main() 