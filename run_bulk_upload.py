#!/usr/bin/env python
import os
import sys
import django
import json
import time
import asyncio
import shutil
import threading
from dotenv import load_dotenv
from django.core.files.uploadedfile import SimpleUploadedFile

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'instagram_uploader.settings')
django.setup()

from uploader.models import BulkUploadTask, InstagramAccount, BulkUploadAccount, BulkVideo, VideoTitle
from uploader.bulk_tasks_playwright import run_bulk_upload_task
from django.utils import timezone
import argparse

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

def print_separator(title=""):
    """Print decorative separator with optional title"""
    if title:
        title_text = f" {title} "
        padding = (60 - len(title_text)) // 2
        print(Colors.BOLD + "=" * padding + title_text + "=" * padding + Colors.END)
    else:
        print("=" * 60)

def format_status(status):
    """Format status with appropriate color"""
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

def print_videos_table(videos):
    """Print videos assignment table"""
    if not videos:
        print(f"{Colors.YELLOW}No videos found{Colors.END}")
        return
    
    print_separator("VIDEOS ASSIGNMENT")
    
    # Table header
    print(f"{Colors.BOLD}{'ORDER':<6} {'FILENAME':<30} {'ASSIGNED TO':<20} {'STATUS':<10}{Colors.END}")
    print("-" * 75)
    
    for video in videos:
        filename = os.path.basename(video.video_file.name)[:29] if video.video_file.name else "Unknown"
        
        assigned_to = "Unassigned"
        status = Colors.colorize("PENDING", Colors.YELLOW)
        
        if video.assigned_to:
            assigned_to = video.assigned_to.account.username[:19]
            status = format_status(video.assigned_to.status)
        
        print(f"{video.order:<6} {filename:<30} {assigned_to:<20} {status:<10}")

def list_tasks():
    """List all bulk upload tasks with status"""
    tasks = BulkUploadTask.objects.order_by('-created_at')
    
    if not tasks:
        print(f"{Colors.YELLOW}No bulk upload tasks found{Colors.END}")
        return
    
    print_separator("ALL BULK UPLOAD TASKS")
    
    # Table header
    print(f"{Colors.BOLD}{'ID':<4} {'NAME':<25} {'STATUS':<25} {'ACCOUNTS':<9} {'VIDEOS':<7} {'PROGRESS':<10} {'CREATED':<12}{Colors.END}")
    print("-" * 100)
    
    for task in tasks:
        name = task.name[:24] if len(task.name) > 24 else task.name
        status_display = format_status(task.status)
        
        accounts_count = task.get_total_count()
        videos_count = task.videos.count()
        
        progress = ""
        if task.status in ['RUNNING', 'PARTIALLY_COMPLETED', 'COMPLETED']:
            progress = f"{task.get_completion_percentage()}%"
        
        created = task.created_at.strftime('%m-%d %H:%M')
        
        print(f"{task.id:<4} {name:<25} {status_display:<25} {accounts_count:<9} {videos_count:<7} {progress:<10} {created:<12}")

def create_test_video():
    """Create a simple test video file if none exists"""
    test_video_path = os.path.join("media", "test_video.mp4")
    os.makedirs(os.path.dirname(test_video_path), exist_ok=True)
    
    # Check if we already have a test video
    if os.path.exists(test_video_path):
        print(f"Using existing test video: {test_video_path}")
        return test_video_path
        
    # Check if there are any videos in videos directory
    videos_dir = os.path.join("bot", "videos")
    if os.path.exists(videos_dir) and os.listdir(videos_dir):
        # Take the first video file
        for filename in os.listdir(videos_dir):
            if filename.endswith(".mp4") or filename.endswith(".mov"):
                source_path = os.path.join(videos_dir, filename)
                shutil.copy(source_path, test_video_path)
                print(f"Copied test video from {source_path} to {test_video_path}")
                return test_video_path
    
    # Create a very small empty video file if no existing videos
    print("Creating empty test video file")
    with open(test_video_path, 'wb') as f:
        f.write(b'TEST VIDEO CONTENT')
    return test_video_path

def create_test_bulk_upload(name="Test Bulk Upload", add_video=True):
    """Create a test bulk upload task with the first available account"""
    print(f"Creating test bulk upload task: {name}")
    
    # Check if we have any accounts
    if not InstagramAccount.objects.exists():
        print(f"{Colors.RED}No Instagram accounts found. Please create at least one account first.{Colors.END}")
        return None
        
    # Create the bulk upload task
    bulk_task = BulkUploadTask.objects.create(
        name=name,
        status='PENDING',
        log=f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] Task created via CLI tool\n"
    )
    
    # Add the first account to the task
    account = InstagramAccount.objects.first()
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
        test_video_path = create_test_video()
        
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
        
        # Assign video to account
        bulk_video.assigned_to = bulk_account
        bulk_video.save()
        
        # Add a test caption
        title = VideoTitle.objects.create(
            bulk_task=bulk_task,
            title="Test video uploaded via Dolphin Anty integration #test #automation",
            used=True,
            assigned_to=bulk_video
        )
        
        print(f"Added test video and assigned to account {Colors.colorize(account.username, Colors.CYAN)}")
    
    print(f"{Colors.GREEN}Created bulk task {bulk_task.id}: {bulk_task.name}{Colors.END}")
    return bulk_task

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

