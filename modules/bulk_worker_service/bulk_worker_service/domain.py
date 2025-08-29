from __future__ import annotations
from typing import Optional, List, Literal
from pydantic import BaseModel, Field, HttpUrl


class ProxyData(BaseModel):
    type: Literal["http", "https", "socks5"] = Field(default="http")
    host: str
    port: int
    user: Optional[str] = None
    pass_: Optional[str] = Field(default=None, alias="pass")

    class Config:
        populate_by_name = True


class AccountDetails(BaseModel):
    username: str
    password: str
    tfa_secret: Optional[str] = None
    email_username: Optional[str] = None
    email_password: Optional[str] = None
    dolphin_profile_id: Optional[str] = None
    phone: Optional[str] = None
    proxy: Optional[ProxyData] = None


class BulkUploadAccountTask(BaseModel):
    account_task_id: int
    account: AccountDetails


class BulkVideo(BaseModel):
    id: int
    order: int = 0
    title: Optional[str] = None
    location: Optional[str] = None
    mentions: Optional[str] = None
    url: Optional[HttpUrl] = None


class BulkTaskAggregate(BaseModel):
    id: int
    default_location: Optional[str] = None
    default_mentions: Optional[str] = None
    accounts: List[BulkUploadAccountTask]
    videos: List[BulkVideo]


class StartOptions(BaseModel):
    concurrency: Optional[int] = None
    headless: Optional[bool] = None
    visible: Optional[bool] = None
    batch_index: Optional[int] = None
    batch_count: Optional[int] = None
    upload_method: Optional[Literal["playwright", "instagrapi"]] = None


class StartRequest(BaseModel):
    mode: Literal["pull", "push"] = "pull"
    task_id: Optional[int] = None
    aggregate: Optional[BulkTaskAggregate] = None
    options: Optional[StartOptions] = None


class StartResponse(BaseModel):
    job_id: str
    accepted: bool


class JobStatus(BaseModel):
    job_id: str
    task_id: Optional[int] = None
    status: Literal["PENDING", "RUNNING", "COMPLETED", "FAILED"]
    successful_accounts: int = 0
    failed_accounts: int = 0
    total_uploaded: int = 0
    total_failed_uploads: int = 0
    message: Optional[str] = None


# ===== Additional Aggregates =====

class BulkLoginAccountTask(BaseModel):
    account_task_id: int
    account: AccountDetails


class BulkLoginAggregate(BaseModel):
    id: int
    accounts: List[BulkLoginAccountTask]


class WarmupActions(BaseModel):
    feed_scroll_min_count: int = 1
    feed_scroll_max_count: int = 3
    like_min_count: int = 0
    like_max_count: int = 3
    view_stories_min_count: int = 0
    view_stories_max_count: int = 5
    follow_min_count: int = 0
    follow_max_count: int = 2


class WarmupAccountTask(BaseModel):
    account_task_id: int
    account: AccountDetails


class WarmupAggregate(BaseModel):
    id: int
    actions: WarmupActions
    accounts: List[WarmupAccountTask]


class ImageItem(BaseModel):
    id: int
    order: int = 0
    url: Optional[HttpUrl] = None


class AvatarAccountTask(BaseModel):
    account_task_id: int
    account: AccountDetails


class AvatarStrategy(str):
    pass


class AvatarAggregate(BaseModel):
    id: int
    strategy: Literal["random_reuse", "one_to_one"] = "random_reuse"
    accounts: List[AvatarAccountTask]
    images: List[ImageItem]


class BioAccountTask(BaseModel):
    account_task_id: int
    account: AccountDetails


class BioAggregate(BaseModel):
    id: int
    link_url: HttpUrl
    accounts: List[BioAccountTask]


class FollowTarget(BaseModel):
    username: str


class FollowAccountTask(BaseModel):
    account_task_id: int
    account: AccountDetails


class FollowOptions(BaseModel):
    follow_min_count: int = 3
    follow_max_count: int = 10


