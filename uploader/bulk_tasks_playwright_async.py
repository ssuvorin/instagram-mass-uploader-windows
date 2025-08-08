"""
Асинхронная версия bulk upload tasks для Instagram automation - ПОЛНАЯ КОПИЯ sync версии
"""

import os
import asyncio
import time
import traceback
import logging
import random
import math
import json
import tempfile
import shutil
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any, Optional, Callable, Awaitable
from pathlib import Path
import aiohttp

# Import all the same optimization modules as sync version
from .constants import (
    TimeConstants, InstagramTexts, BrowserConfig, Limits, TaskStatus, LogCategories, FilePaths,
    VerboseFilters, InstagramSelectors, APIConstants
)
from .selectors_config import InstagramSelectors as SelectorConfig, SelectorUtils
from .task_utils import (
    update_task_log, update_account_task, update_task_status, get_account_username,
    get_account_from_task, mark_account_as_used, get_task_with_accounts, 
    get_account_tasks, get_assigned_videos, get_all_task_videos, get_all_task_titles,
    handle_verification_error, handle_task_completion, handle_emergency_cleanup,
    process_browser_result, handle_account_task_error, handle_critical_task_error
)
from .account_utils import (
    get_account_details, get_proxy_details, get_account_proxy,
    get_account_dolphin_profile_id, save_dolphin_profile_id
)
from .browser_support import (
    cleanup_hanging_browser_processes, safely_close_all_windows,
    simulate_human_rest_behavior, simulate_normal_browsing_behavior,
    simulate_extended_human_rest_behavior
)
from .instagram_automation import InstagramNavigator, InstagramUploader, InstagramLoginHandler
from .browser_utils import BrowserManager, PageUtils, ErrorHandler, NetworkUtils, FileUtils, DebugUtils
from .crop_handler import CropHandler, handle_crop_and_aspect_ratio
from .logging_utils import log_info, log_error, log_debug, log_warning
from .human_behavior import AdvancedHumanBehavior, init_human_behavior, get_human_behavior
from .captcha_solver import solve_recaptcha_if_present, detect_recaptcha_on_page, solve_recaptcha_if_present_sync

# Import email verification functions
from .email_verification_async import (
    get_email_verification_code_async,
    get_2fa_code_async,
    determine_verification_type_async
)

# Configure Django settings for async operations
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'instagram_uploader.settings')
import django
django.setup()

from .models import InstagramAccount, BulkUploadAccount
from .async_impl.types import PlaywrightLogFilter


# Apply browser environment configuration (ПОЛНАЯ КОПИЯ из sync)
for env_var, value in BrowserConfig.ENV_VARS.items():
    os.environ[env_var] = value

# Suppress browser console logs and detailed traces (ПОЛНАЯ КОПИЯ из sync)
os.environ['PLAYWRIGHT_BROWSERS_PATH'] = '0'
os.environ['DEBUG'] = ''
os.environ['PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD'] = '1'

# Additional environment variables to suppress verbose Playwright output (ПОЛНАЯ КОПИЯ из sync)
os.environ['PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS'] = '1'
os.environ['PLAYWRIGHT_DISABLE_COLORS'] = '1'
os.environ['PLAYWRIGHT_QUIET'] = '1'

# Suppress Chrome/Chromium verbose logging (ПОЛНАЯ КОПИЯ из sync)
os.environ['CHROME_LOG_FILE'] = '/dev/null'
os.environ['CHROME_HEADLESS'] = '1'

# Disable verbose Playwright logging (ПОЛНАЯ КОПИЯ из sync)
logging.getLogger('playwright').setLevel(logging.ERROR)
logging.getLogger('playwright._impl').setLevel(logging.ERROR)

# Suppress other verbose loggers (ПОЛНАЯ КОПИЯ из sync)
for logger_name in ['urllib3', 'requests', 'asyncio']:
    logging.getLogger(logger_name).setLevel(logging.WARNING)

# Configure Python logging to filter out Playwright verbose messages (ПОЛНАЯ КОПИЯ из sync)

# Apply the filter to all relevant loggers (ПОЛНАЯ КОПИЯ из sync)
playwright_filter = PlaywrightLogFilter()
for logger_name in ['playwright', 'playwright._impl', 'playwright.sync_api', 'root']:
    try:
        target_logger = logging.getLogger(logger_name)
        target_logger.addFilter(playwright_filter)
        target_logger.setLevel(logging.CRITICAL)
    except:
        pass

