# Localization Audit Report

This report details the findings of a localization audit for the project, focusing on Cyrillic characters in CSS/XPath selectors within Python files.

## Summary of Files Requiring Attention

The following files contain Cyrillic characters in selectors and require attention:

-   `uploader/selectors_config.py`: This file contains the majority of the Cyrillic selectors.
-   `uploader/bulk_tasks_playwright_async.py`: This file uses the selectors defined in `selectors_config.py`.
-   `uploader/bulk_tasks_playwright.py`: This file also uses the selectors defined in `selectors_config.py`.
-   `uploader/constants.py`: This file contains Cyrillic text for various UI elements.
-   `uploader/forms.py`: This file contains Cyrillic text in form labels and help text.
-   `uploader/models.py`: This file contains Cyrillic text in model field help text.

## Detailed Findings

### File: `uploader/selectors_config.py`

This file defines the majority of the selectors used in the application. The following selectors contain Cyrillic characters and should be updated to their English equivalents.

#### `UPLOAD_BUTTON`

-   **Lines**: 10-16
-   **Original (RU)**:
    -   `'svg[aria-label="Новая публикация"]'`
    -   `'svg[aria-label*="Новая публикация"]'`
    -   `'svg[aria-label="Создать"]'`
    -   `'svg[aria-label*="Создать"]'`
    -   `'span:has-text("Создать")'`
    -   `'a:has(span:has-text("Создать"))'`
    -   `'div[role="button"]:has-text("Создать")'`
    -   `'button:has-text("Создать")'`
-   **Suggested (EN)**:
    -   `'svg[aria-label="New post"]'`
    -   `'svg[aria-label*="New post"]'`
    -   `'svg[aria-label="Create"]'`
    -   `'svg[aria-label*="Create"]'`
    -   `'span:has-text("Create")'`
    -   `'a:has(span:has-text("Create"))'`
    -   `'div[role="button"]:has-text("Create")'`
    -   `'button:has-text("Create")'`
-   **Context**: Selectors for the "New Post" or "Create" button.
-   **Notes**: The English equivalents are already present in the list of selectors. It is recommended to remove the Cyrillic selectors.

#### `POST_OPTION`

-   **Lines**: 68-79
-   **Original (RU)**:
    -   `'svg[aria-label="Публикация"]'`
    -   `'svg[aria-label*="Публикация"]'`
    -   `'a:has(svg[aria-label="Публикация"])'`
    -   `'div[role="menuitem"]:has(svg[aria-label="Публикация"])'`
    -   `'div[role="button"]:has(svg[aria-label="Публикация"])'`
    -   `'a:has(span:has-text("Публикация"))'`
    -   `'div[role="menuitem"]:has(span:has-text("Публикация"))'`
    -   `'div[role="button"]:has(span:has-text("Публикация"))'`
    -   `'span:has-text("Публикация")'`
-   **Suggested (EN)**:
    -   `'svg[aria-label="Post"]'`
    -   `'svg[aria-label*="Post"]'`
    -   `'a:has(svg[aria-label="Post"])'`
    -   `'div[role="menuitem"]:has(svg[aria-label="Post"])'`
    -   `'div[role="button"]:has(svg[aria-label="Post"])'`
    -   `'a:has(span:has-text("Post"))'`
    -   `'div[role="menuitem"]:has(span:has-text("Post"))'`
    -   `'div[role="button"]:has(span:has-text("Post"))'`
    -   `'span:has-text("Post")'`
-   **Context**: Selectors for the "Post" option in a menu.
-   **Notes**: It is recommended to add selectors with their English equivalents.

#### `FILE_INPUT`

-   **Lines**: 126-131
-   **Original (RU)**:
    -   `'button:has-text("Выбрать на компьютере")'`
    -   `'div[role="button"]:has-text("Выбрать на компьютере")'`
    -   `'button:has-text("Выбрать файлы")'`
    -   `'div[role="button"]:has-text("Выбрать файлы")'`
    -   `'button:has-text("Выбрать с компьютера")'`
    -   `'div[role="button"]:has-text("Выбрать с компьютера")'`
