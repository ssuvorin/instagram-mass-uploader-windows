from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
import threading
import random
import time

from ..models import (
    InstagramAccount, Proxy, InstagramDevice,
    BioLinkChangeTask, BioLinkChangeTaskAccount,
)
from ..forms import BioLinkChangeTaskForm

from instgrapi_func.bio_manager import change_bio_link_for_account
from instgrapi_func.services.session_store import DjangoDeviceSessionStore
from instgrapi_func.services.device_service import ensure_persistent_device

import logging
logger = logging.getLogger(__name__)


@login_required
def bio_task_list(request):
    tasks = BioLinkChangeTask.objects.order_by('-created_at')
    return render(request, 'uploader/bio/list.html', {
        'tasks': tasks,
        'active_tab': 'bio',
    })


@login_required
def create_bio_task(request):
    if request.method == 'POST':
        form = BioLinkChangeTaskForm(request.POST)
        if form.is_valid():
            task = BioLinkChangeTask.objects.create(
                name=f"Bio Link Change - {timezone.now().strftime('%Y-%m-%d %H:%M')}",
                link_url=form.cleaned_data['link_url'],
                delay_min_sec=form.cleaned_data['delay_min_sec'],
                delay_max_sec=form.cleaned_data['delay_max_sec'],
                concurrency=form.cleaned_data['concurrency'],
            )
            # link accounts
            for acc in form.cleaned_data['selected_accounts']:
                BioLinkChangeTaskAccount.objects.create(
                    task=task, account=acc, proxy=(acc.current_proxy or acc.proxy)
                )
            # initial log entry
            task.log = (task.log or '') + f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] Task created with {form.cleaned_data['selected_accounts'].count()} accounts\n"
            task.save(update_fields=['log'])

            messages.success(request, f'Bio task #{task.id} created')
            return redirect('bio_task_detail', task_id=task.id)
        else:
            messages.error(request, 'Please fix the errors in the form and try again.')
    else:
        form = BioLinkChangeTaskForm()
    return render(request, 'uploader/bio/create.html', {
        'form': form,
        'active_tab': 'bio',
    })


@login_required
def bio_task_detail(request, task_id):
    task = get_object_or_404(BioLinkChangeTask, id=task_id)
    accounts = task.accounts.select_related('account', 'proxy').all()
    return render(request, 'uploader/bio/detail.html', {
        'task': task,
        'accounts': accounts,
        'active_tab': 'bio',
    })


@login_required
def start_bio_task(request, task_id):
    task = get_object_or_404(BioLinkChangeTask, id=task_id)
    if task.status == 'RUNNING':
        messages.info(request, 'Task already running')
        return redirect('bio_task_detail', task_id=task.id)

    task.status = 'RUNNING'
    task.log += f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] Start task\n"
    task.save(update_fields=['status', 'log'])

    # run background thread
    t = threading.Thread(target=_run_bio_task_worker, args=(task.id,), daemon=True)
    t.start()

    messages.success(request, f'Bio task #{task.id} started')
    return redirect('bio_task_detail', task_id=task.id)


def _ensure_device(account: InstagramAccount) -> InstagramDevice:
    device = getattr(account, 'device', None)
    if device:
        # If exists but empty, try to populate from session or generate once
        if not device.device_settings or not any(device.device_settings.get(k) for k in ("uuid","android_device_id","phone_id","client_session_id")) or not device.user_agent:
            try:
                store = DjangoDeviceSessionStore()
                persisted = store.load(account.username) or {}
                dev_settings, ua = ensure_persistent_device(account.username, persisted)
                updates = []
                if not device.device_settings:
                    device.device_settings = dev_settings
                    updates.append('device_settings')
                if not device.user_agent and ua:
                    device.user_agent = ua
                    updates.append('user_agent')
                if updates:
                    device.save(update_fields=updates)
            except Exception:
                pass
        return device
    try:
        store = DjangoDeviceSessionStore()
        persisted = store.load(account.username) or {}
        dev_settings, ua = ensure_persistent_device(account.username, persisted)
        return InstagramDevice.objects.create(account=account, device_settings=dev_settings, user_agent=(ua or ""))
    except Exception:
        return InstagramDevice.objects.create(account=account, device_settings={}, user_agent="")


def _build_proxy_dict(proxy: Proxy):
    if not proxy:
        return None
    return proxy.to_dict()