# Also apply to the root logger to catch any unfiltered messages (ПОЛНАЯ КОПИЯ из sync)
root_logger = logging.getLogger()
root_logger.addFilter(playwright_filter)

# Import Playwright and Bot modules (ПОЛНАЯ КОПИЯ из sync)
try:
    from playwright.async_api import async_playwright
    from bot.src.instagram_uploader.dolphin_anty import DolphinAnty
    from bot.src.instagram_uploader.browser_dolphin import DolphinBrowser
    from bot.src.instagram_uploader.email_client import Email
except ImportError as e:
    log_info(f"Error importing required modules: {str(e)}. Make sure they're installed.")

# Setup logging (ПОЛНАЯ КОПИЯ из sync)
logger = logging.getLogger('uploader.async_bulk_tasks')











































































# Add configuration for parallel processing
PARALLEL_CONFIG = {
    'MAX_CONCURRENT_ACCOUNTS': 3,  # Maximum accounts to process simultaneously
    'MAX_RETRIES_PER_ACCOUNT': 2,  # Retry failed accounts
    'ACCOUNT_START_DELAY': (5, 15), # Random delay between starting accounts
    'BATCH_SIZE': 5,  # Process accounts in batches
}





# Helper functions for async operations





# Main entry point - use parallel version




# Add this new retry function after the imports section (around line 100)


# === Auto-imports from async_impl ===
from .async_impl.dolphin import AsyncDolphinBrowser, authenticate_dolphin_async, cleanup_browser_session_async, get_dolphin_profile_id_async, run_dolphin_browser_async
from .async_impl.services import perform_final_cleanup_async, perform_instagram_operations_async, update_account_last_used_async, update_account_status_async, update_task_status_async
from .async_impl.human import _human_click_with_timeout_async, _type_like_human_async, click_element_with_behavior_async, init_human_behavior_async, simulate_human_mouse_movement_async, simulate_mouse_movement_to_element_async, simulate_page_scan_async, simulate_random_browsing_async
from .async_impl.login import check_post_login_verifications_async, handle_2fa_async, handle_email_verification_async, handle_login_completion_async, handle_login_flow_async, handle_save_login_info_dialog_async, perform_enhanced_instagram_login_async, perform_instagram_login_optimized_async
from .async_impl.utils_dom import _find_any_available_option_async, _find_original_by_first_position_async, _find_original_by_svg_icon_async, _find_original_by_text_content_async, _quick_click_async, add_video_location_async, add_video_mentions_async, check_for_account_suspension_async, check_for_dropdown_menu_async, check_for_phone_verification_page_async, check_if_already_logged_in_async, check_video_posted_successfully_async, cleanup_original_video_files_async, click_post_option_async, click_share_button_async, find_element_with_selectors_async, get_account_details_async, get_assigned_videos_async, handle_cookie_consent_async, handle_email_field_verification_async, handle_recaptcha_if_present_async, log_video_info_async, prepare_unique_videos_async, retry_navigation_async, safely_close_all_windows_async, verify_page_elements_state_async, wait_for_page_ready_async
from .async_impl.upload import add_human_delay_between_uploads_async, add_video_caption_async, click_next_button_async, handle_post_upload_click_async, handle_reels_dialog_async, navigate_to_upload_alternative_async, navigate_to_upload_core_async, navigate_to_upload_with_human_behavior_async, retry_upload_with_page_refresh_async, run_bulk_upload_task_async, run_bulk_upload_task_parallel_async, try_broader_upload_detection_async, upload_video_core_async, upload_video_with_human_behavior_async
from .async_impl.file_input import check_for_file_dialog_async, check_for_human_verification_dialog_async, find_file_input_adaptive_async, find_input_via_broad_search_async, find_input_via_button_async, find_input_via_css_patterns_async, find_input_via_dialog_structure_async, find_input_via_form_context_async, is_valid_file_input_async
from .async_impl.crop import _find_crop_by_context_analysis_async, _find_crop_by_fallback_patterns_async, _find_crop_by_semantic_attributes_async, _find_crop_by_svg_content_async, _handle_crop_adaptive_async, _human_click_crop_button_async, _select_original_aspect_ratio_async, _verify_crop_page_adaptive_async, handle_crop_async
from .async_impl.runner import get_task_with_accounts_async, process_account_batch_async, process_single_account_with_semaphore_async
from .async_impl.types import PlaywrightLogFilter