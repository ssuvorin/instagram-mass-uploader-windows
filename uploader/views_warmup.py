from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone

import random
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from .models import (
    InstagramAccount,
    InstagramDevice,
    Proxy,
    WarmupTask,
    WarmupTaskAccount,
    FollowCategory,
    FollowTarget,
)
from .forms import WarmupTaskForm

from instgrapi_func.services.warmup_service import WarmupService
from instgrapi_func.services.auth_service import IGAuthService


def _ensure_device(account: InstagramAccount) -> InstagramDevice:
    device = getattr(account, 'device', None)
    if device:
        return device
    return InstagramDevice.objects.create(account=account, device_settings={}, user_agent="")


def _build_proxy_dict(proxy: Proxy):
    return proxy.to_dict() if proxy else None


@login_required
def warmup_task_list(request):
    tasks = WarmupTask.objects.order_by('-created_at')
    return render(request, 'uploader/warmup/list.html', {
        'tasks': tasks,
        'active_tab': 'warmup',
    })


@login_required
def warmup_task_create(request):
    if request.method == 'POST':
        form = WarmupTaskForm(request.POST)
        if form.is_valid():
            task = WarmupTask.objects.create(
                name=f"Warmup Task - {timezone.now().strftime('%Y-%m-%d %H:%M')}",
                follow_category=form.cleaned_data['follow_category'],
                delay_min_sec=form.cleaned_data['delay_min_sec'],
                delay_max_sec=form.cleaned_data['delay_max_sec'],
                concurrency=form.cleaned_data['concurrency'],
                feed_scroll_min_count=form.cleaned_data['feed_scroll_min_count'],
                feed_scroll_max_count=form.cleaned_data['feed_scroll_max_count'],
                like_min_count=form.cleaned_data['like_min_count'],
                like_max_count=form.cleaned_data['like_max_count'],
                view_stories_min_count=form.cleaned_data['view_stories_min_count'],
                view_stories_max_count=form.cleaned_data['view_stories_max_count'],
                follow_min_count=form.cleaned_data['follow_min_count'],
                follow_max_count=form.cleaned_data['follow_max_count'],
            )
            # link accounts
            for acc in form.cleaned_data['selected_accounts']:
                WarmupTaskAccount.objects.create(
                    task=task, account=acc, proxy=(acc.current_proxy or acc.proxy)
                )
            task.log = (task.log or '') + f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] Task created with {form.cleaned_data['selected_accounts'].count()} accounts\n"
            task.save(update_fields=['log'])
            messages.success(request, f'Warmup task #{task.id} created')
            return redirect('warmup_task_detail', task_id=task.id)
        else:
            messages.error(request, 'Please fix the errors in the form and try again.')
    else:
        form = WarmupTaskForm()
    return render(request, 'uploader/warmup/create.html', {
        'form': form,
        'active_tab': 'warmup',
    })


@login_required
def warmup_task_detail(request, task_id):
    task = get_object_or_404(WarmupTask, id=task_id)
    accounts = task.accounts.select_related('account', 'proxy').all()
    return render(request, 'uploader/warmup/detail.html', {
        'task': task,
        'accounts': accounts,
        'active_tab': 'warmup',
    })


@login_required
def warmup_task_start(request, task_id):
    task = get_object_or_404(WarmupTask, id=task_id)
    if task.status == 'RUNNING':
        messages.info(request, 'Task already running')
        return redirect('warmup_task_detail', task_id=task.id)

    task.status = 'RUNNING'
    task.log += f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] Start task\n"
    task.save(update_fields=['status', 'log'])

    t = threading.Thread(target=_warmup_task_worker, args=(task.id,), daemon=True)
    t.start()

    messages.success(request, f'Warmup task #{task.id} started')
    return redirect('warmup_task_detail', task_id=task.id)


def _make_logger(task: WarmupTask, prefix: str):
    def _log(line: str):
        nonlocal task
        task.log = (task.log or '') + f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] {prefix} | {line}\n"
        task.save(update_fields=['log'])
    return _log


