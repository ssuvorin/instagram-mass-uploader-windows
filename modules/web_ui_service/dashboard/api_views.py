from __future__ import annotations
import json
from typing import Any, Dict, List
from django.conf import settings
from django.http import JsonResponse, FileResponse, HttpResponse, HttpResponseForbidden, Http404
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.utils import timezone

from uploader.models import (
    BulkUploadTask, BulkUploadAccount, BulkVideo,
    BulkLoginTask, BulkLoginAccount,
    WarmupTask, WarmupTaskAccount,
    AvatarChangeTask, AvatarChangeTaskAccount, AvatarImage,
    BioLinkChangeTask, BioLinkChangeTaskAccount,
    FollowTask, FollowTaskAccount, FollowTarget,
    InstagramAccount, Proxy, DolphinCookieRobotTask,
    FollowCategory
)
from .models import TaskLock, WorkerNode
import time


def _ip_allowed(request) -> bool:
    allow = getattr(settings, 'WORKER_ALLOWED_IPS', [])
    if not allow:
        return True
    meta_ip = request.META.get('HTTP_X_FORWARDED_FOR') or request.META.get('REMOTE_ADDR')
    client_ip = (meta_ip.split(',')[0] if meta_ip else '').strip()
    return client_ip in allow


def _auth_ok(request) -> bool:
    if not _ip_allowed(request):
        return False
    auth = request.headers.get("Authorization") or ""
    tokens = []
    single = getattr(settings, 'WORKER_API_TOKEN', '')
    if single:
        tokens.append(single)
    tokens.extend(getattr(settings, 'WORKER_API_TOKENS', []) or [])
    if not tokens:
        return False
    if not auth.startswith("Bearer "):
        return False
    presented = auth.split(" ", 1)[1]
    return presented in tokens


def _forbidden() -> HttpResponse:
    return HttpResponseForbidden(JsonResponse({"detail": "Forbidden"}).content, content_type="application/json")


# ===== Bulk Upload =====

@require_GET
@csrf_exempt
def bulk_task_aggregate(request, task_id: int):
    if not _auth_ok(request):
        return _forbidden()
    task = get_object_or_404(BulkUploadTask, id=task_id)
    accounts_payload = []
    for at in task.accounts.select_related("account", "proxy").all():
        acc = at.account
        accounts_payload.append({
            "account_task_id": at.id,
            "account": acc.to_dict(),
        })
    videos_payload = []
    for v in task.videos.order_by("order", "id").all():
        title_val = getattr(v, 'title_data', None).title if getattr(v, 'title_data', None) else None
        videos_payload.append({
            "id": v.id,
            "order": v.order,
            "title": title_val,
            "location": v.location or "",
            "mentions": v.mentions or "",
            "url": None,
        })
    payload = {
        "id": task.id,
        "default_location": task.default_location or "",
        "default_mentions": task.default_mentions or "",
        "accounts": accounts_payload,
        "videos": videos_payload,
    }
    return JsonResponse(payload)

@require_GET
@csrf_exempt
def media_download(request, video_id: int):
    if not _auth_ok(request):
        return _forbidden()
    # Backward-compatible endpoint: try BulkVideo first, then AvatarImage
    try:
        v = BulkVideo.objects.get(id=video_id)
        if not v.video_file:
            raise Http404("Video file not found")
        return FileResponse(
            v.video_file.open("rb"),
            as_attachment=True,
            filename=v.video_file.name.split("/")[-1],
        )
    except BulkVideo.DoesNotExist:
        img = get_object_or_404(AvatarImage, id=video_id)
        if not img.image:
            raise Http404("Image file not found")
        return FileResponse(
            img.image.open("rb"),
            as_attachment=True,
            filename=img.image.name.split("/")[-1],
        )


