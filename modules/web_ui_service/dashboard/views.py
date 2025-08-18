from __future__ import annotations
import os
import requests
import itertools
import concurrent.futures
from django.conf import settings
from django.shortcuts import redirect, render
from django.db import transaction
from .models import WorkerNode, TaskLock


def _worker_headers():
    headers = {"Accept": "application/json"}
    token = os.getenv('WORKER_UI_TOKEN') or settings.WORKER_API_TOKEN
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _worker_url(base: str, path: str) -> str:
    return f"{base.rstrip('/')}" + path


def _pick_workers() -> list[str]:
    # Prefer registered active workers if exist; fallback to env pool/base
    try:
        nodes = list(WorkerNode.objects.filter(is_active=True).order_by('-capacity', 'id'))
        if nodes:
            return [n.base_url for n in nodes]
    except Exception:
        pass
    pool = getattr(settings, 'WORKER_POOL', [])
    base = getattr(settings, 'WORKER_BASE_URL', '')
    return pool if pool else ([base] if base else [])


def _dispatch_batches(start_endpoint: str, task_id: int):
    # Build weighted worker list from registry or env
    try:
        nodes = list(WorkerNode.objects.filter(is_active=True).order_by('-capacity', 'id'))
        worker_specs = [(n.base_url, max(1, int(n.capacity))) for n in nodes]
    except Exception:
        worker_specs = []
    if not worker_specs:
        workers = _pick_workers()
        worker_specs = [(w, 1) for w in workers]
    if not worker_specs:
        return
    batch_size = getattr(settings, 'DISPATCH_BATCH_SIZE', 5)
    concurrency = getattr(settings, 'DISPATCH_CONCURRENCY', 2)
    total_capacity = sum(cap for _, cap in worker_specs)
    batch_count = max(1, total_capacity)
    # Weighted round-robin assignment of batch indices to workers
    expanded = []
    for base, cap in worker_specs:
        expanded.extend([base] * cap)
    rr = itertools.cycle(expanded)
    payloads = []
    for idx in range(batch_count):
        base = next(rr)
        if start_endpoint.endswith('/bulk-tasks/start'):
            payload = {"mode": "pull", "task_id": task_id, "options": {}}
            method = 'json'
        else:
            payload = {"task_id": task_id}
            method = 'params'
        payloads.append((base, payload, method, idx, batch_count))

    def _send(item):
        base, payload, method, idx, cnt = item
        url = _worker_url(base, start_endpoint)
        headers = _worker_headers()
        if method == 'json':
            payload['options']['batch_index'] = idx
            payload['options']['batch_count'] = cnt
            return requests.post(url, json=payload, headers=headers, timeout=30)
        else:
            payload['batch_index'] = idx
            payload['batch_count'] = cnt
            return requests.post(url, params=payload, headers=headers, timeout=30)

    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as ex:
        list(ex.map(_send, payloads))


def _acquire_lock(kind: str, task_id: int) -> bool:
    try:
        with transaction.atomic():
            TaskLock.objects.create(kind=kind, task_id=task_id)
            return True
    except Exception:
        return False


def start_bulk_upload_via_worker(request, task_id: int):
    if not _acquire_lock('bulk', task_id):
        return redirect('bulk_upload_detail', task_id=task_id)
    workers = _pick_workers()
    if workers and len(workers) > 1:
        _dispatch_batches('/api/v1/bulk-tasks/start', task_id)
    else:
        base = workers[0] if workers else settings.WORKER_BASE_URL
        requests.post(_worker_url(base, '/api/v1/bulk-tasks/start'), json={"mode":"pull","task_id": task_id}, headers=_worker_headers(), timeout=30)
    return redirect('bulk_upload_detail', task_id=task_id)


def start_bulk_login_via_worker(request, task_id: int):
    if not _acquire_lock('bulk_login', task_id):
        return redirect('bulk_login_detail', task_id=task_id)
    workers = _pick_workers()
    if workers and len(workers) > 1:
        _dispatch_batches('/api/v1/bulk-login/start', task_id)
    else:
        base = workers[0] if workers else settings.WORKER_BASE_URL
        requests.post(_worker_url(base, '/api/v1/bulk-login/start'), params={"task_id": task_id}, headers=_worker_headers(), timeout=30)
    return redirect('bulk_login_detail', task_id=task_id)


