"""
Metrics calculation engine for standardized analytics calculations.

This module provides a unified calculation engine for all metrics calculations
across the cabinet system, ensuring consistency and preventing duplication.
"""

import logging
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any, Union, Tuple
from dataclasses import dataclass
from django.db.models import QuerySet, Sum, Avg, Count, Max, Min, F, Q
from django.utils import timezone

from .models import HashtagAnalytics
from .metrics_data_layer import DateRange, MetricsScope

logger = logging.getLogger(__name__)


@dataclass
class NetworkMetrics:
    """Metrics for a specific social network."""
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
    accounts_count: int
    data_sources: List[str]
    calculation_method: str
    
    # Platform-specific metrics
    instagram_stories_views: int = 0
    instagram_reels_views: int = 0
    youtube_subscribers: int = 0
    youtube_watch_time: int = 0
    tiktok_video_views: int = 0
    tiktok_profile_views: int = 0


@dataclass
class TimeSeriesPoint:
    """A single point in a time series."""
    date: date
    views: int
    likes: int
    comments: int
    shares: int
    followers: int
    engagement_rate: float
    posts_count: int


@dataclass
class AccountLevelMetrics:
    """Account-level statistics."""
    total_accounts: int
    avg_videos_per_account: float
    max_videos_per_account: int
    avg_views_per_video: float
    max_views_per_video: int
    avg_views_per_account: float
    max_views_per_account: int
    avg_likes_per_video: float
    max_likes_per_video: int
    avg_likes_per_account: float
    max_likes_per_account: int


