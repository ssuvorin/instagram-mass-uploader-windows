import os
import time
import logging
import asyncio
import requests

logger = logging.getLogger(__name__)


def play_sound_notification():
    """Воспроизвести звуковое оповещение"""
    try:
        # Для macOS
        os.system("afplay /System/Library/Sounds/Glass.aiff")
    except:
        try:
            # Для Linux
            os.system("paplay /usr/share/sounds/freedesktop/stereo/complete.oga")
        except:
            try:
                # Для Windows
                os.system("powershell -c '[console]::beep(800,500)'")
            except:
                # Fallback - просто выводим в консоль
                print("\n" + "🔔" * 10)
                print("🔔 CAPTCHA DETECTED - PLEASE SOLVE IT! 🔔")
                print("🔔" * 10 + "\n")


def send_captcha_notification_to_dashboard(bulk_upload_id):
    """Отправить уведомление на dashboard о необходимости решения капчи"""
    try:
        # Отправляем POST запрос на dashboard для показа баннера
        notification_data = {
            "type": "captcha_detected",
            "message": "CAPTCHA detected! Please solve it manually in the browser.",
            "bulk_upload_id": bulk_upload_id,
            "timestamp": time.time()
        }
        
        # Отправляем уведомление на dashboard
        try:
            response = requests.post(
                f"http://127.0.0.1:8000/api/captcha-notification/", 
                json=notification_data,
                timeout=5
            )
            if response.status_code == 200:
                print(f"📢 Captcha notification sent to dashboard for bulk upload {bulk_upload_id}")
            else:
                print(f"[WARN] Failed to send captcha notification: {response.status_code}")
        except requests.exceptions.RequestException:
            # Если API недоступен, просто логируем
            print(f"📢 Captcha detected for bulk upload {bulk_upload_id} - notification logged")
                
    except Exception as e:
        print(f"[FAIL] Error sending captcha notification: {e}")


async def detect_recaptcha_on_page_async(page):
    """
    Определить наличие reCAPTCHA на странице
    """
    try:
        page_url = page.url
        print(f"🔍 Checking for reCAPTCHA on {page_url}")
        
        # СПЕЦИАЛЬНО ДЛЯ CHALLENGE-СТРАНИЦ INSTAGRAM
        if '/challenge/' in page_url:
            print("🚨 Instagram challenge page detected!")
            
            # Проверяем наличие Facebook's reCAPTCHA iframe
            try:
                fb_recaptcha_iframe = page.locator('iframe[src*="fbsbx.com/captcha/recaptcha/iframe"]')
                if await fb_recaptcha_iframe.count() > 0:
                    iframe_src = await fb_recaptcha_iframe.first.get_attribute('src')
                    print(f"[OK] Found Facebook's reCAPTCHA iframe")
                else:
                    print("[WARN] Facebook's reCAPTCHA iframe not found")
            except Exception as e:
                print(f"[WARN] Error in Facebook's reCAPTCHA detection: {e}")
            
            return {
                "site_key": None,  # Не нужен для ручного решения
                "page_url": page_url,
                "iframe_present": True,
                "is_invisible": False,
                "is_challenge_page": True,
                "is_facebook_recaptcha": True
            }
        
        # Обычная логика для не-challenge страниц
        return None
        
    except Exception as e:
        print(f"[FAIL] Error detecting reCAPTCHA: {str(e)}")
        return None


async def solve_recaptcha_if_present(page, account_details=None, max_attempts=3):
    """
    РУЧНОЕ решение reCAPTCHA с ожиданием действий пользователя
    """
    try:
        print("[BOT] Starting MANUAL reCAPTCHA solving")
            
        # Определяем капчу
        captcha_params = await detect_recaptcha_on_page_async(page)
            
        if not captcha_params:
            print("[OK] No reCAPTCHA detected")
            return True
        
        page_url = captcha_params.get("page_url")
        is_challenge_page = captcha_params.get("is_challenge_page", False)
        
        print(f"🔍 Detected reCAPTCHA:")
        print(f"   - Page URL: {page_url}")
        print(f"   - Challenge Page: {is_challenge_page}")
        
        # Звуковое оповещение
        play_sound_notification()
        
        # Уведомление на dashboard (если есть bulk_upload_id)
        if account_details and account_details.get("bulk_upload_id"):
            send_captcha_notification_to_dashboard(account_details["bulk_upload_id"])
        
        # Запоминаем начальный URL для отслеживания изменений
        initial_url = page.url
        start_time = time.time()
        timeout_seconds = 5 * 60  # 5 минут
        check_interval_seconds = 30  # Проверяем каждые 30 секунд
        
        print(f"[WAIT] Waiting for manual solution... (timeout: 5 minutes)")
        print(f"📋 Please solve the reCAPTCHA manually in the browser")
        print(f"[RETRY] Will check every {check_interval_seconds} seconds for page change")
        
        check_count = 0
        
        while time.time() - start_time < timeout_seconds:
            check_count += 1
            elapsed_minutes = int((time.time() - start_time) / 60)
            elapsed_seconds = int(time.time() - start_time) % 60
            
            print(f"🔍 Check #{check_count} - {elapsed_minutes}m {elapsed_seconds}s elapsed")
            
            try:
                # Проверяем изменился ли URL (успешное решение)
                current_url = page.url
                if current_url != initial_url:
                    print(f"[OK] Page URL changed from {initial_url} to {current_url}")
                    print(f"[OK] Manual reCAPTCHA solution successful!")
                    return True
            
                # Ждем до следующей проверки
                remaining_time = timeout_seconds - (time.time() - start_time)
                remaining_minutes = int(remaining_time / 60)
                remaining_seconds = int(remaining_time % 60)
                
                print(f"[WAIT] Next check in {check_interval_seconds}s (remaining: {remaining_minutes}m {remaining_seconds}s)")
                await page.wait_for_timeout(check_interval_seconds * 1000)
                
            except Exception as e:
                print(f"[FAIL] Error during manual captcha check: {e}")
                await page.wait_for_timeout(check_interval_seconds * 1000)
        
        # Таймаут достигнут
        print(f"[FAIL] Manual reCAPTCHA solving timeout after 5 minutes")
        print(f"[FAIL] User did not solve the reCAPTCHA in time")
        return False
        
    except Exception as e:
        print(f"[FAIL] Error in manual reCAPTCHA solving: {e}")
        return False


