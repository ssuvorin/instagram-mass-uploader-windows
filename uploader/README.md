# REAL REFACTOR – implementations moved

How to use:
1. Backup your original `bulk_tasks_playwright_async.py`
2. Copy `uploader_real/async_impl/` next to it.
3. Replace your original `bulk_tasks_playwright_async.py` with `uploader_real/bulk_tasks_playwright_async.py`
4. Run your flows. If any missing import appears, send me the traceback.

Summary:
{
  "functions_moved": 87,
  "classes_moved": 2,
  "group_counts": {
    "dolphin": 5,
    "services": 5,
    "human": 8,
    "login": 8,
    "utils_dom": 27,
    "upload": 14,
    "file_input": 9,
    "crop": 9,
    "runner": 3,
    "types": 1
  },
  "module_dependencies": {
    "dolphin": [
      "services:perform_instagram_operations_async",
      "services:update_account_last_used_async",
      "services:update_account_status_async"
    ],
    "services": [
      "human:init_human_behavior_async",
      "login:check_post_login_verifications_async",
      "login:handle_login_flow_async",
      "upload:add_human_delay_between_uploads_async",
      "upload:navigate_to_upload_with_human_behavior_async",
      "upload:upload_video_with_human_behavior_async",
      "utils_dom:handle_cookie_consent_async",
      "utils_dom:log_video_info_async",
      "utils_dom:retry_navigation_async"
    ],
    "human": [
      "utils_dom:_quick_click_async"
    ],
    "login": [
      "file_input:check_for_human_verification_dialog_async",
      "utils_dom:check_if_already_logged_in_async",
      "utils_dom:handle_email_field_verification_async",
      "utils_dom:handle_recaptcha_if_present_async"
    ],
    "utils_dom": [
      "file_input:check_for_file_dialog_async",
      "human:_type_like_human_async",
      "human:click_element_with_behavior_async",
      "human:simulate_human_mouse_movement_async",
      "human:simulate_page_scan_async"
    ],
    "upload": [
      "crop:handle_crop_async",
      "file_input:check_for_file_dialog_async",
      "file_input:find_file_input_adaptive_async",
      "human:_type_like_human_async",
      "human:click_element_with_behavior_async",
      "human:simulate_page_scan_async",
      "human:simulate_random_browsing_async",
      "runner:get_task_with_accounts_async",
      "runner:process_account_batch_async",
      "services:update_task_status_async",
      "utils_dom:add_video_location_async",
      "utils_dom:add_video_mentions_async",
      "utils_dom:check_for_dropdown_menu_async",
      "utils_dom:check_video_posted_successfully_async",
      "utils_dom:cleanup_original_video_files_async",
      "utils_dom:click_post_option_async",
      "utils_dom:click_share_button_async",
      "utils_dom:find_element_with_selectors_async",
      "utils_dom:retry_navigation_async",
      "utils_dom:wait_for_page_ready_async"
    ],
    "crop": [
      "human:_human_click_with_timeout_async",
      "upload:handle_reels_dialog_async",
      "utils_dom:_find_any_available_option_async",
      "utils_dom:_find_original_by_first_position_async",
      "utils_dom:_find_original_by_svg_icon_async",
      "utils_dom:_find_original_by_text_content_async"
    ],
    "runner": [
      "dolphin:run_dolphin_browser_async",
      "utils_dom:get_account_details_async",
      "utils_dom:get_assigned_videos_async",
      "utils_dom:prepare_unique_videos_async"
    ]
  }
}
