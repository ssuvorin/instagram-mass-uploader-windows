# Implementation Plan

- [ ] 0. Complete audit of hardcoded selectors across entire codebase
  - Scan all Python files for hardcoded text selectors using has-text(), contains(text()), and similar patterns
  - Document all found hardcoded selectors by file and function
  - Identify missing selector categories in SelectorConfig (crop, file selection, etc.)
  - Create comprehensive mapping of hardcoded selectors to centralized equivalents
  - Prioritize most critical selectors for immediate migration
  - _Requirements: 3.1, 3.2, 3.3_

- [x] 1. Enhance i18n resources with comprehensive selector text mappings
  - Create complete Spanish selector text mappings in es.json (including crop terms like "Original")
  - Create complete Portuguese selector text mappings in pt.json (including crop terms)
  - Add English selector text mappings in en.json for consistency
  - Add Russian selector text mappings in ru.json for completeness (including "Оригинал")
  - Add crop-related terms: original, square, portrait, landscape aspect ratios
  - Add file selection terms: "Seleccionar desde el ordenador", "Selecionar do computador"
  - _Requirements: 1.1, 2.1, 6.2, 6.3_

- [ ] 2. Implement LocaleResolver component
  - Create LocaleResolver class with account locale resolution logic
  - Implement resolve_account_locale method to extract locale from account objects
  - Implement get_language_priority method for fallback chain generation
  - Add unit tests for locale resolution edge cases
  - _Requirements: 4.1, 4.2, 6.2_

- [ ] 3. Create SelectorResult and SelectorMetrics data models
  - Define SelectorResult dataclass with success metadata
  - Define SelectorMetrics dataclass for performance tracking
  - Add serialization methods for logging and monitoring
  - Create factory methods for common result types
  - _Requirements: 5.1, 5.2, 5.3_

- [x] 4. Implement MultilingualSelectorProvider core functionality
  - Create MultilingualSelectorProvider class with i18n integration
  - Implement get_selectors method with locale-aware generation
  - Implement _generate_text_selectors method using i18n templates
  - Implement _get_fallback_chain method for language priority
  - Add selector caching mechanism for performance
  - _Requirements: 3.1, 3.2, 4.1, 4.2, 6.1_

- [ ] 5. Enhance SelectorConfig with template support and missing selector categories
  - Add TEXT_SELECTOR_TEMPLATES dictionary with i18n key placeholders
  - Add SEMANTIC_SELECTORS dictionary for language-independent selectors
  - Add CROP_SELECTORS section for aspect ratio and crop-related selectors
  - Add ORIGINAL_BUTTON_SELECTORS for "Оригинал"/"Original" buttons
  - Add FILE_SELECTION_SELECTORS for computer file selection buttons
  - Implement template rendering methods for dynamic selector generation
  - Maintain backward compatibility with existing static selectors
  - _Requirements: 3.1, 3.3, 4.3_

- [ ] 6. Implement SelectorErrorHandler for robust error handling
  - Create SelectorErrorHandler class with fallback strategies
  - Implement handle_selector_failure method for alternative selector generation
  - Implement log_selector_failure method with structured logging
  - Add retry logic with exponential backoff for transient failures
  - _Requirements: 4.2, 4.3, 5.4_

- [ ] 7. Create SelectorMetricsCollector for performance monitoring
  - Implement SelectorMetricsCollector class for metrics aggregation
  - Add record_selector_attempt method for individual attempt tracking
  - Add get_language_success_rates method for success rate analysis
  - Add get_fallback_usage_stats method for fallback pattern analysis
  - Implement metrics persistence for long-term monitoring
  - _Requirements: 5.1, 5.2, 5.3, 5.5_

- [x] 8. Update async_impl/utils_dom.py to use multilingual selectors
  - Replace hardcoded text selectors with MultilingualSelectorProvider calls
  - Update find_element_with_selectors_async to use locale-aware selectors
  - Add locale parameter to all selector-using functions
  - Implement fallback chain logic in element finding functions
  - _Requirements: 1.1, 2.1, 3.2, 4.1_

- [x] 9. Update async_impl/upload.py with multilingual selector support
  - Replace SelectorConfig direct usage with MultilingualSelectorProvider
  - Add locale resolution from account/task context
  - Update all upload workflow functions to use locale-aware selectors
  - Add comprehensive logging of selector attempts and results
  - _Requirements: 1.1, 2.1, 3.2, 5.1_