@require_GET
@csrf_exempt
def avatar_media_download(request, image_id: int):
    if not _auth_ok(request):
        return _forbidden()
    img = get_object_or_404(AvatarImage, id=image_id)
    if not img.image:
        raise Http404("Image file not found")
    return FileResponse(
        img.image.open("rb"),
        as_attachment=True,
        filename=img.image.name.split("/")[-1],
    )


# ===== Worker registration & heartbeat =====

@require_POST
@csrf_exempt
def worker_register(request):
    if not _auth_ok(request):
        return _forbidden()
    try:
        body = json.loads(request.body.decode('utf-8')) if request.body else {}
    except json.JSONDecodeError:
        body = {}
    base_url = body.get('base_url') or ''
    name = body.get('name') or ''
    capacity = int(body.get('capacity') or 1)
    if not base_url:
        return JsonResponse({"detail": "base_url required"}, status=400)
    node, _created = WorkerNode.objects.get_or_create(base_url=base_url, defaults={"name": name, "capacity": capacity})
    if not _created:
        changed = False
        if name and node.name != name:
            node.name = name
            changed = True
        if node.capacity != capacity:
            node.capacity = capacity
            changed = True
        if changed:
            node.save(update_fields=['name', 'capacity', 'updated_at'])
    node.mark_heartbeat(ok=True)
    return JsonResponse({"ok": True})


@require_POST
@csrf_exempt
def worker_heartbeat(request):
    if not _auth_ok(request):
        return _forbidden()
    try:
        body = json.loads(request.body.decode('utf-8')) if request.body else {}
    except json.JSONDecodeError:
        body = {}
    base_url = body.get('base_url') or ''
    if not base_url:
        return JsonResponse({"detail": "base_url required"}, status=400)
    node = WorkerNode.objects.filter(base_url=base_url).first()
    if not node:
        return JsonResponse({"detail": "unknown worker"}, status=404)
    node.mark_heartbeat(ok=True)
    return JsonResponse({"ok": True})

@require_POST
@csrf_exempt
def bulk_task_status(request, task_id: int):
    if not _auth_ok(request):
        return _forbidden()
    task = get_object_or_404(BulkUploadTask, id=task_id)
    try:
        data = json.loads(request.body.decode("utf-8")) if request.body else {}
    except json.JSONDecodeError:
        data = {}
    status_val = data.get("status")
    log = data.get("log")
    log_append = data.get("log_append")
    if status_val:
        task.status = status_val
    if log:
        task.log = (task.log or "") + log + "\n"
    if log_append:
        task.log = (task.log or "") + log_append + "\n"
    task.save(update_fields=['status','log','updated_at'])
    # Release lock on terminal statuses
    if status_val in ("COMPLETED", "FAILED"):
        try:
            TaskLock.objects.filter(kind='bulk', task_id=task_id).delete()
        except Exception:
            pass
    return JsonResponse({"ok": True, "status": task.status})

@require_POST
@csrf_exempt
def bulk_account_status(request, account_task_id: int):
    if not _auth_ok(request):
        return _forbidden()
    at = get_object_or_404(BulkUploadAccount, id=account_task_id)
    try:
        data = json.loads(request.body.decode("utf-8")) if request.body else {}
    except json.JSONDecodeError:
        data = {}
    status_val = data.get("status")
    log_append = data.get("log_append")
    if status_val:
        at.status = status_val
    if log_append:
        at.log = (at.log or "") + log_append + "\n"
    at.save(update_fields=['status','log','updated_at'])
    return JsonResponse({"ok": True, "status": at.status})

@require_POST
@csrf_exempt
def bulk_account_counters(request, account_task_id: int):
    if not _auth_ok(request):
        return _forbidden()
    at = get_object_or_404(BulkUploadAccount, id=account_task_id)
    try:
        data = json.loads(request.body.decode("utf-8")) if request.body else {}
    except json.JSONDecodeError:
        data = {}
    at.uploaded_success_count = (at.uploaded_success_count or 0) + int(data.get('success', 0) or 0)
    at.uploaded_failed_count = (at.uploaded_failed_count or 0) + int(data.get('failed', 0) or 0)
    at.save(update_fields=['uploaded_success_count','uploaded_failed_count','updated_at'])
    return JsonResponse({
        "ok": True,
        "uploaded_success_count": at.uploaded_success_count,
        "uploaded_failed_count": at.uploaded_failed_count,
    })


