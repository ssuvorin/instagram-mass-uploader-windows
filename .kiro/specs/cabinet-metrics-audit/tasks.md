# Implementation Plan

- [x] 1. Create unified data layer for metrics
  - Create MetricsDataLayer class with standardized data access methods
  - Implement data validation and duplicate detection
  - Add comprehensive logging for data quality issues
  - _Requirements: 1.1, 1.4, 4.1, 4.3_

- [x] 1.1 Implement MetricsDataLayer base class
  - Write MetricsDataLayer class with get_raw_analytics method
  - Add proper filtering by client, agency, time period, and networks
  - Implement data source tracking and validation
  - _Requirements: 1.1, 1.4, 4.1_

- [x] 1.2 Add duplicate detection and resolution
  - Implement detect_duplicates method to find duplicate records
  - Add logic to resolve duplicates by keeping latest or merging data
  - Create validation methods for data consistency checks
  - _Requirements: 1.1, 1.5, 4.4_

- [x] 1.3 Implement comprehensive data validation
  - Add validate_data_consistency method with detailed checks
  - Implement warnings for potential data quality issues
  - Add logging for all validation results and data quality metrics
  - _Requirements: 1.1, 4.3, 4.4, 5.5_

- [x] 2. Create metrics calculation engine
  - Implement MetricsCalculationEngine with standardized calculation methods
  - Add methods for calculating totals, averages, and engagement rates
  - Ensure consistent calculation logic across all components
  - _Requirements: 1.2, 4.1, 4.2, 5.1_

- [x] 2.1 Implement core calculation methods
  - Write calculate_network_metrics method for per-network calculations
  - Add calculate_time_series method for temporal data analysis
  - Implement calculate_engagement_rates with proper formulas
  - _Requirements: 1.2, 4.1, 5.1, 5.2_

- [x] 2.2 Add advanced metrics calculations
  - Implement calculate_growth_rates method for follower growth analysis
  - Add calculate_account_level_metrics for account-based statistics
  - Create calculate_platform_specific_metrics for platform features
  - _Requirements: 1.2, 3.2, 4.1, 5.1_

- [x] 2.3 Implement aggregation logic with duplicate prevention
  - Create aggregate_by_network method that prevents double counting
  - Add aggregate_by_time_period method with proper time filtering
  - Implement aggregate_by_client method for agency-level aggregation
  - _Requirements: 1.1, 1.5, 2.4, 4.1_

- [x] 3. Refactor AnalyticsService to use unified components
  - Update existing AnalyticsService to use MetricsDataLayer
  - Replace custom calculation logic with MetricsCalculationEngine
  - Ensure backward compatibility with existing API
  - _Requirements: 1.2, 2.1, 3.1, 4.2_

- [x] 3.1 Update get_manual_analytics_by_network method
  - Refactor to use MetricsDataLayer for data access
  - Fix duplicate data issues in Instagram analytics combination
  - Add proper validation and error handling
  - _Requirements: 1.1, 1.4, 3.4, 4.2_

- [x] 3.2 Fix get_combined_analytics_summary method
  - Remove duplicate Instagram data aggregation
  - Use MetricsCalculationEngine for consistent calculations
  - Add data source tracking and validation
  - _Requirements: 1.1, 1.5, 3.4, 4.2_

- [x] 3.3 Update time-based analytics methods
  - Fix get_daily_stats to prevent duplicate counting
  - Update get_weekly_stats with consistent aggregation logic
  - Add proper time period validation and filtering
  - _Requirements: 1.2, 2.3, 3.3, 4.1_

- [ ] 4. Update dashboard views to use unified service
  - Refactor admin_dashboard view to use consistent metrics calculation
  - Update agency_dashboard view to prevent client data duplication
  - Fix client_dashboard view to show accurate individual metrics
  - _Requirements: 1.1, 1.2, 2.1, 2.2, 3.1_

- [ ] 4.1 Fix admin_dashboard metrics consistency
  - Update daily stats calculation to use unified aggregation
  - Fix agencies_rows calculation to prevent duplicate counting
  - Ensure clients_rows shows accurate per-client metrics
  - _Requirements: 1.1, 1.2, 1.3, 4.2_