class FollowAggregate(BaseModel):
    id: int
    accounts: List[FollowAccountTask]
    targets: List[FollowTarget]
    options: FollowOptions


class ProxyDiagnosticsAccountTask(BaseModel):
    account_task_id: int
    account: AccountDetails


class ProxyDiagnosticsAggregate(BaseModel):
    id: int
    accounts: List[ProxyDiagnosticsAccountTask]


class MediaUniqVideo(BaseModel):
    id: int
    url: Optional[HttpUrl] = None


class MediaUniqAggregate(BaseModel):
    id: int
    videos: List[MediaUniqVideo]


class CookieRobotAccountTask(BaseModel):
    account_task_id: int
    account: AccountDetails


class CookieRobotUrls(BaseModel):
    urls: List[str]
    headless: bool = True
    imageless: bool = False


class CookieRobotAggregate(BaseModel):
    id: int
    accounts: List[CookieRobotAccountTask]
    config: CookieRobotUrls


# ===== Account Management Domain Models =====

class AccountCreationRequest(BaseModel):
    username: str
    password: str
    email_username: Optional[str] = None
    email_password: Optional[str] = None
    tfa_secret: Optional[str] = None
    phone_number: Optional[str] = None
    proxy_id: Optional[int] = None
    notes: Optional[str] = None


class AccountImportRequest(BaseModel):
    accounts: List[AccountCreationRequest]


class BulkProxyChangeRequest(BaseModel):
    account_ids: List[int]
    proxy_id: Optional[int] = None


class DolphinProfileCreationRequest(BaseModel):
    account_id: int
    profile_config: Optional[dict] = None


# ===== Proxy Management Domain Models =====

class ProxyCreationRequest(BaseModel):
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    proxy_type: Literal["HTTP", "HTTPS", "SOCKS5"] = "HTTP"
    country: Optional[str] = None
    city: Optional[str] = None
    notes: Optional[str] = None


class ProxyImportRequest(BaseModel):
    proxies: List[ProxyCreationRequest]


# ===== TikTok Domain Models (Placeholder) =====

class TikTokBoosterRequest(BaseModel):
    account_ids: List[int]
    boost_config: Optional[dict] = None


class TikTokBoosterAggregate(BaseModel):
    id: int
    accounts: List[dict]  # Placeholder for TikTok accounts
    config: dict  # Placeholder for TikTok configuration


# ===== Worker Management Domain Models =====

class WorkerRegistrationRequest(BaseModel):
    worker_id: str
    base_url: str
    name: Optional[str] = None
    capacity: int = 1
    capabilities: Optional[List[str]] = None


class WorkerHeartbeatRequest(BaseModel):
    worker_id: str
    base_url: str
    status: Literal["ACTIVE", "BUSY", "MAINTENANCE"] = "ACTIVE"
    current_jobs: int = 0
    metrics: Optional[dict] = None


# ===== Task Processing Domain Models =====

class TaskExecutionMetrics(BaseModel):
    task_id: int
    worker_id: str
    start_time: float
    end_time: Optional[float] = None
    success_count: int = 0
    failure_count: int = 0
    processing_time: Optional[float] = None
    error_messages: Optional[List[str]] = None


class WorkerCapabilities(BaseModel):
    supports_bulk_upload: bool = True
    supports_media_uniquification: bool = True
    supports_proxy_diagnostics: bool = True
    supports_cookie_robot: bool = True
    supports_account_management: bool = True
    supports_tiktok: bool = False  # TikTok still handled by web
    max_concurrent_tasks: int = 2


# ===== Error Handling Domain Models =====

class ErrorDetails(BaseModel):
    error_type: str
    error_message: str
    stack_trace: Optional[str] = None
    context: Optional[dict] = None
    timestamp: float
    worker_id: str


class RetryableError(BaseModel):
    original_error: ErrorDetails
    retry_count: int
    max_retries: int
    next_retry_at: Optional[float] = None 