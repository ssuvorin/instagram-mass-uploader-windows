"""
Services Layer for Bot Integration
===================================

Адаптер между Django моделями и логикой бота.
Все функции сохраняют оригинальную логику бота без изменений.
"""

import os
import json
import time
from typing import List, Dict, Any, Optional
from playwright.sync_api import sync_playwright

from django.utils import timezone
from django.db import transaction

from tiktok_uploader.bot_integration import logger
from tiktok_uploader.bot_integration.db import DataBase
from tiktok_uploader.bot_integration.dolphin.dolphin import Dolphin
from tiktok_uploader.bot_integration.tiktok.auth import Auth
from tiktok_uploader.bot_integration.tiktok.upload import Uploader
from tiktok_uploader.bot_integration.tiktok.booster import Booster
from tiktok_uploader.bot_integration.tiktok.video import Video
from tiktok_uploader.bot_integration.tiktok.getCode import Email
from tiktok_uploader.bot_integration.telegram_notifier import send_message


# ============================================================================
# DOLPHIN ANTY INTEGRATION
# ============================================================================

def create_dolphin_profile_for_account(account, locale: str = None) -> Dict[str, Any]:
    """
    Создает Dolphin профиль для TikTok аккаунта.
    
    Args:
        account: TikTokAccount instance
        locale: Локаль (по умолчанию берется из аккаунта)
    
    Returns:
        dict: Результат создания профиля с ключами success, profile_id, error
    """
    try:
        dolphin = Dolphin()
        
        # Получаем прокси из аккаунта
        proxy = None
        if account.current_proxy:
            proxy = account.current_proxy.to_dict()
        elif account.proxy:
            proxy = account.proxy.to_dict()
        
        if not proxy:
            logger.error(f"No proxy configured for account {account.username}")
            return {
                "success": False,
                "error": "No proxy configured for account"
            }
        
        # Используем локаль из аккаунта или переданную
        profile_locale = locale or account.locale or 'en_US'
        
        # Создаем профиль через метод create_profile из бота
        result = dolphin.create_profile(
            name=account.username,
            proxy=proxy,
            tags=['tiktok', 'django'],
            locale=profile_locale
        )
        
        if result.get("success", True) and (result.get("browserProfileId") or result.get("data", {}).get("id")):
            profile_id = result.get("browserProfileId") or result.get("data", {}).get("id")
            
            # Сохраняем profile_id в аккаунт
            account.dolphin_profile_id = str(profile_id)
            account.save(update_fields=['dolphin_profile_id'])
            
            # Сохраняем снимок профиля для возможности восстановления
            from tiktok_uploader.models import DolphinProfileSnapshot
            DolphinProfileSnapshot.objects.update_or_create(
                account=account,
                defaults={
                    'profile_id': str(profile_id),
                    'payload_json': result.get('_payload_used', {}),
                    'response_json': result,
                    'meta_json': result.get('_meta', {})
                }
            )
            
            logger.info(f"Dolphin profile created for {account.username}: {profile_id}")
            
            return {
                "success": True,
                "profile_id": profile_id,
                "result": result
            }
        else:
            error_msg = result.get("error", "Unknown error during profile creation")
            logger.error(f"Failed to create Dolphin profile for {account.username}: {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "result": result
            }
    
    except Exception as e:
        logger.error(f"Exception creating Dolphin profile for {account.username}: {str(e)}")
        logger.log_err()
        return {
            "success": False,
            "error": str(e)
        }


def delete_dolphin_profile(profile_id: str) -> bool:
    """
    Удаляет Dolphin профиль.
    
    Args:
        profile_id: ID профиля в Dolphin
    
    Returns:
        bool: True если успешно удален
    """
    try:
        dolphin = Dolphin()
        
        # Находим профиль
        profile = None
        for p in dolphin.get_profiles():
            if str(p.id) == str(profile_id):
                profile = p
                break
        
        if profile:
            profile.delete_profile()
            logger.info(f"Dolphin profile {profile_id} deleted")
            return True
        else:
            logger.warning(f"Dolphin profile {profile_id} not found")
            return False
    
    except Exception as e:
        logger.error(f"Error deleting Dolphin profile {profile_id}: {str(e)}")
        logger.log_err()
        return False


