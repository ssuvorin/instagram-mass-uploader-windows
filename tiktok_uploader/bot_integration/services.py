"""
Services Layer for Bot Integration
===================================

Адаптер между Django моделями и логикой бота.
Все функции сохраняют оригинальную логику бота без изменений.
"""

import os
import json
import time
from typing import List, Dict, Any, Optional, Tuple
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
    from tiktok_uploader.models import BulkUploadTask, BulkUploadAccount, BulkVideo
    
    try:
        task = BulkUploadTask.objects.get(id=task_id)
        
        # Обновляем статус задачи и инициализируем логи
        task.status = 'RUNNING'
        task.started_at = timezone.now()
        task.log = f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] 🚀 Bulk upload task started\n"
        task.log += f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] Total accounts: {len(task.accounts.all())}\n"
        task.save(update_fields=['status', 'started_at', 'log'])
        
        # Отправляем уведомление о старте
        send_message(f'Bulk upload task "{task.name}" started')
        
        # Инициализируем Dolphin
        dolphin = Dolphin()
        
        # Получаем все аккаунты задачи ДО входа в Playwright контекст
        # Используем select_related и prefetch_related для prefetch связанных объектов
        bulk_accounts = list(
            task.accounts.select_related('account', 'account__proxy')
            .prefetch_related('assigned_videos')
            .all()
        )

        # Предварительно собираем список видео для каждого аккаунта (без ORM внутри Playwright)
        # Ключ: BulkUploadAccount.id -> список словарей с данными видео
        precomputed_videos_by_account: Dict[int, List[Dict[str, Any]]] = {}
        for bulk_account in bulk_accounts:
            videos_data: List[Dict[str, Any]] = []
            # ВАЖНО: не вызывать ORM в Playwright, фильтруем сейчас
            assigned_videos = list(bulk_account.assigned_videos.all())
            for v in assigned_videos:
                if getattr(v, 'uploaded', False):
                    continue
                caption = v.get_effective_caption()
                hashtags = v.get_effective_hashtags()
                full_description = f"{caption} {hashtags}".strip()
                try:
                    video_name = os.path.basename(v.video_file.name)
                    video_path = v.video_file.path
                except Exception:
                    # Если файл недоступен, пропускаем, отметим fail в логах во время апдейта
                    continue
                videos_data.append({
                    'id': v.id,
                    'name': video_name,
                    'path': video_path,
                    'description': full_description,
                })
            precomputed_videos_by_account[bulk_account.id] = videos_data
        
        results = {
            "success": True,
            "total_accounts": len(bulk_accounts),
            "processed": 0,
            "successful": 0,
            "failed": 0,
            "errors": []
        }
        
        # Список для сбора результатов (обновим БД после Playwright)
        accounts_results = []
        
        # Запускаем Playwright для автоматизации
        with sync_playwright() as playwright:
            for bulk_account in bulk_accounts:
                account = bulk_account.account
                start_time = timezone.now()
                
                # Подготавливаем результат для этого аккаунта
                account_result = {
                    'bulk_account_id': bulk_account.id,
                    'account_username': account.username,
                    'status': 'RUNNING',
                    'started_at': start_time,
                    'completed_at': None,
                    'log': bulk_account.log + f"\n[{start_time.strftime('%Y-%m-%d %H:%M:%S')}] 🔄 Starting upload for {account.username}\n",
                    'uploaded_success_count': 0,
                    'uploaded_fail_count': 0
                }
                logger.info(f"[UPLOAD] Starting upload for account {account.username}")
                
                try:
                    # Получаем профиль Dolphin
                    if not account.dolphin_profile_id:
                        logger.error(f"No Dolphin profile for account {account.username}")
                        account_result['status'] = 'FAILED'
                        account_result['log'] += f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] ❌ No Dolphin profile\n"
                        account_result['completed_at'] = timezone.now()
                        accounts_results.append(account_result)
                        results["failed"] += 1
                        continue
                    
                    account_result['log'] += f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] ✓ Dolphin profile found: {account.dolphin_profile_id}\n"
                    
                    profile = dolphin.get_profile_by_name(account.username)
                    if not profile:
                        logger.error(f"Dolphin profile not found for {account.username}")
                        account_result['status'] = 'FAILED'
                        account_result['log'] += f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] ❌ Profile not found in Dolphin\n"
                        account_result['completed_at'] = timezone.now()
                        accounts_results.append(account_result)
                        results["failed"] += 1
                        continue
                    
                    account_result['log'] += f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] ✓ Profile loaded from Dolphin\n"
                    
                    # Создаем объект Email для получения кодов
                    email_obj = None
                    if account.email and account.email_password:
                        email_obj = Email(account.email, account.email_password)
                        account_result['log'] += f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] ✓ Email configured for verification\n"
                    
                    # Создаем объект Auth
                    account_result['log'] += f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] 🔐 Starting authentication...\n"
                    
                    # Callback для обновления пароля в БД (НЕ делаем .save() здесь!)
                    def update_password_callback(username, new_password):
                        account_result['new_password'] = new_password
                        account_result['log'] += f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] 🔑 Password will be updated in database\n"
                        logger.info(f"[PASSWORD_UPDATE] Password changed for {username}, will update DB after Playwright")
                    
                    # Callback для обновления статуса аккаунта (НЕ делаем .save() здесь!)
                    def update_status_callback(username, status, error_message):
                        account_result['new_status'] = status
                        account_result['status_reason'] = error_message
                        account_result['log'] += f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] ⚠️ Status will be updated to: {status}\n"
                        account_result['log'] += f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}]    Reason: {error_message}\n"
                        logger.warning(f"[STATUS_UPDATE] {username} -> {status}: {error_message}")
                    
                    auth = Auth(
                        login=account.username,
                        password=account.password,
                        email=email_obj,
                        profile=profile,
                        playwright=playwright,
                        db=None,  # Используем Django ORM вместо SQLite
                        password_update_callback=update_password_callback,
                        status_update_callback=update_status_callback
                    )
                    
                    # Создаем Uploader
                    uploader = Uploader(auth)
                    account_result['log'] += f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] ✅ Uploader initialized\n"
                    account_result['reset_status_to_active'] = True  # Сброс статуса при успешном входе
                    
                    # Получаем видео для этого аккаунта (из предварительно подготовленных данных)
                    videos_to_upload: List[Tuple[Video, Dict[str, Any]]] = []
                    pre_videos = precomputed_videos_by_account.get(bulk_account.id, [])
                    for vdata in pre_videos:
                        video = Video(
                            name=vdata['name'],
                            path=vdata['path'],
                            description=vdata['description'],
                            music=None
                        )
                        videos_to_upload.append((video, vdata))
                    
                    # Загружаем видео
                    if videos_to_upload:
                        account_result['log'] += f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] 📹 Found {len(videos_to_upload)} videos to upload\n"
                        
                        # Список успешно загруженных видео id для последующего обновления БД
                        uploaded_video_ids: List[int] = []
                        for video, vdata in videos_to_upload:
                            try:
                                account_result['log'] += f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] ⬆️ Uploading: {video.name}\n"
                                
                                # Аутентификация происходит внутри upload_videos
                                uploader.upload_videos([video])
                                
                                # Копим id для обновления после Playwright
                                if 'id' in vdata:
                                    uploaded_video_ids.append(vdata['id'])
                                
                                account_result['uploaded_success_count'] += 1
                                account_result['log'] += f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] ✅ Uploaded: {video.name}\n"
                                logger.info(f"[UPLOAD] Successfully uploaded {video.name} for {account.username}")
                                
                                # Задержка между загрузками
                                import random
                                delay = random.randint(task.delay_min_sec, task.delay_max_sec)
                                account_result['log'] += f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] ⏳ Delay: {delay}s\n"
                                time.sleep(delay)
                                
                            except Exception as ve:
                                logger.error(f"Error uploading video {video.name}: {str(ve)}")
                                logger.log_err()
                                account_result['uploaded_fail_count'] += 1
                                account_result['log'] += f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] ❌ Failed: {video.name} - {str(ve)}\n"
                        
                        account_result['status'] = 'COMPLETED'
                        # Сохраняем список успешно загруженных видео для обновления после Playwright
                        if uploaded_video_ids:
                            account_result['uploaded_video_ids'] = uploaded_video_ids
                        account_result['log'] += f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] ✅ All videos processed\n"
                        account_result['log'] += f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}]    Success: {account_result['uploaded_success_count']}, Failed: {account_result['uploaded_fail_count']}\n"
                        results["successful"] += 1
                    else:
                        logger.warning(f"No videos assigned to {account.username}")
                        account_result['status'] = 'COMPLETED'
                        account_result['log'] += f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] ⚠️ No videos to upload\n"
                        results["successful"] += 1
                    
                except Exception as e:
                    logger.error(f"Error processing account {account.username}: {str(e)}")
                    logger.log_err()
                    account_result['status'] = 'FAILED'
                    account_result['log'] += f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] ❌ Error: {str(e)}\n"
                    results["failed"] += 1
                    results["errors"].append({
                        "account": account.username,
                        "error": str(e)
                    })
                
                finally:
                    account_result['completed_at'] = timezone.now()
                    accounts_results.append(account_result)
                    results["processed"] += 1
        
        # ПОСЛЕ выхода из Playwright контекста - обновляем БД
        logger.info(f"[UPLOAD] Updating database for {len(accounts_results)} accounts")
        
        # Обновляем лог задачи сводной информацией
        task.log += f"\n[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] 📊 Processing results:\n"
        
        for result in accounts_results:
            try:
                bulk_acc = BulkUploadAccount.objects.get(id=result['bulk_account_id'])
                bulk_acc.status = result['status']
                bulk_acc.started_at = result['started_at']
                bulk_acc.completed_at = result['completed_at']
                bulk_acc.uploaded_success_count = result['uploaded_success_count']
                bulk_acc.uploaded_failed_count = result['uploaded_fail_count']
                bulk_acc.log = result['log']
                bulk_acc.save()

                # Обновляем статус выгруженных видео, если есть
                uploaded_ids = result.get('uploaded_video_ids')
                if uploaded_ids:
                    try:
                        BulkVideo.objects.filter(id__in=uploaded_ids).update(uploaded=True)
                    except Exception as ve:
                        logger.error(f"Error updating uploaded flags for videos {uploaded_ids}: {ve}")
                
                # Обновляем пароль если он был изменен
                if result.get('new_password'):
                    bulk_acc.account.password = result['new_password']
                    bulk_acc.account.save(update_fields=['password'])
                    logger.info(f"[PASSWORD_UPDATE] Password updated for {bulk_acc.account.username}")
                
                # Обновляем статус аккаунта
                if result.get('new_status'):
                    bulk_acc.account.status = result['new_status']
                    bulk_acc.account.save(update_fields=['status'])
                    logger.info(f"[STATUS_UPDATE] {bulk_acc.account.username} status updated to {result['new_status']}")
                
                # Сбрасываем статус на ACTIVE при успешном входе
                if result.get('reset_status_to_active') and result['status'] == 'COMPLETED':
                    bulk_acc.account.status = 'ACTIVE'
                    bulk_acc.account.save(update_fields=['status'])
                    logger.info(f"[STATUS_RESET] {bulk_acc.account.username} status reset to ACTIVE")
                
                # Добавляем в общий лог задачи
                status_emoji = "✅" if result['status'] == 'COMPLETED' else "❌"
                task.log += f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}]    {status_emoji} {result['account_username']}: {result['uploaded_success_count']} uploaded, {result['uploaded_fail_count']} failed\n"
                
            except Exception as e:
                logger.error(f"Error updating bulk account {result['bulk_account_id']}: {str(e)}")
                task.log += f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}]    ⚠️ Error updating {result.get('account_username', 'unknown')}\n"
        
        # Обновляем статус задачи
        task.status = 'COMPLETED'
        task.completed_at = timezone.now()
        task.log += f"\n[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] 🎉 Task completed!\n"
        task.log += f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}]    Total processed: {results['processed']}, Successful: {results['successful']}, Failed: {results['failed']}\n"
        task.save(update_fields=['status', 'completed_at', 'log'])
        
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