-   **Suggested (EN)**:
    -   `'button:has-text("Select from computer")'`
    -   `'div[role="button"]:has-text("Select from computer")'`
    -   `'button:has-text("Select files")'`
    -   `'div[role="button"]:has-text("Select files")'`
-   **Context**: Selectors for the file input button.
-   **Notes**: The English equivalents are already present in the list of selectors. It is recommended to remove the Cyrillic selectors.

#### `OK_BUTTON`

-   **Lines**: 178-182
-   **Original (RU)**:
    -   `'button:has-text("ОК")'`
-   **Suggested (EN)**:
    -   `'button:has-text("OK")'`
-   **Context**: Selector for the "OK" button.
-   **Notes**: It is recommended to add selector with its English equivalent.

#### `NEXT_BUTTON`

-   **Lines**: 187-194
-   **Original (RU)**:
    -   `'button:has-text("Далее")'`
    -   `'button:has-text("Продолжить")'`
    -   `'div[role="button"]:has-text("Далее")'`
    -   `'div[role="button"]:has-text("Продолжить")'`
-   **Suggested (EN)**:
    -   `'button:has-text("Next")'`
    -   `'button:has-text("Continue")'`
    -   `'div[role="button"]:has-text("Next")'`
    -   `'div[role="button"]:has-text("Continue")'`
-   **Context**: Selectors for the "Next" or "Continue" button.
-   **Notes**: The English equivalents are already present in the list of selectors. It is recommended to remove the Cyrillic selectors.

#### `SHARE_BUTTON`

-   **Lines**: 223-228
-   **Original (RU)**:
    -   `'button:has-text("Поделиться")'`
    -   `'button:has-text("Опубликовать")'`
    -   `'div[role="button"]:has-text("Поделиться")'`
    -   `'div[role="button"]:has-text("Опубликовать")'`
-   **Suggested (EN)**:
    -   `'button:has-text("Share")'`
    -   `'button:has-text("Post")'`
    -   `'div[role="button"]:has-text("Share")'`
    -   `'div[role="button"]:has-text("Post")'`
-   **Context**: Selectors for the "Share" or "Post" button.
-   **Notes**: It is recommended to add selectors with their English equivalents.

#### `CAPTION_FIELD`

-   **Lines**: 253-255
-   **Original (RU)**:
    -   `'textarea[aria-label*="Напишите подпись" i]'`
    -   `'textarea[placeholder*="подпись" i]'`
    -   `'div[contenteditable="true"][aria-label*="подпись" i]'`
-   **Suggested (EN)**:
    -   `'textarea[aria-label*="Write a caption" i]'`
    -   `'textarea[placeholder*="caption" i]'`
    -   `'div[contenteditable="true"][aria-label*="caption" i]'`
-   **Context**: Selectors for the caption field.
-   **Notes**: It is recommended to add selectors with their English equivalents.

#### `LOCATION_FIELD`

-   **Lines**: 311-327
-   **Original (RU)**:
    -   `'input[placeholder="Добавить место"]'`
    -   `'input[placeholder*="Добавить местоположение"]'`
-   **Suggested (EN)**:
    -   `'input[placeholder="Add location"]'`
-   **Context**: Selectors for the location field.
-   **Notes**: It is recommended to add selectors with their English equivalents.

#### `MENTIONS_FIELD`

-   **Lines**: 359-399
-   **Original (RU)**:
    -   `'input[placeholder="Добавить соавторов"]'`
-   **Suggested (EN)**:
    -   `'input[placeholder="Add collaborators"]'`
-   **Context**: Selectors for the mentions field.
-   **Notes**: It is recommended to add selector with its English equivalent.

#### `MENTIONS_DONE_BUTTON`

