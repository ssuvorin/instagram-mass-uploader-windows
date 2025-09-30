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


@login_required
def create_photo_post(request):
    if request.method == 'POST':
        form = PhotoPostForm(request.POST, request.FILES)
        if form.is_valid():
            accounts = list(form.cleaned_data['selected_accounts'])
            photo_file = request.FILES.get('photo')
            caption = form.cleaned_data.get('caption') or ''
            mentions = form.cleaned_data.get('mentions') or ''
            location = form.cleaned_data.get('location') or ''
            delay_min = form.cleaned_data.get('delay_min_sec') or 10
            delay_max = form.cleaned_data.get('delay_max_sec') or 25

            # Save photo to media temporary path
            saved_path = default_storage.save(os.path.join('bot', 'photos', photo_file.name), photo_file)
            abs_photo_path = default_storage.path(saved_path)

            # Start background worker thread to post per account sequentially with delays
            def _worker(photo_path: str, acc_ids):
                try:
                    for idx, acc_id in enumerate(acc_ids):
                        # human-like delay between accounts
                        if idx > 0:
                            time.sleep(random.uniform(delay_min, delay_max))

                        try:
                            acc = InstagramAccount.objects.get(id=acc_id)
                        except Exception:
                            continue

                        def on_log(line: str):
                            # Simple stdout log; could be extended to per-account logs
                            log_info(f"[PHOTO_POST] {acc.username} | {line}")

                        account_details = {
                            'username': acc.username,
                            'password': acc.password,
                            'tfa_secret': getattr(acc, 'tfa_secret', None),
                            'email_login': getattr(acc, 'email_username', None),
                            'email_password': getattr(acc, 'email_password', None),
                            'proxy': (acc.current_proxy or acc.proxy).to_dict() if (acc.current_proxy or acc.proxy) else {},
                        }

                        try:
                            import asyncio
                            asyncio.run(run_instagrapi_photo_upload_async(
                                account_details=account_details,
                                photo_files_to_upload=[photo_path],
                                captions=[caption],
                                mentions_list=[mentions],
                                locations_list=[location],
                                on_log=on_log,
                            ))
                        except RuntimeError:
                            # If we're inside an existing loop (unlikely here), fallback
                            loop = asyncio.new_event_loop()
                            try:
                                loop.run_until_complete(run_instagrapi_photo_upload_async(
                                    account_details=account_details,
                                    photo_files_to_upload=[photo_path],
                                    captions=[caption],
                                    mentions_list=[mentions],
                                    locations_list=[location],
                                    on_log=on_log,
                                ))
                            finally:
                                loop.close()
                finally:
                    # best-effort cleanup: keep the uploaded media as audit by default
                    pass

            t = threading.Thread(target=_worker, args=(abs_photo_path, [a.id for a in accounts]), daemon=True)
            t.start()

            messages.success(request, f"Photo posting started for {len(accounts)} accounts")
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
    """Simple status page showing recent log lines for photo posting activity."""
    log_lines = []
    try:
        # Tail last 300 lines from bot/log.txt if exists
        log_path = default_storage.path('bot/log.txt') if hasattr(default_storage, 'path') else os.path.join(os.getcwd(), 'bot', 'log.txt')
        if os.path.exists(log_path):
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                log_lines = lines[-300:]
    except Exception:
        log_lines = []

    return render(request, 'uploader/photos/status.html', {
        'log_lines': log_lines,
        'active_tab': 'avatars',
    })

