class Pages:
    main = "https://www.tiktok.com/foryou?lang=en"
    login = "https://www.tiktok.com/login/phone-or-email/email"
    upload = "https://www.tiktok.com/creator-center/upload?lang=en"
    forgot_password = "https://www.tiktok.com/login/email/forget-password"


class Login:
    username_field = "//input[@name=\"username\"]"
    password_field = "//input[@type=\"password\"]"
    login_button = "//button[@type=\"submit\"]"

    cookies_button = "div.button-wrapper"

    # Email locators
    code_field = "//input[@placeholder='Enter 6-digit code']"
    email_next_button = "//button[text()='Next']"

    # Forgot password
    forgot_password_button = "//a[text()='Forgot password?']"
    email_field = "//input[@placeholder='Email address']"
    code_button = "//button[text()='Send code']"
    new_password = "//input[@autocomplete='new-password']"


class Upload:
    iframe = "//iframe"

    upload_video = "//input[@type='file']"
    uploaded = "//span[contains(@class, 'TUXText') and text()='Uploaded']"
    description = "//div[@contenteditable='true']"

    visibility = "//div[@class='tiktok-select-selector']"
    options = ["Public", "Friends", "Private"]

    mention_box = "//div[contains(@class, 'mention-list-popover')]"
    mention_box_user_id = "//span[contains(@class, 'user-id')]"

    comment = "//label[.='Comment']/following-sibling::div/input"
    duet = "//label[.='Duet']/following-sibling::div/input"
    stitch = "//label[.='Stitch']/following-sibling::div/input"

    post = "//button[@data-e2e='post_video_button']"
    post_confirmation = "//div[text()='Video published']"
    upload_failed = "//span[text()='Upload failed']"
    uploading_status = "//span[@class='TUXText TUXText--tiktok-sans']"

    copyright_button = "//div[text()='Turn on']/.."
    content_may_be_restricted = "//div[contains(@class, 'jsx-2910096029') and contains(@class, 'common-modal-close')]"
    force_post = "//div[text()='Post now']/../.."


class Error:
    error_description = "//span[@role='status']"


class Ads:
    banner = "//div[text()='Choose how ads are shown']"
    button = "//div[@class='webapp-pa-prompt_container__ga_button']"


class Interests:
    banner = "//h1[text()='Choose your interests']"
    skip = "//div[text()='Skip']/../.."


class Feed:
    scroll_down = '//button[@class="TUXButton TUXButton--capsule TUXButton--medium TUXButton--secondary action-item css-1rxmjnh"]'
    like = "//button[starts-with(@aria-label, 'Like video')]"


class CheckAuth:
    activity_button = '//div[text()="Activity"]'
    messages_button = '//div[text()="Messages"]'

    got_it = "//div[text()='Got it']/../.."
