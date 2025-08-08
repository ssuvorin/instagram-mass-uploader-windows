from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.urls import reverse
from django.db import transaction

import random
import time
import logging

from .models import (
    InstagramAccount,
    Proxy,
    InstagramDevice,
    FollowCategory,
    FollowTarget,
    FollowTask,
    FollowTaskAccount,
)
from .forms import FollowCategoryForm, FollowTargetForm, FollowTaskForm, FollowTargetsBulkForm

from instgrapi_func.services.follow_service import FollowService
from instgrapi_func.services.auth_service import IGAuthService

logger = logging.getLogger(__name__)


@login_required
def follow_category_list(request):
    categories = FollowCategory.objects.order_by('name')
    return render(request, 'uploader/follow/category_list.html', {
        'categories': categories,
        'active_tab': 'follow',
    })


@login_required
def follow_category_create(request):
    if request.method == 'POST':
        form = FollowCategoryForm(request.POST)
        bulk_form = FollowTargetsBulkForm(request.POST)
        if form.is_valid() and bulk_form.is_valid():
            category = form.save()
            usernames = bulk_form.cleaned_data.get('usernames', [])
            created = 0
            for uname in usernames:
                obj, was_created = FollowTarget.objects.get_or_create(category=category, username=uname)
                if was_created:
                    created += 1
            messages.success(request, f"Category created. Added {created} usernames")
            return redirect('follow_category_detail', category_id=category.id)
    else:
        form = FollowCategoryForm()
        bulk_form = FollowTargetsBulkForm()
    return render(request, 'uploader/follow/category_create.html', {
        'form': form,
        'bulk_form': bulk_form,
        'active_tab': 'follow',
    })


@login_required
def follow_category_detail(request, category_id):
    category = get_object_or_404(FollowCategory, id=category_id)
    targets = category.targets.order_by('username')
    target_form = FollowTargetForm()
    bulk_form = FollowTargetsBulkForm()
    return render(request, 'uploader/follow/category_detail.html', {
        'category': category,
        'targets': targets,
        'target_form': target_form,
        'bulk_form': bulk_form,
        'active_tab': 'follow',
    })


@login_required
def follow_target_add(request, category_id):
    category = get_object_or_404(FollowCategory, id=category_id)
    if request.method == 'POST':
        # Support single add OR bulk add
        form = FollowTargetForm(request.POST)
        bulk_form = FollowTargetsBulkForm(request.POST)
        added = 0
        if bulk_form.is_valid() and bulk_form.cleaned_data.get('usernames'):
            for uname in bulk_form.cleaned_data['usernames']:
                _, created = FollowTarget.objects.get_or_create(category=category, username=uname)
                if created:
                    added += 1
            messages.success(request, f'Added {added} usernames')
            return redirect('follow_category_detail', category_id=category.id)
        if form.is_valid():
            username = form.cleaned_data['username'].lstrip('@').strip().lower()
            if not username:
                messages.error(request, 'Username is required')
                return redirect('follow_category_detail', category_id=category.id)
            FollowTarget.objects.get_or_create(category=category, username=username)
            messages.success(request, f'Added {username}')
    return redirect('follow_category_detail', category_id=category.id)


@login_required
def follow_target_delete(request, category_id, target_id):
    category = get_object_or_404(FollowCategory, id=category_id)
    target = get_object_or_404(FollowTarget, id=target_id, category=category)
    target.delete()
    messages.success(request, 'Deleted target')
    return redirect('follow_category_detail', category_id=category.id)


@login_required
def follow_task_create(request):
    if request.method == 'POST':
        form = FollowTaskForm(request.POST)
        if form.is_valid():
            task = FollowTask.objects.create(
                name=f"Follow Task - {timezone.now().strftime('%Y-%m-%d %H:%M')}",
                category=form.cleaned_data['category'],
                delay_min_sec=form.cleaned_data['delay_min_sec'],
                delay_max_sec=form.cleaned_data['delay_max_sec'],
                concurrency=form.cleaned_data['concurrency'],
            )
            for acc in form.cleaned_data['selected_accounts']:
                FollowTaskAccount.objects.create(
                    task=task, account=acc, proxy=(acc.current_proxy or acc.proxy)
                )
            task.log = (task.log or '') + f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] Task created with {form.cleaned_data['selected_accounts'].count()} accounts\n"
            task.save(update_fields=['log'])
            messages.success(request, f'Task #{task.id} created')
            return redirect('follow_task_detail', task_id=task.id)
    else:
        form = FollowTaskForm()
    return render(request, 'uploader/follow/task_create.html', {
        'form': form,
        'active_tab': 'follow',
    })