- [ ] 4.2 Correct agency_dashboard aggregation logic
  - Fix client_rows calculation to show accurate individual client metrics
  - Update hashtags_breakdown to prevent duplicate hashtag counting
  - Ensure accounts_analytics shows correct account-level data
  - _Requirements: 2.1, 2.2, 2.4, 4.2_

- [ ] 4.3 Improve client_dashboard data accuracy
  - Fix network_breakdown to show correct per-network metrics
  - Update combined_summary to prevent data source mixing
  - Ensure daily and weekly stats are calculated consistently
  - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [ ] 5. Add data quality indicators and user feedback
  - Add data quality indicators to dashboard displays
  - Implement tooltips explaining calculation methods
  - Add warnings for potential data inconsistencies
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [ ] 5.1 Implement data quality indicators
  - Add visual indicators for data quality status on dashboards
  - Show data source information for each metric
  - Display validation warnings and data quality scores
  - _Requirements: 5.1, 5.3, 5.5_

- [ ] 5.2 Add calculation method explanations
  - Implement tooltips with formula explanations for key metrics
  - Add help text explaining data sources and calculation periods
  - Create documentation links for complex metrics
  - _Requirements: 5.1, 5.2, 5.4_

- [ ] 5.3 Improve error handling and user notifications
  - Add user-friendly error messages for data quality issues
  - Implement warnings for incomplete or inconsistent data
  - Add notifications when data is being recalculated or updated
  - _Requirements: 1.3, 5.5, 4.3_

- [ ] 6. Update export functionality for consistency
  - Fix export_excel to use unified metrics calculation
  - Ensure exported data matches dashboard displays
  - Add data quality information to exports
  - _Requirements: 1.3, 4.2, 5.3_

- [ ] 6.1 Refactor export_excel method
  - Update all export sheets to use MetricsDataLayer for data access
  - Fix aggregation logic to prevent duplicate counting in exports
  - Add data quality and source information to exported files
  - _Requirements: 1.3, 4.2, 5.3_

- [ ] 6.2 Add export validation and consistency checks
  - Implement validation that exported data matches UI displays
  - Add checksums or totals validation in exported files
  - Include calculation metadata and data source information
  - _Requirements: 1.3, 4.4, 5.3_

- [ ] 7. Implement comprehensive testing and validation
  - Create unit tests for all new calculation methods
  - Add integration tests comparing old vs new metrics
  - Implement automated data quality monitoring
  - _Requirements: 1.1, 1.2, 4.4, 5.5_

- [ ] 7.1 Create unit tests for metrics calculations
  - Write tests for MetricsDataLayer methods with various data scenarios
  - Add tests for MetricsCalculationEngine with edge cases
  - Test duplicate detection and resolution logic thoroughly
  - _Requirements: 1.1, 1.5, 4.4_

- [ ] 7.2 Add integration tests for dashboard consistency
  - Test that all dashboard views show consistent metrics for same periods
  - Validate that export data matches dashboard displays
  - Test metrics consistency across different user roles and permissions
  - _Requirements: 1.2, 1.3, 2.1, 3.1_

- [ ] 7.3 Implement automated data quality monitoring
  - Create scheduled tasks to validate data quality regularly
  - Add alerts for significant data inconsistencies or duplicates
  - Implement metrics comparison between old and new calculation methods
  - _Requirements: 1.5, 4.3, 5.5_

- [ ] 8. Performance optimization and monitoring
  - Optimize database queries for metrics calculation
  - Add caching for frequently accessed metrics
  - Implement performance monitoring for calculation methods
  - _Requirements: 4.1, 4.2_

- [ ] 8.1 Optimize database queries and indexing
  - Add database indexes for frequently filtered fields
  - Optimize aggregation queries to reduce database load
  - Implement query result caching for expensive calculations
  - _Requirements: 4.1, 4.2_

- [ ] 8.2 Add performance monitoring and alerting
  - Implement timing metrics for all calculation methods
  - Add monitoring for slow queries and performance degradation
  - Create alerts for calculation performance issues
  - _Requirements: 4.3_