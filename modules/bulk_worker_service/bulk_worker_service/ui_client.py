from __future__ import annotations
import os
import tempfile
from pathlib import Path
from typing import Optional
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from .config import settings
from .domain import BulkTaskAggregate


class UiClient:
    def __init__(self, base_url: Optional[str] = None, token: Optional[str] = None, verify_ssl: Optional[bool] = None, timeout: Optional[float] = None):
        self.base_url = base_url or settings.ui_api_base or ""
        self.token = token or settings.ui_api_token or ""
        self.verify_ssl = settings.verify_ssl if verify_ssl is None else verify_ssl
        self.timeout = settings.request_timeout_secs if timeout is None else timeout
        self._client = httpx.AsyncClient(base_url=self.base_url, headers=self._headers(), timeout=self.timeout, verify=self.verify_ssl)

    def _headers(self) -> dict:
        headers = {"Accept": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    async def aclose(self) -> None:
        await self._client.aclose()

    # ===== Bulk Upload (existing) =====

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=5), reraise=True)
    async def get_bulk_task_aggregate(self, task_id: int) -> BulkTaskAggregate:
        resp = await self._client.get(f"/api/bulk-tasks/{task_id}/aggregate")
        resp.raise_for_status()
        data = resp.json()
        return BulkTaskAggregate.model_validate(data)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=5), reraise=True)
    async def update_task_status(self, task_id: int, status: str, log: Optional[str] = None) -> None:
        payload = {"status": status}
        if log:
            payload["log"] = log
        resp = await self._client.post(f"/api/bulk-tasks/{task_id}/status", json=payload)
        if resp.status_code not in (200, 201, 202, 204):
            resp.raise_for_status()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=5), reraise=True)
    async def update_account_status(self, account_task_id: int, status: str, log_append: Optional[str] = None) -> None:
        payload = {"status": status}
        if log_append:
            payload["log_append"] = log_append
        resp = await self._client.post(f"/api/bulk-accounts/{account_task_id}/status", json=payload)
        if resp.status_code not in (200, 201, 202, 204):
            resp.raise_for_status()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=5), reraise=True)
    async def increment_counters(self, account_task_id: int, success: int = 0, failed: int = 0) -> None:
        payload = {"success": success, "failed": failed}
        resp = await self._client.post(f"/api/bulk-accounts/{account_task_id}/counters", json=payload)
        if resp.status_code not in (200, 201, 202, 204):
            resp.raise_for_status()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=5), reraise=True)
    async def append_task_log(self, task_id: int, text: str) -> None:
        payload = {"log_append": text}
        resp = await self._client.post(f"/api/bulk-tasks/{task_id}/status", json=payload)
        if resp.status_code not in (200, 201, 202, 204):
            resp.raise_for_status()

    # ===== Generic helpers for other kinds =====

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=5), reraise=True)
    async def get_aggregate(self, kind: str, task_id: int) -> dict:
        resp = await self._client.get(f"/api/{kind}/{task_id}/aggregate")
        resp.raise_for_status()
        return resp.json()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=5), reraise=True)
    async def update_task_status_generic(self, kind: str, task_id: int, status: Optional[str] = None, log: Optional[str] = None, log_append: Optional[str] = None) -> None:
        payload = {}
        if status is not None:
            payload["status"] = status
        if log is not None:
            payload["log"] = log
        if log_append is not None:
            payload["log_append"] = log_append
        resp = await self._client.post(f"/api/{kind}/{task_id}/status", json=payload)
        if resp.status_code not in (200, 201, 202, 204):
            resp.raise_for_status()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=5), reraise=True)
    async def update_account_status_generic(self, kind: str, account_task_id: int, status: Optional[str] = None, log_append: Optional[str] = None) -> None:
        payload = {}
        if status is not None:
            payload["status"] = status
        if log_append is not None:
            payload["log_append"] = log_append
        resp = await self._client.post(f"/api/{kind}/accounts/{account_task_id}/status", json=payload)
        if resp.status_code not in (200, 201, 202, 204):
            resp.raise_for_status()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=5), reraise=True)
    async def increment_counters_generic(self, kind: str, account_task_id: int, **counters) -> None:
        resp = await self._client.post(f"/api/{kind}/accounts/{account_task_id}/counters", json=counters)
        if resp.status_code not in (200, 201, 202, 204):
            resp.raise_for_status()

    # ===== Downloads =====

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10), reraise=True)
    async def download_video_to_temp(self, video_id: int, url: Optional[str] = None, dest_dir: Optional[str] = None) -> str:
        dest_dir = dest_dir or settings.media_temp_dir
        os.makedirs(dest_dir, exist_ok=True)
        tmp_file = tempfile.NamedTemporaryFile(delete=False, dir=dest_dir, suffix=f"_video_{video_id}.mp4")
        tmp_file_path = tmp_file.name
        tmp_file.close()

        request_url = url if url else f"/api/media/{video_id}/download"
        async with self._client.stream("GET", request_url) as resp:
            resp.raise_for_status()
            async for chunk in resp.aiter_bytes():
                if chunk:
                    with open(tmp_file_path, "ab") as out:
                        out.write(chunk)

        return tmp_file_path

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10), reraise=True)
    async def download_image_to_temp(self, image_id: int, url: Optional[str] = None, dest_dir: Optional[str] = None) -> str:
        dest_dir = dest_dir or settings.media_temp_dir
        os.makedirs(dest_dir, exist_ok=True)
        tmp_file = tempfile.NamedTemporaryFile(delete=False, dir=dest_dir, suffix=f"_image_{image_id}.jpg")
        tmp_file_path = tmp_file.name
        tmp_file.close()

        request_url = url if url else f"/api/media/{image_id}/download"
        async with self._client.stream("GET", request_url) as resp:
            resp.raise_for_status()
            async for chunk in resp.aiter_bytes():
                if chunk:
                    with open(tmp_file_path, "ab") as out:
                        out.write(chunk)

        return tmp_file_path 