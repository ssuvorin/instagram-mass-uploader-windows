#!/usr/bin/env python
import json
import sys
import os
import asyncio
import time
import random
from playwright.async_api import async_playwright

def log_message(msg):
    print(f"[ISOLATED] {msg}")

async def run_cookie_robot_isolated(params):
    try:
        profile_id = params['profile_id']
        urls = params['urls']
        headless = params['headless']
        imageless = params['imageless']
        duration = params['duration']
        api_key = params['api_key']
        local_api_base = params['local_api_base']
        
        log_message(f"Starting Cookie Robot for profile {profile_id}")
        log_message(f"URLs: {len(urls)}, Duration: {duration}s")
        
        # Импортируем DolphinAnty
        sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        from bot.src.instagram_uploader.dolphin_anty import DolphinAnty
        
        dolphin = DolphinAnty(api_key=api_key, local_api_base=local_api_base)
        
        # Запускаем профиль
        log_message("Starting Dolphin profile...")
        success, automation_data = dolphin.start_profile(profile_id, headless=headless)
        
        if not success or not automation_data:
            return {"success": False, "error": "Failed to start profile"}
        
        port = automation_data.get("port")
        ws_endpoint = automation_data.get("wsEndpoint")
        
        if not port or not ws_endpoint:
            return {"success": False, "error": "No automation data"}
        
        ws_url = f"ws://127.0.0.1:{port}{ws_endpoint}"
        log_message(f"Connecting to: {ws_url}")
        
        # Используем async_playwright в новом процессе
        async with async_playwright() as p:
            browser = await p.chromium.connect_over_cdp(ws_url)
            log_message("Connected to browser")
            
            try:
                # Получаем контекст
                contexts = browser.contexts
                if contexts:
                    context = contexts[0]
                else:
                    context = await browser.new_context()
                
                page = await context.new_page()
                
                # Настройки для imageless
                if imageless:
                    await page.route("**/*.{png,jpg,jpeg,gif,webp,svg,ico}", lambda route: route.abort())
                
                successful_visits = 0
                failed_visits = 0
                start_time = time.time()
                
                # Рандомизируем URLs
                shuffled_urls = urls.copy()
                random.shuffle(shuffled_urls)
                
                log_message(f"Processing {len(shuffled_urls)} URLs...")
                
                for i, url in enumerate(shuffled_urls, 1):
                    if time.time() - start_time > duration:
                        log_message("Duration limit reached")
                        break
                    
                    try:
                        log_message(f"[{i}/{len(shuffled_urls)}] Visiting: {url}")
                        
                        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                        
                        # Имитация активности
                        activity_time = random.uniform(5, 15)
                        await asyncio.sleep(activity_time)
                        
                        # Случайные действия
                        if random.choice([True, False]):
                            await page.evaluate("window.scrollBy(0, Math.random() * 500)")
                            await asyncio.sleep(random.uniform(1, 3))
                        
                        successful_visits += 1
                        log_message(f"[{i}/{len(shuffled_urls)}] Success: {url}")
                        
                    except Exception as e:
                        failed_visits += 1
                        log_message(f"[{i}/{len(shuffled_urls)}] Error: {url} - {str(e)}")
                    
                    # Пауза между URL
                    await asyncio.sleep(random.uniform(2, 8))
                
                # Закрываем страницу
                try:
                    await page.close()
                except:
                    pass
                
                log_message(f"Completed: {successful_visits} success, {failed_visits} failed")
                
                result = {
                    "success": True,
                    "data": {
                        "message": "Cookie Robot completed in isolated process",
                        "urls_total": len(urls),
                        "successful_visits": successful_visits,
                        "failed_visits": failed_visits,
                        "success_rate": round((successful_visits / len(shuffled_urls)) * 100, 2) if shuffled_urls else 0,
                        "total_duration": time.time() - start_time
                    }
                }
                
                return result
                
            finally:
                # Закрываем браузер
                try:
                    await browser.close()
                except:
                    pass
                
                # Останавливаем профиль
                try:
                    dolphin.stop_profile(profile_id)
                    log_message("Profile stopped")
                except:
                    pass
                
    except Exception as e:
        log_message(f"Error: {str(e)}")
        return {"success": False, "error": str(e)}

def main():
    if len(sys.argv) != 2:
        print("Usage: python isolated_cookie_robot.py <params_file>")
        sys.exit(1)
    
    params_file = sys.argv[1]
    
    try:
        # Загружаем параметры
        with open(params_file, 'r') as f:
            params = json.load(f)
        
        # Запускаем в новом event loop
        result = asyncio.run(run_cookie_robot_isolated(params))
        
        # Выводим результат как JSON
        print("RESULT_START")
        print(json.dumps(result))
        print("RESULT_END")
        
    except Exception as e:
        error_result = {"success": False, "error": str(e)}
        print("RESULT_START")
        print(json.dumps(error_result))
        print("RESULT_END")
    finally:
        # Удаляем временный файл
        try:
            os.unlink(params_file)
        except:
            pass

if __name__ == "__main__":
    main()