def run_warmup_task_wrapper(task_id: int):
    """
    Wrapper для запуска задачи прогрева в отдельном потоке.
    Создает новое подключение к БД для изоляции от async контекста Playwright.
    """
    from django.db import connection
    
    # Закрываем текущее подключение чтобы создать новое в потоке
    connection.close()
    
    try:
        run_warmup_task(task_id)
    except Exception as e:
        logger.error(f"Error in warmup task wrapper {task_id}: {str(e)}")
        logger.log_err()
    finally:
        # Закрываем подключение после завершения
        connection.close()


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
        
        # Обновляем статус задачи и инициализируем логи
        task.status = 'RUNNING'
        task.started_at = timezone.now()
        task.log = f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] 🚀 Task started\n"
        task.log += f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] Total accounts: {len(task.accounts.all())}\n"
        task.save(update_fields=['status', 'started_at', 'log'])
        
        # Отправляем уведомление
        # send_message(f'Warmup task "{task.name}" started')
        
        # Инициализируем Dolphin
        dolphin = Dolphin()
        
        # Получаем аккаунты задачи ДО входа в Playwright контекст
        # Используем select_related для prefetch связанных объектов
        warmup_accounts = list(task.accounts.select_related('account', 'account__proxy').all())
        
        results = {
            "success": True,
            "total_accounts": len(warmup_accounts),
            "processed": 0,
            "successful": 0,
            "failed": 0
        }
        
        # Собираем результаты в памяти для обновления БД после Playwright
        accounts_results = []
        
        # Запускаем Playwright
        with sync_playwright() as playwright:
            for warmup_account in warmup_accounts:
                account = warmup_account.account
                
                # Подготавливаем результат для этого аккаунта
                start_time = timezone.now()
                account_result = {
                    'warmup_account_id': warmup_account.id,
                    'account_username': account.username,
                    'status': 'RUNNING',
                    'started_at': start_time,
                    'completed_at': None,
                    'log': warmup_account.log + f"\n[{start_time.strftime('%Y-%m-%d %H:%M:%S')}] 🔄 Starting warmup for {account.username}\n"
                }
                logger.info(f"[WARMUP] Starting warmup for account {account.username}")
                
                try:
                    # Получаем профиль Dolphin
                    if not account.dolphin_profile_id:
                        logger.error(f"No Dolphin profile for account {account.username}")
                        account_result['status'] = 'FAILED'
                        account_result['log'] += f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] ❌ No Dolphin profile\n"
                        account_result['completed_at'] = timezone.now()
                        accounts_results.append(account_result)
                        results["failed"] += 1
                        continue
                    
                    account_result['log'] += f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] ✓ Dolphin profile found: {account.dolphin_profile_id}\n"
                    
                    profile = dolphin.get_profile_by_name(account.username)
                    if not profile:
                        logger.error(f"Dolphin profile not found for {account.username}")
                        account_result['status'] = 'FAILED'
                        account_result['log'] += f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] ❌ Profile not found in Dolphin\n"
                        account_result['completed_at'] = timezone.now()
                        accounts_results.append(account_result)
                        results["failed"] += 1
                        continue
                    
                    account_result['log'] += f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] ✓ Profile loaded from Dolphin\n"
                    
                    # Создаем Email объект
                    email_obj = None
                    if account.email and account.email_password:
                        email_obj = Email(account.email, account.email_password)
                        account_result['log'] += f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] ✓ Email configured for code verification\n"
                    
                    # Создаем Auth
                    account_result['log'] += f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] 🔐 Starting authentication...\n"
                    
                    # Callback для обновления пароля в БД (НЕ делаем .save() здесь!)
                    def update_password_callback(username, new_password):
                        account_result['new_password'] = new_password
                        account_result['log'] += f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] 🔑 Password will be updated in database\n"
                        logger.info(f"[PASSWORD_UPDATE] Password changed for {username}, will update DB after Playwright")
                    
                    # Callback для обновления статуса аккаунта (НЕ делаем .save() здесь!)
                    def update_status_callback(username, status, error_message):
                        account_result['new_status'] = status
                        account_result['status_reason'] = error_message
                        account_result['log'] += f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] ⚠️ Status will be updated to: {status}\n"
                        account_result['log'] += f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}]    Reason: {error_message}\n"
                        logger.warning(f"[STATUS_UPDATE] {username} -> {status}: {error_message}")
                    
                    auth = Auth(
                        login=account.username,
                        password=account.password,
                        email=email_obj,
                        profile=profile,
                        playwright=playwright,
                        db=None,
                        password_update_callback=update_password_callback,
                        status_update_callback=update_status_callback
                    )
                    
                    # Аутентификация
                    page = auth.authenticate()
                    
                    if page and not isinstance(page, int):
                        account_result['log'] += f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] ✅ Authentication successful\n"
                        
                        # Сбрасываем статус на ACTIVE при успешном входе
                        account_result['reset_status_to_active'] = True
                        
                        # Создаем Booster и запускаем прогрев
                        account_result['log'] += f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] 🔥 Starting warmup activities...\n"
                        booster = Booster(auth)
                        
                        # Логируем настройки прогрева
                        account_result['log'] += f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}]    - Feed scrolls: {task.feed_scroll_min_count}-{task.feed_scroll_max_count}\n"
                        account_result['log'] += f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}]    - Likes: {task.like_min_count}-{task.like_max_count}\n"
                        account_result['log'] += f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}]    - Videos: {task.watch_video_min_count}-{task.watch_video_max_count}\n"
                        
                        booster.start(page)
                        
                        # Отмечаем результат как успешный (БД обновим позже)
                        account_result['status'] = 'COMPLETED'
                        account_result['log'] += f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] ✅ Warmup completed successfully\n"
                        account_result['mark_as_warmed'] = True  # Флаг для обновления аккаунта
                        results["successful"] += 1
                        logger.info(f"[WARMUP] Account {account.username} warmed up successfully")
                    else:
                        logger.error(f"Failed to authenticate {account.username}")
                        account_result['status'] = 'FAILED'
                        account_result['log'] += f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] ❌ Authentication failed\n"
                        results["failed"] += 1
                    
                except Exception as e:
                    logger.error(f"Error warming up {account.username}: {str(e)}")
                    logger.log_err()
                    account_result['status'] = 'FAILED'
                    account_result['log'] += f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] ❌ Error: {str(e)}\n"
                    results["failed"] += 1
                
                finally:
                    account_result['completed_at'] = timezone.now()
                    accounts_results.append(account_result)
                    results["processed"] += 1
        
        # ПОСЛЕ выхода из Playwright контекста - обновляем БД
        logger.info(f"[WARMUP] Updating database for {len(accounts_results)} accounts")
        
        # Обновляем лог задачи сводной информацией
        task.log += f"\n[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] 📊 Processing results:\n"
        
        for result in accounts_results:
            try:
                warmup_acc = WarmupTaskAccount.objects.get(id=result['warmup_account_id'])
                warmup_acc.status = result['status']
                warmup_acc.started_at = result['started_at']
                warmup_acc.completed_at = result['completed_at']
                warmup_acc.log = result['log']
                warmup_acc.save()
                
                # Добавляем в общий лог задачи
                status_emoji = "✅" if result['status'] == 'COMPLETED' else "❌"
                task.log += f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}]    {status_emoji} {result['account_username']}: {result['status']}\n"
                
                # Отмечаем аккаунт как прогретый если нужно
                if result.get('mark_as_warmed'):
                    warmup_acc.account.mark_as_warmed()
                
                # Обновляем пароль если он был изменен
                if result.get('new_password'):
                    warmup_acc.account.password = result['new_password']
                    warmup_acc.account.save(update_fields=['password'])
                    logger.info(f"[PASSWORD_UPDATE] Password updated for {warmup_acc.account.username}")
                
                # Обновляем статус аккаунта
                if result.get('new_status'):
                    warmup_acc.account.status = result['new_status']
                    warmup_acc.account.save(update_fields=['status'])
                    logger.info(f"[STATUS_UPDATE] {warmup_acc.account.username} status updated to {result['new_status']}")
                
                # Сбрасываем статус на ACTIVE при успешном входе
                if result.get('reset_status_to_active'):
                    warmup_acc.account.status = 'ACTIVE'
                    warmup_acc.account.save(update_fields=['status'])
                    logger.info(f"[STATUS_RESET] {warmup_acc.account.username} status reset to ACTIVE")
                
            except Exception as e:
                logger.error(f"Error updating warmup account {result['warmup_account_id']}: {str(e)}")
                task.log += f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}]    ⚠️ Error updating {result.get('account_username', 'unknown')}\n"
        
        # Обновляем статус задачи
        task.status = 'COMPLETED'
        task.completed_at = timezone.now()
        task.log += f"\n[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] 🎉 Task completed!\n"
        task.log += f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}]    Successful: {results['successful']}, Failed: {results['failed']}\n"
        task.save(update_fields=['status', 'completed_at', 'log'])
        
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
            task.completed_at = timezone.now()
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


