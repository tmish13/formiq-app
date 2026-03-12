# FormIQ Database Indexes Documentation

## Overview

This document describes the database indexing strategy for FormIQ, including critical performance indexes and supplementary analytics indexes.

## Index Categories

### Critical Performance Indexes
These indexes are essential for production performance and should be applied immediately.

**Migration**: `2025_12_06_critical_performance_indexes.py`

#### Video Model Indexes
- `ix_videos_user_id` - Foreign key index for video-user associations (critical)
- `ix_videos_status` - Status filtering for video processing queries
- `ix_videos_exercise_type` - Exercise type filtering (partial index)
- `ix_videos_celery_task_id` - Async task tracking (partial index)
- `ix_videos_object_key_unique` - Unique constraint for S3 object keys
- `ix_videos_user_status_created` - Composite index for user video listings

#### FormCheck Model Indexes
- `ix_form_checks_video_id` - Foreign key index for form check-video associations
- `ix_form_checks_configuration_id` - Configuration lookup index
- `ix_form_checks_user_status` - Composite index for user status queries
- `ix_form_checks_updated_at` - Temporal ordering for change tracking

#### FeedbackItem Model Indexes
- `ix_feedback_items_form_check_id` - Foreign key index (critical for cascading)
- `ix_feedback_items_timestamp` - Temporal ordering for feedback
- `ix_feedback_items_severity` - Severity filtering
- `ix_feedback_items_type` - Type-based filtering
- `ix_feedback_items_form_check_timestamp` - Composite for feedback retrieval

#### User Model Optimization
- `ix_users_email_active` - Authentication queries (partial index)
- `ix_users_subscription_tier` - Access control filtering
- `ix_users_verified_active` - Verification status queries
- `ix_users_onboarding_status` - Onboarding progress tracking

#### UserSession Model Indexes
- `ix_user_sessions_session_id` - Session lookup (critical for auth)
- `ix_user_sessions_user_expires` - Session cleanup and management
- `ix_user_sessions_last_active` - Active session tracking

### Supplementary Analytics Indexes
These indexes optimize analytics, reporting, and advanced query patterns.

**Migration**: `2025_12_06_supplementary_indexes.py`

#### Analytics and Reporting
- `ix_videos_exercise_status_created` - Completion rates by exercise type
- `ix_form_checks_user_created_overall_score` - Success rate analytics
- `ix_videos_processing_duration` - Performance monitoring

#### ML Model Performance
- `ix_form_checks_ml_scores` - ML score analysis (composite)
- `ix_form_checks_classified_exercise` - Exercise classification tracking

#### Video Storage Optimization
- `ix_videos_file_size_created` - Storage analytics
- `ix_videos_resolution_fps` - Quality analysis
- `ix_videos_compression_ratio` - Compression efficiency

#### User Behavior Analysis
- `ix_users_last_login_tier` - Engagement patterns
- `ix_user_sessions_duration` - Session duration analysis

#### Quality Assurance
- `ix_feedback_items_severity_type_timestamp` - Feedback quality tracking
- `ix_exercise_configs_updated_at` - Configuration change tracking

#### Error Tracking
- `ix_videos_error_message` - Processing error analysis (partial)
- `ix_form_checks_error_status` - Error pattern identification (partial)

## Index Design Principles

### Performance Optimizations
1. **Foreign Key Indexes**: All foreign key relationships have corresponding indexes
2. **Composite Indexes**: Common multi-column queries are optimized
3. **Partial Indexes**: Filtered indexes for specific conditions reduce storage overhead
4. **Concurrent Creation**: All indexes created with `CONCURRENTLY` to avoid downtime

### Query Pattern Coverage
1. **Authentication**: Email + active status lookups
2. **Video Processing**: Status tracking and user associations
3. **Form Analysis**: Video-form check-feedback cascading queries
4. **Analytics**: Time-series and aggregation queries
5. **Error Tracking**: Status-based error pattern analysis

## Performance Impact Analysis

### Before Indexes (Estimated Query Times)
- User video listing: 500-1000ms (table scan)
- Form check retrieval: 200-500ms (foreign key scan)
- Feedback cascading: 300-800ms (multiple table scans)
- Authentication lookup: 100-300ms (email scan)

### After Critical Indexes (Estimated Query Times)
- User video listing: 5-15ms (index scan)
- Form check retrieval: 2-8ms (index lookup)
- Feedback cascading: 3-10ms (index joins)
- Authentication lookup: 1-5ms (composite index)

### Performance Gains
- **Video queries**: 95-98% improvement
- **Authentication**: 90-95% improvement  
- **Form analysis**: 90-97% improvement
- **Analytics queries**: 80-90% improvement

## Index Maintenance

### Monitoring
- Use `pg_stat_user_indexes` to monitor index usage
- Track index bloat with `pgstattuple` extension
- Monitor query performance with `pg_stat_statements`

### Maintenance Commands
```sql
-- Check index usage statistics
SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read, idx_tup_fetch 
FROM pg_stat_user_indexes 
WHERE schemaname = 'public'
ORDER BY idx_scan DESC;

-- Check index bloat
SELECT schemaname, tablename, indexname, 
       pg_size_pretty(pg_relation_size(indexrelid)) as size,
       round(100 * pg_relation_size(indexrelid) / pg_relation_size(indrelid), 1) as index_ratio
FROM pg_stat_user_indexes 
WHERE schemaname = 'public'
ORDER BY pg_relation_size(indexrelid) DESC;

-- Reindex if needed
REINDEX INDEX CONCURRENTLY ix_videos_user_id;
```

## Deployment Strategy

### Phase 1: Critical Indexes (Immediate)
Deploy `2025_12_06_critical_performance_indexes.py` first as these provide the most significant performance improvements for core operations.

### Phase 2: Supplementary Indexes (Short-term)
Deploy `2025_12_06_supplementary_indexes.py` after validating the critical indexes are working correctly and providing expected performance gains.

### Rollback Plan
Both migrations include complete `downgrade()` functions that remove all created indexes in reverse order using `CONCURRENTLY` to maintain availability.

## Query Optimization Examples

### Before (Slow Query)
```sql
-- Slow: Table scan on videos
SELECT * FROM videos WHERE user_id = 123 AND status = 'PROCESSED' ORDER BY created_at DESC;
```

### After (Optimized Query)
```sql  
-- Fast: Uses ix_videos_user_status_created composite index
SELECT * FROM videos WHERE user_id = 123 AND status = 'PROCESSED' ORDER BY created_at DESC;
```

### Analytics Query Optimization
```sql
-- Uses ix_form_checks_user_created_overall_score for fast aggregation
SELECT user_id, DATE_TRUNC('day', created_at) as day, AVG(overall_score)
FROM form_checks 
WHERE user_id = 123 AND created_at >= '2024-01-01'
GROUP BY user_id, DATE_TRUNC('day', created_at)
ORDER BY day;
```

## Additional Considerations

### Storage Impact
- Critical indexes: ~50-100MB additional storage (estimated)
- Supplementary indexes: ~30-80MB additional storage (estimated)
- Total impact: <200MB for typical production workload

### Write Performance
- Minimal impact on INSERT/UPDATE operations
- Index maintenance is asynchronous and optimized
- CONCURRENTLY creation prevents lock contention

### Monitoring Recommendations
1. Set up alerts for slow queries (>100ms for simple lookups)
2. Monitor index hit ratios (should be >95% for frequently used indexes)
3. Track query plan changes after index deployment
4. Set up automated index usage reporting