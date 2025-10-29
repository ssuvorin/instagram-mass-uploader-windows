"""
Unified data layer for metrics calculation and validation.

This module provides a standardized interface for accessing analytics data
with proper filtering, validation, and duplicate detection.
"""

import logging
from datetime import datetime, date
from typing import Optional, List, Dict, Any, Union
from dataclasses import dataclass
from django.db.models import QuerySet, Q, Min, Max, F
from django.utils import timezone
from django.db import models

from .models import HashtagAnalytics
from cabinet.models import Client, Agency

logger = logging.getLogger(__name__)


@dataclass
class DateRange:
    """Represents a date range for filtering analytics data."""
    start: Optional[date] = None
    end: Optional[date] = None
    
    def is_all_time(self) -> bool:
        """Check if this represents an all-time range."""
        return self.start is None and self.end is None
    
    def to_filter_kwargs(self, field_prefix: str = 'created_at') -> Dict[str, Any]:
        """Convert to Django filter kwargs."""
        kwargs = {}
        if self.start:
            kwargs[f'{field_prefix}__date__gte'] = self.start
        if self.end:
            kwargs[f'{field_prefix}__date__lte'] = self.end
        return kwargs


@dataclass
class MetricsScope:
    """Defines the scope for metrics calculation."""
    client: Optional[Client] = None
    agency: Optional[Agency] = None
    admin_view: bool = False
    
    def get_filter_kwargs(self) -> Dict[str, Any]:
        """Get Django filter kwargs for this scope."""
        kwargs = {}
        
        if self.client:
            kwargs['client'] = self.client
        elif self.agency:
            kwargs['client__agency'] = self.agency
        # For admin_view=True, no additional filters are applied
        
        return kwargs
    
    def __str__(self) -> str:
        if self.client:
            return f"Client: {self.client.name}"
        elif self.agency:
            return f"Agency: {self.agency.name}"
        elif self.admin_view:
            return "Admin View (All Data)"
        return "Unknown Scope"


@dataclass
class ValidationResult:
    """Result of data validation checks."""
    is_valid: bool
    warnings: List[str]
    errors: List[str]
    duplicate_records: List[int]
    inconsistencies: List[str]
    
    def add_warning(self, message: str) -> None:
        """Add a warning message."""
        self.warnings.append(message)
        logger.warning(f"Data validation warning: {message}")
    
    def add_error(self, message: str) -> None:
        """Add an error message."""
        self.errors.append(message)
        self.is_valid = False
        logger.error(f"Data validation error: {message}")
    
    def add_duplicates(self, record_ids: List[int]) -> None:
        """Add duplicate record IDs."""
        self.duplicate_records.extend(record_ids)
        if record_ids:
            self.add_warning(f"Found {len(record_ids)} duplicate records")
    
    def add_inconsistency(self, message: str) -> None:
        """Add an inconsistency message."""
        self.inconsistencies.append(message)
        self.add_warning(f"Data inconsistency: {message}")