# ===== Placeholders for other aggregates (return minimal structure until full mapping is needed) =====

@require_GET
@csrf_exempt
def bulk_login_aggregate(request, task_id: int):
    if not _auth_ok(request):
        return _forbidden()
    task = get_object_or_404(BulkLoginTask, id=task_id)
    accounts = [
        {"account_task_id": at.id, "account": at.account.to_dict()}
        for at in task.accounts.select_related("account","proxy").all()
    ]
    return JsonResponse({"id": task.id, "accounts": accounts})

@require_GET
@csrf_exempt
def warmup_aggregate(request, task_id: int):
    if not _auth_ok(request):
        return _forbidden()
    task = get_object_or_404(WarmupTask, id=task_id)
    accounts = [
        {"account_task_id": at.id, "account": at.account.to_dict()}
        for at in task.accounts.select_related("account","proxy").all()
    ]
    actions = {
        "feed_scroll_min_count": task.feed_scroll_min_count,
        "feed_scroll_max_count": task.feed_scroll_max_count,
        "like_min_count": task.like_min_count,
        "like_max_count": task.like_max_count,
        "view_stories_min_count": task.view_stories_min_count,
        "view_stories_max_count": task.view_stories_max_count,
        "follow_min_count": task.follow_min_count,
        "follow_max_count": task.follow_max_count,
    }
    return JsonResponse({"id": task.id, "actions": actions, "accounts": accounts})

@require_GET
@csrf_exempt
def avatar_aggregate(request, task_id: int):
    if not _auth_ok(request):
        return _forbidden()
    task = get_object_or_404(AvatarChangeTask, id=task_id)
    accounts = [
        {"account_task_id": at.id, "account": at.account.to_dict()}
        for at in task.accounts.select_related("account","proxy").all()
    ]
    images = [
        {"id": img.id, "order": img.order, "url": None}
        for img in task.images.order_by('order','id').all()
    ]
    return JsonResponse({"id": task.id, "strategy": task.strategy, "accounts": accounts, "images": images})

@require_GET
@csrf_exempt
def bio_aggregate(request, task_id: int):
    if not _auth_ok(request):
        return _forbidden()
    task = get_object_or_404(BioLinkChangeTask, id=task_id)
    accounts = [
        {"account_task_id": at.id, "account": at.account.to_dict()}
        for at in task.accounts.select_related("account","proxy").all()
    ]
    return JsonResponse({"id": task.id, "link_url": task.link_url, "accounts": accounts})

@require_GET
@csrf_exempt
def follow_aggregate(request, task_id: int):
    if not _auth_ok(request):
        return _forbidden()
    task = get_object_or_404(FollowTask, id=task_id)
    accounts = [
        {"account_task_id": at.id, "account": at.account.to_dict()}
        for at in task.accounts.select_related("account","proxy").all()
    ]
    targets = [
        {"username": t.username} for t in FollowTarget.objects.filter(category=task.category).all()
    ]
    options = {"follow_min_count": task.follow_min_count, "follow_max_count": task.follow_max_count}
    return JsonResponse({"id": task.id, "accounts": accounts, "targets": targets, "options": options})

@require_GET
@csrf_exempt
def proxy_diag_aggregate(request, task_id: int):
    if not _auth_ok(request):
        return _forbidden()
    task = get_object_or_404(BulkUploadTask, id=task_id)  # или отдельная модель задач для прокси
    accounts = [
        {"account_task_id": at.id, "account": at.account.to_dict()}
        for at in task.accounts.select_related("account","proxy").all()
    ]
    return JsonResponse({"id": task.id, "accounts": accounts})