# ============================================================================
# VIDEO UPLOAD SERVICE
# ============================================================================

def run_bulk_upload_task(task_id: int) -> Dict[str, Any]:
    """
    Запускает задачу массовой загрузки видео.
    Использует оригинальную логику бота без изменений.
    
    Args:
        task_id: ID задачи BulkUploadTask
    
    Returns:
        dict: Результат выполнения задачи
    """
    from tiktok_uploader.models import BulkUploadTask, BulkUploadAccount
    
    try:
        task = BulkUploadTask.objects.get(id=task_id)
        
        # Обновляем статус задачи
        task.status = 'RUNNING'
        task.started_at = timezone.now()
        task.save(update_fields=['status', 'started_at'])
        
        # Отправляем уведомление о старте
        send_message(f'Bulk upload task "{task.name}" started')
        
        # Инициализируем Dolphin
        dolphin = Dolphin()
        
        # Получаем все аккаунты задачи
        bulk_accounts = task.accounts.all()
        
        results = {
            "success": True,
            "total_accounts": bulk_accounts.count(),
            "processed": 0,
            "successful": 0,
            "failed": 0,
            "errors": []
        }
        
        # Запускаем Playwright для автоматизации
        with sync_playwright() as playwright:
            for bulk_account in bulk_accounts:
                account = bulk_account.account
                
                # Обновляем статус аккаунта
                bulk_account.status = 'RUNNING'
                bulk_account.started_at = timezone.now()
                bulk_account.save(update_fields=['status', 'started_at'])
                
                try:
                    # Получаем профиль Dolphin
                    if not account.dolphin_profile_id:
                        logger.error(f"No Dolphin profile for account {account.username}")
                        bulk_account.status = 'FAILED'
                        bulk_account.log += f"\n[{timezone.now()}] No Dolphin profile configured"
                        bulk_account.save()
                        results["failed"] += 1
                        continue
                    
                    profile = dolphin.get_profile_by_name(account.username)
                    if not profile:
                        logger.error(f"Dolphin profile not found for {account.username}")
                        bulk_account.status = 'FAILED'
                        bulk_account.log += f"\n[{timezone.now()}] Dolphin profile not found"
                        bulk_account.save()
                        results["failed"] += 1
                        continue
                    
                    # Создаем объект Email для получения кодов
                    email_obj = None
                    if account.email and account.email_password:
                        email_obj = Email(account.email, account.email_password)
                    
                    # Создаем объект Auth
                    auth = Auth(
                        login=account.username,
                        password=account.password,
                        email=email_obj,
                        profile=profile,
                        playwright=playwright,
                        db=None  # Используем Django ORM вместо SQLite
                    )
                    
                    # Создаем Uploader
                    uploader = Uploader(auth)
                    
                    # Получаем видео для этого аккаунта
                    videos_to_upload = []
                    for video_obj in bulk_account.assigned_videos.filter(uploaded=False):
                        caption = video_obj.get_effective_caption()
                        hashtags = video_obj.get_effective_hashtags()
                        
                        # Объединяем описание и хештеги
                        full_description = f"{caption} {hashtags}".strip()
                        
                        video = Video(
                            name=os.path.basename(video_obj.video_file.name),
                            path=video_obj.video_file.path,
                            description=full_description,
                            music=None  # TODO: добавить поддержку музыки если нужно
                        )
                        videos_to_upload.append((video, video_obj))
                    
                    # Загружаем видео
                    if videos_to_upload:
                        for video, video_obj in videos_to_upload:
                            try:
                                # Аутентификация происходит внутри upload_videos
                                uploader.upload_videos([video])
                                
                                # Отмечаем видео как загруженное
                                video_obj.uploaded = True
                                video_obj.save(update_fields=['uploaded'])
                                
                                bulk_account.uploaded_success_count += 1
                                bulk_account.log += f"\n[{timezone.now()}] Uploaded: {video.name}"
                                
                                # Задержка между загрузками
                                delay = time.randint(task.delay_min_sec, task.delay_max_sec)
                                time.sleep(delay)
                                
                            except Exception as ve:
                                logger.error(f"Error uploading video {video.name}: {str(ve)}")
                                logger.log_err()
                                bulk_account.uploaded_failed_count += 1
                                bulk_account.log += f"\n[{timezone.now()}] Failed: {video.name} - {str(ve)}"
                        
                        bulk_account.status = 'COMPLETED'
                        results["successful"] += 1
                    else:
                        bulk_account.status = 'COMPLETED'
                        bulk_account.log += f"\n[{timezone.now()}] No videos to upload"
                        results["successful"] += 1
                    
                    # Отмечаем аккаунт как использованный
                    account.mark_as_used()
                    
                except Exception as e:
                    logger.error(f"Error processing account {account.username}: {str(e)}")
                    logger.log_err()
                    bulk_account.status = 'FAILED'
                    bulk_account.log += f"\n[{timezone.now()}] Error: {str(e)}"
                    results["failed"] += 1
                    results["errors"].append({
                        "account": account.username,
                        "error": str(e)
                    })
                
                finally:
                    bulk_account.completed_at = timezone.now()
                    bulk_account.save()
                    results["processed"] += 1
        
        # Обновляем статус задачи
        task.status = 'COMPLETED'
        task.completed_at = timezone.now()
        task.save(update_fields=['status', 'completed_at'])
        
        # Отправляем уведомление о завершении
        send_message(
            f'Bulk upload task "{task.name}" completed\n'
            f'Successful: {results["successful"]}, Failed: {results["failed"]}'
        )
        
        logger.info(f"Bulk upload task {task_id} completed: {results}")
        
        return results
    
    except Exception as e:
        logger.error(f"Critical error in bulk upload task {task_id}: {str(e)}")
        logger.log_err()
        
        # Обновляем статус задачи на Failed
        try:
            task = BulkUploadTask.objects.get(id=task_id)
            task.status = 'FAILED'
            task.completed_at = timezone.now()
            task.log += f"\n[{timezone.now()}] Critical error: {str(e)}"
            task.save()
        except:
            pass
        
        return {
            "success": False,
            "error": str(e)
        }


