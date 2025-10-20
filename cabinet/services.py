from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Tuple
from decimal import Decimal, ROUND_HALF_UP
import os
import json
from django.db.models import QuerySet, Sum, Q
from django.utils import timezone
from django.db.models.functions import TruncDate, TruncWeek
from .models import Client, ClientHashtag
from uploader.models import HashtagAnalytics
from .currency_service import currency_service


@dataclass
class HashtagSummary:
    hashtag: str
    total_views: int
    average_views: float
    last_snapshot_id: int


@dataclass
class HashtagDetail:
    hashtag: str
    total_videos: int
    total_views: int
    average_views: float
    total_likes: int
    total_comments: int
    engagement_rate: float
    last_snapshot_id: int


@dataclass
class SocialNetworkAnalytics:
    """Analytics data for a specific social network"""
    network: str
    total_posts: int
    total_views: int
    total_likes: int
    total_comments: int
    total_shares: int
    total_followers: int
    average_views: float
    engagement_rate: float
    growth_rate: float
    # Platform-specific metrics
    instagram_stories_views: int = 0
    instagram_reels_views: int = 0
    youtube_subscribers: int = 0
    youtube_watch_time: int = 0
    tiktok_video_views: int = 0
    tiktok_profile_views: int = 0
    # Advanced account-level metrics
    total_accounts: int = 0
    avg_videos_per_account: float = 0.0
    max_videos_per_account: int = 0
    avg_views_per_video: float = 0.0
    max_views_per_video: int = 0
    avg_views_per_account: float = 0.0
    max_views_per_account: int = 0
    avg_likes_per_video: float = 0.0
    max_likes_per_video: int = 0
    avg_likes_per_account: float = 0.0
    max_likes_per_account: int = 0


@dataclass
class ClientAnalyticsSummary:
    """Combined analytics summary for a client across all networks"""
    client: Client
    networks: Dict[str, SocialNetworkAnalytics]
    total_posts: int
    total_views: int
    total_likes: int
    total_comments: int
    total_shares: int
    total_followers: int
    average_views: float
    engagement_rate: float


