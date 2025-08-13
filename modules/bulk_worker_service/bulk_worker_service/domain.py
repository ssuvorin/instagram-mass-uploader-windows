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