@require_GET
@csrf_exempt
def media_uniq_aggregate(request, task_id: int):
    if not _auth_ok(request):
        return _forbidden()
    task = get_object_or_404(BulkUploadTask, id=task_id)
    videos = [
        {"id": v.id, "url": None}
        for v in task.videos.order_by('order','id').all()
    ]
    return JsonResponse({"id": task.id, "videos": videos})


# ===== TikTok API Passthrough (Placeholder) =====

@require_POST
@csrf_exempt
def tiktok_booster_start_api(request):
    """TikTok Booster start endpoint - passes through to web for now"""
    if not _auth_ok(request):
        return _forbidden()
    
    # For now, just return success - TikTok functionality remains web-based
    return JsonResponse({
        "ok": True,
        "message": "TikTok functionality currently handled by web interface",
        "redirect_url": "/tiktok/booster/"
    })


@require_GET
@csrf_exempt
def tiktok_booster_status_api(request):
    """TikTok Booster status endpoint - placeholder"""
    if not _auth_ok(request):
        return _forbidden()
    
    return JsonResponse({
        "status": "WEB_HANDLED",
        "message": "TikTok functionality currently handled by web interface"
    })


# ===== Generic status endpoints for other kinds =====

_KIND_TASK_MODEL = {
    'bulk_login': BulkLoginTask,
    'warmup': WarmupTask,
    'avatar': AvatarChangeTask,
    'bio': BioLinkChangeTask,
    'follow': FollowTask,
    'proxy_diag': BulkUploadTask,
    'media_uniq': BulkUploadTask,
}

_KIND_ACCOUNT_MODEL = {
    'bulk_login': BulkLoginAccount,
    'warmup': WarmupTaskAccount,
    'avatar': AvatarChangeTaskAccount,
    'bio': BioLinkChangeTaskAccount,
    'follow': FollowTaskAccount,
    'proxy_diag': BulkUploadAccount,
}


def _get_task_model(kind: str):
    return _KIND_TASK_MODEL.get(kind)


def _get_account_model(kind: str):
    return _KIND_ACCOUNT_MODEL.get(kind)


@require_POST
@csrf_exempt
def generic_task_status(request, kind: str, task_id: int):
    if not _auth_ok(request):
        return _forbidden()
    Model = _get_task_model(kind)
    if not Model:
        return JsonResponse({"detail": "Unknown kind"}, status=400)
    task = get_object_or_404(Model, id=task_id)
    try:
        data = json.loads(request.body.decode("utf-8")) if request.body else {}
    except json.JSONDecodeError:
        data = {}
    status_val = data.get("status")
    log = data.get("log")
    log_append = data.get("log_append")
    if hasattr(task, 'status') and status_val:
        task.status = status_val
    if hasattr(task, 'log') and (log or log_append):
        if log:
            task.log = (task.log or "") + log + "\n"
        if log_append:
            task.log = (task.log or "") + log_append + "\n"
    task.save()
    # Release lock on terminal statuses
    if status_val in ("COMPLETED", "FAILED"):
        try:
            TaskLock.objects.filter(kind=kind, task_id=task_id).delete()
        except Exception:
            pass
    return JsonResponse({"ok": True, "status": getattr(task, 'status', None)})


@require_POST
@csrf_exempt
def generic_account_status(request, kind: str, account_task_id: int):
    if not _auth_ok(request):
        return _forbidden()
    Model = _get_account_model(kind)
    if not Model:
        return JsonResponse({"detail": "Unknown kind"}, status=400)
    at = get_object_or_404(Model, id=account_task_id)
    try:
        data = json.loads(request.body.decode("utf-8")) if request.body else {}
    except json.JSONDecodeError:
        data = {}
    status_val = data.get("status")
    log_append = data.get("log_append")
    if hasattr(at, 'status') and status_val:
        at.status = status_val
    if hasattr(at, 'log') and log_append:
        at.log = (at.log or "") + log_append + "\n"
    at.save()
    return JsonResponse({"ok": True, "status": getattr(at, 'status', None)})