def start_warmup_via_worker(request, task_id: int):
    if not _acquire_lock('warmup', task_id):
        return redirect('warmup_task_detail', task_id=task_id)
    workers = _pick_workers()
    if workers and len(workers) > 1:
        _dispatch_batches('/api/v1/warmup/start', task_id)
    else:
        base = workers[0] if workers else settings.WORKER_BASE_URL
        requests.post(_worker_url(base, '/api/v1/warmup/start'), params={"task_id": task_id}, headers=_worker_headers(), timeout=30)
    return redirect('warmup_task_detail', task_id=task_id)


def start_avatar_via_worker(request, task_id: int):
    if not _acquire_lock('avatar', task_id):
        return redirect('avatar_task_detail', task_id=task_id)
    workers = _pick_workers()
    if workers and len(workers) > 1:
        _dispatch_batches('/api/v1/avatar/start', task_id)
    else:
        base = workers[0] if workers else settings.WORKER_BASE_URL
        requests.post(_worker_url(base, '/api/v1/avatar/start'), params={"task_id": task_id}, headers=_worker_headers(), timeout=30)
    return redirect('avatar_task_detail', task_id=task_id)


def start_bio_via_worker(request, task_id: int):
    if not _acquire_lock('bio', task_id):
        return redirect('bio_task_detail', task_id=task_id)
    workers = _pick_workers()
    if workers and len(workers) > 1:
        _dispatch_batches('/api/v1/bio/start', task_id)
    else:
        base = workers[0] if workers else settings.WORKER_BASE_URL
        requests.post(_worker_url(base, '/api/v1/bio/start'), params={"task_id": task_id}, headers=_worker_headers(), timeout=30)
    return redirect('bio_task_detail', task_id=task_id)


def start_follow_via_worker(request, task_id: int):
    if not _acquire_lock('follow', task_id):
        return redirect('follow_task_detail', task_id=task_id)
    workers = _pick_workers()
    if workers and len(workers) > 1:
        _dispatch_batches('/api/v1/follow/start', task_id)
    else:
        base = workers[0] if workers else settings.WORKER_BASE_URL
        requests.post(_worker_url(base, '/api/v1/follow/start'), params={"task_id": task_id}, headers=_worker_headers(), timeout=30)
    return redirect('follow_task_detail', task_id=task_id)


def start_proxy_diag_via_worker(request, task_id: int):
    if not _acquire_lock('proxy_diag', task_id):
        return redirect('bulk_upload_detail', task_id=task_id)
    workers = _pick_workers()
    if workers and len(workers) > 1:
        _dispatch_batches('/api/v1/proxy-diagnostics/start', task_id)
    else:
        base = workers[0] if workers else settings.WORKER_BASE_URL
        requests.post(_worker_url(base, '/api/v1/proxy-diagnostics/start'), params={"task_id": task_id}, headers=_worker_headers(), timeout=30)
    return redirect('bulk_upload_detail', task_id=task_id)


def start_media_uniq_via_worker(request, task_id: int):
    if not _acquire_lock('media_uniq', task_id):
        return redirect('bulk_upload_detail', task_id=task_id)
    workers = _pick_workers()
def workers_list(request):
    nodes = WorkerNode.objects.all().order_by('-is_active', '-capacity', 'name')
    return render(request, 'dashboard/workers.html', {'nodes': nodes})


def health_poll(request):
    nodes = WorkerNode.objects.all()
    for n in nodes:
        try:
            url = _worker_url(n.base_url, '/api/v1/health')
            headers = _worker_headers()
            resp = requests.get(url, headers=headers, timeout=5)
            ok = (resp.status_code == 200 and resp.json().get('ok') is True)
            n.mark_heartbeat(ok=ok, error=None if ok else f"HTTP {resp.status_code}")
        except Exception as e:
            n.mark_heartbeat(ok=False, error=str(e))
    return redirect('workers_list')
    if workers and len(workers) > 1:
        _dispatch_batches('/api/v1/media-uniq/start', task_id)
    else:
        base = workers[0] if workers else settings.WORKER_BASE_URL
        requests.post(_worker_url(base, '/api/v1/media-uniq/start'), params={"task_id": task_id}, headers=_worker_headers(), timeout=30)
    return redirect('bulk_upload_detail', task_id=task_id) 