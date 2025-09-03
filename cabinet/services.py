from dataclasses import dataclass
from typing import List, Optional
from django.db.models import QuerySet, Sum, Avg
from .models import Client, ClientHashtag
from uploader.models import HashtagAnalytics


@dataclass
class HashtagSummary:
    hashtag: str
    total_views: int
    average_views: float
    last_snapshot_id: int


class AnalyticsService:
    def __init__(self, client: Client) -> None:
        self.client = client

    def get_client_hashtags(self) -> QuerySet[ClientHashtag]:
        return ClientHashtag.objects.filter(client=self.client)

    def get_hashtag_summaries(self) -> List[HashtagSummary]:
        summaries: List[HashtagSummary] = []
        for ch in self.get_client_hashtags():
            last_snap: Optional[HashtagAnalytics] = (
                HashtagAnalytics.objects.filter(hashtag=ch.hashtag)
                .order_by("-created_at")
                .first()
            )
            if not last_snap:
                continue
            summaries.append(
                HashtagSummary(
                    hashtag=ch.hashtag,
                    total_views=last_snap.total_views,
                    average_views=last_snap.average_views,
                    last_snapshot_id=last_snap.id,
                )
            )
        return summaries