-   **Lines**: 438-472
-   **Original (RU)**:
    -   `"//div[text()='Готово']"`
    -   `"//button[text()='Готово']"`
    -   `'button:has-text("Готово")'`
    -   `'button:has-text("Продолжить")'`
    -   `'div[role="button"]:has-text("Готово")'`
-   **Suggested (EN)**:
    -   `"//div[text()='Done']"`
    -   `"//button[text()='Done']"`
    -   `'button:has-text("Done")'`
    -   `'button:has-text("Continue")'`
    -   `'div[role="button"]:has-text("Done")'`
-   **Context**: Selectors for the "Done" button in the mentions section.
-   **Notes**: It is recommended to add selectors with their English equivalents.

#### `LOGIN_USERNAME_FIELD`

-   **Lines**: 1377-1386
-   **Original (RU)**:
    -   `'input[aria-label*="Телефон"]'`
    -   `'input[placeholder*="Телефон"]'`
    -   `'input[aria-label*="Имя пользователя"]'`
    -   `'input[placeholder*="Имя пользователя"]'`
    -   `'input[aria-label*="электронный адрес"]'`
    -   `'input[placeholder*="электронный адрес"]'`
-   **Suggested (EN)**:
    -   `'input[aria-label*="Phone"]'`
    -   `'input[placeholder*="Phone"]'`
    -   `'input[aria-label*="Username"]'`
    -   `'input[placeholder*="Username"]'`
    -   `'input[aria-label*="email address"]'`
    -   `'input[placeholder*="email address"]'`
-   **Context**: Selectors for the username/phone/email field on the login page.
-   **Notes**: It is recommended to add selectors with their English equivalents.

#### `LOGIN_PASSWORD_FIELD`

-   **Lines**: 1392-1394
-   **Original (RU)**:
    -   `'input[aria-label*="Пароль"]'`
    -   `'input[placeholder*="Пароль"]'`
-   **Suggested (EN)**:
    -   `'input[aria-label*="Password"]'`
    -   `'input[placeholder*="Password"]'`
-   **Context**: Selectors for the password field on the login page.
-   **Notes**: It is recommended to add selectors with their English equivalents.

#### `LOGIN_BUTTON`

-   **Lines**: 1399-1401
-   **Original (RU)**:
    -   `'button:not([aria-disabled="true"]):has-text("Войти")'`
    -   `'div[role="button"]:not([aria-disabled="true"]):has-text("Войти")'`
-   **Suggested (EN)**:
    -   `'button:not([aria-disabled="true"]):has-text("Log In")'`
    -   `'div[role="button"]:not([aria-disabled="true"]):has-text("Log In")'`
-   **Context**: Selectors for the login button.
-   **Notes**: It is recommended to add selectors with their English equivalents.

#### `VERIFICATION_CODE_FIELD`

-   **Lines**: 2306-2308
-   **Original (RU)**:
    -   `'input[aria-label*="код"]'`
    -   `'input[placeholder*="код"]'`
-   **Suggested (EN)**:
    -   `'input[aria-label*="code"]'`
    -   `'input[placeholder*="code"]'`
-   **Context**: Selectors for the verification code field.
-   **Notes**: It is recommended to add selectors with their English equivalents.

#### `POST_SUCCESSFUL`

-   **Lines**: 315-330
-   **Original (RU)**:
    -   `'div:has-text("Ваша публикация опубликована")'`
    -   `'div:has-text("Публикация опубликована")'`
    -   `'div:has-text("Видео опубликовано")'`
    -   `'div:has-text("Пост опубликован")'`
    -   `'div:has-text("Опубликовано")'`
-   **Suggested (EN)**:
    -   `'div:has-text("Your post has been shared")'`
    -   `'div:has-text("Post shared")'`
    -   `'div:has-text("Video posted")'`
    -   `'div:has-text("Post published")'`
    -   `'div:has-text("Published")'`
-   **Context**: Selectors for the success message after posting a video.
-   **Notes**: It is recommended to add selectors with their English equivalents.