class AnalyticsService:
    def __init__(self, client: Client) -> None:
        self.client = client

    def get_client_hashtags(self) -> QuerySet[ClientHashtag]:
        return ClientHashtag.objects.filter(client=self.client)

    def get_hashtag_summaries(self) -> List[HashtagSummary]:
        summaries: List[HashtagSummary] = []
        for ch in self.get_client_hashtags():
            # Get both manual and automatic Instagram analytics
            last_snap: Optional[HashtagAnalytics] = (
                HashtagAnalytics.objects.filter(
                    hashtag=ch.hashtag
                ).filter(
                    Q(social_network='INSTAGRAM') | Q(social_network__isnull=True) | Q(social_network='')
                )
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

    def get_hashtag_details(self) -> List[HashtagDetail]:
        details: List[HashtagDetail] = []
        for ch in self.get_client_hashtags():
            # Get both manual and automatic Instagram analytics
            last_snap: Optional[HashtagAnalytics] = (
                HashtagAnalytics.objects.filter(
                    hashtag=ch.hashtag
                ).filter(
                    Q(social_network='INSTAGRAM') | Q(social_network__isnull=True) | Q(social_network='')
                )
                .order_by("-created_at")
                .first()
            )
            if not last_snap:
                continue
            details.append(
                HashtagDetail(
                    hashtag=ch.hashtag,
                    total_videos=int(getattr(last_snap, "analyzed_medias", 0) or 0),
                    total_views=int(getattr(last_snap, "total_views", 0) or 0),
                    average_views=float(getattr(last_snap, "average_views", 0.0) or 0.0),
                    total_likes=int(getattr(last_snap, "total_likes", 0) or 0),
                    total_comments=int(getattr(last_snap, "total_comments", 0) or 0),
                    engagement_rate=float(getattr(last_snap, "engagement_rate", 0.0) or 0.0),
                    last_snapshot_id=last_snap.id,
                )
            )
        return details

    def get_daily_stats(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get daily stats - combines all hashtag analytics (both manual and automatic)"""
        hashtags = list(self.get_client_hashtags().values_list("hashtag", flat=True))
        end = timezone.now()
        start = end - timezone.timedelta(days=days)
        
        # Get all hashtag analytics (both manual and automatic)
        hashtag_qs = (
            HashtagAnalytics.objects.filter(
                hashtag__in=hashtags,
                created_at__gte=start, 
                created_at__lte=end
            )
            .annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(
                total_views=Sum("total_views"),
                total_videos=Sum("analyzed_medias"),
                total_likes=Sum("total_likes"),
                total_comments=Sum("total_comments"),
            )
            .order_by("day")
        )
        
        # Get manual analytics by client - each record as separate point on chart
        manual_qs = (
            HashtagAnalytics.objects.filter(
                client=self.client,
                is_manual=True,
                created_at__gte=start,
                created_at__lte=end
            )
            .annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(
                total_views=Sum("total_views"),
                total_videos=Sum("analyzed_medias"),
                total_likes=Sum("total_likes"),
                total_comments=Sum("total_comments"),
            )
            .order_by("day")
        )
        
        # Merge both querysets by date
        stats_dict: Dict[str, Dict[str, int]] = {}
        
        for row in hashtag_qs:
            d = row.get("day")
            if d:
                date_str = d.strftime("%Y-%m-%d")
                stats_dict[date_str] = {
                    "date": date_str,
                    "day_name": d.strftime("%b %d"),
                    "total_views": int(row.get("total_views") or 0),
                    "total_videos": int(row.get("total_videos") or 0),
                    "total_likes": int(row.get("total_likes") or 0),
                    "total_comments": int(row.get("total_comments") or 0),
                }
        
        for row in manual_qs:
            d = row.get("day")
            if d:
                date_str = d.strftime("%Y-%m-%d")
                if date_str in stats_dict:
                    # Add to existing
                    stats_dict[date_str]["total_views"] += int(row.get("total_views") or 0)
                    stats_dict[date_str]["total_videos"] += int(row.get("total_videos") or 0)
                    stats_dict[date_str]["total_likes"] += int(row.get("total_likes") or 0)
                    stats_dict[date_str]["total_comments"] += int(row.get("total_comments") or 0)
                else:
                    # Create new entry
                    stats_dict[date_str] = {
                        "date": date_str,
                        "day_name": d.strftime("%b %d"),
                        "total_views": int(row.get("total_views") or 0),
                        "total_videos": int(row.get("total_videos") or 0),
                        "total_likes": int(row.get("total_likes") or 0),
                        "total_comments": int(row.get("total_comments") or 0),
                    }
        
        # Convert dict to sorted list
        out = sorted(stats_dict.values(), key=lambda x: x["date"])
        return out

    def get_weekly_stats(self, weeks: int = 12) -> List[Dict[str, Any]]:
        """Get weekly stats - combines hashtag analytics and manual analytics"""
        hashtags = list(self.get_client_hashtags().values_list("hashtag", flat=True))
        end = timezone.now()
        start = end - timezone.timedelta(weeks=weeks)
        
        # Get all hashtag analytics (both manual and automatic)
        hashtag_qs = (
            HashtagAnalytics.objects.filter(
                hashtag__in=hashtags,
                created_at__gte=start, 
                created_at__lte=end
            )
            .annotate(week=TruncWeek("created_at"))
            .values("week")
            .annotate(
                total_views=Sum("total_views"),
                total_videos=Sum("analyzed_medias"),
                total_likes=Sum("total_likes"),
                total_comments=Sum("total_comments"),
            )
            .order_by("week")
        )
        
        # Get manual analytics grouped by created_at
        manual_qs = (
            HashtagAnalytics.objects.filter(
                client=self.client,
                is_manual=True,
                created_at__gte=start,
                created_at__lte=end
            )
            .annotate(week=TruncWeek("created_at"))
            .values("week")
            .annotate(
                total_views=Sum("total_views"),
                total_videos=Sum("analyzed_medias"),
                total_likes=Sum("total_likes"),
                total_comments=Sum("total_comments"),
            )
            .order_by("week")
        )
        
        # Merge both querysets by week
        stats_dict: Dict[str, Dict[str, Any]] = {}
        
        for row in hashtag_qs:
            w = row.get("week")
            if w:
                week_str = w.strftime("%Y-%W")
                stats_dict[week_str] = {
                    "week": week_str,
                    "label": w.strftime("%b %d"),
                    "total_views": int(row.get("total_views") or 0),
                    "total_videos": int(row.get("total_videos") or 0),
                    "total_likes": int(row.get("total_likes") or 0),
                    "total_comments": int(row.get("total_comments") or 0),
                }
        
        for row in manual_qs:
            w = row.get("week")
            if w:
                week_str = w.strftime("%Y-%W")
                if week_str in stats_dict:
                    # Add to existing
                    stats_dict[week_str]["total_views"] += int(row.get("total_views") or 0)
                    stats_dict[week_str]["total_videos"] += int(row.get("total_videos") or 0)
                    stats_dict[week_str]["total_likes"] += int(row.get("total_likes") or 0)
                    stats_dict[week_str]["total_comments"] += int(row.get("total_comments") or 0)
                else:
                    # Create new entry
                    stats_dict[week_str] = {
                        "week": week_str,
                        "label": w.strftime("%b %d"),
                        "total_views": int(row.get("total_views") or 0),
                        "total_videos": int(row.get("total_videos") or 0),
                        "total_likes": int(row.get("total_likes") or 0),
                        "total_comments": int(row.get("total_comments") or 0),
                    }
        
        # Convert dict to sorted list
        out = sorted(stats_dict.values(), key=lambda x: x["week"])
        return out

    def get_manual_analytics_by_network(self, days: int = 30) -> Dict[str, SocialNetworkAnalytics]:
        """Get manual analytics data grouped by social network - AGGREGATES cumulative metrics, takes latest for snapshots"""
        from django.db.models import Sum, Avg, Max
        
        end = timezone.now()
        if days is None:
            # All time - no date filtering
            start = None
            time_filter = {}
        else:
            start = end - timezone.timedelta(days=days)
            time_filter = {
                'created_at__gte': start,
                'created_at__lte': end
            }
        
        print(f"\n=== DEBUG get_manual_analytics_by_network ===")
        print(f"Client: {self.client.name} (ID: {self.client.id})")
        if days is None:
            print(f"Period: All time")
        else:
            print(f"Period: {start} to {end} (last {days} days)")
        
        # Get client hashtags first
        client_hashtags = list(self.get_client_hashtags().values_list("hashtag", flat=True))
        print(f"Client hashtags: {client_hashtags}")
        
        # Check raw records first - search by hashtag, not client
        filter_kwargs = {
            'hashtag__in': client_hashtags,
            **time_filter
        }
        all_records = HashtagAnalytics.objects.filter(**filter_kwargs)
        print(f"Total records found: {all_records.count()}")
        for record in all_records[:5]:  # Show first 5
            print(f"  - ID:{record.id}, Hashtag:{record.hashtag}, Network:{record.social_network}, Manual:{record.is_manual}, Created:{record.created_at}, Posts:{record.analyzed_medias}, Views:{record.total_views}")
        
        # Get manual analytics for this client's hashtags and aggregate by network
        # NOTE: We SUM cumulative metrics (posts, views, likes) but take LATEST for snapshot metrics (accounts, followers)
        networks_data = HashtagAnalytics.objects.filter(**filter_kwargs).values('social_network').annotate(
            total_posts=Sum('analyzed_medias'),
            total_views=Sum('total_views'),
            total_likes=Sum('total_likes'),
            total_comments=Sum('total_comments'),
            total_shares=Sum('total_shares'),
            instagram_stories_views=Sum('instagram_stories_views'),
            instagram_reels_views=Sum('instagram_reels_views'),
            youtube_subscribers=Sum('youtube_subscribers'),
            youtube_watch_time=Sum('youtube_watch_time'),
            tiktok_video_views=Sum('tiktok_video_views'),
            tiktok_profile_views=Sum('tiktok_profile_views'),
            # For advanced metrics, we'll calculate them from raw data instead of using pre-calculated fields
            max_videos_per_account=Max('max_videos_per_account'),
            max_views_per_video=Max('max_views_per_video'),
            max_views_per_account=Max('max_views_per_account'),
            max_likes_per_video=Max('max_likes_per_video'),
            max_likes_per_account=Max('max_likes_per_account'),
        )
        
        networks = {}
        
        for network_data in networks_data:
            network_key = network_data['social_network']
            total_posts = network_data['total_posts'] or 0
            total_views = network_data['total_views'] or 0
            
            # Calculate average views and engagement rate from aggregated data
            avg_views = (total_views / total_posts) if total_posts > 0 else 0
            
            total_engagement = (network_data['total_likes'] or 0) + (network_data['total_comments'] or 0) + (network_data['total_shares'] or 0)
            engagement_rate = (total_engagement / total_views) if total_views > 0 else 0
            
            # Get latest record for snapshot metrics (accounts, followers, growth_rate)
            # For total_accounts, get the latest record where total_accounts > 0
            latest_filter = {
                'hashtag__in': client_hashtags,
                'social_network': network_key,
                **time_filter
            }
            latest_record = HashtagAnalytics.objects.filter(**latest_filter).order_by('-created_at').first()
            
            # For total_accounts, try to get a record with actual account count
            accounts_filter = {
                'hashtag__in': client_hashtags,
                'social_network': network_key,
                'total_accounts__gt': 0,
                **time_filter
            }
            accounts_record = HashtagAnalytics.objects.filter(**accounts_filter).order_by('-created_at').first()
            
            # Snapshot metrics from latest record
            total_accounts = accounts_record.total_accounts if accounts_record else (latest_record.total_accounts if latest_record else 0)
            total_followers = latest_record.total_followers if latest_record else 0
            growth_rate = latest_record.growth_rate if latest_record else 0.0
            
            # Calculate advanced metrics from raw data
            avg_videos_per_account = (total_posts / total_accounts) if total_accounts > 0 else 0.0
            avg_views_per_video = avg_views  # Already calculated above
            avg_views_per_account = (total_views / total_accounts) if total_accounts > 0 else 0.0
            avg_likes_per_video = ((network_data['total_likes'] or 0) / total_posts) if total_posts > 0 else 0.0
            avg_likes_per_account = ((network_data['total_likes'] or 0) / total_accounts) if total_accounts > 0 else 0.0
            
            networks[network_key] = SocialNetworkAnalytics(
                network=network_key,
                total_posts=total_posts,
                total_views=total_views,
                total_likes=network_data['total_likes'] or 0,
                total_comments=network_data['total_comments'] or 0,
                total_shares=network_data['total_shares'] or 0,
                total_followers=total_followers,
                average_views=avg_views,
                engagement_rate=engagement_rate,
                growth_rate=growth_rate,
                instagram_stories_views=network_data['instagram_stories_views'] or 0,
                instagram_reels_views=network_data['instagram_reels_views'] or 0,
                youtube_subscribers=network_data['youtube_subscribers'] or 0,
                youtube_watch_time=network_data['youtube_watch_time'] or 0,
                tiktok_video_views=network_data['tiktok_video_views'] or 0,
                tiktok_profile_views=network_data['tiktok_profile_views'] or 0,
                # Advanced metrics - calculated from raw data
                total_accounts=total_accounts,
                avg_videos_per_account=avg_videos_per_account,
                max_videos_per_account=network_data['max_videos_per_account'] or 0,
                avg_views_per_video=avg_views_per_video,
                max_views_per_video=network_data['max_views_per_video'] or 0,
                avg_views_per_account=avg_views_per_account,
                max_views_per_account=network_data['max_views_per_account'] or 0,
                avg_likes_per_video=avg_likes_per_video,
                max_likes_per_video=network_data['max_likes_per_video'] or 0,
                avg_likes_per_account=avg_likes_per_account,
                max_likes_per_account=network_data['max_likes_per_account'] or 0,
            )
        
        return networks

    def get_combined_analytics_summary(self, days: int = 30) -> ClientAnalyticsSummary:
        """Get combined analytics summary including both hashtag and manual data"""
        # Get manual analytics by network
        manual_networks = self.get_manual_analytics_by_network(days)
        
        # Get hashtag analytics (Instagram-focused)
        hashtag_details = self.get_hashtag_details()
        
        # Combine Instagram hashtag data with manual Instagram data
        if 'INSTAGRAM' in manual_networks:
            # Add hashtag data to Instagram manual data
            instagram_manual = manual_networks['INSTAGRAM']
            for detail in hashtag_details:
                instagram_manual.total_posts += detail.total_videos
                instagram_manual.total_views += detail.total_views
                instagram_manual.total_likes += detail.total_likes
                instagram_manual.total_comments += detail.total_comments
        else:
            # Create Instagram entry from hashtag data
            total_posts = sum(detail.total_videos for detail in hashtag_details)
            total_views = sum(detail.total_views for detail in hashtag_details)
            total_likes = sum(detail.total_likes for detail in hashtag_details)
            total_comments = sum(detail.total_comments for detail in hashtag_details)
            
            if total_posts > 0:
                manual_networks['INSTAGRAM'] = SocialNetworkAnalytics(
                    network='INSTAGRAM',
                    total_posts=total_posts,
                    total_views=total_views,
                    total_likes=total_likes,
                    total_comments=total_comments,
                    total_shares=0,  # Not available from hashtag data
                    total_followers=0,  # Not available from hashtag data
                    average_views=total_views / total_posts if total_posts > 0 else 0,
                    engagement_rate=sum(detail.engagement_rate for detail in hashtag_details) / len(hashtag_details) if hashtag_details else 0,
                    growth_rate=0,  # Not available from hashtag data
                )
        
        # Calculate totals across all networks
        total_posts = sum(network.total_posts for network in manual_networks.values())
        total_views = sum(network.total_views for network in manual_networks.values())
        total_likes = sum(network.total_likes for network in manual_networks.values())
        total_comments = sum(network.total_comments for network in manual_networks.values())
        total_shares = sum(network.total_shares for network in manual_networks.values())
        total_followers = sum(network.total_followers for network in manual_networks.values())
        
        return ClientAnalyticsSummary(
            client=self.client,
            networks=manual_networks,
            total_posts=total_posts,
            total_views=total_views,
            total_likes=total_likes,
            total_comments=total_comments,
            total_shares=total_shares,
            total_followers=total_followers,
            average_views=total_views / total_posts if total_posts > 0 else 0,
            engagement_rate=(total_likes + total_comments + total_shares) / total_views if total_views > 0 else 0,
        )

    def get_network_breakdown(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get analytics breakdown by social network for dashboard display"""
        summary = self.get_combined_analytics_summary(days)
        
        breakdown = []
        for network_key, network_data in summary.networks.items():
            network_display = dict(HashtagAnalytics.SOCIAL_NETWORK_CHOICES).get(network_key, network_key)
            
            breakdown.append({
                'network': network_key,
                'network_display': network_display,
                'total_posts': network_data.total_posts,
                'total_views': network_data.total_views,
                'total_likes': network_data.total_likes,
                'total_comments': network_data.total_comments,
                'total_shares': network_data.total_shares,
                'total_followers': network_data.total_followers,
                'average_views': network_data.average_views,
                'engagement_rate': network_data.engagement_rate,
                'growth_rate': network_data.growth_rate,
                # Platform-specific metrics
                'instagram_stories_views': network_data.instagram_stories_views,
                'instagram_reels_views': network_data.instagram_reels_views,
                'youtube_subscribers': network_data.youtube_subscribers,
                'youtube_watch_time': network_data.youtube_watch_time,
                'tiktok_video_views': network_data.tiktok_video_views,
                'tiktok_profile_views': network_data.tiktok_profile_views,
                # Advanced account-level metrics
                'total_accounts': network_data.total_accounts,
                'avg_videos_per_account': network_data.avg_videos_per_account,
                'max_videos_per_account': network_data.max_videos_per_account,
                'avg_views_per_video': network_data.avg_views_per_video,
                'max_views_per_video': network_data.max_views_per_video,
                'avg_views_per_account': network_data.avg_views_per_account,
                'max_views_per_account': network_data.max_views_per_account,
                'avg_likes_per_video': network_data.avg_likes_per_video,
                'max_likes_per_video': network_data.max_likes_per_video,
                'avg_likes_per_account': network_data.avg_likes_per_account,
                'max_likes_per_account': network_data.max_likes_per_account,
            })
        
        return breakdown



# ------------------------
# Agency Calculator Service
# ------------------------

@dataclass
class QuoteInput:
    platform: str
    country: str
    volume_millions: float
    urgent: bool = False
    peak_season: bool = False
    exclusive_content: bool = False
    own_badge: bool = False
    own_content: bool = False
    pilot: bool = False
    vip_percent: float = 0.0  # 0.0 .. 0.15


class AgencyCalculatorService:
    def __init__(self) -> None:
        config_path = os.path.join(os.path.dirname(__file__), "agency_calculator_config.json")
        with open(config_path, "r", encoding="utf-8") as f:
            self.config: Dict[str, Any] = json.load(f)
        # Precompute country -> tier mapping
        tiers = self.config.get("tiers", {})
        self.country_to_tier: Dict[str, str] = {}
        for key, tdata in tiers.items():
            for name in tdata.get("countries", []):
                self.country_to_tier[self._norm(name)] = key
        self.complex_countries: set[str] = set(self._norm(c) for c in tiers.get("complex", {}).get("countries", []))
        # Volume brackets (sorted by min)
        self.brackets: List[Dict[str, Any]] = sorted(
            list(self.config.get("base_prices", {}).get("volume_brackets", [])),
            key=lambda b: b.get("min_millions") or 0,
        )

    def _norm(self, s: str) -> str:
        return (s or "").strip().lower()

    def _find_bracket(self, volume_millions: float) -> Dict[str, Any]:
        for b in self.brackets:
            min_m = b.get("min_millions")
            max_m = b.get("max_millions")
            if volume_millions >= (min_m or 0) and (max_m is None or volume_millions < max_m):
                return b
        return self.brackets[-1] if self.brackets else {}

    def _tier_info(self, country: str) -> Tuple[str, float, bool, float]:
        tiers = self.config.get("tiers", {})
        complex_key = "complex"
        is_complex = self._norm(country) in self.complex_countries
        complex_extra = float(tiers.get(complex_key, {}).get("extra_percent", 0.0)) if is_complex else 0.0
        tier_key = self.country_to_tier.get(self._norm(country))
        if tier_key is None:
            tier_key = "tier1"  # default to base pricing if unknown
        tier_multiplier = float(tiers.get(tier_key, {}).get("multiplier", 1.0))
        return tier_key, tier_multiplier, is_complex, complex_extra

    def _calculate_countries_multiplier(self, countries: List[Dict[str, Any]]) -> Tuple[str, float, bool, float]:
        """Calculate average multiplier for selected countries"""
        if not countries:
            return "tier1", 1.0, False, 0.0
        
        tiers = self.config.get("tiers", {})
        total_multiplier = 0.0
        total_complex_extra = 0.0
        has_complex = False
        
        for country_data in countries:
            country_code = country_data.get("code", "")
            tier = country_data.get("tier", "1")
            
            # Map tier from frontend to config
            if tier == "difficult":
                tier_key = "complex"
                has_complex = True
            else:
                tier_key = f"tier{tier}"
            
            tier_info = tiers.get(tier_key, {})
            multiplier = float(tier_info.get("multiplier", 1.0))
            
            if tier_key == "complex":
                complex_extra = float(tier_info.get("extra_percent", 0.0))
                total_complex_extra += complex_extra
            
            total_multiplier += multiplier
        
        # Calculate averages
        avg_multiplier = total_multiplier / len(countries)
        avg_complex_extra = total_complex_extra / len(countries) if has_complex else 0.0
        
        # Determine representative tier
        avg_tier_num = sum(4 if c.get("tier") == "difficult" else int(c.get("tier", 1)) for c in countries) / len(countries)
        if avg_tier_num >= 4:
            tier_key = "complex"
        elif avg_tier_num >= 3:
            tier_key = "tier3"
        elif avg_tier_num >= 2:
            tier_key = "tier2"
        else:
            tier_key = "tier1"
        
        return tier_key, avg_multiplier, has_complex, avg_complex_extra

    def _market_discount_percent(self, volume_millions: float) -> float:
        rows = sorted(self.config.get("market_discounts", []), key=lambda r: r.get("min_millions", 0))
        pct = 0.0
        for r in rows:
            if volume_millions >= float(r.get("min_millions", 0)):
                pct = float(r.get("percent", 0.0))
        return pct

    def _sum_discounts(self, inp: QuoteInput) -> float:
        cfg = self.config.get("discounts", {})
        total = 0.0
        if inp.own_badge:
            total += float(cfg.get("own_badge", 0.0))
        if inp.own_content:
            total += float(cfg.get("own_content", 0.0))
        if inp.pilot:
            total += float(cfg.get("pilot", 0.0))
        vip_max = float(cfg.get("vip_max", 0.15))
        vip = min(max(inp.vip_percent or 0.0, 0.0), vip_max)
        total += vip
        # Clamp to sane range [0, 0.8]
        return max(0.0, min(total, 0.8))

    def _sum_surcharges(self, inp: QuoteInput, complex_extra: float) -> float:
        cfg = self.config.get("surcharges", {})
        total = 0.0
        if inp.urgent:
            total += float(cfg.get("urgent", 0.0))
        if inp.peak_season:
            total += float(cfg.get("peak_season", 0.0))
        if inp.exclusive_content:
            total += float(cfg.get("exclusive_content", 0.0))
        total += complex_extra
        # Clamp to sane range [0, 1.0]
        return max(0.0, min(total, 1.0))

    def calculate(self, params: Dict[str, Any]) -> Dict[str, Any]:
        # Handle multiple platforms
        platforms = params.get("platforms", [])
        if not platforms:
            platforms = [params.get("platform", "instagram")]
        
        # Handle multiple countries
        countries = params.get("countries", [])
        if not countries and params.get("country"):
            countries = [{"code": params.get("country"), "tier": "1"}]
        
        # Use primary platform for calculation
        primary_platform = platforms[0] if platforms else "instagram"
        
        # Validate and normalize input
        inp = QuoteInput(
            platform=primary_platform.strip().lower(),
            country=countries[0]["code"] if countries else "USA",
            volume_millions=float(params.get("volume_millions") or 0),
            urgent=bool(params.get("urgent") or False),
            peak_season=bool(params.get("peak_season") or False),
            exclusive_content=bool(params.get("exclusive_content") or False),
            own_badge=bool(params.get("own_badge") or False),
            own_content=bool(params.get("own_content") or False),
            pilot=bool(params.get("pilot") or False),
            vip_percent=float(params.get("vip_percent") or 0.0),
        )
        minimums = self.config.get("minimums", {})
        min_order_millions = float(minimums.get("min_order_millions", 15))
        min_order_amount_rub = float(minimums.get("min_order_amount_rub", 615000))
        if inp.volume_millions <= 0:
            return {
                "error": "Volume must be greater than zero (in millions)",
            }

        bracket = self._find_bracket(inp.volume_millions)
        base_rub_per_view = float(bracket.get("rub_per_view", 0.0))
        
        # Получаем актуальные курсы валют
        current_rates = currency_service.get_current_rates()
        usd_to_rub = current_rates["usd_rub"]
        eur_to_rub = current_rates["eur_rub"]

        # Calculate average tier multiplier for selected countries
        tier_key, tier_multiplier, is_complex, complex_extra = self._calculate_countries_multiplier(countries)
        platform_multiplier = float(self.config.get("platform_multipliers", {}).get(inp.platform, 1.0))

        discounts_pct = self._sum_discounts(inp)
        surcharges_pct = self._sum_surcharges(inp, complex_extra)
        market_discount_pct = self._market_discount_percent(inp.volume_millions)

        # Compose price per view (RUB)
        price_per_view_rub = base_rub_per_view
        price_per_view_rub *= tier_multiplier
        price_per_view_rub *= platform_multiplier
        price_per_view_rub *= (1.0 + surcharges_pct)
        price_per_view_rub *= (1.0 - discounts_pct)
        price_per_view_rub *= (1.0 - market_discount_pct)

        total_views = int(round(inp.volume_millions * 1_000_000))
        total_price_rub = price_per_view_rub * total_views

        applied_min_volume = False
        applied_min_amount = False
        effective_views = total_views
        if inp.volume_millions < min_order_millions:
            applied_min_volume = True
            effective_views = int(round(min_order_millions * 1_000_000))
        total_price_rub_effective = price_per_view_rub * effective_views
        if total_price_rub_effective < min_order_amount_rub:
            applied_min_amount = True
            total_price_rub_effective = min_order_amount_rub

        # Compute USD via conversion
        price_per_view_usd = price_per_view_rub / usd_to_rub if usd_to_rub else 0.0
        total_price_usd_effective = total_price_rub_effective / usd_to_rub if usd_to_rub else 0.0

        def _fmt_money(v: float) -> float:
            return float(Decimal(v).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

        def _fmt_micro(v: float) -> float:
            return float(Decimal(v).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP))

        return {
            "inputs": {
                "platform": inp.platform,
                "platforms": platforms,
                "country": inp.country,
                "countries": countries,
                "volume_millions": inp.volume_millions,
                "vip_percent": inp.vip_percent,
                "flags": {
                    "urgent": inp.urgent,
                    "peak_season": inp.peak_season,
                    "exclusive_content": inp.exclusive_content,
                    "own_badge": inp.own_badge,
                    "own_content": inp.own_content,
                    "pilot": inp.pilot,
                },
            },
            "bracket": bracket,
            "tier": {
                "key": tier_key,
                "multiplier": tier_multiplier,
                "is_complex": is_complex,
                "complex_extra": complex_extra,
            },
            "platform_multiplier": platform_multiplier,
            "percents": {
                "surcharges": surcharges_pct,
                "discounts": discounts_pct,
                "market_discount": market_discount_pct,
            },
            "unit_prices": {
                "rub_per_view": _fmt_micro(price_per_view_rub),
                "usd_per_view": _fmt_micro(price_per_view_usd),
            },
            "totals": {
                "total_views_requested": total_views,
                "total_views_effective": effective_views,
                "rub_total": _fmt_money(total_price_rub_effective),
                "usd_total": _fmt_money(total_price_usd_effective),
                "eur_total": _fmt_money(total_price_rub_effective / eur_to_rub if eur_to_rub else 0.0),
                "applied_min_volume": applied_min_volume,
                "applied_min_amount": applied_min_amount,
                "min_order_millions": min_order_millions,
                "min_order_amount_rub": min_order_amount_rub,
            },
            "currency": {
                "usd_to_rub": _fmt_money(usd_to_rub),
                "eur_to_rub": _fmt_money(eur_to_rub),
                "source": current_rates.get("source", "unknown"),
                "last_updated": currency_service.get_rates_info()
            },
        }