@require_POST
@csrf_exempt
def generic_account_counters(request, kind: str, account_task_id: int):
    if not _auth_ok(request):
        return _forbidden()
    Model = _get_account_model(kind)
    if not Model:
        return JsonResponse({"detail": "Unknown kind"}, status=400)
    at = get_object_or_404(Model, id=account_task_id)
    try:
        data = json.loads(request.body.decode("utf-8")) if request.body else {}
    except json.JSONDecodeError:
        data = {}
    # Best-effort counter fields if present
    for key in ("success", "failed", "likes", "follows", "viewed"):
        if hasattr(at, key) and key in data:
            try:
                setattr(at, key, (getattr(at, key) or 0) + int(data.get(key) or 0))
            except Exception:
                pass
    at.save()
    return JsonResponse({"ok": True})


# ===== Follow Category Management APIs =====

@require_POST
@csrf_exempt
def create_follow_category_api(request):
    """API endpoint for creating follow categories"""
    if not _auth_ok(request):
        return _forbidden()
    
    try:
        data = json.loads(request.body.decode("utf-8")) if request.body else {}
    except json.JSONDecodeError:
        return JsonResponse({"detail": "Invalid JSON"}, status=400)
    
    name = data.get('name')
    if not name:
        return JsonResponse({"detail": "Category name required"}, status=400)
    
    try:
        category = FollowCategory.objects.create(
            name=name,
            description=data.get('description', '')
        )
        
        return JsonResponse({
            "ok": True,
            "category_id": category.id,
            "name": category.name
        })
        
    except Exception as e:
        return JsonResponse({"detail": f"Error creating category: {str(e)}"}, status=500)


@require_POST
@csrf_exempt
def add_follow_targets_api(request, category_id: int):
    """API endpoint for adding follow targets to category"""
    if not _auth_ok(request):
        return _forbidden()
    
    category = get_object_or_404(FollowCategory, id=category_id)
    
    try:
        data = json.loads(request.body.decode("utf-8")) if request.body else {}
    except json.JSONDecodeError:
        return JsonResponse({"detail": "Invalid JSON"}, status=400)
    
    targets = data.get('targets', [])
    if not targets:
        return JsonResponse({"detail": "No targets provided"}, status=400)
    
    created_count = 0
    skipped_count = 0
    
    for target_data in targets:
        username = target_data.get('username')
        if not username:
            continue
            
        # Skip if target exists
        if FollowTarget.objects.filter(category=category, username=username).exists():
            skipped_count += 1
            continue
        
        FollowTarget.objects.create(
            category=category,
            username=username,
            user_id=target_data.get('user_id'),
            full_name=target_data.get('full_name', ''),
            is_private=target_data.get('is_private', False),
            is_verified=target_data.get('is_verified', False)
        )
        created_count += 1
    
    return JsonResponse({
        "ok": True,
        "created_count": created_count,
        "skipped_count": skipped_count
    })


# ===== Enhanced Monitoring and Error Tracking APIs =====

@require_POST
@csrf_exempt
def report_worker_metrics_api(request):
    """API endpoint for workers to report metrics"""
    if not _auth_ok(request):
        return _forbidden()
    
    try:
        data = json.loads(request.body.decode("utf-8")) if request.body else {}
    except json.JSONDecodeError:
        return JsonResponse({"detail": "Invalid JSON"}, status=400)
    
    worker_id = data.get('worker_id')
    metrics = data.get('metrics', {})
    
    if not worker_id:
        return JsonResponse({"detail": "Worker ID required"}, status=400)
    
    # Store metrics (in production this would go to metrics database)
    # For now, just acknowledge receipt
    
    return JsonResponse({
        "ok": True,
        "message": "Metrics received",
        "worker_id": worker_id
    })