- [ ] 10. Update async_impl/login.py with multilingual selector support
  - Replace hardcoded login selectors with multilingual variants
  - Add locale-aware selector generation for login forms
  - Update authentication flow to handle Spanish/Portuguese interfaces
  - Add fallback logic for mixed-language login scenarios
  - _Requirements: 1.2, 2.2, 4.1, 4.2_

- [ ] 11. Update async_impl/file_input.py with multilingual selectors
  - Replace file input selectors with locale-aware variants
  - Add Spanish/Portuguese file selection button detection
  - Update file dialog detection with multilingual text patterns
  - Implement fallback chain for file input element finding
  - _Requirements: 1.1, 2.1, 4.2, 4.3_

- [ ] 12. Update async_impl/crop.py with multilingual selector support
  - Replace crop-related text selectors with multilingual variants
  - Add Spanish/Portuguese crop option detection
  - Update Reels dialog detection with multilingual text patterns
  - Implement locale-aware crop workflow navigation
  - _Requirements: 1.1, 2.1, 3.2_

- [ ] 13. Update selector_provider.py to use new multilingual system
  - Refactor BaseSelectorProvider to use MultilingualSelectorProvider
  - Remove hardcoded Spanish/Portuguese extras from individual methods
  - Add locale parameter to all selector getter methods
  - Maintain backward compatibility for existing usage
  - _Requirements: 3.1, 3.2, 3.3_

- [x] 14. Update bulk_tasks_playwright.py with multilingual selectors
  - Replace direct SelectorConfig usage with MultilingualSelectorProvider
  - Add locale resolution from account context in bulk tasks
  - Update cookie consent handling with multilingual selectors
  - Add comprehensive error handling and fallback logic
  - _Requirements: 1.1, 2.1, 3.2, 4.1_

- [ ] 15. Create comprehensive unit test suite
  - Write tests for LocaleResolver with various account types
  - Write tests for MultilingualSelectorProvider selector generation
  - Write tests for i18n integration and template rendering
  - Write tests for fallback chain logic and error handling
  - Write tests for SelectorMetricsCollector functionality
  - _Requirements: 5.1, 5.2, 5.3, 5.4_

- [ ] 16. Create integration test suite for multilingual workflows
  - Write end-to-end tests for Spanish Instagram interface automation
  - Write end-to-end tests for Portuguese Instagram interface automation
  - Write tests for mixed-language scenario handling
  - Write tests for fallback behavior in real browser environments
  - Add performance benchmarks for selector resolution
  - _Requirements: 1.1, 1.2, 2.1, 2.2, 4.1, 4.2_

- [ ] 17. Implement monitoring and logging infrastructure
  - Add structured logging for all selector attempts and results
  - Implement metrics collection and aggregation
  - Create monitoring dashboards for selector performance
  - Add alerting for high failure rates or performance degradation
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [ ] 19. Comprehensive migration of hardcoded selectors to centralized system
  - Migrate hardcoded selectors from crop_handler.py (Оригинал/Original buttons)
  - Migrate hardcoded selectors from async_impl/utils_dom.py (share buttons, crop selectors)
  - Migrate hardcoded selectors from async_impl/file_input.py (Russian text selectors)
  - Migrate hardcoded selectors from selector_provider.py (Spanish/Portuguese extras)
  - Replace all hardcoded text selectors with MultilingualSelectorProvider calls
  - Update all functions to use centralized multilingual selector system
  - Remove duplicate selector definitions across files
  - Verify all migrated selectors work correctly with fallback chains
  - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [ ] 20. Add developer documentation and guidelines
  - Create documentation for using MultilingualSelectorProvider
  - Add guidelines for adding new multilingual selectors
  - Document fallback chain behavior and troubleshooting
  - Create examples for common selector usage patterns
  - _Requirements: 3.4, 5.4_

- [ ] 21. Performance optimization and caching improvements
  - Optimize selector generation performance with caching
  - Implement intelligent cache invalidation strategies
  - Add batch selector generation for related elements
  - Optimize fallback chain execution order based on success rates
  - _Requirements: 4.4, 5.5_