@login_required
def follow_task_list(request):
    tasks = FollowTask.objects.order_by('-created_at')
    return render(request, 'uploader/follow/task_list.html', {
        'tasks': tasks,
        'active_tab': 'follow',
    })


@login_required
def follow_task_detail(request, task_id):
    task = get_object_or_404(FollowTask, id=task_id)
    accounts = task.accounts.select_related('account', 'proxy').all()
    return render(request, 'uploader/follow/task_detail.html', {
        'task': task,
        'accounts': accounts,
        'active_tab': 'follow',
    })


def _ensure_device(account: InstagramAccount) -> InstagramDevice:
    device = getattr(account, 'device', None)
    if device:
        return device
    return InstagramDevice.objects.create(account=account, device_settings={}, user_agent="")


@login_required
def follow_task_start(request, task_id):
    task = get_object_or_404(FollowTask, id=task_id)
    if task.status == 'RUNNING':
        messages.info(request, 'Task already running')
        return redirect('follow_task_detail', task_id=task.id)

    task.status = 'RUNNING'
    task.log += f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] Start task\n"
    task.save(update_fields=['status', 'log'])

    import threading
    t = threading.Thread(target=_follow_task_worker, args=(task.id,), daemon=True)
    t.start()

    messages.success(request, f'Task #{task.id} started')
    return redirect('follow_task_detail', task_id=task.id)


def _follow_task_worker(task_id: int):
    try:
        task = FollowTask.objects.get(id=task_id)
        accounts = list(task.accounts.select_related('account', 'proxy').all())
        targets = list(task.category.targets.order_by('id').all())
        if not accounts or not targets:
            task.status = 'FAILED'
            task.log += f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] No accounts or targets\n"
            task.save(update_fields=['status', 'log'])
            return

        def make_logger(prefix: str):
            def _log(line: str):
                nonlocal task
                task.log = (task.log or '') + f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] {prefix} | {line}\n"
                task.save(update_fields=['log'])
            return _log

        service = FollowService(auth_service=IGAuthService())

        for ta in accounts:
            acc = ta.account
            try:
                delay = random.uniform(task.delay_min_sec, task.delay_max_sec)
                time.sleep(delay)

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

                on_log = make_logger(acc.username)
                on_log("start")
                on_log(f"proxy: {(ta.proxy or acc.current_proxy or acc.proxy).host if (ta.proxy or acc.current_proxy or acc.proxy) else 'none'}")

                # Iterate a random subset of targets per account
                fmin = max(0, int(task.follow_min_count or 0))
                fmax = max(fmin, int(task.follow_max_count or 0))
                if not targets:
                    chosen_targets = []
                else:
                    count = random.randint(fmin, min(fmax, len(targets)))
                    chosen_targets = random.sample(targets, count) if count > 0 else []

                for target in chosen_targets:
                    # human-like pause between follows per account
                    time.sleep(random.uniform(3, 8))
                    ok, resolved_user_id, updated_settings = service.follow_target(
                        account={
                            "username": acc.username,
                            "password": acc.password,
                            "tfa_secret": getattr(acc, 'tfa_secret', None),
                            "email": getattr(acc, 'email_username', None),
                            "email_password": getattr(acc, 'email_password', None),
                        },
                        target_username=target.username,
                        target_user_id=target.user_id,
                        device_settings=device_settings,
                        session_settings=device.session_settings,
                        proxy=(ta.proxy or acc.current_proxy or acc.proxy).to_dict() if (ta.proxy or acc.current_proxy or acc.proxy) else None,
                        on_log=on_log,
                    )
                    if resolved_user_id and target.user_id != resolved_user_id:
                        # persist resolved user_id in DB
                        FollowTarget.objects.filter(id=target.id).update(user_id=resolved_user_id)
                        on_log(f"resolved user_id stored: {resolved_user_id}")
                    if ok:
                        on_log(f"followed {target.username}")
                        if updated_settings:
                            device.session_settings = updated_settings
                            device.last_login_at = timezone.now()
                            device.save(update_fields=['session_settings', 'last_login_at'])
                    else:
                        on_log(f"failed to follow {target.username}")

                ta.status = 'COMPLETED'
                ta.completed_at = timezone.now()
                ta.save(update_fields=['status', 'completed_at'])
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
            task = FollowTask.objects.get(id=task_id)
            task.status = 'FAILED'
            task.log += f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] fatal error: {str(e)}\n"
            task.save(update_fields=['status', 'log'])
        except Exception:
            logger.exception("Follow task fatal error and failed to update task")


@login_required
def follow_task_logs(request, task_id):
    task = get_object_or_404(FollowTask, id=task_id)
    return JsonResponse({
        'status': task.status,
        'log': task.log,
        'updated_at': task.updated_at.isoformat() if task.updated_at else None,
    }) 