@require_POST
@csrf_exempt
def report_worker_error_api(request):
    """API endpoint for workers to report errors"""
    if not _auth_ok(request):
        return _forbidden()
    
    try:
        data = json.loads(request.body.decode("utf-8")) if request.body else {}
    except json.JSONDecodeError:
        return JsonResponse({"detail": "Invalid JSON"}, status=400)
    
    worker_id = data.get('worker_id')
    error_data = data.get('error', {})
    
    if not worker_id:
        return JsonResponse({"detail": "Worker ID required"}, status=400)
    
    # Store error data (in production this would go to error tracking system)
    # For now, just acknowledge receipt
    
    return JsonResponse({
        "ok": True,
        "message": "Error reported",
        "worker_id": worker_id,
        "error_id": f"error_{int(time.time())}"
    })


@require_GET
@csrf_exempt
def get_worker_status_api(request, worker_id: str):
    """API endpoint to get worker status"""
    if not _auth_ok(request):
        return _forbidden()
    
    # Get worker status from database
    try:
        worker = WorkerNode.objects.get(base_url__contains=worker_id)
        return JsonResponse({
            "worker_id": worker_id,
            "status": "ACTIVE" if worker.is_healthy else "INACTIVE",
            "last_heartbeat": worker.last_heartbeat.isoformat() if worker.last_heartbeat else None,
            "capacity": worker.capacity,
            "name": worker.name
        })
    except WorkerNode.DoesNotExist:
        return JsonResponse({"detail": "Worker not found"}, status=404)


@require_GET
@csrf_exempt
def get_system_health_api(request):
    """API endpoint to get overall system health"""
    if not _auth_ok(request):
        return _forbidden()
    
    # Get system health metrics
    total_workers = WorkerNode.objects.count()
    active_workers = WorkerNode.objects.filter(is_healthy=True).count()
    
    # Get task statistics
    running_tasks = 0  # Would count from TaskLock or similar
    pending_tasks = 0  # Would count from task queues
    
    return JsonResponse({
        "system_status": "HEALTHY" if active_workers > 0 else "DEGRADED",
        "workers": {
            "total": total_workers,
            "active": active_workers,
            "inactive": total_workers - active_workers
        },
        "tasks": {
            "running": running_tasks,
            "pending": pending_tasks
        },
        "timestamp": time.time()
    })


@require_POST
@csrf_exempt
def trigger_worker_restart_api(request, worker_id: str):
    """API endpoint to trigger worker restart"""
    if not _auth_ok(request):
        return _forbidden()
    
    # This would trigger a restart signal to the worker
    # Implementation depends on deployment architecture
    
    return JsonResponse({
        "ok": True,
        "message": f"Restart signal sent to worker {worker_id}",
        "worker_id": worker_id
    })


# ===== Task Lock Management APIs =====

@require_POST
@csrf_exempt
def acquire_task_lock_api(request):
    """API endpoint for workers to acquire task locks"""
    if not _auth_ok(request):
        return _forbidden()
    
    try:
        data = json.loads(request.body.decode("utf-8")) if request.body else {}
    except json.JSONDecodeError:
        return JsonResponse({"detail": "Invalid JSON"}, status=400)
    
    task_kind = data.get('task_kind')
    task_id = data.get('task_id')
    worker_id = data.get('worker_id')
    ttl_seconds = data.get('ttl_seconds', 3600)  # Default 1 hour
    
    if not all([task_kind, task_id, worker_id]):
        return JsonResponse({"detail": "Missing required fields"}, status=400)
    
    try:
        # Try to acquire lock
        lock, created = TaskLock.objects.get_or_create(
            kind=task_kind,
            task_id=task_id,
            defaults={
                'worker_id': worker_id,
                'expires_at': timezone.now() + timezone.timedelta(seconds=ttl_seconds)
            }
        )
        
        if created or lock.worker_id == worker_id:
            # Lock acquired or already owned
            return JsonResponse({
                "ok": True,
                "lock_acquired": True,
                "worker_id": worker_id,
                "expires_at": lock.expires_at.isoformat()
            })
        else:
            # Lock held by another worker
            return JsonResponse({
                "ok": True,
                "lock_acquired": False,
                "held_by": lock.worker_id,
                "expires_at": lock.expires_at.isoformat()
            })
            
    except Exception as e:
        return JsonResponse({"detail": f"Error acquiring lock: {str(e)}"}, status=500)


