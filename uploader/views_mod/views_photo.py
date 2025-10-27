from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.core.files.storage import default_storage
from django.urls import reverse
import os
import threading
import time
import random

from ..models import InstagramAccount
from ..forms import PhotoPostForm
from ..logging_utils import log_info
from ..async_impl.instagrapi import run_instagrapi_photo_upload_async
from django.core.cache import cache


@login_required
def create_photo_post(request):
    if request.method == 'POST':
        form = PhotoPostForm(request.POST, request.FILES)
        if form.is_valid():
            accounts = list(form.cleaned_data['selected_accounts'])
            photo_files = request.FILES.getlist('photos')
            captions_file = request.FILES.get('captions_file')
            caption = form.cleaned_data.get('caption') or ''
            mentions = form.cleaned_data.get('mentions') or ''
            location = form.cleaned_data.get('location') or ''
            delay_min = form.cleaned_data.get('delay_min_sec') or 10
            delay_max = form.cleaned_data.get('delay_max_sec') or 25

            if not photo_files:
                messages.error(request, 'Please select at least one photo.')
                return render(request, 'uploader/photos/create.html', {
                    'form': form,
                    'active_tab': 'avatars',
                })

            # Read captions from file if provided
            captions_list = []
            if captions_file:
                try:
                    captions_content = captions_file.read().decode('utf-8')
                    captions_list = [line.strip() for line in captions_content.split('\n') if line.strip()]
                except Exception as e:
                    messages.warning(request, f'Error reading captions file: {e}')
                    captions_list = []

            # Distribute photos and captions among accounts
            photo_account_pairs = []
            account_count = len(accounts)
            photo_count = len(photo_files)
            caption_count = len(captions_list)
            
            if photo_count >= account_count:
                # More photos than accounts - distribute one photo per account, skip extras
                for i, account in enumerate(accounts):
                    if i < photo_count:
                        # Get caption for this photo (from file or default)
                        photo_caption = caption
                        if captions_list and i < caption_count:
                            photo_caption = captions_list[i]
                        elif captions_list and caption_count > 0:
                            # Cycle through captions if fewer captions than photos
                            photo_caption = captions_list[i % caption_count]
                        
                        photo_account_pairs.append((photo_files[i], account, photo_caption))
            else:
                # Fewer photos than accounts - distribute with repetitions
                for i, account in enumerate(accounts):
                    photo_index = i % photo_count
                    # Get caption for this photo (from file or default)
                    photo_caption = caption
                    if captions_list and photo_index < caption_count:
                        photo_caption = captions_list[photo_index]
                    elif captions_list and caption_count > 0:
                        # Cycle through captions if fewer captions than photos
                        photo_caption = captions_list[photo_index % caption_count]
                    
                    photo_account_pairs.append((photo_files[photo_index], account, photo_caption))

            # Save photos to media temporary path
            saved_photo_paths = []
            for photo_file in photo_files:
                saved_path = default_storage.save(os.path.join('bot', 'photos', photo_file.name), photo_file)
                abs_photo_path = default_storage.path(saved_path)
                saved_photo_paths.append(abs_photo_path)

            # Start background worker thread to post photos with session restoration
            def _worker(photo_account_pairs, saved_paths):
                # Initialize statistics tracking
                stats = {
                    'total_accounts': len(photo_account_pairs),
                    'successful_uploads': 0,
                    'failed_uploads': 0,
                    'processed_accounts': 0,
                    'account_stats': {}  # per-account statistics
                }
                
                try:
                    for idx, (photo_file, account, photo_caption) in enumerate(photo_account_pairs):
                        # human-like delay between accounts
                        if idx > 0:
                            time.sleep(random.uniform(delay_min, delay_max))

                        try:
                            acc = InstagramAccount.objects.get(id=account.id)
                        except Exception:
                            stats['failed_uploads'] += 1
                            continue

                        # Initialize account stats
                        stats['account_stats'][acc.username] = {
                            'successful': 0,
                            'failed': 0,
                            'photos_processed': 0
                        }

                        def on_log(line: str):
                            # Forward to centralized logger
                            log_info(f"[PHOTO_POST] {acc.username} | {line}")
                            # Also append to bot/log.txt so /photos/status/ can tail it
                            try:
                                base_dir = os.path.dirname(default_storage.path('bot/log.txt'))
                                os.makedirs(base_dir, exist_ok=True)
                                log_path = default_storage.path('bot/log.txt')
                                from datetime import datetime
                                ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                with open(log_path, 'a', encoding='utf-8', errors='ignore') as f:
                                    f.write(f"[{ts}] [PHOTO_POST] {acc.username} | {line}\n")
                            except Exception:
                                pass

                        account_details = {
                            'username': acc.username,
                            'password': acc.password,
                            'tfa_secret': getattr(acc, 'tfa_secret', None),
                            'email_login': getattr(acc, 'email_username', None),
                            'email_password': getattr(acc, 'email_password', None),
                            'proxy': (acc.current_proxy or acc.proxy).to_dict() if (acc.current_proxy or acc.proxy) else {},
                        }

                        # Find the saved path for this photo
                        photo_path = None
                        for saved_path in saved_paths:
                            if photo_file.name in saved_path:
                                photo_path = saved_path
                                break
                        
                        if not photo_path:
                            on_log(f"Error: Could not find saved path for photo {photo_file.name}")
                            stats['failed_uploads'] += 1
                            stats['account_stats'][acc.username]['failed'] += 1
                            continue

                        stats['processed_accounts'] += 1
                        stats['account_stats'][acc.username]['photos_processed'] += 1

                        try:
                            import asyncio
                            asyncio.run(run_instagrapi_photo_upload_async(
                                account_details=account_details,
                                photo_files_to_upload=[photo_path],
                                captions=[photo_caption],
                                mentions_list=[mentions],
                                locations_list=[location],
                                on_log=on_log,
                            ))
                            # If we get here without exception, upload was successful
                            stats['successful_uploads'] += 1
                            stats['account_stats'][acc.username]['successful'] += 1
                            on_log(f"[OK] Photo uploaded successfully: {photo_file.name}")
                        except Exception as e:
                            stats['failed_uploads'] += 1
                            stats['account_stats'][acc.username]['failed'] += 1
                            on_log(f"[FAIL] Upload failed: {str(e)}")
                        except RuntimeError:
                            # If we're inside an existing loop (unlikely here), fallback
                            loop = asyncio.new_event_loop()
                            try:
                                loop.run_until_complete(run_instagrapi_photo_upload_async(
                                    account_details=account_details,
                                    photo_files_to_upload=[photo_path],
                                    captions=[photo_caption],
                                    mentions_list=[mentions],
                                    locations_list=[location],
                                    on_log=on_log,
                                ))
                                # If we get here without exception, upload was successful
                                stats['successful_uploads'] += 1
                                stats['account_stats'][acc.username]['successful'] += 1
                                on_log(f"[OK] Photo uploaded successfully: {photo_file.name}")
                            except Exception as e:
                                stats['failed_uploads'] += 1
                                stats['account_stats'][acc.username]['failed'] += 1
                                on_log(f"[FAIL] Upload failed: {str(e)}")
                            finally:
                                loop.close()

                    # Save final statistics to cache for web display
                    try:
                        # Calculate success rate
                        success_rate = (stats['successful_uploads'] / stats['total_accounts'] * 100) if stats['total_accounts'] > 0 else 0

                        # Prepare account breakdown for cache
                        account_breakdown = []
                        for username, account_stat in stats['account_stats'].items():
                            acc_success_rate = (account_stat['successful'] / account_stat['photos_processed'] * 100) if account_stat['photos_processed'] > 0 else 0
                            account_breakdown.append({
                                'username': username,
                                'successful': account_stat['successful'],
                                'total': account_stat['photos_processed'],
                                'success_rate': acc_success_rate
                            })

                        # Save to cache with 1 hour timeout
                        photo_stats = {
                            'total_accounts': stats['total_accounts'],
                            'successful_uploads': stats['successful_uploads'],
                            'failed_uploads': stats['failed_uploads'],
                            'success_rate': success_rate,
                            'account_breakdown': account_breakdown,
                            'timestamp': timezone.now().isoformat(),
                            'completed': True
                        }
                        cache.set('photo_upload_stats', photo_stats, 3600)  # 1 hour

                    except Exception as cache_error:
                        log_info(f"[WARN] Failed to save photo upload stats to cache: {cache_error}")

                    # Log final statistics
                    log_info(f"[STATS] [PHOTO_UPLOAD] Final Statistics:")
                    log_info(f"   📊 Total accounts: {stats['total_accounts']}")
                    log_info(f"   ✅ Successful uploads: {stats['successful_uploads']}")
                    log_info(f"   ❌ Failed uploads: {stats['failed_uploads']}")
                    log_info(f"   📈 Success rate: {(stats['successful_uploads'] / stats['total_accounts'] * 100):.1f}%" if stats['total_accounts'] > 0 else "   📈 Success rate: 0%")

                    # Log per-account statistics
                    log_info(f"[STATS] [ACCOUNT_BREAKDOWN]:")
                    for username, account_stat in stats['account_stats'].items():
                        success_rate = (account_stat['successful'] / account_stat['photos_processed'] * 100) if account_stat['photos_processed'] > 0 else 0
                        log_info(f"   👤 {username}: {account_stat['successful']}/{account_stat['photos_processed']} ({success_rate:.1f}%)")
                        
                finally:
                    # best-effort cleanup: keep the uploaded media as audit by default
                    pass

            t = threading.Thread(target=_worker, args=(photo_account_pairs, saved_photo_paths), daemon=True)
            t.start()

            messages.success(request, f"Photo posting started for {len(photo_account_pairs)} account-photo pairs ({len(accounts)} accounts, {len(photo_files)} photos)")
            # Redirect to photo post status page to view logs
            try:
                return redirect('photo_post_status')
            except Exception:
                return redirect('dashboard')
        else:
            messages.error(request, 'Please fix the errors in the form and try again.')
    else:
        form = PhotoPostForm()

    return render(request, 'uploader/photos/create.html', {
        'form': form,
        'active_tab': 'avatars',  # keep in Content group; could be 'photos'
    })


@login_required
def photo_post_status(request):
    """Status page showing recent log lines and upload statistics for photo posting activity."""
    log_lines = []
    photo_stats = None

    try:
        # Tail last 300 lines from bot/log.txt if exists
        log_path = default_storage.path('bot/log.txt') if hasattr(default_storage, 'path') else os.path.join(os.getcwd(), 'bot', 'log.txt')
        if os.path.exists(log_path):
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                log_lines = lines[-300:]
    except Exception:
        log_lines = []

    # Get photo upload statistics from cache
    try:
        photo_stats = cache.get('photo_upload_stats')
    except Exception:
        photo_stats = None

    return render(request, 'uploader/photos/status.html', {
        'log_lines': log_lines,
        'photo_stats': photo_stats,
        'active_tab': 'avatars',
    })

