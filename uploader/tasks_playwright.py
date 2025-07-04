import os
import json
import time
import traceback
import subprocess
import logging
from tempfile import NamedTemporaryFile
from pathlib import Path
from .models import UploadTask, VideoFile, InstagramAccount, DolphinCookieRobotTask
from dotenv import load_dotenv
from bot.src.instagram_uploader.dolphin_anty import DolphinAnty

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

def run_bot_with_playwright(account, video_files, task_id):
    """
    Runs Instagram bot with Playwright and Dolphin Anty to upload videos
    """
    try:
        # Convert account data to JSON format
        account_data = account.to_dict()
        account_data["account_id"] = task_id  # Add task ID as account ID for cookie saving
        logger.info(f"Converted account data to JSON format")
        
        # Save video files to temporary files
        temp_files = []
        saved_video_paths = []
        
        for video_file in video_files:
            # Create a temporary file
            video_filename = os.path.basename(video_file.video_file.name)
            with NamedTemporaryFile(delete=False, suffix=f"_{video_filename}") as tmp:
                for chunk in video_file.video_file.chunks():
                    tmp.write(chunk)
                logger.info(f"Saved video: {tmp.name}")
                temp_files.append(tmp.name)
                saved_video_paths.append(tmp.name)
        
        # Prepare environment variables for bot execution
        env = os.environ.copy()
        env["PYTHONPATH"] = os.getcwd()
        env["VISIBLE"] = "1"  # Display browser
        env["HEADLESS"] = "0"  # Force non-headless mode
        
        # Write account data and video paths to temporary files
        account_file = NamedTemporaryFile(delete=False, mode='w')
        json.dump(account_data, account_file)
        account_file.close()
        
        videos_file = NamedTemporaryFile(delete=False, mode='w')
        json.dump(saved_video_paths, videos_file)
        videos_file.close()
        
        # Get Dolphin API token from environment variables
        dolphin_token = os.environ.get("DOLPHIN_API_TOKEN")
        
        # Build the command
        cmd = [
            "python", "bot/run_bot_playwright.py",
            "--account", account_file.name,
            "--videos", videos_file.name,
            "--non-interactive",
            "--visible"  # Explicitly request visible browser
        ]
        
        # Add proxy if available
        if account.proxy:
            # Write proxy data to temporary file
            proxy_file = NamedTemporaryFile(delete=False, mode='w')
            json.dump(account.proxy.to_dict(), proxy_file)
            proxy_file.close()
            # Add --proxy parameter to command
            cmd.extend(["--proxy", proxy_file.name])
        
        # Add Dolphin token if available
        if dolphin_token:
            cmd.extend(["--dolphin-token", dolphin_token])
        
        # Run the bot
        logger.info("Starting bot with Playwright and Dolphin Anty in visible mode...")
        process = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        
        # Record results
        stdout_text = stdout.decode()
        stderr_text = stderr.decode() if stderr else ""
        
        logger.info(f"Bot output:\n{stdout_text}")
        if stderr_text:
            logger.error(f"Errors:\n{stderr_text}")
        
        # Clean up temporary files
        for file_path in temp_files:
            if os.path.exists(file_path):
                os.unlink(file_path)
        
        os.unlink(account_file.name)
        os.unlink(videos_file.name)
        if account.proxy:
            os.unlink(proxy_file.name)
        
        # Update Dolphin profile ID if it's in the output and not already set
        if not account.dolphin_profile_id:
            # Look for a line like "✅ Profile Dolphin 12345678 saved for account"
            import re
            profile_matches = re.findall(r"Profile Dolphin ([a-zA-Z0-9]+) saved for account", stdout_text)
            if profile_matches:
                dolphin_profile_id = profile_matches[0]
                logger.info(f"Detected new Dolphin profile ID: {dolphin_profile_id}")
                account.dolphin_profile_id = dolphin_profile_id
                account.save(update_fields=['dolphin_profile_id'])
                logger.info(f"Saved Dolphin profile ID to account {account.username}")
        
        return process.returncode == 0, stdout_text, stderr_text
        
    except Exception as e:
        error_message = f"Error running bot: {e}\n{traceback.format_exc()}"
        logger.error(error_message)
        return False, "", error_message