class MetricsCalculationEngine:
    """
    Unified calculation engine for all metrics calculations.
    
    This class provides standardized methods for calculating various metrics
    from HashtagAnalytics data, ensuring consistency across all components.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def calculate_network_metrics(
        self,
        raw_data: QuerySet[HashtagAnalytics],
        network: str,
        prevent_duplicates: bool = True
    ) -> NetworkMetrics:
        """
        Calculate comprehensive metrics for a specific social network.
        
        Args:
            raw_data: QuerySet of HashtagAnalytics records
            network: Social network name (e.g., 'INSTAGRAM', 'YOUTUBE', 'TIKTOK')
            prevent_duplicates: Whether to apply duplicate prevention logic
            
        Returns:
            NetworkMetrics object with calculated values
        """
        self.logger.info(f"Calculating network metrics for {network}")
        
        # Filter data for the specific network
        network_data = raw_data.filter(social_network=network)
        
        if prevent_duplicates:
            network_data = self._apply_duplicate_prevention(network_data)
        
        # Calculate basic aggregations
        aggregations = network_data.aggregate(
            total_posts=Sum('analyzed_medias'),
            total_views=Sum('total_views'),
            total_likes=Sum('total_likes'),
            total_comments=Sum('total_comments'),
            total_shares=Sum('total_shares'),
            total_followers=Sum('total_followers'),
            accounts_count=Sum('total_accounts'),
            # Platform-specific metrics
            instagram_stories_views=Sum('instagram_stories_views'),
            instagram_reels_views=Sum('instagram_reels_views'),
            youtube_subscribers=Sum('youtube_subscribers'),
            youtube_watch_time=Sum('youtube_watch_time'),
            tiktok_video_views=Sum('tiktok_video_views'),
            tiktok_profile_views=Sum('tiktok_profile_views'),
        )
        
        # Handle None values from aggregation
        for key, value in aggregations.items():
            if value is None:
                aggregations[key] = 0
        
        # Calculate derived metrics
        average_views = self._calculate_safe_average(
            aggregations['total_views'], 
            aggregations['total_posts']
        )
        
        engagement_rate = self._calculate_engagement_rate(
            aggregations['total_likes'],
            aggregations['total_comments'],
            aggregations['total_views']
        )
        
        # Calculate growth rate (weighted average)
        growth_rate = self._calculate_weighted_growth_rate(network_data)
        
        # Determine data sources
        data_sources = self._identify_data_sources(network_data)
        
        return NetworkMetrics(
            network=network,
            total_posts=aggregations['total_posts'],
            total_views=aggregations['total_views'],
            total_likes=aggregations['total_likes'],
            total_comments=aggregations['total_comments'],
            total_shares=aggregations['total_shares'],
            total_followers=aggregations['total_followers'],
            average_views=average_views,
            engagement_rate=engagement_rate,
            growth_rate=growth_rate,
            accounts_count=aggregations['accounts_count'],
            data_sources=data_sources,
            calculation_method="standardized_aggregation_with_duplicate_prevention",
            instagram_stories_views=aggregations['instagram_stories_views'],
            instagram_reels_views=aggregations['instagram_reels_views'],
            youtube_subscribers=aggregations['youtube_subscribers'],
            youtube_watch_time=aggregations['youtube_watch_time'],
            tiktok_video_views=aggregations['tiktok_video_views'],
            tiktok_profile_views=aggregations['tiktok_profile_views'],
        )
    
    def calculate_time_series(
        self,
        raw_data: QuerySet[HashtagAnalytics],
        granularity: str = 'daily',
        period: Optional[DateRange] = None
    ) -> List[TimeSeriesPoint]:
        """
        Calculate time series data for temporal analysis.
        
        Args:
            raw_data: QuerySet of HashtagAnalytics records
            granularity: Time granularity ('daily', 'weekly', 'monthly')
            period: Optional date range to limit the analysis
            
        Returns:
            List of TimeSeriesPoint objects ordered by date
        """
        self.logger.info(f"Calculating {granularity} time series for {raw_data.count()} records")
        
        # Apply period filtering if specified
        if period and not period.is_all_time():
            period_filters = period.to_filter_kwargs()
            raw_data = raw_data.filter(**period_filters)
        
        # Apply duplicate prevention
        clean_data = self._apply_duplicate_prevention(raw_data)
        
        # Group data by time period
        if granularity == 'daily':
            time_series = self._calculate_daily_time_series(clean_data)
        elif granularity == 'weekly':
            time_series = self._calculate_weekly_time_series(clean_data)
        elif granularity == 'monthly':
            time_series = self._calculate_monthly_time_series(clean_data)
        else:
            raise ValueError(f"Unsupported granularity: {granularity}")
        
        self.logger.info(f"Generated {len(time_series)} time series points")
        return time_series
    
    def calculate_engagement_rates(
        self,
        raw_data: QuerySet[HashtagAnalytics],
        group_by: Optional[str] = None
    ) -> Dict[str, float]:
        """
        Calculate engagement rates with proper formulas.
        
        Args:
            raw_data: QuerySet of HashtagAnalytics records
            group_by: Optional field to group by ('social_network', 'client', 'hashtag')
            
        Returns:
            Dictionary mapping group keys to engagement rates
        """
        self.logger.info(f"Calculating engagement rates, group_by={group_by}")
        
        # Apply duplicate prevention
        clean_data = self._apply_duplicate_prevention(raw_data)
        
        if group_by:
            return self._calculate_grouped_engagement_rates(clean_data, group_by)
        else:
            # Calculate overall engagement rate
            aggregations = clean_data.aggregate(
                total_likes=Sum('total_likes'),
                total_comments=Sum('total_comments'),
                total_views=Sum('total_views')
            )
            
            engagement_rate = self._calculate_engagement_rate(
                aggregations['total_likes'] or 0,
                aggregations['total_comments'] or 0,
                aggregations['total_views'] or 0
            )
            
            return {'overall': engagement_rate}
    
    def _apply_duplicate_prevention(
        self,
        queryset: QuerySet[HashtagAnalytics]
    ) -> QuerySet[HashtagAnalytics]:
        """
        Apply duplicate prevention logic to ensure accurate calculations.
        
        This method identifies and handles potential duplicates based on
        different criteria for manual vs automatic records.
        """
        # For manual records, prevent duplicates by client, hashtag, network, and period
        manual_records = queryset.filter(is_manual=True)
        automatic_records = queryset.filter(is_manual=False)
        
        # Handle manual records - keep latest for each unique combination
        if manual_records.exists():
            manual_unique = self._get_unique_manual_records(manual_records)
        else:
            manual_unique = manual_records
        
        # Handle automatic records - keep latest for each hashtag/network/date
        if automatic_records.exists():
            automatic_unique = self._get_unique_automatic_records(automatic_records)
        else:
            automatic_unique = automatic_records
        
        # Combine the unique records
        if manual_unique.exists() and automatic_unique.exists():
            # Use union to combine querysets
            return manual_unique.union(automatic_unique)
        elif manual_unique.exists():
            return manual_unique
        elif automatic_unique.exists():
            return automatic_unique
        else:
            return queryset.none()
    
    def _get_unique_manual_records(
        self,
        manual_records: QuerySet[HashtagAnalytics]
    ) -> QuerySet[HashtagAnalytics]:
        """Get unique manual records, keeping the latest for each combination."""
        from django.db.models import OuterRef, Subquery
        
        # Find the latest record for each unique combination
        latest_records = manual_records.filter(
            client=OuterRef('client'),
            hashtag=OuterRef('hashtag'),
            social_network=OuterRef('social_network'),
            period_start=OuterRef('period_start'),
            period_end=OuterRef('period_end')
        ).order_by('-created_at', '-id')
        
        # Get the IDs of the latest records
        unique_ids = manual_records.annotate(
            latest_id=Subquery(latest_records.values('id')[:1])
        ).filter(id=F('latest_id')).values_list('id', flat=True)
        
        return manual_records.filter(id__in=unique_ids)
    
    def _get_unique_automatic_records(
        self,
        automatic_records: QuerySet[HashtagAnalytics]
    ) -> QuerySet[HashtagAnalytics]:
        """Get unique automatic records, keeping the latest for each combination."""
        from django.db.models import OuterRef, Subquery
        
        # Find the latest record for each hashtag/network/date combination
        latest_records = automatic_records.filter(
            hashtag=OuterRef('hashtag'),
            social_network=OuterRef('social_network'),
            created_at__date=OuterRef('created_at__date')
        ).order_by('-created_at', '-id')
        
        # Get the IDs of the latest records
        unique_ids = automatic_records.annotate(
            latest_id=Subquery(latest_records.values('id')[:1])
        ).filter(id=F('latest_id')).values_list('id', flat=True)
        
        return automatic_records.filter(id__in=unique_ids)
    
    def _calculate_safe_average(self, total: int, count: int) -> float:
        """Calculate average with safe division."""
        if count and count > 0:
            return float(total) / float(count)
        return 0.0
    
    def _calculate_engagement_rate(
        self,
        total_likes: int,
        total_comments: int,
        total_views: int
    ) -> float:
        """Calculate engagement rate using the standard formula."""
        if total_views and total_views > 0:
            engagement = (total_likes + total_comments) / total_views * 100
            return round(engagement, 2)
        return 0.0
    
    def _calculate_weighted_growth_rate(
        self,
        queryset: QuerySet[HashtagAnalytics]
    ) -> float:
        """Calculate weighted average growth rate."""
        # Get records with growth rate and follower data
        growth_data = queryset.filter(
            growth_rate__isnull=False,
            total_followers__gt=0
        ).values_list('growth_rate', 'total_followers')
        
        if not growth_data:
            return 0.0
        
        # Calculate weighted average (weight by follower count)
        total_weighted_growth = 0.0
        total_weight = 0
        
        for growth_rate, followers in growth_data:
            total_weighted_growth += growth_rate * followers
            total_weight += followers
        
        if total_weight > 0:
            return round(total_weighted_growth / total_weight, 2)
        
        # Fallback to simple average if no follower data
        simple_avg = sum(rate for rate, _ in growth_data) / len(growth_data)
        return round(simple_avg, 2)
    
    def _identify_data_sources(
        self,
        queryset: QuerySet[HashtagAnalytics]
    ) -> List[str]:
        """Identify the data sources present in the queryset."""
        sources = []
        
        if queryset.filter(is_manual=True).exists():
            sources.append('manual')
        
        if queryset.filter(is_manual=False).exists():
            sources.append('automatic')
        
        return sources
    
    def _calculate_daily_time_series(
        self,
        queryset: QuerySet[HashtagAnalytics]
    ) -> List[TimeSeriesPoint]:
        """Calculate daily time series data."""
        from django.db.models.functions import TruncDate
        
        daily_data = (
            queryset
            .annotate(date=TruncDate('created_at'))
            .values('date')
            .annotate(
                views=Sum('total_views'),
                likes=Sum('total_likes'),
                comments=Sum('total_comments'),
                shares=Sum('total_shares'),
                followers=Sum('total_followers'),
                posts_count=Sum('analyzed_medias')
            )
            .order_by('date')
        )
        
        time_series = []
        for day in daily_data:
            engagement_rate = self._calculate_engagement_rate(
                day['likes'] or 0,
                day['comments'] or 0,
                day['views'] or 0
            )
            
            time_series.append(TimeSeriesPoint(
                date=day['date'],
                views=day['views'] or 0,
                likes=day['likes'] or 0,
                comments=day['comments'] or 0,
                shares=day['shares'] or 0,
                followers=day['followers'] or 0,
                engagement_rate=engagement_rate,
                posts_count=day['posts_count'] or 0
            ))
        
        return time_series
    
    def _calculate_weekly_time_series(
        self,
        queryset: QuerySet[HashtagAnalytics]
    ) -> List[TimeSeriesPoint]:
        """Calculate weekly time series data."""
        from django.db.models.functions import TruncWeek
        
        weekly_data = (
            queryset
            .annotate(week=TruncWeek('created_at'))
            .values('week')
            .annotate(
                views=Sum('total_views'),
                likes=Sum('total_likes'),
                comments=Sum('total_comments'),
                shares=Sum('total_shares'),
                followers=Sum('total_followers'),
                posts_count=Sum('analyzed_medias')
            )
            .order_by('week')
        )
        
        time_series = []
        for week in weekly_data:
            engagement_rate = self._calculate_engagement_rate(
                week['likes'] or 0,
                week['comments'] or 0,
                week['views'] or 0
            )
            
            time_series.append(TimeSeriesPoint(
                date=week['week'].date(),
                views=week['views'] or 0,
                likes=week['likes'] or 0,
                comments=week['comments'] or 0,
                shares=week['shares'] or 0,
                followers=week['followers'] or 0,
                engagement_rate=engagement_rate,
                posts_count=week['posts_count'] or 0
            ))
        
        return time_series
    
    def _calculate_monthly_time_series(
        self,
        queryset: QuerySet[HashtagAnalytics]
    ) -> List[TimeSeriesPoint]:
        """Calculate monthly time series data."""
        from django.db.models.functions import TruncMonth
        
        monthly_data = (
            queryset
            .annotate(month=TruncMonth('created_at'))
            .values('month')
            .annotate(
                views=Sum('total_views'),
                likes=Sum('total_likes'),
                comments=Sum('total_comments'),
                shares=Sum('total_shares'),
                followers=Sum('total_followers'),
                posts_count=Sum('analyzed_medias')
            )
            .order_by('month')
        )
        
        time_series = []
        for month in monthly_data:
            engagement_rate = self._calculate_engagement_rate(
                month['likes'] or 0,
                month['comments'] or 0,
                month['views'] or 0
            )
            
            time_series.append(TimeSeriesPoint(
                date=month['month'].date(),
                views=month['views'] or 0,
                likes=month['likes'] or 0,
                comments=month['comments'] or 0,
                shares=month['shares'] or 0,
                followers=month['followers'] or 0,
                engagement_rate=engagement_rate,
                posts_count=month['posts_count'] or 0
            ))
        
        return time_series
    
    def _calculate_grouped_engagement_rates(
        self,
        queryset: QuerySet[HashtagAnalytics],
        group_by: str
    ) -> Dict[str, float]:
        """Calculate engagement rates grouped by a specific field."""
        grouped_data = (
            queryset
            .values(group_by)
            .annotate(
                total_likes=Sum('total_likes'),
                total_comments=Sum('total_comments'),
                total_views=Sum('total_views')
            )
        )
        
        engagement_rates = {}
        for group in grouped_data:
            group_key = str(group[group_by])
            engagement_rate = self._calculate_engagement_rate(
                group['total_likes'] or 0,
                group['total_comments'] or 0,
                group['total_views'] or 0
            )
            engagement_rates[group_key] = engagement_rate
        
        return engagement_rates
    
    def calculate_growth_rates(
        self,
        raw_data: QuerySet[HashtagAnalytics],
        period: Optional[DateRange] = None,
        group_by: Optional[str] = None
    ) -> Dict[str, float]:
        """
        Calculate follower growth rates for analysis.
        
        Args:
            raw_data: QuerySet of HashtagAnalytics records
            period: Optional date range for comparison
            group_by: Optional field to group by ('social_network', 'client', 'hashtag')
            
        Returns:
            Dictionary mapping group keys to growth rates
        """
        self.logger.info(f"Calculating growth rates, group_by={group_by}")
        
        # Apply duplicate prevention
        clean_data = self._apply_duplicate_prevention(raw_data)
        
        if period and not period.is_all_time():
            period_filters = period.to_filter_kwargs()
            clean_data = clean_data.filter(**period_filters)
        
        if group_by:
            return self._calculate_grouped_growth_rates(clean_data, group_by)
        else:
            # Calculate overall growth rate
            growth_rate = self._calculate_weighted_growth_rate(clean_data)
            return {'overall': growth_rate}
    
    def calculate_account_level_metrics(
        self,
        raw_data: QuerySet[HashtagAnalytics],
        scope: Optional[MetricsScope] = None
    ) -> AccountLevelMetrics:
        """
        Calculate account-based statistics.
        
        Args:
            raw_data: QuerySet of HashtagAnalytics records
            scope: Optional metrics scope for filtering
            
        Returns:
            AccountLevelMetrics object with calculated values
        """
        self.logger.info("Calculating account-level metrics")
        
        # Apply scope filtering if provided
        if scope:
            scope_filters = scope.get_filter_kwargs()
            if scope_filters:
                raw_data = raw_data.filter(**scope_filters)
        
        # Apply duplicate prevention
        clean_data = self._apply_duplicate_prevention(raw_data)
        
        # Calculate aggregations for account-level metrics
        aggregations = clean_data.aggregate(
            total_accounts=Sum('total_accounts'),
            avg_videos_per_account=Avg('avg_videos_per_account'),
            max_videos_per_account=Max('max_videos_per_account'),
            avg_views_per_video=Avg('avg_views_per_video'),
            max_views_per_video=Max('max_views_per_video'),
            avg_views_per_account=Avg('avg_views_per_account'),
            max_views_per_account=Max('max_views_per_account'),
            avg_likes_per_video=Avg('avg_likes_per_video'),
            max_likes_per_video=Max('max_likes_per_video'),
            avg_likes_per_account=Avg('avg_likes_per_account'),
            max_likes_per_account=Max('max_likes_per_account'),
        )
        
        # Handle None values and convert to appropriate types
        return AccountLevelMetrics(
            total_accounts=int(aggregations['total_accounts'] or 0),
            avg_videos_per_account=float(aggregations['avg_videos_per_account'] or 0.0),
            max_videos_per_account=int(aggregations['max_videos_per_account'] or 0),
            avg_views_per_video=float(aggregations['avg_views_per_video'] or 0.0),
            max_views_per_video=int(aggregations['max_views_per_video'] or 0),
            avg_views_per_account=float(aggregations['avg_views_per_account'] or 0.0),
            max_views_per_account=int(aggregations['max_views_per_account'] or 0),
            avg_likes_per_video=float(aggregations['avg_likes_per_video'] or 0.0),
            max_likes_per_video=int(aggregations['max_likes_per_video'] or 0),
            avg_likes_per_account=float(aggregations['avg_likes_per_account'] or 0.0),
            max_likes_per_account=int(aggregations['max_likes_per_account'] or 0),
        )
    
    def calculate_platform_specific_metrics(
        self,
        raw_data: QuerySet[HashtagAnalytics],
        platform: str
    ) -> Dict[str, Any]:
        """
        Calculate platform-specific metrics for platform features.
        
        Args:
            raw_data: QuerySet of HashtagAnalytics records
            platform: Platform name ('INSTAGRAM', 'YOUTUBE', 'TIKTOK')
            
        Returns:
            Dictionary with platform-specific metrics
        """
        self.logger.info(f"Calculating platform-specific metrics for {platform}")
        
        # Filter for the specific platform
        platform_data = raw_data.filter(social_network=platform)
        
        # Apply duplicate prevention
        clean_data = self._apply_duplicate_prevention(platform_data)
        
        if platform == 'INSTAGRAM':
            return self._calculate_instagram_metrics(clean_data)
        elif platform == 'YOUTUBE':
            return self._calculate_youtube_metrics(clean_data)
        elif platform == 'TIKTOK':
            return self._calculate_tiktok_metrics(clean_data)
        else:
            raise ValueError(f"Unsupported platform: {platform}")
    
    def _calculate_grouped_growth_rates(
        self,
        queryset: QuerySet[HashtagAnalytics],
        group_by: str
    ) -> Dict[str, float]:
        """Calculate growth rates grouped by a specific field."""
        growth_rates = {}
        
        # Get unique values for the grouping field
        group_values = queryset.values_list(group_by, flat=True).distinct()
        
        for group_value in group_values:
            if group_value is None:
                continue
                
            group_data = queryset.filter(**{group_by: group_value})
            growth_rate = self._calculate_weighted_growth_rate(group_data)
            growth_rates[str(group_value)] = growth_rate
        
        return growth_rates
    
    def _calculate_instagram_metrics(
        self,
        queryset: QuerySet[HashtagAnalytics]
    ) -> Dict[str, Any]:
        """Calculate Instagram-specific metrics."""
        aggregations = queryset.aggregate(
            total_posts=Sum('analyzed_medias'),
            total_views=Sum('total_views'),
            total_likes=Sum('total_likes'),
            total_comments=Sum('total_comments'),
            total_shares=Sum('total_shares'),
            total_followers=Sum('total_followers'),
            stories_views=Sum('instagram_stories_views'),
            reels_views=Sum('instagram_reels_views'),
        )
        
        # Handle None values
        for key, value in aggregations.items():
            if value is None:
                aggregations[key] = 0
        
        # Calculate Instagram-specific ratios
        stories_to_total_ratio = 0.0
        reels_to_total_ratio = 0.0
        
        if aggregations['total_views'] > 0:
            stories_to_total_ratio = (aggregations['stories_views'] / aggregations['total_views']) * 100
            reels_to_total_ratio = (aggregations['reels_views'] / aggregations['total_views']) * 100
        
        # Calculate average engagement per post type
        avg_stories_views = self._calculate_safe_average(
            aggregations['stories_views'],
            queryset.filter(instagram_stories_views__gt=0).count()
        )
        
        avg_reels_views = self._calculate_safe_average(
            aggregations['reels_views'],
            queryset.filter(instagram_reels_views__gt=0).count()
        )
        
        return {
            'platform': 'INSTAGRAM',
            'total_posts': aggregations['total_posts'],
            'total_views': aggregations['total_views'],
            'total_likes': aggregations['total_likes'],
            'total_comments': aggregations['total_comments'],
            'total_shares': aggregations['total_shares'],
            'total_followers': aggregations['total_followers'],
            'stories_views': aggregations['stories_views'],
            'reels_views': aggregations['reels_views'],
            'stories_to_total_ratio': round(stories_to_total_ratio, 2),
            'reels_to_total_ratio': round(reels_to_total_ratio, 2),
            'avg_stories_views': round(avg_stories_views, 2),
            'avg_reels_views': round(avg_reels_views, 2),
            'engagement_rate': self._calculate_engagement_rate(
                aggregations['total_likes'],
                aggregations['total_comments'],
                aggregations['total_views']
            )
        }
    
    def _calculate_youtube_metrics(
        self,
        queryset: QuerySet[HashtagAnalytics]
    ) -> Dict[str, Any]:
        """Calculate YouTube-specific metrics."""
        aggregations = queryset.aggregate(
            total_posts=Sum('analyzed_medias'),
            total_views=Sum('total_views'),
            total_likes=Sum('total_likes'),
            total_comments=Sum('total_comments'),
            total_shares=Sum('total_shares'),
            total_subscribers=Sum('youtube_subscribers'),
            total_watch_time=Sum('youtube_watch_time'),
        )
        
        # Handle None values
        for key, value in aggregations.items():
            if value is None:
                aggregations[key] = 0
        
        # Calculate YouTube-specific metrics
        avg_watch_time_per_video = self._calculate_safe_average(
            aggregations['total_watch_time'],
            aggregations['total_posts']
        )
        
        avg_watch_time_per_view = self._calculate_safe_average(
            aggregations['total_watch_time'],
            aggregations['total_views']
        )
        
        subscriber_to_view_ratio = 0.0
        if aggregations['total_views'] > 0:
            subscriber_to_view_ratio = (aggregations['total_subscribers'] / aggregations['total_views']) * 100
        
        return {
            'platform': 'YOUTUBE',
            'total_posts': aggregations['total_posts'],
            'total_views': aggregations['total_views'],
            'total_likes': aggregations['total_likes'],
            'total_comments': aggregations['total_comments'],
            'total_shares': aggregations['total_shares'],
            'total_subscribers': aggregations['total_subscribers'],
            'total_watch_time_minutes': aggregations['total_watch_time'],
            'avg_watch_time_per_video': round(avg_watch_time_per_video, 2),
            'avg_watch_time_per_view': round(avg_watch_time_per_view, 4),
            'subscriber_to_view_ratio': round(subscriber_to_view_ratio, 2),
            'engagement_rate': self._calculate_engagement_rate(
                aggregations['total_likes'],
                aggregations['total_comments'],
                aggregations['total_views']
            )
        }
    
    def _calculate_tiktok_metrics(
        self,
        queryset: QuerySet[HashtagAnalytics]
    ) -> Dict[str, Any]:
        """Calculate TikTok-specific metrics."""
        aggregations = queryset.aggregate(
            total_posts=Sum('analyzed_medias'),
            total_views=Sum('total_views'),
            total_likes=Sum('total_likes'),
            total_comments=Sum('total_comments'),
            total_shares=Sum('total_shares'),
            total_followers=Sum('total_followers'),
            video_views=Sum('tiktok_video_views'),
            profile_views=Sum('tiktok_profile_views'),
        )
        
        # Handle None values
        for key, value in aggregations.items():
            if value is None:
                aggregations[key] = 0
        
        # Calculate TikTok-specific metrics
        profile_to_video_ratio = 0.0
        if aggregations['video_views'] > 0:
            profile_to_video_ratio = (aggregations['profile_views'] / aggregations['video_views']) * 100
        
        avg_video_views = self._calculate_safe_average(
            aggregations['video_views'],
            aggregations['total_posts']
        )
        
        profile_conversion_rate = 0.0
        if aggregations['profile_views'] > 0:
            profile_conversion_rate = (aggregations['total_followers'] / aggregations['profile_views']) * 100
        
        return {
            'platform': 'TIKTOK',
            'total_posts': aggregations['total_posts'],
            'total_views': aggregations['total_views'],
            'total_likes': aggregations['total_likes'],
            'total_comments': aggregations['total_comments'],
            'total_shares': aggregations['total_shares'],
            'total_followers': aggregations['total_followers'],
            'video_views': aggregations['video_views'],
            'profile_views': aggregations['profile_views'],
            'profile_to_video_ratio': round(profile_to_video_ratio, 2),
            'avg_video_views': round(avg_video_views, 2),
            'profile_conversion_rate': round(profile_conversion_rate, 2),
            'engagement_rate': self._calculate_engagement_rate(
                aggregations['total_likes'],
                aggregations['total_comments'],
                aggregations['total_views']
            )
        } 
   
    def aggregate_by_network(
        self,
        raw_data: QuerySet[HashtagAnalytics],
        networks: Optional[List[str]] = None,
        prevent_duplicates: bool = True
    ) -> Dict[str, NetworkMetrics]:
        """
        Aggregate metrics by social network, preventing double counting.
        
        Args:
            raw_data: QuerySet of HashtagAnalytics records
            networks: Optional list of networks to include
            prevent_duplicates: Whether to apply duplicate prevention
            
        Returns:
            Dictionary mapping network names to NetworkMetrics
        """
        self.logger.info("Aggregating metrics by network")
        
        # Apply duplicate prevention if requested
        if prevent_duplicates:
            clean_data = self._apply_duplicate_prevention(raw_data)
        else:
            clean_data = raw_data
        
        # Get available networks
        if networks:
            available_networks = networks
        else:
            available_networks = list(
                clean_data.values_list('social_network', flat=True).distinct()
            )
        
        network_metrics = {}
        for network in available_networks:
            if network:  # Skip None values
                metrics = self.calculate_network_metrics(
                    clean_data, 
                    network, 
                    prevent_duplicates=False  # Already applied above
                )
                network_metrics[network] = metrics
        
        self.logger.info(f"Aggregated metrics for {len(network_metrics)} networks")
        return network_metrics
    
    def aggregate_by_time_period(
        self,
        raw_data: QuerySet[HashtagAnalytics],
        period: DateRange,
        granularity: str = 'daily',
        prevent_duplicates: bool = True
    ) -> Dict[str, Any]:
        """
        Aggregate metrics by time period with proper time filtering.
        
        Args:
            raw_data: QuerySet of HashtagAnalytics records
            period: Date range for filtering
            granularity: Time granularity ('daily', 'weekly', 'monthly')
            prevent_duplicates: Whether to apply duplicate prevention
            
        Returns:
            Dictionary with time-based aggregated metrics
        """
        self.logger.info(f"Aggregating metrics by {granularity} periods")
        
        # Apply period filtering
        if not period.is_all_time():
            period_filters = period.to_filter_kwargs()
            filtered_data = raw_data.filter(**period_filters)
        else:
            filtered_data = raw_data
        
        # Apply duplicate prevention if requested
        if prevent_duplicates:
            clean_data = self._apply_duplicate_prevention(filtered_data)
        else:
            clean_data = filtered_data
        
        # Calculate time series
        time_series = self.calculate_time_series(
            clean_data, 
            granularity=granularity,
            period=None  # Already filtered above
        )
        
        # Calculate overall metrics for the period
        overall_metrics = self._calculate_period_summary(clean_data)
        
        # Calculate network breakdown
        network_breakdown = self.aggregate_by_network(
            clean_data,
            prevent_duplicates=False  # Already applied above
        )
        
        return {
            'period': {
                'start': period.start,
                'end': period.end,
                'granularity': granularity
            },
            'time_series': time_series,
            'overall_metrics': overall_metrics,
            'network_breakdown': network_breakdown,
            'total_records': clean_data.count(),
            'data_quality': {
                'duplicates_removed': raw_data.count() - clean_data.count() if prevent_duplicates else 0,
                'period_filtered': raw_data.count() - filtered_data.count() if not period.is_all_time() else 0
            }
        }
    
    def aggregate_by_client(
        self,
        raw_data: QuerySet[HashtagAnalytics],
        agency_id: Optional[int] = None,
        prevent_duplicates: bool = True
    ) -> Dict[str, Any]:
        """
        Aggregate metrics by client for agency-level aggregation.
        
        Args:
            raw_data: QuerySet of HashtagAnalytics records
            agency_id: Optional agency ID to filter by
            prevent_duplicates: Whether to apply duplicate prevention
            
        Returns:
            Dictionary with client-level aggregated metrics
        """
        self.logger.info("Aggregating metrics by client")
        
        # Filter by agency if specified
        if agency_id:
            agency_data = raw_data.filter(client__agency_id=agency_id)
        else:
            agency_data = raw_data
        
        # Apply duplicate prevention if requested
        if prevent_duplicates:
            clean_data = self._apply_duplicate_prevention(agency_data)
        else:
            clean_data = agency_data
        
        # Get unique clients
        client_ids = list(
            clean_data.filter(client__isnull=False)
            .values_list('client_id', flat=True)
            .distinct()
        )
        
        client_metrics = {}
        total_agency_metrics = {
            'total_views': 0,
            'total_likes': 0,
            'total_comments': 0,
            'total_shares': 0,
            'total_followers': 0,
            'total_posts': 0,
            'clients_count': 0
        }
        
        for client_id in client_ids:
            if client_id is None:
                continue
                
            client_data = clean_data.filter(client_id=client_id)
            
            # Calculate client metrics
            client_aggregations = client_data.aggregate(
                total_views=Sum('total_views'),
                total_likes=Sum('total_likes'),
                total_comments=Sum('total_comments'),
                total_shares=Sum('total_shares'),
                total_followers=Sum('total_followers'),
                total_posts=Sum('analyzed_medias'),
            )
            
            # Handle None values
            for key, value in client_aggregations.items():
                if value is None:
                    client_aggregations[key] = 0
            
            # Calculate derived metrics
            engagement_rate = self._calculate_engagement_rate(
                client_aggregations['total_likes'],
                client_aggregations['total_comments'],
                client_aggregations['total_views']
            )
            
            average_views = self._calculate_safe_average(
                client_aggregations['total_views'],
                client_aggregations['total_posts']
            )
            
            # Get client info
            client_info = client_data.first().client if client_data.exists() else None
            client_name = client_info.name if client_info else f"Client {client_id}"
            
            # Calculate network breakdown for this client
            client_networks = self.aggregate_by_network(
                client_data,
                prevent_duplicates=False  # Already applied above
            )
            
            client_metrics[client_name] = {
                'client_id': client_id,
                'client_name': client_name,
                'total_views': client_aggregations['total_views'],
                'total_likes': client_aggregations['total_likes'],
                'total_comments': client_aggregations['total_comments'],
                'total_shares': client_aggregations['total_shares'],
                'total_followers': client_aggregations['total_followers'],
                'total_posts': client_aggregations['total_posts'],
                'engagement_rate': engagement_rate,
                'average_views': average_views,
                'networks': client_networks,
                'records_count': client_data.count()
            }
            
            # Add to agency totals
            total_agency_metrics['total_views'] += client_aggregations['total_views']
            total_agency_metrics['total_likes'] += client_aggregations['total_likes']
            total_agency_metrics['total_comments'] += client_aggregations['total_comments']
            total_agency_metrics['total_shares'] += client_aggregations['total_shares']
            total_agency_metrics['total_followers'] += client_aggregations['total_followers']
            total_agency_metrics['total_posts'] += client_aggregations['total_posts']
            total_agency_metrics['clients_count'] += 1
        
        # Calculate agency-level engagement rate
        agency_engagement_rate = self._calculate_engagement_rate(
            total_agency_metrics['total_likes'],
            total_agency_metrics['total_comments'],
            total_agency_metrics['total_views']
        )
        
        # Calculate agency-level network breakdown
        agency_networks = self.aggregate_by_network(
            clean_data,
            prevent_duplicates=False  # Already applied above
        )
        
        return {
            'agency_totals': {
                **total_agency_metrics,
                'engagement_rate': agency_engagement_rate,
                'average_views': self._calculate_safe_average(
                    total_agency_metrics['total_views'],
                    total_agency_metrics['total_posts']
                )
            },
            'clients': client_metrics,
            'agency_networks': agency_networks,
            'data_quality': {
                'total_records': clean_data.count(),
                'duplicates_removed': agency_data.count() - clean_data.count() if prevent_duplicates else 0,
                'clients_with_data': len(client_metrics)
            }
        }
    
    def _calculate_period_summary(
        self,
        queryset: QuerySet[HashtagAnalytics]
    ) -> Dict[str, Any]:
        """Calculate summary metrics for a time period."""
        aggregations = queryset.aggregate(
            total_views=Sum('total_views'),
            total_likes=Sum('total_likes'),
            total_comments=Sum('total_comments'),
            total_shares=Sum('total_shares'),
            total_followers=Sum('total_followers'),
            total_posts=Sum('analyzed_medias'),
            records_count=Count('id'),
            date_range_start=Min('created_at'),
            date_range_end=Max('created_at')
        )
        
        # Handle None values
        for key, value in aggregations.items():
            if value is None and key not in ['date_range_start', 'date_range_end']:
                aggregations[key] = 0
        
        # Calculate derived metrics
        engagement_rate = self._calculate_engagement_rate(
            aggregations['total_likes'],
            aggregations['total_comments'],
            aggregations['total_views']
        )
        
        average_views = self._calculate_safe_average(
            aggregations['total_views'],
            aggregations['total_posts']
        )
        
        return {
            'total_views': aggregations['total_views'],
            'total_likes': aggregations['total_likes'],
            'total_comments': aggregations['total_comments'],
            'total_shares': aggregations['total_shares'],
            'total_followers': aggregations['total_followers'],
            'total_posts': aggregations['total_posts'],
            'engagement_rate': engagement_rate,
            'average_views': average_views,
            'records_count': aggregations['records_count'],
            'date_range': {
                'start': aggregations['date_range_start'],
                'end': aggregations['date_range_end']
            }
        }
    
    def validate_aggregation_consistency(
        self,
        raw_data: QuerySet[HashtagAnalytics],
        aggregated_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate that aggregated results are consistent with raw data.
        
        Args:
            raw_data: Original QuerySet used for aggregation
            aggregated_results: Results from aggregation methods
            
        Returns:
            Dictionary with validation results
        """
        self.logger.info("Validating aggregation consistency")
        
        # Calculate raw totals
        raw_totals = raw_data.aggregate(
            total_views=Sum('total_views'),
            total_likes=Sum('total_likes'),
            total_comments=Sum('total_comments'),
            total_posts=Sum('analyzed_medias'),
            records_count=Count('id')
        )
        
        # Handle None values
        for key, value in raw_totals.items():
            if value is None:
                raw_totals[key] = 0
        
        validation_results = {
            'is_consistent': True,
            'discrepancies': [],
            'raw_totals': raw_totals,
            'aggregated_totals': {},
            'tolerance_percentage': 1.0  # 1% tolerance for rounding differences
        }
        
        # Extract aggregated totals based on result structure
        if 'overall_metrics' in aggregated_results:
            # Time period aggregation format
            agg_totals = aggregated_results['overall_metrics']
        elif 'agency_totals' in aggregated_results:
            # Client aggregation format
            agg_totals = aggregated_results['agency_totals']
        else:
            # Network aggregation format - sum across networks
            agg_totals = self._sum_network_metrics(aggregated_results)
        
        validation_results['aggregated_totals'] = agg_totals
        
        # Compare key metrics
        metrics_to_compare = ['total_views', 'total_likes', 'total_comments', 'total_posts']
        
        for metric in metrics_to_compare:
            raw_value = raw_totals.get(metric, 0)
            agg_value = agg_totals.get(metric, 0)
            
            if raw_value > 0:
                percentage_diff = abs(raw_value - agg_value) / raw_value * 100
                
                if percentage_diff > validation_results['tolerance_percentage']:
                    validation_results['is_consistent'] = False
                    validation_results['discrepancies'].append({
                        'metric': metric,
                        'raw_value': raw_value,
                        'aggregated_value': agg_value,
                        'difference': agg_value - raw_value,
                        'percentage_difference': round(percentage_diff, 2)
                    })
            elif raw_value != agg_value:
                # Both should be zero
                validation_results['is_consistent'] = False
                validation_results['discrepancies'].append({
                    'metric': metric,
                    'raw_value': raw_value,
                    'aggregated_value': agg_value,
                    'difference': agg_value - raw_value,
                    'percentage_difference': 0.0
                })
        
        self.logger.info(f"Aggregation validation complete: consistent={validation_results['is_consistent']}")
        return validation_results
    
    def _sum_network_metrics(self, network_results: Dict[str, NetworkMetrics]) -> Dict[str, int]:
        """Sum metrics across all networks."""
        totals = {
            'total_views': 0,
            'total_likes': 0,
            'total_comments': 0,
            'total_shares': 0,
            'total_followers': 0,
            'total_posts': 0
        }
        
        for network_metrics in network_results.values():
            if isinstance(network_metrics, NetworkMetrics):
                totals['total_views'] += network_metrics.total_views
                totals['total_likes'] += network_metrics.total_likes
                totals['total_comments'] += network_metrics.total_comments
                totals['total_shares'] += network_metrics.total_shares
                totals['total_followers'] += network_metrics.total_followers
                totals['total_posts'] += network_metrics.total_posts
        
        return totals