class MetricsDataLayer:
    """
    Unified data layer for accessing and validating analytics data.
    
    This class provides standardized methods for accessing HashtagAnalytics data
    with proper filtering, validation, and duplicate detection.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def get_raw_analytics(
        self,
        scope: Optional[MetricsScope] = None,
        period: Optional[DateRange] = None,
        networks: Optional[List[str]] = None,
        include_manual: bool = True,
        include_automatic: bool = True,
        hashtags: Optional[List[str]] = None
    ) -> QuerySet[HashtagAnalytics]:
        """
        Get raw analytics data with standardized filtering.
        
        Args:
            scope: Metrics scope (client, agency, or admin)
            period: Date range for filtering
            networks: List of social networks to include
            include_manual: Whether to include manual analytics
            include_automatic: Whether to include automatic analytics
            hashtags: List of specific hashtags to filter by
            
        Returns:
            QuerySet of HashtagAnalytics objects
        """
        self.logger.info(f"Getting raw analytics for scope: {scope}, period: {period}")
        
        # Start with base queryset
        queryset = HashtagAnalytics.objects.select_related('client', 'created_by')
        
        # Apply scope filtering
        if scope:
            scope_filters = scope.get_filter_kwargs()
            if scope_filters:
                queryset = queryset.filter(**scope_filters)
                self.logger.debug(f"Applied scope filters: {scope_filters}")
        
        # Apply period filtering
        if period and not period.is_all_time():
            period_filters = period.to_filter_kwargs()
            queryset = queryset.filter(**period_filters)
            self.logger.debug(f"Applied period filters: {period_filters}")
        
        # Apply network filtering
        if networks:
            queryset = queryset.filter(social_network__in=networks)
            self.logger.debug(f"Applied network filters: {networks}")
        
        # Apply hashtag filtering
        if hashtags:
            queryset = queryset.filter(hashtag__in=hashtags)
            self.logger.debug(f"Applied hashtag filters: {hashtags}")
        
        # Apply manual/automatic filtering
        data_type_filters = []
        if include_manual:
            data_type_filters.append(Q(is_manual=True))
        if include_automatic:
            data_type_filters.append(Q(is_manual=False))
        
        if data_type_filters:
            # Combine with OR
            combined_filter = data_type_filters[0]
            for filter_q in data_type_filters[1:]:
                combined_filter |= filter_q
            queryset = queryset.filter(combined_filter)
            self.logger.debug(f"Applied data type filters: manual={include_manual}, automatic={include_automatic}")
        else:
            # If neither manual nor automatic is included, return empty queryset
            queryset = queryset.none()
            self.logger.warning("Neither manual nor automatic data requested, returning empty queryset")
        
        # Order by creation date for consistency
        queryset = queryset.order_by('-created_at', 'id')
        
        count = queryset.count()
        self.logger.info(f"Retrieved {count} analytics records")
        
        return queryset
    
    def get_data_sources_info(self, queryset: QuerySet[HashtagAnalytics]) -> Dict[str, Any]:
        """
        Get information about data sources in the queryset.
        
        Args:
            queryset: QuerySet to analyze
            
        Returns:
            Dictionary with data source information
        """
        manual_count = queryset.filter(is_manual=True).count()
        automatic_count = queryset.filter(is_manual=False).count()
        
        networks = list(queryset.values_list('social_network', flat=True).distinct())
        clients = list(queryset.filter(client__isnull=False).values_list('client__name', flat=True).distinct())
        
        date_range = queryset.aggregate(
            earliest=Min('created_at'),
            latest=Max('created_at')
        )
        
        return {
            'total_records': queryset.count(),
            'manual_records': manual_count,
            'automatic_records': automatic_count,
            'networks': networks,
            'clients': clients,
            'date_range': {
                'earliest': date_range['earliest'],
                'latest': date_range['latest']
            }
        }
    
    def validate_data_consistency(self, queryset: QuerySet[HashtagAnalytics]) -> ValidationResult:
        """
        Validate data consistency and detect potential issues.
        
        Args:
            queryset: QuerySet to validate
            
        Returns:
            ValidationResult with findings
        """
        result = ValidationResult(
            is_valid=True,
            warnings=[],
            errors=[],
            duplicate_records=[],
            inconsistencies=[]
        )
        
        self.logger.info(f"Validating data consistency for {queryset.count()} records")
        
        # Check for basic data integrity
        self._validate_basic_integrity(queryset, result)
        
        # Check for duplicates
        self._detect_duplicates(queryset, result)
        
        # Check for data inconsistencies
        self._validate_data_relationships(queryset, result)
        
        # Check for missing required fields
        self._validate_required_fields(queryset, result)
        
        self.logger.info(f"Validation complete: valid={result.is_valid}, "
                        f"warnings={len(result.warnings)}, errors={len(result.errors)}")
        
        return result
    
    def detect_duplicates(
        self,
        queryset: QuerySet[HashtagAnalytics],
        criteria: Optional[List[str]] = None
    ) -> Dict[str, List[int]]:
        """
        Detect duplicate records based on specified criteria.
        
        Args:
            queryset: QuerySet to check for duplicates
            criteria: List of field names to use for duplicate detection.
                     If None, uses default criteria based on record type.
        
        Returns:
            Dictionary mapping duplicate group keys to lists of record IDs
        """
        self.logger.info(f"Detecting duplicates in {queryset.count()} records")
        
        if criteria is None:
            # Use different criteria for manual vs automatic records
            manual_criteria = ['client', 'hashtag', 'social_network', 'period_start', 'period_end']
            automatic_criteria = ['hashtag', 'social_network', 'created_at__date']
        else:
            manual_criteria = automatic_criteria = criteria
        
        duplicates = {}
        
        # Check manual records
        manual_records = queryset.filter(is_manual=True)
        if manual_records.exists():
            manual_duplicates = self._find_duplicates_by_criteria(manual_records, manual_criteria)
            duplicates.update({f"manual_{k}": v for k, v in manual_duplicates.items()})
        
        # Check automatic records
        automatic_records = queryset.filter(is_manual=False)
        if automatic_records.exists():
            auto_duplicates = self._find_duplicates_by_criteria(automatic_records, automatic_criteria)
            duplicates.update({f"automatic_{k}": v for k, v in auto_duplicates.items()})
        
        total_duplicates = sum(len(ids) for ids in duplicates.values())
        self.logger.info(f"Found {len(duplicates)} duplicate groups with {total_duplicates} total records")
        
        return duplicates
    
    def resolve_duplicates(
        self,
        queryset: QuerySet[HashtagAnalytics],
        strategy: str = 'keep_latest',
        dry_run: bool = True
    ) -> Dict[str, Any]:
        """
        Resolve duplicate records using the specified strategy.
        
        Args:
            queryset: QuerySet containing duplicates to resolve
            strategy: Resolution strategy ('keep_latest', 'keep_first', 'merge')
            dry_run: If True, only simulate the resolution without making changes
        
        Returns:
            Dictionary with resolution results
        """
        self.logger.info(f"Resolving duplicates with strategy '{strategy}', dry_run={dry_run}")
        
        duplicates = self.detect_duplicates(queryset)
        
        if not duplicates:
            return {
                'resolved_groups': 0,
                'records_removed': 0,
                'records_merged': 0,
                'actions': []
            }
        
        actions = []
        records_removed = 0
        records_merged = 0
        
        for group_key, record_ids in duplicates.items():
            if len(record_ids) <= 1:
                continue
            
            group_records = queryset.filter(id__in=record_ids).order_by('-created_at', 'id')
            
            if strategy == 'keep_latest':
                action = self._resolve_keep_latest(group_records, dry_run)
            elif strategy == 'keep_first':
                action = self._resolve_keep_first(group_records, dry_run)
            elif strategy == 'merge':
                action = self._resolve_merge(group_records, dry_run)
            else:
                raise ValueError(f"Unknown resolution strategy: {strategy}")
            
            actions.append(action)
            records_removed += action.get('records_removed', 0)
            records_merged += action.get('records_merged', 0)
        
        result = {
            'resolved_groups': len([a for a in actions if a.get('success', False)]),
            'records_removed': records_removed,
            'records_merged': records_merged,
            'actions': actions
        }
        
        self.logger.info(f"Resolution complete: {result}")
        return result
    
    def _find_duplicates_by_criteria(
        self,
        queryset: QuerySet[HashtagAnalytics],
        criteria: List[str]
    ) -> Dict[str, List[int]]:
        """Find duplicates based on specified criteria."""
        from django.db.models import Count
        
        # Handle date truncation for created_at__date
        values_criteria = []
        for criterion in criteria:
            if criterion == 'created_at__date':
                values_criteria.append('created_at__date')
            else:
                values_criteria.append(criterion)
        
        # Group by criteria and find groups with more than one record
        duplicate_groups = (
            queryset
            .values(*values_criteria)
            .annotate(count=Count('id'))
            .filter(count__gt=1)
        )
        
        duplicates = {}
        for group in duplicate_groups:
            # Create filter kwargs from the group
            filter_kwargs = {k: v for k, v in group.items() if k != 'count'}
            
            # Get all record IDs in this group
            group_records = queryset.filter(**filter_kwargs).values_list('id', flat=True)
            
            # Create a key for this duplicate group
            key_parts = [f"{k}={v}" for k, v in filter_kwargs.items()]
            group_key = "|".join(key_parts)
            
            duplicates[group_key] = list(group_records)
        
        return duplicates
    
    def _resolve_keep_latest(
        self,
        group_records: QuerySet[HashtagAnalytics],
        dry_run: bool
    ) -> Dict[str, Any]:
        """Resolve duplicates by keeping the latest record."""
        records_list = list(group_records)
        if len(records_list) <= 1:
            return {'success': False, 'reason': 'No duplicates to resolve'}
        
        # Keep the first record (latest due to ordering)
        keep_record = records_list[0]
        remove_records = records_list[1:]
        
        action = {
            'strategy': 'keep_latest',
            'group_size': len(records_list),
            'kept_record_id': keep_record.id,
            'removed_record_ids': [r.id for r in remove_records],
            'records_removed': len(remove_records),
            'dry_run': dry_run,
            'success': True
        }
        
        if not dry_run:
            # Actually remove the duplicate records
            for record in remove_records:
                self.logger.info(f"Removing duplicate record {record.id}")
                record.delete()
        
        return action
    
    def _resolve_keep_first(
        self,
        group_records: QuerySet[HashtagAnalytics],
        dry_run: bool
    ) -> Dict[str, Any]:
        """Resolve duplicates by keeping the first record."""
        records_list = list(group_records.order_by('created_at', 'id'))
        if len(records_list) <= 1:
            return {'success': False, 'reason': 'No duplicates to resolve'}
        
        # Keep the first record (earliest)
        keep_record = records_list[0]
        remove_records = records_list[1:]
        
        action = {
            'strategy': 'keep_first',
            'group_size': len(records_list),
            'kept_record_id': keep_record.id,
            'removed_record_ids': [r.id for r in remove_records],
            'records_removed': len(remove_records),
            'dry_run': dry_run,
            'success': True
        }
        
        if not dry_run:
            # Actually remove the duplicate records
            for record in remove_records:
                self.logger.info(f"Removing duplicate record {record.id}")
                record.delete()
        
        return action
    
    def _resolve_merge(
        self,
        group_records: QuerySet[HashtagAnalytics],
        dry_run: bool
    ) -> Dict[str, Any]:
        """Resolve duplicates by merging data into the latest record."""
        records_list = list(group_records)
        if len(records_list) <= 1:
            return {'success': False, 'reason': 'No duplicates to resolve'}
        
        # Use the latest record as the base
        base_record = records_list[0]
        merge_records = records_list[1:]
        
        # Merge numeric fields by summing
        numeric_fields = [
            'total_views', 'total_likes', 'total_comments', 'total_shares',
            'total_followers', 'analyzed_medias', 'fetched_medias',
            'instagram_stories_views', 'instagram_reels_views',
            'youtube_subscribers', 'youtube_watch_time',
            'tiktok_video_views', 'tiktok_profile_views'
        ]
        
        merged_values = {}
        for field in numeric_fields:
            total = getattr(base_record, field, 0) or 0
            for record in merge_records:
                total += getattr(record, field, 0) or 0
            merged_values[field] = total
        
        # Recalculate derived fields
        if merged_values['total_views'] > 0:
            merged_values['engagement_rate'] = (
                (merged_values['total_likes'] + merged_values['total_comments']) 
                / merged_values['total_views']
            ) * 100
            merged_values['average_views'] = merged_values['total_views'] / max(merged_values['analyzed_medias'], 1)
        
        action = {
            'strategy': 'merge',
            'group_size': len(records_list),
            'base_record_id': base_record.id,
            'merged_record_ids': [r.id for r in merge_records],
            'records_removed': len(merge_records),
            'records_merged': 1,
            'merged_values': merged_values,
            'dry_run': dry_run,
            'success': True
        }
        
        if not dry_run:
            # Update the base record with merged values
            for field, value in merged_values.items():
                setattr(base_record, field, value)
            base_record.save()
            
            # Remove the merged records
            for record in merge_records:
                self.logger.info(f"Removing merged record {record.id}")
                record.delete()
        
        return action
    
    def _validate_basic_integrity(self, queryset: QuerySet[HashtagAnalytics], result: ValidationResult) -> None:
        """Validate basic data integrity."""
        # Check for negative values
        negative_views = queryset.filter(total_views__lt=0).count()
        if negative_views > 0:
            result.add_error(f"Found {negative_views} records with negative total_views")
        
        negative_likes = queryset.filter(total_likes__lt=0).count()
        if negative_likes > 0:
            result.add_error(f"Found {negative_likes} records with negative total_likes")
        
        # Check for unrealistic engagement rates
        high_engagement = queryset.filter(engagement_rate__gt=100).count()
        if high_engagement > 0:
            result.add_warning(f"Found {high_engagement} records with engagement rate > 100%")
    
    def _detect_duplicates(self, queryset: QuerySet[HashtagAnalytics], result: ValidationResult) -> None:
        """Detect potential duplicate records."""
        # For manual analytics, check for duplicates by client, hashtag, social_network, and period
        manual_records = queryset.filter(is_manual=True)
        
        # Group by potential duplicate criteria
        from django.db.models import Count
        
        duplicates = (
            manual_records
            .values('client', 'hashtag', 'social_network', 'period_start', 'period_end')
            .annotate(count=Count('id'))
            .filter(count__gt=1)
        )
        
        duplicate_ids = []
        for dup_group in duplicates:
            # Get all records in this duplicate group
            group_records = manual_records.filter(
                client=dup_group['client'],
                hashtag=dup_group['hashtag'],
                social_network=dup_group['social_network'],
                period_start=dup_group['period_start'],
                period_end=dup_group['period_end']
            ).values_list('id', flat=True)
            
            duplicate_ids.extend(list(group_records))
        
        if duplicate_ids:
            result.add_duplicates(duplicate_ids)
    
    def _validate_data_relationships(self, queryset: QuerySet[HashtagAnalytics], result: ValidationResult) -> None:
        """Validate relationships between data fields."""
        # Check if engagement rate matches calculated value
        inconsistent_engagement = 0
        for record in queryset.filter(total_views__gt=0)[:100]:  # Sample check
            if record.total_views > 0:
                calculated_rate = ((record.total_likes + record.total_comments) / record.total_views) * 100
                if abs(calculated_rate - record.engagement_rate) > 1.0:  # Allow 1% tolerance
                    inconsistent_engagement += 1
        
        if inconsistent_engagement > 0:
            result.add_inconsistency(f"Found {inconsistent_engagement} records with inconsistent engagement rates")
        
        # Check for manual records without clients
        manual_without_client = queryset.filter(is_manual=True, client__isnull=True).count()
        if manual_without_client > 0:
            result.add_inconsistency(f"Found {manual_without_client} manual records without associated client")
    
    def _validate_required_fields(self, queryset: QuerySet[HashtagAnalytics], result: ValidationResult) -> None:
        """Validate required fields are present."""
        # Check for empty hashtags
        empty_hashtags = queryset.filter(hashtag__isnull=True).count() + queryset.filter(hashtag='').count()
        if empty_hashtags > 0:
            result.add_error(f"Found {empty_hashtags} records with empty hashtags")
        
        # Check for manual records without period information
        manual_no_period = queryset.filter(
            is_manual=True,
            period_start__isnull=True,
            period_end__isnull=True
        ).count()
        if manual_no_period > 0:
            result.add_warning(f"Found {manual_no_period} manual records without period information")
    
    def validate_data_quality(
        self,
        queryset: QuerySet[HashtagAnalytics],
        include_detailed_checks: bool = True
    ) -> ValidationResult:
        """
        Comprehensive data quality validation with detailed checks.
        
        Args:
            queryset: QuerySet to validate
            include_detailed_checks: Whether to perform detailed validation checks
        
        Returns:
            ValidationResult with comprehensive findings
        """
        result = ValidationResult(
            is_valid=True,
            warnings=[],
            errors=[],
            duplicate_records=[],
            inconsistencies=[]
        )
        
        self.logger.info(f"Starting comprehensive data quality validation for {queryset.count()} records")
        
        # Basic validation (always performed)
        self.validate_data_consistency(queryset)
        
        if include_detailed_checks:
            # Advanced validation checks
            self._validate_business_rules(queryset, result)
            self._validate_data_completeness(queryset, result)
            self._validate_temporal_consistency(queryset, result)
            self._validate_cross_field_relationships(queryset, result)
            self._validate_statistical_outliers(queryset, result)
        
        # Generate data quality score
        quality_score = self._calculate_quality_score(result, queryset.count())
        result.quality_score = quality_score
        
        self.logger.info(f"Data quality validation complete. Score: {quality_score:.2f}/100")
        
        return result
    
    def _validate_business_rules(self, queryset: QuerySet[HashtagAnalytics], result: ValidationResult) -> None:
        """Validate business logic rules."""
        # Rule: Manual records should have associated clients
        manual_without_client = queryset.filter(is_manual=True, client__isnull=True).count()
        if manual_without_client > 0:
            result.add_error(f"Business rule violation: {manual_without_client} manual records without clients")
        
        # Rule: Engagement rate should be reasonable (0-100%)
        invalid_engagement = queryset.filter(
            Q(engagement_rate__lt=0) | Q(engagement_rate__gt=100)
        ).count()
        if invalid_engagement > 0:
            result.add_warning(f"Business rule warning: {invalid_engagement} records with invalid engagement rates")
        
        # Rule: Views should be >= likes + comments for engagement calculation
        inconsistent_engagement = 0
        for record in queryset.filter(total_views__gt=0, engagement_rate__gt=0)[:50]:  # Sample check
            min_views_needed = record.total_likes + record.total_comments
            if record.total_views < min_views_needed:
                inconsistent_engagement += 1
        
        if inconsistent_engagement > 0:
            result.add_inconsistency(f"Found {inconsistent_engagement} records where views < likes + comments")
        
        # Rule: Follower growth rate should be reasonable (-100% to +1000%)
        extreme_growth = queryset.filter(
            Q(growth_rate__lt=-100) | Q(growth_rate__gt=1000)
        ).count()
        if extreme_growth > 0:
            result.add_warning(f"Found {extreme_growth} records with extreme growth rates")
    
    def _validate_data_completeness(self, queryset: QuerySet[HashtagAnalytics], result: ValidationResult) -> None:
        """Validate data completeness."""
        total_records = queryset.count()
        if total_records == 0:
            return
        
        # Check for missing core metrics
        missing_views = queryset.filter(total_views=0).count()
        if missing_views > total_records * 0.5:  # More than 50% missing
            result.add_warning(f"Data completeness issue: {missing_views}/{total_records} records have zero views")
        
        # Check for missing engagement data
        missing_engagement = queryset.filter(total_likes=0, total_comments=0).count()
        if missing_engagement > total_records * 0.3:  # More than 30% missing
            result.add_warning(f"Data completeness issue: {missing_engagement}/{total_records} records have no engagement data")
        
        # Check for missing hashtags
        missing_hashtags = queryset.filter(Q(hashtag__isnull=True) | Q(hashtag='')).count()
        if missing_hashtags > 0:
            result.add_error(f"Data completeness error: {missing_hashtags} records have missing hashtags")
        
        # Check manual records for missing period information
        manual_records = queryset.filter(is_manual=True)
        if manual_records.exists():
            missing_periods = manual_records.filter(
                period_start__isnull=True,
                period_end__isnull=True
            ).count()
            if missing_periods > 0:
                result.add_warning(f"Data completeness issue: {missing_periods} manual records missing period information")
    
    def _validate_temporal_consistency(self, queryset: QuerySet[HashtagAnalytics], result: ValidationResult) -> None:
        """Validate temporal data consistency."""
        # Check for future dates
        from django.utils import timezone
        now = timezone.now()
        
        future_records = queryset.filter(created_at__gt=now).count()
        if future_records > 0:
            result.add_error(f"Temporal error: {future_records} records have future creation dates")
        
        # Check for invalid period ranges in manual records
        invalid_periods = queryset.filter(
            is_manual=True,
            period_start__isnull=False,
            period_end__isnull=False,
            period_start__gt=F('period_end')
        ).count()
        if invalid_periods > 0:
            result.add_error(f"Temporal error: {invalid_periods} records have period_start > period_end")
        
        # Check for very old records (might indicate data import issues)
        from datetime import timedelta
        very_old_threshold = now - timedelta(days=365 * 3)  # 3 years
        very_old_records = queryset.filter(created_at__lt=very_old_threshold).count()
        if very_old_records > 0:
            result.add_warning(f"Temporal warning: {very_old_records} records are older than 3 years")
    
    def _validate_cross_field_relationships(self, queryset: QuerySet[HashtagAnalytics], result: ValidationResult) -> None:
        """Validate relationships between different fields."""
        # Check average_views calculation
        incorrect_avg_views = 0
        for record in queryset.filter(analyzed_medias__gt=0, total_views__gt=0)[:100]:  # Sample
            expected_avg = record.total_views / record.analyzed_medias
            if abs(expected_avg - record.average_views) > expected_avg * 0.1:  # 10% tolerance
                incorrect_avg_views += 1
        
        if incorrect_avg_views > 0:
            result.add_inconsistency(f"Found {incorrect_avg_views} records with incorrect average_views calculation")
        
        # Check engagement rate calculation
        incorrect_engagement = 0
        for record in queryset.filter(total_views__gt=0)[:100]:  # Sample
            expected_rate = ((record.total_likes + record.total_comments) / record.total_views) * 100
            if abs(expected_rate - record.engagement_rate) > 1.0:  # 1% tolerance
                incorrect_engagement += 1
        
        if incorrect_engagement > 0:
            result.add_inconsistency(f"Found {incorrect_engagement} records with incorrect engagement_rate calculation")
        
        # Check for logical inconsistencies
        impossible_ratios = queryset.filter(
            total_likes__gt=F('total_views')
        ).count()
        if impossible_ratios > 0:
            result.add_error(f"Logical error: {impossible_ratios} records have more likes than views")
    
    def _validate_statistical_outliers(self, queryset: QuerySet[HashtagAnalytics], result: ValidationResult) -> None:
        """Detect statistical outliers that might indicate data quality issues."""
        if queryset.count() < 10:  # Need sufficient data for statistical analysis
            return
        
        from django.db.models import Avg, StdDev
        
        # Calculate statistics for key metrics
        stats = queryset.aggregate(
            avg_views=Avg('total_views'),
            stddev_views=StdDev('total_views'),
            avg_engagement=Avg('engagement_rate'),
            stddev_engagement=StdDev('engagement_rate')
        )
        
        if stats['stddev_views'] and stats['avg_views']:
            # Find extreme outliers (more than 3 standard deviations from mean)
            outlier_threshold = stats['avg_views'] + (3 * stats['stddev_views'])
            extreme_outliers = queryset.filter(total_views__gt=outlier_threshold).count()
            
            if extreme_outliers > 0:
                result.add_warning(f"Statistical outliers: {extreme_outliers} records with extremely high views")
        
        # Check for suspiciously round numbers (might indicate manual entry errors)
        round_numbers = queryset.filter(
            total_views__in=[1000000, 5000000, 10000000, 50000000, 100000000]
        ).count()
        if round_numbers > queryset.count() * 0.1:  # More than 10%
            result.add_warning(f"Suspicious data: {round_numbers} records with suspiciously round view counts")
    
    def _calculate_quality_score(self, result: ValidationResult, total_records: int) -> float:
        """Calculate an overall data quality score (0-100)."""
        if total_records == 0:
            return 0.0
        
        score = 100.0
        
        # Deduct points for errors (more severe)
        score -= len(result.errors) * 10
        
        # Deduct points for warnings (less severe)
        score -= len(result.warnings) * 3
        
        # Deduct points for inconsistencies
        score -= len(result.inconsistencies) * 5
        
        # Deduct points for duplicates (based on percentage)
        if result.duplicate_records:
            duplicate_percentage = len(result.duplicate_records) / total_records * 100
            score -= duplicate_percentage * 2
        
        # Ensure score doesn't go below 0
        return max(0.0, score)
    
    def generate_data_quality_report(
        self,
        queryset: QuerySet[HashtagAnalytics],
        scope: Optional[MetricsScope] = None
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive data quality report.
        
        Args:
            queryset: QuerySet to analyze
            scope: Metrics scope for context
        
        Returns:
            Dictionary with comprehensive data quality report
        """
        self.logger.info("Generating comprehensive data quality report")
        
        # Perform validation
        validation_result = self.validate_data_quality(queryset, include_detailed_checks=True)
        
        # Get data sources info
        sources_info = self.get_data_sources_info(queryset)
        
        # Detect duplicates
        duplicates = self.detect_duplicates(queryset)
        
        # Generate summary statistics
        from django.db.models import Avg, Sum, Count, Min, Max
        summary_stats = queryset.aggregate(
            total_records=Count('id'),
            total_views=Sum('total_views'),
            total_likes=Sum('total_likes'),
            total_comments=Sum('total_comments'),
            avg_engagement=Avg('engagement_rate'),
            min_date=Min('created_at'),
            max_date=Max('created_at')
        )
        
        report = {
            'scope': str(scope) if scope else "All Data",
            'generated_at': timezone.now().isoformat(),
            'summary_statistics': summary_stats,
            'data_sources': sources_info,
            'validation_result': {
                'quality_score': getattr(validation_result, 'quality_score', 0),
                'is_valid': validation_result.is_valid,
                'error_count': len(validation_result.errors),
                'warning_count': len(validation_result.warnings),
                'inconsistency_count': len(validation_result.inconsistencies),
                'duplicate_count': len(validation_result.duplicate_records),
                'errors': validation_result.errors,
                'warnings': validation_result.warnings,
                'inconsistencies': validation_result.inconsistencies
            },
            'duplicate_analysis': {
                'duplicate_groups': len(duplicates),
                'total_duplicates': sum(len(ids) for ids in duplicates.values()),
                'groups': duplicates
            },
            'recommendations': self._generate_recommendations(validation_result, duplicates)
        }
        
        self.logger.info(f"Data quality report generated. Quality score: {report['validation_result']['quality_score']:.2f}")
        
        return report
    
    def _generate_recommendations(
        self,
        validation_result: ValidationResult,
        duplicates: Dict[str, List[int]]
    ) -> List[str]:
        """Generate actionable recommendations based on validation results."""
        recommendations = []
        
        if validation_result.errors:
            recommendations.append("🔴 Critical: Fix data errors before using metrics for decision making")
        
        if duplicates:
            recommendations.append(f"🟡 Resolve {len(duplicates)} duplicate groups to improve data accuracy")
        
        if validation_result.warnings:
            recommendations.append("🟡 Review and address data quality warnings")
        
        if validation_result.inconsistencies:
            recommendations.append("🟡 Investigate data inconsistencies to ensure calculation accuracy")
        
        quality_score = getattr(validation_result, 'quality_score', 0)
        if quality_score < 70:
            recommendations.append("🔴 Data quality score is low - comprehensive cleanup recommended")
        elif quality_score < 85:
            recommendations.append("🟡 Data quality could be improved - targeted fixes recommended")
        else:
            recommendations.append("🟢 Data quality is good - continue monitoring")
        
        if not recommendations:
            recommendations.append("🟢 No major data quality issues detected")
        
        return recommendations