#### `CLOSE_BUTTON`

-   **Lines**: 338-354
-   **Original (RU)**:
    -   `'button[aria-label*="Закрыть"]'`
    -   `'svg[aria-label*="Закрыть"]'`
    -   `'[aria-label*="Закрыть"]'`
-   **Suggested (EN)**:
    -   `'button[aria-label*="Close"]'`
    -   `'svg[aria-label*="Close"]'`
    -   `'[aria-label*="Close"]'`
-   **Context**: Selectors for the "Close" button.
-   **Notes**: It is recommended to add selectors with their English equivalents.

#### `HOME_BUTTON`

-   **Lines**: 376-378
-   **Original (RU)**:
    -   `'svg[aria-label*="Главная"]'`
    -   `'svg[aria-label*="Создать"]'`
    -   `'[aria-label*="Главная"]'`
-   **Suggested (EN)**:
    -   `'svg[aria-label*="Home"]'`
    -   `'svg[aria-label*="Create"]'`
    -   `'[aria-label*="Home"]'`
-   **Context**: Selectors for the "Home" and "Create" buttons on the main page.
-   **Notes**: It is recommended to add selectors with their English equivalents.

#### `HUMAN_VERIFICATION_DIALOG`

-   **Lines**: 984-993
-   **Original (RU)**:
    -   `'span:has-text("подтвердите, что это вы")'`
    -   `'span:has-text("подтвердите что это вы")'`
    -   `'span:has-text("подтвердите, что вы")'`
    -   `'span:has-text("человек")'`
    -   `'div:has-text("целостности аккаунта")'`
    -   `'div:has-text("целостность аккаунта")'`
    -   `'span:has-text("Почему вы это видите")'`
    -   `'span:has-text("Что это означает")'`
    -   `'span:has-text("Что можно сделать")'`
-   **Suggested (EN)**:
    -   `'span:has-text("confirm it's you")'`
    -   `'span:has-text("confirm you are human")'`
    -   `'div:has-text("account integrity")'`
    -   `'span:has-text("Why you are seeing this")'`
    -   `'span:has-text("What this means")'`
    -   `'span:has-text("What you can do")'`
-   **Context**: Selectors for the human verification dialog.
-   **Notes**: It is recommended to add selectors with their English equivalents.

#### `CROP_BUTTON`

-   **Lines**: 1017-1020
-   **Original (RU)**:
    -   `'svg[aria-label="Выбрать размер и обрезать"]'`
    -   `'svg[aria-label*="Выбрать размер"]'`
    -   `'svg[aria-label*="обрезать"]'`
    -   `'svg[aria-label*="размер"]'`
-   **Suggested (EN)**:
    -   `'svg[aria-label="Select size and crop"]'`
    -   `'svg[aria-label*="Select size"]'`
    -   `'svg[aria-label*="crop"]'`
    -   `'svg[aria-label*="size"]'`
-   **Context**: Selectors for the crop button.
-   **Notes**: It is recommended to add selectors with their English equivalents.

#### `ORIGINAL_CROP_OPTION`

-   **Lines**: 1084-1110
-   **Original (RU)**:
    -   `'span:has-text("Оригинал")'`
    -   `'div[role="button"]:has(span:has-text("Оригинал"))'`
    -   `'button:has(span:has-text("Оригинал"))'`
    -   `'div[role="button"]:has-text("Оригинал")'`
    -   `'button:has-text("Оригинал")'`
    -   `'svg[aria-label="Значок контура фото"]'`
    -   `'svg[aria-label*="контур"]'`
    -   `'svg[aria-label*="фото"]'`
-   **Suggested (EN)**:
    -   `'span:has-text("Original")'`
    -   `'div[role="button"]:has(span:has-text("Original"))'`
    -   `'button:has(span:has-text("Original"))'`
    -   `'div[role="button"]:has-text("Original")'`
    -   `'button:has-text("Original")'`
    -   `'svg[aria-label="Photo outline icon"]'`
    -   `'svg[aria-label*="outline"]'`
    -   `'svg[aria-label*="photo"]'`