# ============================================================================
# WARMUP SERVICE
# ============================================================================

def run_warmup_task(task_id: int) -> Dict[str, Any]:
    """
    Запускает задачу прогрева аккаунтов.
    Использует оригинальную логику Booster из бота.
    
    Args:
        task_id: ID задачи WarmupTask
    
    Returns:
        dict: Результат выполнения задачи
    """
    from tiktok_uploader.models import WarmupTask, WarmupTaskAccount
    
    try:
        task = WarmupTask.objects.get(id=task_id)
        
        # Обновляем статус задачи
        task.status = 'RUNNING'
        task.save(update_fields=['status'])
        
        # Отправляем уведомление
        send_message(f'Warmup task "{task.name}" started')
        
        # Инициализируем Dolphin
        dolphin = Dolphin()
        
        # Получаем аккаунты задачи
        warmup_accounts = task.accounts.all()
        
        results = {
            "success": True,
            "total_accounts": warmup_accounts.count(),
            "processed": 0,
            "successful": 0,
            "failed": 0
        }
        
        # Запускаем Playwright
        with sync_playwright() as playwright:
            for warmup_account in warmup_accounts:
                account = warmup_account.account
                
                # Обновляем статус
                warmup_account.status = 'RUNNING'
                warmup_account.started_at = timezone.now()
                warmup_account.save(update_fields=['status', 'started_at'])
                
                try:
                    # Получаем профиль Dolphin
                    if not account.dolphin_profile_id:
                        logger.error(f"No Dolphin profile for account {account.username}")
                        warmup_account.status = 'FAILED'
                        warmup_account.log += f"\n[{timezone.now()}] No Dolphin profile"
                        warmup_account.save()
                        results["failed"] += 1
                        continue
                    
                    profile = dolphin.get_profile_by_name(account.username)
                    if not profile:
                        logger.error(f"Dolphin profile not found for {account.username}")
                        warmup_account.status = 'FAILED'
                        warmup_account.log += f"\n[{timezone.now()}] Profile not found"
                        warmup_account.save()
                        results["failed"] += 1
                        continue
                    
                    # Создаем Email объект
                    email_obj = None
                    if account.email and account.email_password:
                        email_obj = Email(account.email, account.email_password)
                    
                    # Создаем Auth
                    auth = Auth(
                        login=account.username,
                        password=account.password,
                        email=email_obj,
                        profile=profile,
                        playwright=playwright,
                        db=None
                    )
                    
                    # Аутентификация
                    page = auth.authenticate()
                    
                    if page and not isinstance(page, int):
                        # Создаем Booster и запускаем прогрев
                        booster = Booster(auth)
                        booster.start(page)
                        
                        # Отмечаем аккаунт как прогретый
                        account.mark_as_warmed()
                        
                        warmup_account.status = 'COMPLETED'
                        warmup_account.log += f"\n[{timezone.now()}] Warmup completed successfully"
                        results["successful"] += 1
                    else:
                        logger.error(f"Failed to authenticate {account.username}")
                        warmup_account.status = 'FAILED'
                        warmup_account.log += f"\n[{timezone.now()}] Authentication failed"
                        results["failed"] += 1
                    
                except Exception as e:
                    logger.error(f"Error warming up {account.username}: {str(e)}")
                    logger.log_err()
                    warmup_account.status = 'FAILED'
                    warmup_account.log += f"\n[{timezone.now()}] Error: {str(e)}"
                    results["failed"] += 1
                
                finally:
                    warmup_account.completed_at = timezone.now()
                    warmup_account.save()
                    results["processed"] += 1
        
        # Обновляем статус задачи
        task.status = 'COMPLETED'
        task.save(update_fields=['status'])
        
        send_message(
            f'Warmup task "{task.name}" completed\n'
            f'Successful: {results["successful"]}, Failed: {results["failed"]}'
        )
        
        return results
    
    except Exception as e:
        logger.error(f"Critical error in warmup task {task_id}: {str(e)}")
        logger.log_err()
        
        try:
            task = WarmupTask.objects.get(id=task_id)
            task.status = 'FAILED'
            task.save()
        except:
            pass
        
        return {
            "success": False,
            "error": str(e)
        }


