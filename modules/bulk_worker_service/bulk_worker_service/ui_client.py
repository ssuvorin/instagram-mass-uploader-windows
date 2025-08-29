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

    # ===== Extended Media Operations =====

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10), reraise=True)
    async def get_video_download_url(self, video_id: int) -> str:
        """Get download URL for a video"""
        return f"/api/media/{video_id}/download"

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10), reraise=True)
    async def download_avatar_image(self, image_id: int, dest_dir: Optional[str] = None) -> str:
        """Download avatar image for processing"""
        dest_dir = dest_dir or settings.media_temp_dir
        os.makedirs(dest_dir, exist_ok=True)
        tmp_file = tempfile.NamedTemporaryFile(delete=False, dir=dest_dir, suffix=f"_avatar_{image_id}.jpg")
        tmp_file_path = tmp_file.name
        tmp_file.close()

        async with self._client.stream("GET", f"/api/media/images/{image_id}/download") as resp:
            resp.raise_for_status()
            async for chunk in resp.aiter_bytes():
                if chunk:
                    with open(tmp_file_path, "ab") as out:
                        out.write(chunk)

        return tmp_file_path

    # ===== Account Management APIs =====

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=5), reraise=True)
    async def create_account(self, account_data: dict) -> dict:
        """Create new Instagram account"""
        resp = await self._client.post("/api/accounts/create/", json=account_data)
        resp.raise_for_status()
        return resp.json()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=5), reraise=True)
    async def import_accounts(self, accounts_data: list) -> dict:
        """Import multiple accounts"""
        payload = {"accounts": accounts_data}
        resp = await self._client.post("/api/accounts/import/", json=payload)
        resp.raise_for_status()
        return resp.json()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=5), reraise=True)
    async def edit_account(self, account_id: int, account_data: dict) -> dict:
        """Edit account details"""
        resp = await self._client.post(f"/api/accounts/{account_id}/edit/", json=account_data)
        resp.raise_for_status()
        return resp.json()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=5), reraise=True)
    async def bulk_change_proxy(self, account_ids: list, proxy_id: Optional[int]) -> dict:
        """Bulk change proxy for accounts"""
        payload = {"account_ids": account_ids, "proxy_id": proxy_id}
        resp = await self._client.post("/api/accounts/bulk-change-proxy/", json=payload)
        resp.raise_for_status()
        return resp.json()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=5), reraise=True)
    async def create_dolphin_profile(self, account_id: int, profile_data: Optional[dict] = None) -> dict:
        """Create Dolphin profile for account"""
        payload = profile_data or {}
        resp = await self._client.post(f"/api/accounts/{account_id}/create-dolphin-profile/", json=payload)
        resp.raise_for_status()
        return resp.json()

    # ===== Proxy Management APIs =====

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=5), reraise=True)
    async def create_proxy(self, proxy_data: dict) -> dict:
        """Create new proxy"""
        resp = await self._client.post("/api/proxies/create/", json=proxy_data)
        resp.raise_for_status()
        return resp.json()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=5), reraise=True)
    async def import_proxies(self, proxies_data: list) -> dict:
        """Import multiple proxies"""
        payload = {"proxies": proxies_data}
        resp = await self._client.post("/api/proxies/import/", json=payload)
        resp.raise_for_status()
        return resp.json()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=5), reraise=True)
    async def validate_all_proxies(self) -> dict:
        """Validate all proxies"""
        resp = await self._client.post("/api/proxies/validate-all/")
        resp.raise_for_status()
        return resp.json()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=5), reraise=True)
    async def cleanup_inactive_proxies(self) -> dict:
        """Cleanup inactive proxies"""
        resp = await self._client.post("/api/proxies/cleanup-inactive/")
        resp.raise_for_status()
        return resp.json()

    # ===== Media Processing APIs =====

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=5), reraise=True)
    async def start_media_uniquification(self, video_ids: list) -> dict:
        """Start media uniquification task"""
        payload = {"video_ids": video_ids}
        resp = await self._client.post("/api/media/uniquify/", json=payload)
        resp.raise_for_status()
        return resp.json()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=5), reraise=True)
    async def get_media_uniquification_status(self, task_id: str) -> dict:
        """Get media uniquification status"""
        resp = await self._client.get(f"/api/media/uniquify/{task_id}/status/")
        resp.raise_for_status()
        return resp.json()

    # ===== Cookie Robot APIs =====

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=5), reraise=True)
    async def start_cookie_robot(self, account_id: int, urls: list, **options) -> dict:
        """Start cookie robot task"""
        payload = {
            "account_id": account_id,
            "urls": urls,
            **options
        }
        resp = await self._client.post("/api/cookie-robot/start/", json=payload)
        resp.raise_for_status()
        return resp.json()

    # ===== Follow Category APIs =====

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=5), reraise=True)
    async def create_follow_category(self, name: str, description: str = "") -> dict:
        """Create follow category"""
        payload = {"name": name, "description": description}
        resp = await self._client.post("/api/follow/categories/create/", json=payload)
        resp.raise_for_status()
        return resp.json()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=5), reraise=True)
    async def add_follow_targets(self, category_id: int, targets: list) -> dict:
        """Add follow targets to category"""
        payload = {"targets": targets}
        resp = await self._client.post(f"/api/follow/categories/{category_id}/targets/", json=payload)
        resp.raise_for_status()
        return resp.json()

    # ===== Worker Registration & Health =====

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=5), reraise=True)
    async def register_worker(self, worker_data: dict) -> dict:
        """Register worker with UI service"""
        resp = await self._client.post("/api/worker/register", json=worker_data)
        resp.raise_for_status()
        return resp.json()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=5), reraise=True)
    async def send_heartbeat(self, worker_data: dict) -> dict:
        """Send worker heartbeat"""
        resp = await self._client.post("/api/worker/heartbeat", json=worker_data)
        resp.raise_for_status()
        return resp.json()

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