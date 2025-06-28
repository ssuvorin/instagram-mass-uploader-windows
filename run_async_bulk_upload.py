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
    }
    color = status_colors.get(status, Colors.END)
    return Colors.colorize(status, color)

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
        print(f"{Colors.GREEN}✅ Async configuration updated{Colors.END}")
        print_async_config()
    
    return settings_changed

async def run_async_task_with_monitoring(task_id):
    """Run async task with real-time monitoring"""
    print_separator(f"STARTING ASYNC BULK UPLOAD TASK {task_id}")
    
    # Get the task
    try:
        task = BulkUploadTask.objects.get(id=task_id)
    except BulkUploadTask.DoesNotExist:
        print(f"{Colors.RED}Task with ID {task_id} not found{Colors.END}")
        return False
    
    print(f"{Colors.BOLD}Task:{Colors.END} {task.name}")
    print(f"{Colors.BOLD}Status:{Colors.END} {format_status(task.status)}")
    print(f"{Colors.BOLD}Accounts:{Colors.END} {task.accounts.count()}")
    print(f"{Colors.BOLD}Videos:{Colors.END} {task.videos.count()}")
    
    # Show current async configuration
    print_async_config()
    
    print_separator("ASYNC EXECUTION STARTING")
    print(f"{Colors.BOLD}{Colors.YELLOW}ВАЖНО: Браузеры будут запускаться ПАРАЛЛЕЛЬНО{Colors.END}")
    print(f"{Colors.BOLD}Следите за прогрессом в веб-интерфейсе или в этом терминале{Colors.END}")
    print_separator()
    
    # Start monitoring task
    monitor_task = asyncio.create_task(monitor_async_task_health(task_id, 30))
    
    # Run the main task
    start_time = time.time()
    try:
        result = await run_async_bulk_upload_task(task_id)
        end_time = time.time()
        
        # Cancel monitoring
        monitor_task.cancel()
        
        execution_time = end_time - start_time
        
        print_separator("ASYNC EXECUTION COMPLETED")
        
        # Get final status
        task.refresh_from_db()
        print(f"{Colors.BOLD}Final Status:{Colors.END} {format_status(task.status)}")
        print(f"{Colors.BOLD}Execution Time:{Colors.END} {Colors.colorize(f'{execution_time:.2f}s', Colors.CYAN)}")
        print(f"{Colors.BOLD}Result:{Colors.END} {Colors.colorize(str(result), Colors.GREEN if result else Colors.RED)}")
        
        # Show account results
        accounts = task.accounts.all()
        print(f"\n{Colors.BOLD}ACCOUNT RESULTS:{Colors.END}")
        for account in accounts:
            status_color = Colors.GREEN if account.status == 'COMPLETED' else Colors.RED if account.status == 'FAILED' else Colors.YELLOW
            print(f"  {account.account.username}: {Colors.colorize(account.status, status_color)}")
        
        return result
        
    except Exception as e:
        monitor_task.cancel()
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
    
    print(f"\n{Colors.YELLOW}⚠️  ВНИМАНИЕ: Это тест производительности, не реальная загрузка!{Colors.END}")
    print(f"{Colors.YELLOW}⚠️  Для реального теста используйте отдельные задачи{Colors.END}")
    
    # Run async performance test
    print(f"\n{Colors.BLUE}🚀 Running ASYNC performance test...{Colors.END}")
    async_result = asyncio.run(test_async_performance(task_id))
    
    print(f"\n{Colors.BOLD}ASYNC Results:{Colors.END}")
    print(f"  Success: {Colors.colorize(str(async_result['success']), Colors.GREEN if async_result['success'] else Colors.RED)}")
    print(f"  Time: {Colors.colorize(f'{async_result['execution_time']:.2f}s', Colors.CYAN)}")
    
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

def main():
    parser = argparse.ArgumentParser(description='Async Bulk Upload CLI Tool')
    
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
    
    # Configuration options
    parser.add_argument('--max-accounts', type=int,
                       help='Max concurrent accounts (default: 3)')
    parser.add_argument('--account-delay-min', type=int,
                       help='Min delay between accounts in seconds (default: 30)')
    parser.add_argument('--account-delay-max', type=int,
                       help='Max delay between accounts in seconds (default: 120)')
    parser.add_argument('--retry-attempts', type=int,
                       help='Number of retry attempts (default: 2)')
    
    # Add test performance argument
    parser.add_argument('--test-performance', action='store_true', help='Test async performance (requires no task ID)')
    
    args = parser.parse_args()
    
    # Configure async settings if provided
    configure_async_settings(args)
    
    if args.config:
        print_async_config()
    
    elif args.test_performance:
        print(f"{Colors.BOLD}🚀 ASYNC PERFORMANCE TEST{Colors.END}")
        print("This would test async performance with a sample task.")
        print("For now, use --compare TASK_ID to compare sync vs async performance.")
        
    elif args.list:
        list_suitable_tasks()
    
    elif args.run_async:
        print(f"{Colors.BOLD}🚀 Starting ASYNC bulk upload task {args.run_async}{Colors.END}")
        result = asyncio.run(run_async_task_with_monitoring(args.run_async))
        if result:
            print(f"{Colors.GREEN}✅ Async task completed successfully{Colors.END}")
        else:
            print(f"{Colors.RED}❌ Async task failed{Colors.END}")
    
    elif args.run_sync:
        print(f"{Colors.BOLD}🔄 Starting SYNC bulk upload task {args.run_sync}{Colors.END}")
        from uploader.bulk_tasks_playwright import run_bulk_upload_task
        
        start_time = time.time()
        result = run_bulk_upload_task(args.run_sync)
        end_time = time.time()
        
        execution_time = end_time - start_time
        print(f"{Colors.BOLD}Sync Execution Time:{Colors.END} {Colors.colorize(f'{execution_time:.2f}s', Colors.CYAN)}")
        
        if result:
            print(f"{Colors.GREEN}✅ Sync task completed successfully{Colors.END}")
        else:
            print(f"{Colors.RED}❌ Sync task failed{Colors.END}")
    
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