async def handle_recaptcha_if_present_async(page, account_details=None):
    """Обработка reCAPTCHA если присутствует - алиас для совместимости"""
    return await solve_recaptcha_if_present(page, account_details)


# ============================================================================
# СИНХРОННЫЕ ВЕРСИИ ДЛЯ СОВМЕСТИМОСТИ
# ============================================================================

def detect_recaptcha_on_page(page):
    """
    Синхронная версия определения reCAPTCHA
    """
    try:
        page_url = page.url
        
        # Проверяем challenge-страницы Instagram
        if '/challenge/' in page_url:
            print("🚨 Instagram challenge page detected")
            return {
                "site_key": None,  # Не нужен для ручного решения
                "page_url": page_url,
                "iframe_present": True,
                "is_challenge_page": True
            }
        
        # Проверяем наличие reCAPTCHA iframe
        recaptcha_iframe = page.locator('iframe[title*="recaptcha" i], iframe[src*="recaptcha"], iframe[id*="recaptcha"]')
        
        if recaptcha_iframe.count() > 0:
            print("🔍 reCAPTCHA iframe detected")
            return {
                "site_key": None,  # Не нужен для ручного решения
                "page_url": page_url,
                "iframe_present": True,
                "is_challenge_page": False
            }
        
        return None
                            
    except Exception as e:
        print(f"[FAIL] Error detecting reCAPTCHA: {str(e)}")
        return None


def solve_recaptcha_if_present_sync(page, account_details=None, max_attempts=3):
    """
    Синхронная версия ручного решения reCAPTCHA
    """
    try:
        print("🔍 Starting synchronous reCAPTCHA detection...")
        
        # Detect reCAPTCHA on page
        captcha_params = detect_recaptcha_on_page(page)
        if not captcha_params:
            print("ℹ️ No reCAPTCHA detected on page")
            return True  # No captcha to solve
        
        page_url = captcha_params.get('page_url')
        is_challenge_page = captcha_params.get('is_challenge_page', False)
        
        print(f"[TOOL] reCAPTCHA detected on: {page_url}")
        print(f"[TOOL] Challenge page: {is_challenge_page}")
        
        # Звуковое оповещение
        play_sound_notification()
        
        # Уведомление на dashboard (если есть bulk_upload_id)
        if account_details and account_details.get("bulk_upload_id"):
            send_captcha_notification_to_dashboard(account_details["bulk_upload_id"])
        
        # Запоминаем начальный URL для отслеживания изменений
        initial_url = page.url
        start_time = time.time()
        timeout_seconds = 5 * 60  # 5 минут
        check_interval_seconds = 30  # Проверяем каждые 30 секунд
        
        print(f"[WAIT] Waiting for manual solution... (timeout: 5 minutes)")
        print(f"📋 Please solve the reCAPTCHA manually in the browser")
        print(f"[RETRY] Will check every {check_interval_seconds} seconds for page change")
        
        check_count = 0
        
        while time.time() - start_time < timeout_seconds:
            check_count += 1
            elapsed_minutes = int((time.time() - start_time) / 60)
            elapsed_seconds = int(time.time() - start_time) % 60
            
            print(f"🔍 Check #{check_count} - {elapsed_minutes}m {elapsed_seconds}s elapsed")
            
            try:
                # Проверяем изменился ли URL (успешное решение)
                current_url = page.url
                if current_url != initial_url:
                    print(f"[OK] Page URL changed from {initial_url} to {current_url}")
                    print(f"[OK] Manual reCAPTCHA solution successful!")
                    return True
                
                # Ждем до следующей проверки
                remaining_time = timeout_seconds - (time.time() - start_time)
                remaining_minutes = int(remaining_time / 60)
                remaining_seconds = int(remaining_time % 60)
                
                print(f"[WAIT] Next check in {check_interval_seconds}s (remaining: {remaining_minutes}m {remaining_seconds}s)")
                time.sleep(check_interval_seconds)
                        
            except Exception as e:
                print(f"[FAIL] Error during manual captcha check: {e}")
                time.sleep(check_interval_seconds)
        
        # Таймаут достигнут
        print(f"[FAIL] Manual reCAPTCHA solving timeout after 5 minutes")
        print(f"[FAIL] User did not solve the reCAPTCHA in time")
        return False
        
    except Exception as e:
        print(f"[FAIL] Unexpected error in sync reCAPTCHA solving: {e}")
        return False

