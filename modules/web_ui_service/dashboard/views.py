from __future__ import annotations
import os
import requests
import itertools
import concurrent.futures
from django.conf import settings
from django.shortcuts import redirect


def _worker_headers():
    headers = {"Accept": "application/json"}
    token = os.getenv('WORKER_UI_TOKEN') or settings.WORKER_API_TOKEN
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _worker_url(base: str, path: str) -> str:
    return f"{base.rstrip('/')}{path}"


def _pick_workers() -> list[str]:
    pool = getattr(settings, 'WORKER_POOL', [])
    base = getattr(settings, 'WORKER_BASE_URL', '')
    return pool if pool else ([base] if base else [])


def _dispatch_batches(start_endpoint: str, task_id: int):
    workers = _pick_workers()
    if not workers:
        return
    batch_size = getattr(settings, 'DISPATCH_BATCH_SIZE', 5)
    concurrency = getattr(settings, 'DISPATCH_CONCURRENCY', 2)
    # Разбиваем условно на батчи, передавая параметр batch_index/batch_count
    # UI сам не делит аккаунты; воркер при расширении API сможет принять subset.
    batch_count = max(1, len(workers))
    indices = list(range(batch_count))
    rr = itertools.cycle(workers)
    payloads = []
    for idx in indices:
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


def start_bulk_upload_via_worker(request, task_id: int):
    workers = _pick_workers()
    if workers and len(workers) > 1:
        _dispatch_batches('/api/v1/bulk-tasks/start', task_id)
    else:
        base = workers[0] if workers else settings.WORKER_BASE_URL
        requests.post(_worker_url(base, '/api/v1/bulk-tasks/start'), json={"mode":"pull","task_id": task_id}, headers=_worker_headers(), timeout=30)
    return redirect('bulk_upload_detail', task_id=task_id)


def start_bulk_login_via_worker(request, task_id: int):
    workers = _pick_workers()
    if workers and len(workers) > 1:
        _dispatch_batches('/api/v1/bulk-login/start', task_id)
    else:
        base = workers[0] if workers else settings.WORKER_BASE_URL
        requests.post(_worker_url(base, '/api/v1/bulk-login/start'), params={"task_id": task_id}, headers=_worker_headers(), timeout=30)
    return redirect('bulk_login_detail', task_id=task_id)


def start_warmup_via_worker(request, task_id: int):
    workers = _pick_workers()
    if workers and len(workers) > 1:
        _dispatch_batches('/api/v1/warmup/start', task_id)
    else:
        base = workers[0] if workers else settings.WORKER_BASE_URL
        requests.post(_worker_url(base, '/api/v1/warmup/start'), params={"task_id": task_id}, headers=_worker_headers(), timeout=30)
    return redirect('warmup_task_detail', task_id=task_id)


def start_avatar_via_worker(request, task_id: int):
    workers = _pick_workers()
    if workers and len(workers) > 1:
        _dispatch_batches('/api/v1/avatar/start', task_id)
    else:
        base = workers[0] if workers else settings.WORKER_BASE_URL
        requests.post(_worker_url(base, '/api/v1/avatar/start'), params={"task_id": task_id}, headers=_worker_headers(), timeout=30)
    return redirect('avatar_task_detail', task_id=task_id)


def start_bio_via_worker(request, task_id: int):
    workers = _pick_workers()
    if workers and len(workers) > 1:
        _dispatch_batches('/api/v1/bio/start', task_id)
    else:
        base = workers[0] if workers else settings.WORKER_BASE_URL
        requests.post(_worker_url(base, '/api/v1/bio/start'), params={"task_id": task_id}, headers=_worker_headers(), timeout=30)
    return redirect('bio_task_detail', task_id=task_id)


def start_follow_via_worker(request, task_id: int):
    workers = _pick_workers()
    if workers and len(workers) > 1:
        _dispatch_batches('/api/v1/follow/start', task_id)
    else:
        base = workers[0] if workers else settings.WORKER_BASE_URL
        requests.post(_worker_url(base, '/api/v1/follow/start'), params={"task_id": task_id}, headers=_worker_headers(), timeout=30)
    return redirect('follow_task_detail', task_id=task_id) 