def run_task_with_monitoring(task_id):
    """Run a bulk upload task with real-time monitoring"""
    print_separator(f"STARTING BULK UPLOAD TASK {task_id}")
    
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
    
    # Show videos table
    videos = task.videos.all().select_related('assigned_to__account')
    print_videos_table(videos)
    
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
    task.log += f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] Task started via CLI tool\n"
    task.save()
    
    print_separator("BROWSER STARTING")
    print(f"{Colors.BOLD}{Colors.YELLOW}IMPORTANT: Browser window will open - DO NOT CLOSE TERMINAL{Colors.END}")
    print(f"{Colors.BOLD}You can monitor progress in the web interface or watch this terminal{Colors.END}")
    print(f"{Colors.BOLD}Real-time status updates will appear below...{Colors.END}")
    print_separator()
    
    # Force environment variables for visibility
    os.environ["VISIBLE"] = "1"
    os.environ["HEADLESS"] = "0"
    
    # Start monitoring thread
    stop_event = threading.Event()
    monitor_thread = threading.Thread(target=monitor_task_progress, args=(task_id, stop_event))
    monitor_thread.daemon = True
    monitor_thread.start()
    
    # Run the task asynchronously
    try:
        asyncio.run(run_bulk_upload_task(task_id))
        
        # Stop monitoring
        stop_event.set()
        monitor_thread.join(timeout=1)
        
        # Get final status
        task.refresh_from_db()
        print_separator("UPLOAD COMPLETED")
        print_task_summary(task)
        
        # Show final accounts status
        accounts = task.accounts.all().select_related('account', 'proxy')
        print_accounts_table(accounts)
        
    except Exception as e:
        stop_event.set()
        print(f"{Colors.RED}Error during upload execution: {str(e)}{Colors.END}")
        return False
    
    print(f"{Colors.GREEN}Task {task_id} execution complete{Colors.END}")
    return True

def run_task(task_id):
    """Run a bulk upload task asynchronously"""
    return run_task_with_monitoring(task_id)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Instagram Bulk Upload CLI Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_bulk_upload.py --list                    # List all tasks
  python run_bulk_upload.py --create                  # Create new test task
  python run_bulk_upload.py --create --name "My Task" # Create task with custom name  
  python run_bulk_upload.py --run 5                   # Run task with ID 5
  python run_bulk_upload.py --status 5                # Show detailed status for task 5
        """
    )
    
    parser.add_argument('--create', action='store_true', help='Create a new test bulk upload task')
    parser.add_argument('--run', type=int, help='Run an existing bulk upload task by ID', default=None)
    parser.add_argument('--status', type=int, help='Show detailed status for a task by ID', default=None)
    parser.add_argument('--list', action='store_true', help='List all bulk upload tasks')
    parser.add_argument('--name', type=str, help='Name for the new task', default="Test Bulk Upload")
    parser.add_argument('--no-video', action='store_true', help='Do not add test video to the task')
    
    args = parser.parse_args()
    
    # Check if we have a Dolphin API token
    dolphin_token = os.environ.get("DOLPHIN_API_TOKEN")
    if not dolphin_token and not args.list and not args.status:
        print(f"{Colors.YELLOW}⚠️ No DOLPHIN_API_TOKEN found in environment. Please set it in a .env file or enter it now.{Colors.END}")
        dolphin_token = input("Enter your Dolphin API token (or press Enter to proceed anyway): ")
        if dolphin_token:
            # Set it for this session
            os.environ["DOLPHIN_API_TOKEN"] = dolphin_token
    
    if args.list:
        list_tasks()
    
    elif args.status:
        try:
            task = BulkUploadTask.objects.get(id=args.status)
            print_task_summary(task)
            
            # Show accounts table
            accounts = task.accounts.all().select_related('account', 'proxy')
            print_accounts_table(accounts)
            
            # Show videos table
            videos = task.videos.all().select_related('assigned_to__account')
            print_videos_table(videos)
            
        except BulkUploadTask.DoesNotExist:
            print(f"{Colors.RED}Task with ID {args.status} not found{Colors.END}")
    
    elif args.create:
        task = create_test_bulk_upload(name=args.name, add_video=not args.no_video)
        if task:
            print(f"\n{Colors.GREEN}Created task with ID: {task.id}{Colors.END}")
            
            # Ask if user wants to run it
            run_now = input(f"Do you want to run task {task.id} now? (y/n): ")
            if run_now.lower() == 'y':
                run_task(task.id)
    
    elif args.run:
        run_task(args.run)
    
    else:
        # Show help and list tasks by default
        parser.print_help()
        print("\n")
        list_tasks() 