def _select_follow_usernames(task: WarmupTask) -> list[str]:
    if not task.follow_category:
        return []
    targets = list(task.follow_category.targets.order_by('id').all())
    if not targets:
        return []
    fmin = max(0, int(task.follow_min_count or 0))
    fmax = max(fmin, int(task.follow_max_count or 0))
    count = random.randint(fmin, min(fmax, len(targets))) if targets else 0
    if count <= 0:
        return []
    chosen = random.sample(targets, count)
    return [t.username for t in chosen if t.username]


def _warmup_task_worker(task_id: int):
    try:
        task = WarmupTask.objects.get(id=task_id)
        accounts = list(task.accounts.select_related('account', 'proxy').all())
        if not accounts:
            task.status = 'FAILED'
            task.log += f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] No accounts\n"
            task.save(update_fields=['status', 'log'])
            return

        service = WarmupService(auth_service=IGAuthService())

        # Concurrency hard cap at 4
        max_workers = min(int(task.concurrency or 1), 4)

        def _run_one(ta: WarmupTaskAccount):
            acc = ta.account
            on_log = _make_logger(task, acc.username)
            try:
                # human-like delay between account starts
                time.sleep(random.uniform(task.delay_min_sec, task.delay_max_sec))

                device = _ensure_device(acc)
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

                proxy_dict = _build_proxy_dict(ta.proxy or acc.current_proxy or acc.proxy)
                on_log("start")
                if proxy_dict:
                    on_log(f"proxy: {proxy_dict.get('host')}")
                follow_usernames = _select_follow_usernames(task)
                config = {
                    'instagrapi_delay_range': [1, 3],
                    'feed_scroll_min_count': task.feed_scroll_min_count,
                    'feed_scroll_max_count': task.feed_scroll_max_count,
                    'like_min_count': task.like_min_count,
                    'like_max_count': task.like_max_count,
                    'view_stories_min_count': task.view_stories_min_count,
                    'view_stories_max_count': task.view_stories_max_count,
                }
                ok, updated_settings = service.perform_warmup(
                    account={
                        "username": acc.username,
                        "password": acc.password,
                        "tfa_secret": getattr(acc, 'tfa_secret', None),
                        "email": getattr(acc, 'email_username', None),
                        "email_password": getattr(acc, 'email_password', None),
                    },
                    device_settings=device_settings,
                    session_settings=device.session_settings,
                    proxy=proxy_dict,
                    config=config,
                    follow_usernames=follow_usernames,
                    on_log=on_log,
                )

                if ok:
                    ta.status = 'COMPLETED'
                    ta.completed_at = timezone.now()
                    if updated_settings:
                        # persist session and capture device identifiers if missing
                        device.session_settings = updated_settings
                        device.last_login_at = timezone.now()
                        # If device_settings lacks uuids/user_agent, try to adopt from settings
                        try:
                            if not device.device_settings:
                                device.device_settings = updated_settings.get('device_settings') or device_settings
                            if not device.user_agent and updated_settings.get('user_agent'):
                                device.user_agent = updated_settings.get('user_agent')
                        except Exception:
                            pass
                        device.save(update_fields=['session_settings', 'last_login_at', 'device_settings', 'user_agent'])
                    on_log("warmup completed")
                else:
                    ta.status = 'FAILED'
                    on_log("warmup failed")
                ta.save(update_fields=['status', 'completed_at', 'log'] if hasattr(ta, 'log') else ['status', 'completed_at'])
            except Exception as e:
                ta.status = 'FAILED'
                ta.log = (ta.log or '') + f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] Error: {str(e)}\n"
                ta.completed_at = timezone.now()
                ta.save(update_fields=['status', 'log', 'completed_at'])
                task.log += f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] {acc.username} | exception {str(e)}\n"
                task.save(update_fields=['log'])

        # Run accounts with limited concurrency
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(_run_one, ta) for ta in accounts]
            for _ in as_completed(futures):
                pass

        task.status = 'COMPLETED'
        task.save(update_fields=['status'])
    except Exception as e:
        try:
            task = WarmupTask.objects.get(id=task_id)
            task.status = 'FAILED'
            task.log += f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] fatal error: {str(e)}\n"
            task.save(update_fields=['status', 'log'])
        except Exception:
            pass


@login_required
def warmup_task_logs(request, task_id):
    task = get_object_or_404(WarmupTask, id=task_id)
    return JsonResponse({
        'status': task.status,
        'log': task.log,
        'updated_at': task.updated_at.isoformat() if task.updated_at else None,
    })
