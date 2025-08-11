import os
import sys
import asyncio
import signal
import threading
from dataclasses import dataclass
from typing import Optional, List, Dict, Tuple

import django
from django.utils import timezone

django.setup()

from ..models import BulkLoginTask, BulkLoginAccount, Proxy
from ..constants import TaskStatus
from ..logging_utils import set_async_logger, log_info, log_error, log_warning
from ..async_bulk_tasks import AsyncLogger
from ..account_utils import get_account_details
from ..async_impl.dolphin import AsyncDolphinBrowser, authenticate_dolphin_async
from ..async_impl.login import handle_login_flow_async
from ..utils import validate_proxy


@dataclass
class LoginAccountData:
    id: int
    username: str
    password: str
    tfa_secret: Optional[str]


class AsyncBulkLoginCoordinator:
    def __init__(self, task_id: int):
        self.task_id = task_id
        self.semaphore = asyncio.Semaphore(5)
        self.logger = AsyncLogger(task_id, cache_ns="bulk_login_logs", persist_db=False)
        set_async_logger(self.logger)

    async def run(self) -> bool:
        await self.logger.log('INFO', f"[START] Starting ASYNC bulk login task {self.task_id}")
        task = await asyncio.to_thread(BulkLoginTask.objects.get, id=self.task_id)
        accounts: List[BulkLoginAccount] = await asyncio.to_thread(lambda: list(task.accounts.select_related('account', 'proxy').all()))
        await self.logger.log('INFO', f"[SEARCH] Accounts to process: {len(accounts)}")
        if accounts:
            try:
                usernames = ", ".join([a.account.username for a in accounts][:10])
                ell = "..." if len(accounts) > 10 else ""
                await self.logger.log('INFO', f"[LIST] {usernames}{ell}")
            except Exception:
                pass
        if not accounts:
            await self.logger.log('ERROR', "No accounts assigned to this task")
            await asyncio.to_thread(self._mark_task_failed, task, "No accounts assigned to this task")
            return False

        # Pre-validate dolphin profiles
        try:
            missing = [a.account.username for a in accounts if not getattr(a.account, 'dolphin_profile_id', None)]
            if missing:
                await self.logger.log('WARNING', f"[WARN] {len(missing)} accounts have no dolphin_profile_id: {', '.join(missing[:10])}{'...' if len(missing)>10 else ''}")
                await self.logger.log('INFO', "[INFO] These accounts will be skipped. Create Dolphin profiles and rerun.")
            # Filter out missing
            accounts = [a for a in accounts if getattr(a.account, 'dolphin_profile_id', None)]
            await self.logger.log('INFO', f"[SEARCH] Accounts after validation: {len(accounts)}")
            if not accounts:
                await self.logger.log('ERROR', "All accounts missing dolphin_profile_id. Nothing to process.")
                await asyncio.to_thread(self._mark_task_failed, task, "All accounts missing dolphin_profile_id")
                return False
        except Exception as pre_err:
            await self.logger.log('WARNING', f"[WARN] Pre-validation error: {str(pre_err)}")

        # Mark task started (offloaded to thread)
        try:
            await asyncio.to_thread(self._mark_task_started, task)
        except Exception as save_err:
            await self.logger.log('WARNING', f"[WARN] Could not persist RUNNING status: {str(save_err)}")

        # Process sequentially to ensure stable logging without races
        results = []
        try:
            await self.logger.log('INFO', f"[ENTER] Starting account processing loop")
            for idx, acc in enumerate(accounts, 1):
                try:
                    await self.logger.log('INFO', f"[PROCESS] [{idx}/{len(accounts)}] {acc.account.username} starting")
                except Exception:
                    pass
                res = await self._process_account(acc)
                results.append(res)
                try:
                    await self.logger.log('INFO', f"[PROCESS] [{idx}/{len(accounts)}] {acc.account.username} finished: {'OK' if res else 'FAIL'}")
                except Exception:
                    pass
        except Exception as loop_error:
            try:
                await self.logger.log('ERROR', f"[EXPLODE] Loop error before processing accounts: {str(loop_error)}")
            except Exception:
                pass
            # Mark failure and exit
            await asyncio.to_thread(self._mark_task_failed, task, f"Loop error: {loop_error}")
            return False

        completed = sum(1 for r in results if r is True)
        failed = len(results) - completed
        final_status = TaskStatus.COMPLETED if failed == 0 else (TaskStatus.PARTIALLY_COMPLETED if completed > 0 else TaskStatus.FAILED)
        try:
            await asyncio.to_thread(self._finalize_task, task, final_status, completed, failed)
        except Exception as end_err:
            await self.logger.log('WARNING', f"[WARN] Could not persist final status: {str(end_err)}")
        await self.logger.log('SUCCESS', f"Task finished: {completed} ok / {failed} failed")
        return True

    async def _process_account(self, account_task: BulkLoginAccount) -> bool:
        account_logger = AsyncLogger(self.task_id, account_id=account_task.id, cache_ns="bulk_login_logs", persist_db=False)
        # Ensure nested modules mirror logs into this account stream
        try:
            set_async_logger(account_logger)
        except Exception:
            pass
        try:
            await account_logger.log('INFO', f"[ACCOUNT] Starting login for {account_task.account.username}")
            await asyncio.to_thread(self._update_account_status, account_task, TaskStatus.RUNNING, "Started")

            # Start Dolphin and connect to profile
            dolphin_token = os.environ.get("DOLPHIN_API_TOKEN")
            if not dolphin_token:
                await account_logger.log('ERROR', "DOLPHIN_API_TOKEN not found")
                await asyncio.to_thread(self._update_account_status, account_task, TaskStatus.FAILED, "Missing Dolphin token")
                return False

            browser = None
            try:
                # Authenticate Dolphin API
                from bot.src.instagram_uploader.dolphin_anty import DolphinAnty
                dolphin = DolphinAnty(api_key=dolphin_token, local_api_base=os.environ.get("DOLPHIN_API_HOST", "http://localhost:3001/v1.0"))
                await account_logger.log('INFO', f"[CLIPBOARD] Using Dolphin host: {os.environ.get('DOLPHIN_API_HOST', 'http://localhost:3001/v1.0')}")
                status = None
                try:
                    status = dolphin.check_dolphin_status()
                    await account_logger.log('INFO', f"[SEARCH] Dolphin status: {status}")
                except Exception as se:
                    await account_logger.log('WARNING', f"[WARN] Cannot query Dolphin status: {str(se)}")
                if not await authenticate_dolphin_async(dolphin):
                    await account_logger.log('ERROR', "Failed Dolphin authentication")
                    await asyncio.to_thread(self._update_account_status, account_task, TaskStatus.FAILED, "Dolphin auth failed")
                    return False

                # Use existing Dolphin profile id stored on account
                profile_id = account_task.account.dolphin_profile_id
                if not profile_id:
                    await account_logger.log('ERROR', "No Dolphin profile id on account")
                    await asyncio.to_thread(self._update_account_status, account_task, TaskStatus.FAILED, "No Dolphin profile")
                    return False

                # Ensure visible mode
                os.environ["VISIBLE"] = "1"
                os.environ["HEADLESS"] = "0"

                # Connect to running profile
                browser = AsyncDolphinBrowser(dolphin_token)
                page = await browser.connect_to_profile_async(profile_id, headless=False)
                if not page:
                    await account_logger.log('ERROR', "Failed to connect to Dolphin profile")
                    await asyncio.to_thread(self._update_account_status, account_task, TaskStatus.FAILED, "Profile connect failed")
                    # Fallback diagnostic: explicitly try to start profile via Dolphin and connect
                    try:
                        ok, automation = dolphin.start_profile(profile_id, headless=False)
                        await account_logger.log('INFO', f"[RETRY] Explicit start_profile: ok={ok}, automation={(automation or {}).get('port')}")
                        if ok and automation:
                            from playwright.async_api import async_playwright
                            host = '127.0.0.1'
                            ws_url = f"ws://{host}:{automation.get('port')}{automation.get('wsEndpoint')}"
                            await account_logger.log('INFO', f"[RETRY] Trying direct CDP connect: {ws_url}")
                            async with async_playwright() as p:
                                try:
                                    pw_browser = await p.chromium.connect_over_cdp(ws_url)
                                    ctx = pw_browser.contexts[0] if pw_browser.contexts else await pw_browser.new_context()
                                    page = ctx.pages[0] if ctx.pages else await ctx.new_page()
                                except Exception as cdp_err:
                                    await account_logger.log('ERROR', f"[FAIL] Direct CDP connect error: {str(cdp_err)}")
                    except Exception as sp_err:
                        await account_logger.log('ERROR', f"[FAIL] start_profile fallback error: {str(sp_err)}")
                    if not page:
                        return False

                # Pre-navigation warmup before login
                # Step 1: connectivity check (generic internet)
                try:
                    await account_logger.log('INFO', "🌐 [CHECK] Connectivity test: example.com")
                    await page.goto("https://example.com", wait_until="domcontentloaded", timeout=30000)
                except Exception as e:
                    await account_logger.log('ERROR', f"[FAIL] Connectivity to internet failed: {str(e)}")
                    # Try to validate and mark proxy inactive if it's down
                    try:
                        proxy_obj = account_task.proxy or getattr(account_task.account, 'proxy', None) or getattr(account_task.account, 'current_proxy', None)
                        if proxy_obj:
                            await account_logger.log('WARNING', f"[WARN] Validating proxy {proxy_obj.host}:{proxy_obj.port} after connectivity failure")
                            await asyncio.to_thread(self._validate_and_update_proxy_status, proxy_obj)
                    except Exception as pv_err:
                        await account_logger.log('WARNING', f"[WARN] Proxy validation/update skipped: {str(pv_err)}")
                    await asyncio.to_thread(self._update_account_status, account_task, TaskStatus.FAILED, "No internet connectivity from profile/proxy")
                    return False

                # Step 2: go directly to Instagram login page
                try:
                    await account_logger.log('INFO', "🌐 [NAV] Navigating to Instagram login page")
                    await page.goto("https://www.instagram.com/", wait_until="domcontentloaded", timeout=60000)
                    try:
                        await page.wait_for_load_state("networkidle", timeout=15000)
                    except Exception as e:
                        await account_logger.log('WARNING', f"[WARN] networkidle timeout on login page: {str(e)}")
                except Exception as e:
                    await account_logger.log('ERROR', f"[FAIL] Navigation to Instagram login failed: {str(e)}")
                    # Validate proxy as well, since Instagram may be blocked or proxy is dead
                    try:
                        proxy_obj = account_task.proxy or getattr(account_task.account, 'proxy', None) or getattr(account_task.account, 'current_proxy', None)
                        if proxy_obj:
                            await account_logger.log('WARNING', f"[WARN] Validating proxy {proxy_obj.host}:{proxy_obj.port} after Instagram navigation failure")
                            await asyncio.to_thread(self._validate_and_update_proxy_status, proxy_obj)
                    except Exception as pv_err:
                        await account_logger.log('WARNING', f"[WARN] Proxy validation/update skipped: {str(pv_err)}")
                    await asyncio.to_thread(self._update_account_status, account_task, TaskStatus.FAILED, "Cannot open Instagram login page (proxy/blocked)")
                    return False

                # Perform login
                account_details = get_account_details(account_task.account)
                login_ok = await handle_login_flow_async(page, account_details)
                if not login_ok:
                    await account_logger.log('ERROR', "Login failed")
                    await asyncio.to_thread(self._update_account_status, account_task, TaskStatus.FAILED, "Login failed")
                    return False

                await account_logger.log('SUCCESS', "Login completed and cookies saved in profile")
                await asyncio.to_thread(self._update_account_status, account_task, TaskStatus.COMPLETED, "Login OK")
                return True
            except Exception as e:
                await account_logger.log('ERROR', f"[EXPLODE] Account error: {str(e)}")
                await asyncio.to_thread(self._update_account_status, account_task, TaskStatus.FAILED, str(e))
                return False
            finally:
                if browser:
                    try:
                        await browser.cleanup_async()
                    except Exception:
                        pass
        except Exception as e:
            await account_logger.log('ERROR', f"[EXPLODE] Critical: {str(e)}")
            await asyncio.to_thread(self._update_account_status, account_task, TaskStatus.FAILED, str(e))
            return False

    def _update_account_status(self, account_task: BulkLoginAccount, status: str, message: str):
        account_task.status = status
        account_task.log = (account_task.log or "") + f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}\n"
        if status in (TaskStatus.COMPLETED, TaskStatus.FAILED, 'SUSPENDED', 'PHONE_VERIFICATION_REQUIRED', 'HUMAN_VERIFICATION_REQUIRED'):
            account_task.completed_at = timezone.now()
        if status == TaskStatus.RUNNING:
            account_task.started_at = timezone.now()
        account_task.save(update_fields=['status','log','started_at','completed_at'])

    # Validate proxy and persist status based on result
    def _validate_and_update_proxy_status(self, proxy: Proxy) -> None:
        try:
            ok, message, geo = validate_proxy(
                host=proxy.host,
                port=proxy.port,
                username=proxy.username,
                password=proxy.password,
                timeout=10,
                proxy_type=proxy.proxy_type
            )
            proxy.last_checked = timezone.now()
            proxy.last_verified = timezone.now()
            if ok:
                proxy.status = 'active'
                proxy.is_active = True
                # optionally update geo
                if geo:
                    if geo.get('country'): proxy.country = geo.get('country')
                    if geo.get('city'): proxy.city = geo.get('city')
            else:
                proxy.status = 'inactive'
                proxy.is_active = False
                # append note
                try:
                    proxy.notes = (proxy.notes or "") + f"\n[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] Auto-marked inactive by Bulk Login: {message}"
                except Exception:
                    pass
            proxy.save(update_fields=['status','is_active','last_checked','last_verified','country','city','notes'])
        except Exception:
            # Do not raise from validation path
            pass

    # New helpers to safely persist task status/log from async context
    def _mark_task_started(self, task: BulkLoginTask):
        task.status = TaskStatus.RUNNING
        task.log += f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] Task started via Web (ASYNC mode)\n"
        task.save(update_fields=['status','log'])

    def _mark_task_failed(self, task: BulkLoginTask, reason: str):
        task.status = TaskStatus.FAILED
        task.log += f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] {reason}\n"
        task.save(update_fields=['status','log'])

    def _finalize_task(self, task: BulkLoginTask, final_status: str, completed: int, failed: int):
        task.status = final_status
        task.log += f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] Finished: {completed} ok / {failed} failed\n"
        task.save(update_fields=['status','log'])


async def run_async_bulk_login_task(task_id: int) -> bool:
    coordinator = AsyncBulkLoginCoordinator(task_id)
    return await coordinator.run()


def run_async_bulk_login_task_sync(task_id: int) -> bool:
    current_task = None
    def signal_handler(signum, frame):
        sys.exit(1)
    if threading.current_thread() is threading.main_thread():
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
    try:
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        result = new_loop.run_until_complete(run_async_bulk_login_task(task_id))
        new_loop.close()
        return bool(result)
    except Exception:
        return False 