from __future__ import annotations
import asyncio
import json
import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from .config import settings
from .domain import BulkVideo, BulkUploadAccountTask
from .ui_client import UiClient


@dataclass
class AccountRunResult:
    success_count: int
    failed_count: int
    stdout: str
    stderr: str


def _repo_root() -> Path:
    current = Path(__file__).resolve()
    # modules/bulk_worker_service/bulk_worker_service -> go up 3 to repo root
    return current.parents[3]


def _bot_script_path() -> str:
    return str(_repo_root() / "bot" / "run_bot_playwright.py")


async def _run_subprocess(cmd: List[str], env: Optional[dict] = None) -> tuple[int, str, str]:
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env or os.environ.copy(),
    )
    stdout_bytes, stderr_bytes = await process.communicate()
    return process.returncode, stdout_bytes.decode(errors="ignore"), stderr_bytes.decode(errors="ignore")


async def run_account_upload(ui: UiClient, task_id: int, account_task: BulkUploadAccountTask, videos: List[BulkVideo], headless: bool, visible: bool) -> AccountRunResult:
    await ui.update_account_status(account_task.account_task_id, "RUNNING", log_append=f"Starting account {account_task.account.username}\n")

    success = 0
    failed = 0
    full_stdout = ""
    full_stderr = ""

    env = os.environ.copy()
    if settings.dolphin_api_token:
        env["DOLPHIN_API_TOKEN"] = settings.dolphin_api_token
    if settings.dolphin_api_host:
        env["DOLPHIN_API_HOST"] = settings.dolphin_api_host

    # Process each video individually to get precise counters
    for video in sorted(videos, key=lambda v: v.order):
        try:
            tmp_paths: List[str] = []
            # Download video to temp path via UI API
            tmp_video_path = await ui.download_video_to_temp(video.id)
            tmp_paths.append(tmp_video_path)

            # Build account JSON
            account_payload = account_task.account.model_dump(by_alias=True)
            # Convert proxy pass_ back to pass key name
            if account_payload.get("proxy") and "pass_" in account_payload["proxy"]:
                account_payload["proxy"]["pass"] = account_payload["proxy"].pop("pass_")

            # Inject title/location/mentions into a per-video options file if needed by bot
            # Current bot expects only paths; description is handled inside selenium-like pipeline.

            with tempfile.NamedTemporaryFile(delete=False, mode="w", suffix="_account.json") as f_acc:
                json.dump(account_payload, f_acc)
                account_json_path = f_acc.name

            with tempfile.NamedTemporaryFile(delete=False, mode="w", suffix="_videos.json") as f_vid:
                json.dump([tmp_video_path], f_vid)
                videos_json_path = f_vid.name

            cmd = [
                sys.executable,
                _bot_script_path(),
                "--account", account_json_path,
                "--videos", videos_json_path,
                "--non-interactive",
            ]
            if visible:
                cmd.append("--visible")

            rc, out, err = await _run_subprocess(cmd, env=env)
            full_stdout += out + "\n"
            full_stderr += err + "\n"

            # Cleanup temp files
            for p in [*tmp_paths, account_json_path, videos_json_path]:
                try:
                    os.unlink(p)
                except Exception:
                    pass

            if rc == 0:
                success += 1
                await ui.increment_counters(account_task.account_task_id, success=1, failed=0)
                await ui.update_account_status(account_task.account_task_id, "RUNNING", log_append=f"Video {video.id} uploaded successfully\n")
            else:
                failed += 1
                await ui.increment_counters(account_task.account_task_id, success=0, failed=1)
                await ui.update_account_status(account_task.account_task_id, "RUNNING", log_append=f"Video {video.id} failed to upload\n")

        except Exception as e:
            failed += 1
            await ui.increment_counters(account_task.account_task_id, success=0, failed=1)
            await ui.update_account_status(account_task.account_task_id, "RUNNING", log_append=f"Exception: {e}\n")

    final_status = "COMPLETED" if failed == 0 and success > 0 else ("FAILED" if success == 0 else "COMPLETED")
    await ui.update_account_status(account_task.account_task_id, final_status)

    return AccountRunResult(success_count=success, failed_count=failed, stdout=full_stdout, stderr=full_stderr) 