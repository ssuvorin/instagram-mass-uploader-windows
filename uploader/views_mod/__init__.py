# Re-export split views
from .dashboard import dashboard
from .tasks import task_list, task_detail, create_task, start_task
from .accounts import account_list, account_detail, delete_account, create_account, edit_account, warm_account, change_account_proxy, import_accounts, import_accounts_ua_cookies, import_accounts_bundle
from .proxies import proxy_list, create_proxy, edit_proxy, test_proxy, import_proxies, validate_all_proxies, _validate_proxies_background, delete_proxy
from .bulk import bulk_upload_list, create_bulk_upload, bulk_upload_detail, add_bulk_videos, add_bulk_titles, start_bulk_upload, start_bulk_upload_api, get_bulk_task_logs, delete_bulk_upload, assign_titles_to_videos, assign_videos_to_accounts, all_videos_assigned, all_titles_assigned
from .cookie_robot import create_cookie_robot_task
from .misc import (
    cookie_task_detail, 
    cookie_dashboard, 
    cookie_task_list, 
    start_cookie_task, 
    account_cookies, 
    get_cookie_task_logs, 
    stop_cookie_task, 
    delete_cookie_task, 
    run_cookie_robot_task, 
    bulk_cookie_robot, 
    create_dolphin_profile, 
    edit_video_location_mentions, 
    bulk_edit_location_mentions, 
    bulk_change_proxy, 
    refresh_dolphin_proxies, 
    cleanup_inactive_proxies, 
    bulk_upload_logs, 
    captcha_notification, 
    get_captcha_status, 
    clear_captcha_notification, 
    refresh_cookies_from_profiles,
    # TikTok functions - Only UI rendering, no API handling
    tiktok_booster,
)

# Bulk login views
from .bulk_login import (
    bulk_login_list,
    create_bulk_login,
    bulk_login_detail,
    start_bulk_login,
    get_bulk_login_logs,
    delete_bulk_login,
)