@require_POST
@csrf_exempt
def release_task_lock_api(request):
    """API endpoint for workers to release task locks"""
    if not _auth_ok(request):
        return _forbidden()
    
    try:
        data = json.loads(request.body.decode("utf-8")) if request.body else {}
    except json.JSONDecodeError:
        return JsonResponse({"detail": "Invalid JSON"}, status=400)
    
    task_kind = data.get('task_kind')
    task_id = data.get('task_id')
    worker_id = data.get('worker_id')
    
    if not all([task_kind, task_id, worker_id]):
        return JsonResponse({"detail": "Missing required fields"}, status=400)
    
    try:
        # Release lock if owned by this worker
        deleted_count, _ = TaskLock.objects.filter(
            kind=task_kind,
            task_id=task_id,
            worker_id=worker_id
        ).delete()
        
        return JsonResponse({
            "ok": True,
            "lock_released": deleted_count > 0,
            "worker_id": worker_id
        })
        
    except Exception as e:
        return JsonResponse({"detail": f"Error releasing lock: {str(e)}"}, status=500)


# ===== Media Uniquifier APIs =====

@require_POST
@csrf_exempt
def media_uniquify_start_api(request):
    """Start media uniquification task"""
    if not _auth_ok(request):
        return _forbidden()
    
    try:
        data = json.loads(request.body.decode("utf-8")) if request.body else {}
    except json.JSONDecodeError:
        return JsonResponse({"detail": "Invalid JSON"}, status=400)
    
    video_ids = data.get('video_ids', [])
    if not video_ids:
        return JsonResponse({"detail": "No video IDs provided"}, status=400)
    
    # Create a uniquification task
    task_id = f"uniq_{int(time.time())}"
    
    return JsonResponse({
        "ok": True,
        "task_id": task_id,
        "video_count": len(video_ids),
        "message": "Uniquification task started"
    })


@require_GET
@csrf_exempt
def media_uniquify_status_api(request, task_id: str):
    """Get media uniquification task status"""
    if not _auth_ok(request):
        return _forbidden()
    
    # Placeholder implementation
    return JsonResponse({
        "task_id": task_id,
        "status": "RUNNING",
        "progress": "Processing videos..."
    })


# ===== Cookie Robot APIs =====

@require_POST
@csrf_exempt
def cookie_robot_start_api(request):
    """Start cookie robot task"""
    if not _auth_ok(request):
        return _forbidden()
    
    try:
        data = json.loads(request.body.decode("utf-8")) if request.body else {}
    except json.JSONDecodeError:
        return JsonResponse({"detail": "Invalid JSON"}, status=400)
    
    account_id = data.get('account_id')
    urls = data.get('urls', [])
    
    if not account_id:
        return JsonResponse({"detail": "Account ID required"}, status=400)
    
    try:
        account = InstagramAccount.objects.get(id=account_id)
        
        # Create cookie robot task
        task = DolphinCookieRobotTask.objects.create(
            account=account,
            urls=urls,
            headless=data.get('headless', True),
            imageless=data.get('imageless', False)
        )
        
        return JsonResponse({
            "ok": True,
            "task_id": task.id,
            "account_username": account.username
        })
        
    except InstagramAccount.DoesNotExist:
        return JsonResponse({"detail": "Account not found"}, status=404)
    except Exception as e:
        return JsonResponse({"detail": f"Error creating task: {str(e)}"}, status=500)