def run_upload_task(task_id):
    """
    Run an upload task in the background
    """
    task = UploadTask.objects.get(id=task_id)
    task.status = 'RUNNING'
    task.save()
    
    try:
        # Get the video file
        video_file = VideoFile.objects.filter(task=task).first()
        if not video_file:
            task.log += "No video file found for this task.\n"
            task.status = 'FAILED'
            task.save()
            return
        
        # Run the bot with Playwright
        success, stdout, stderr = run_bot_with_playwright(task.account, [video_file], task_id)
        
        # Update task with result
        if success:
            task.status = 'COMPLETED'
            task.log += f"Upload successful!\n"
        else:
            task.status = 'FAILED'
            task.log += f"Upload failed. Check the logs for details.\n"
        
        # Add stdout and stderr to log
        task.log += f"\nOutput:\n{stdout}\n\nErrors:\n{stderr}\n"
        task.save()
        
        # Mark account as used
        task.account.mark_as_used()
        
    except Exception as e:
        task.status = 'FAILED'
        task.log += f"Exception occurred: {str(e)}\n"
        task.log += traceback.format_exc()
        task.save()

def run_cookie_robot_task(task_id):
    """
    Run a cookie robot task in the background
    """
    task = DolphinCookieRobotTask.objects.get(id=task_id)
    task.status = 'RUNNING'
    
    log_message = f"Starting Cookie Robot task for task ID: {task_id}"
    task.log += log_message + "\n"
    logger.info(log_message)
    
    log_message = f"URLs to visit: {task.urls}"
    task.log += log_message + "\n"
    logger.info(log_message)
    
    log_message = f"Headless mode: {task.headless}"
    task.log += log_message + "\n"
    logger.info(log_message)
    
    log_message = f"Disable images: {task.imageless}"
    task.log += log_message + "\n"
    logger.info(log_message)
    
    task.save()
    
    try:
        # Get the account
        account = task.account
        log_message = f"Using account: {account.username}"
        task.log += log_message + "\n"
        logger.info(log_message)
        
        # Check if account has a Dolphin profile ID
        if not account.dolphin_profile_id:
            log_message = f"❌ Error: Account does not have a Dolphin profile ID."
            task.log += log_message + "\n"
            logger.error(log_message)
            task.status = 'FAILED'
            task.save()
            return
        
        log_message = f"Using Dolphin profile ID: {account.dolphin_profile_id}"
        task.log += log_message + "\n"
        logger.info(log_message)
        
        # Initialize Dolphin API
        api_key = os.environ.get("DOLPHIN_API_TOKEN", "")
        if not api_key:
            log_message = f"❌ Error: Dolphin API token not found in environment variables."
            task.log += log_message + "\n"
            logger.error(log_message)
            task.status = 'FAILED'
            task.save()
            return
        
        log_message = f"Initializing Dolphin API client..."
        logger.info(log_message)
        task.log_message = log_message
        task.save(update_fields=['log_message'])

        # Get Dolphin API host from environment (critical for Docker Windows deployment)
        dolphin_api_host = os.environ.get("DOLPHIN_API_HOST", "http://localhost:3001/v1.0")
        if not dolphin_api_host.endswith("/v1.0"):
            dolphin_api_host = dolphin_api_host.rstrip("/") + "/v1.0"
        
        dolphin = DolphinAnty(api_key=api_key, local_api_base=dolphin_api_host)
        
        # Run the cookie robot
        log_message = f"🚀 Starting Cookie Robot on Dolphin profile {account.dolphin_profile_id}..."
        task.log += log_message + "\n"
        logger.info(log_message)
        
        result = dolphin.run_cookie_robot_sync(
            profile_id=account.dolphin_profile_id,
            urls=task.urls,
            headless=task.headless,
            imageless=task.imageless
        )
        
        # Update task with result
        if result.get('success', False):
            task.status = 'COMPLETED'
            log_message = f"✅ Cookie Robot completed successfully!"
            task.log += log_message + "\n"
            logger.info(log_message)
            
            log_message = f"Response details:"
            task.log += log_message + "\n"
            logger.info(log_message)
            
            response_json = json.dumps(result.get('data', {}), indent=2)
            task.log += response_json + "\n"
            logger.info(f"Response JSON: {response_json}")
        else:
            task.status = 'FAILED'
            error_details = result.get('error', 'Unknown error')
            log_message = f"❌ Cookie Robot failed: {error_details}"
            task.log += log_message + "\n"
            logger.error(log_message)
            
            # Add full error details if available
            if isinstance(error_details, dict):
                error_json = json.dumps(error_details, indent=2)
                task.log += f"Full error details:\n{error_json}\n"
                logger.error(f"Full API error: {error_json}")
        
        task.save()
        
    except Exception as e:
        task.status = 'FAILED'
        log_message = f"❌ Exception occurred: {str(e)}"
        task.log += log_message + "\n"
        logger.error(log_message)
        
        stack_trace = traceback.format_exc()
        task.log += stack_trace
        logger.error(f"Stack trace: {stack_trace}")
        
        task.save() 