# ============================================================================
# COOKIE ROBOT SERVICE
# ============================================================================

def run_cookie_robot_for_account(account) -> Dict[str, Any]:
    """
    Запускает Cookie Robot для одного аккаунта.
    
    Args:
        account: TikTokAccount instance
    
    Returns:
        dict: Результат выполнения
    """
    try:
        if not account.dolphin_profile_id:
            return {
                "success": False,
                "error": "No Dolphin profile configured"
            }
        
        dolphin = Dolphin()
        profile = dolphin.get_profile_by_name(account.username)
        
        if not profile:
            return {
                "success": False,
                "error": "Dolphin profile not found"
            }
        
        # Запускаем Cookie Robot
        profile.start_cookie_robot()
        
        logger.info(f"Cookie robot completed for {account.username}")
        
        return {
            "success": True,
            "message": "Cookie robot completed successfully"
        }
    
    except Exception as e:
        logger.error(f"Error running cookie robot for {account.username}: {str(e)}")
        logger.log_err()
        return {
            "success": False,
            "error": str(e)
        }


def export_cookies_from_profile(account) -> Optional[List[Dict[str, Any]]]:
    """
    Экспортирует cookies из Dolphin профиля аккаунта.
    
    Args:
        account: TikTokAccount instance
    
    Returns:
        list: Список cookies или None при ошибке
    """
    try:
        if not account.dolphin_profile_id:
            logger.error(f"No Dolphin profile for {account.username}")
            return None
        
        dolphin = Dolphin()
        profile = dolphin.get_profile_by_name(account.username)
        
        if not profile:
            logger.error(f"Dolphin profile not found for {account.username}")
            return None
        
        cookies = profile.export_cookies()
        
        logger.info(f"Exported {len(cookies)} cookies from {account.username}")
        
        return cookies
    
    except Exception as e:
        logger.error(f"Error exporting cookies from {account.username}: {str(e)}")
        logger.log_err()
        return None