-   **Context**: Selectors for the "Original" crop option.
-   **Notes**: It is recommended to add selectors with their English equivalents.

#### `COOKIE_CONSENT_BUTTON`

-   **Lines**: 725-730
-   **Original (RU)**:
    -   `'button:has-text("Разрешить все cookie")'`
    -   `'button:has-text("Разрешить все файлы cookie")'`
    -   `'button[class*="_asz1"]:has-text("Разрешить")'`
    -   `'button[class*="_a9--"]:has-text("Разрешить")'`
    -   `'button[tabindex="0"]:has-text("Разрешить все")'`
    -   `'button[tabindex="0"]:has-text("Разрешить")'`
-   **Suggested (EN)**:
    -   `'button:has-text("Allow all cookies")'`
    -   `'button:has-text("Allow all")'`
    -   `'button:has-text("Allow")'`
-   **Context**: Selectors for the cookie consent button.
-   **Notes**: The English equivalents are already present in the list of selectors. It is recommended to remove the Cyrillic selectors.

#### `COOKIE_DECLINE_BUTTON`

-   **Lines**: 793-796
-   **Original (RU)**:
    -   `'button:has-text("Отклонить необязательные файлы cookie")'`
    -   `'button:has-text("Отклонить необязательные")'`
    -   `'button:has-text("Отклонить")'`
    -   `'button[class*="_a9_1"]:has-text("Отклонить")'`
-   **Suggested (EN)**:
    -   `'button:has-text("Decline optional cookies")'`
    -   `'button:has-text("Decline")'`
-   **Context**: Selectors for the cookie decline button.
-   **Notes**: It is recommended to add selectors with their English equivalents.

#### `COOKIE_MODAL_INDICATORS`

-   **Lines**: 820-828
-   **Original (RU)**:
    -   `'h2:has-text("Разрешить использование файлов cookie")'`
    -   `'h1:has-text("Разрешить использование файлов cookie")'`
    -   `'div:has-text("Мы используем файлы cookie")'`
    -   `'span:has-text("файлы cookie")'`
-   **Suggested (EN)**:
    -   `'h2:has-text("Allow the use of cookies")'`
    -   `'h1:has-text("Allow the use of cookies")'`
    -   `'div:has-text("We use cookies")'`
    -   `'span:has-text("cookies")'`
-   **Context**: Selectors for the cookie consent modal.
-   **Notes**: It is recommended to add selectors with their English equivalents.

### File: `uploader/forms.py` and `uploader/models.py`

These files contain Cyrillic characters in `label` and `help_text` attributes of form and model fields. While these are not CSS/XPath selectors, they are part of the user interface and should be translated for a fully localized application.

**Example from `uploader/forms.py`:**

-   **Line**: 80
-   **Original (RU)**: `label="Локация по умолчанию"`
-   **Suggested (EN)**: `label="Default Location"`

**Example from `uploader/models.py`:**

-   **Line**: 249
-   **Original (RU)**: `help_text="Шаблон локации для копирования в видео (не применяется автоматически)"`
-   **Suggested (EN)**: `help_text="Location template to copy to videos (not applied automatically)"`

### General Recommendations

-   It is highly recommended to replace all Cyrillic selectors with their English equivalents to improve code readability and maintainability, especially in a multilingual development environment.
-   For UI text in `forms.py` and `models.py`, consider using Django's built-in internationalization and localization features to manage translations.
-   The `uploader/constants.py` file also contains a significant amount of Cyrillic text. This should be reviewed and translated as well.
-   The files `uploader/bulk_tasks_playwright_async.py` and `uploader/bulk_tasks_playwright.py` use the selectors defined in `uploader/selectors_config.py`. Once the selectors are updated in the config file, these files will automatically use the updated selectors.