def _run_bio_task_worker(task_id: int):
    try:
        task = BioLinkChangeTask.objects.get(id=task_id)
        accounts = list(task.accounts.select_related('account', 'proxy').all())
        if not accounts:
            task.status = 'FAILED'
            task.log += f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] No accounts\n"
            task.save(update_fields=['status', 'log'])
            return

        def make_logger(username: str):
            def _log(line: str):
                nonlocal task
                task.log = (task.log or '') + f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] {username} | {line}\n"
                task.save(update_fields=['log'])
            return _log

        # Sequential with human-like delays; respect concurrency=1 for now
        for idx, ta in enumerate(accounts):
            acc = ta.account
            try:
                # human-like delay between accounts
                delay = random.uniform(task.delay_min_sec, task.delay_max_sec)
                time.sleep(delay)

                device = _ensure_device(acc)

                # compose device settings fallback if empty
                device_settings = device.device_settings or {
                    "cpu": "exynos9820",
                    "dpi": "640dpi",
                    "model": "SM-G973F",
                    "device": "beyond1",
                    "resolution": "1440x3040",
                    "app_version": "269.0.0.18.75",
                    "manufacturer": "samsung",
                    "version_code": "314665256",
                    "android_release": "10",
                    "android_version": 29,
                    "uuid": None,
                    "android_device_id": None,
                    "phone_id": None,
                    "client_session_id": None,
                    "locale": "en_US",
                    "country": "US",
                }
                if device.user_agent:
                    device_settings['user_agent'] = device.user_agent

                on_log = make_logger(acc.username)
                on_log("start")
                on_log(f"proxy: { (ta.proxy or acc.current_proxy or acc.proxy).host if (ta.proxy or acc.current_proxy or acc.proxy) else 'none' }")
                on_log("build client")
                success, updated_settings = change_bio_link_for_account(
                    account={"username": acc.username, "password": acc.password, "tfa_secret": getattr(acc, 'tfa_secret', None), "email": getattr(acc, 'email_username', None), "email_password": getattr(acc, 'email_password', None)},
                    link_url=task.link_url,
                    device_settings=device_settings,
                    session_settings=device.session_settings,
                    proxy=_build_proxy_dict(ta.proxy or acc.current_proxy or acc.proxy),
                    on_log=on_log,
                )

                if success:
                    ta.status = 'COMPLETED'
                    ta.completed_at = timezone.now()
                    on_log("bio link updated")
                    # persist session/device if updated
                    if updated_settings:
                        device.session_settings = updated_settings
                        device.last_login_at = timezone.now()
                        device.save(update_fields=['session_settings', 'last_login_at'])
                        try:
                            country = updated_settings.get('country')
                            locale = updated_settings.get('locale')
                            tz = updated_settings.get('timezone_offset')
                            on_log(f"session saved: keys={len(updated_settings.keys())}, country={country}, locale={locale}, tz_offset={tz}")
                        except Exception:
                            on_log("session saved")
                    else:
                        on_log("session not returned by client; skip save")
                else:
                    ta.status = 'FAILED'
                    on_log("failed")
                ta.save(update_fields=['status', 'completed_at', 'log'] if hasattr(ta, 'log') else ['status', 'completed_at'])
                task.save(update_fields=['log'])
            except Exception as e:
                ta.status = 'FAILED'
                ta.log = (ta.log or '') + f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] Error: {str(e)}\n"
                ta.completed_at = timezone.now()
                ta.save(update_fields=['status', 'log', 'completed_at'])
                task.log += f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] {acc.username} | exception {str(e)}\n"
                task.save(update_fields=['log'])

        task.status = 'COMPLETED'
        task.save(update_fields=['status'])
    except Exception as e:
        try:
            task = BioLinkChangeTask.objects.get(id=task_id)
            task.status = 'FAILED'
            task.log += f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] fatal error: {str(e)}\n"
            task.save(update_fields=['status', 'log'])
        except Exception:
            logger.exception("Bio task fatal error and failed to update task")


@login_required
def get_bio_task_logs(request, task_id):
    task = get_object_or_404(BioLinkChangeTask, id=task_id)
    return JsonResponse({
        'status': task.status,
        'log': task.log,
        'updated_at': task.updated_at.isoformat() if task.updated_at else None,
    }) 