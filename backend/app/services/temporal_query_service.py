"""
Temporal query service utilizing optimized database indexes.

This service provides high-performance temporal queries for pose sequence analysis
by leveraging the specialized indexes created for time-series data.

Features:
- User timeline analysis with temporal ordering
- Exercise performance trends over time
- Processing pipeline status monitoring
- Form check historical analysis
- Feedback timeline reconstruction
- JSON pose data querying with GIN indexes
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from sqlalchemy import and_, or_, desc, asc, func, text
from sqlalchemy.orm import Session
from uuid import UUID

from app.models.video import Video
from app.models.form_check import FormCheck, FeedbackItem
from app.models.enums import VideoStatus, FormCheckStatus

logger = logging.getLogger(__name__)


@dataclass
class TemporalQueryResult:
    """Result container for temporal queries."""
    total_count: int
    results: List[Any]
    query_time_ms: float
    index_used: Optional[str] = None


@dataclass
class UserTimelineMetrics:
    """Metrics for user timeline analysis."""
    user_id: UUID
    total_videos: int
    completed_analyses: int
    average_score: Optional[float]
    improvement_trend: str
    most_common_exercise: Optional[str]
    latest_activity: Optional[datetime]


@dataclass 
class ExercisePerformanceTrend:
    """Exercise performance trend data."""
    exercise_type: str
    time_period: str
    score_trend: List[Tuple[datetime, float]]
    improvement_rate: float
    total_sessions: int


class TemporalQueryService:
    """
    High-performance temporal query service utilizing database indexes.
    
    This service provides optimized queries for time-series pose data analysis,
    leveraging the specialized indexes for maximum performance.
    """
    
    def __init__(self):
        pass
    
    async def get_user_video_timeline(
        self,
        db: Session,
        user_id: UUID,
        days_back: int = 30,
        limit: int = 50,
        exercise_type: Optional[str] = None
    ) -> TemporalQueryResult:
        """
        Get user's video timeline with temporal ordering.
        
        Utilizes: idx_videos_temporal_user, idx_videos_user_exercise_temporal
        
        Args:
            db: Database session
            user_id: User ID to query
            days_back: Number of days to look back
            limit: Maximum number of results
            exercise_type: Optional exercise type filter
            
        Returns:
            Temporal query result with user's videos
        """
        import time
        start_time = time.time()
        
        try:
            # Build query with index-optimized conditions
            query = db.query(Video).filter(Video.user_id == user_id)
            
            # Add date filter for temporal optimization
            if days_back > 0:
                cutoff_date = datetime.utcnow() - timedelta(days=days_back)
                query = query.filter(Video.created_at >= cutoff_date)
            
            # Add exercise type filter if specified (uses composite index)
            if exercise_type:
                query = query.filter(Video.exercise_type == exercise_type)
            
            # Order by created_at DESC (utilizes temporal index)
            query = query.order_by(desc(Video.created_at))
            
            # Apply limit
            query = query.limit(limit)
            
            # Get total count for metadata
            count_query = db.query(func.count(Video.id)).filter(Video.user_id == user_id)
            if days_back > 0:
                count_query = count_query.filter(Video.created_at >= cutoff_date)
            if exercise_type:
                count_query = count_query.filter(Video.exercise_type == exercise_type)
            
            total_count = count_query.scalar()
            results = query.all()
            
            query_time = (time.time() - start_time) * 1000
            
            # Determine index used based on query pattern
            index_used = "idx_videos_user_exercise_temporal" if exercise_type else "idx_videos_temporal_user"
            
            return TemporalQueryResult(
                total_count=total_count,
                results=results,
                query_time_ms=query_time,
                index_used=index_used
            )
            
        except Exception as e:
            logger.error(f"Error in user video timeline query: {e}")
            raise
    
    async def get_processing_status_timeline(
        self,
        db: Session,
        status_filter: Optional[List[VideoStatus]] = None,
        hours_back: int = 24,
        limit: int = 100
    ) -> TemporalQueryResult:
        """
        Get video processing status timeline.
        
        Utilizes: idx_videos_processing_temporal, idx_videos_status_temporal
        
        Args:
            db: Database session
            status_filter: Optional list of statuses to filter by
            hours_back: Number of hours to look back
            limit: Maximum number of results
            
        Returns:
            Temporal query result with processing status timeline
        """
        import time
        start_time = time.time()
        
        try:
            # Build query with processing status optimization
            if status_filter:
                # Use partial index for active processing statuses
                active_statuses = [VideoStatus.UPLOADED, VideoStatus.PROCESSING, VideoStatus.ANALYZING]
                if any(status in active_statuses for status in status_filter):
                    query = db.query(Video).filter(Video.status.in_(status_filter))
                    index_used = "idx_videos_processing_temporal"
                else:
                    query = db.query(Video).filter(Video.status.in_(status_filter))
                    index_used = "idx_videos_status_temporal"
            else:
                # Query all videos with status temporal ordering
                query = db.query(Video)
                index_used = "idx_videos_status_temporal"
            
            # Add temporal filter
            if hours_back > 0:
                cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
                query = query.filter(Video.updated_at >= cutoff_time)
            
            # Order by updated_at DESC for processing timeline
            query = query.order_by(desc(Video.updated_at)).limit(limit)
            
            # Get total count
            count_query = db.query(func.count(Video.id))
            if status_filter:
                count_query = count_query.filter(Video.status.in_(status_filter))
            if hours_back > 0:
                count_query = count_query.filter(Video.updated_at >= cutoff_time)
            
            total_count = count_query.scalar()
            results = query.all()
            
            query_time = (time.time() - start_time) * 1000
            
            return TemporalQueryResult(
                total_count=total_count,
                results=results,
                query_time_ms=query_time,
                index_used=index_used
            )
            
        except Exception as e:
            logger.error(f"Error in processing status timeline query: {e}")
            raise
    
    async def get_form_check_performance_timeline(
        self,
        db: Session,
        user_id: UUID,
        exercise_type: Optional[str] = None,
        days_back: int = 90
    ) -> UserTimelineMetrics:
        """
        Get user's form check performance timeline with trends.
        
        Utilizes: idx_form_checks_temporal_user, idx_form_checks_scores_temporal
        
        Args:
            db: Database session
            user_id: User ID to analyze
            exercise_type: Optional exercise type filter
            days_back: Number of days to analyze
            
        Returns:
            User timeline metrics with performance trends
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_back)
            
            # Get user's form checks with score ordering (uses scores temporal index)
            query = db.query(FormCheck).filter(
                and_(
                    FormCheck.user_id == user_id,
                    FormCheck.created_at >= cutoff_date,
                    FormCheck.score.isnot(None)
                )
            ).order_by(desc(FormCheck.score), desc(FormCheck.created_at))
            
            if exercise_type:
                # Join with videos to filter by exercise type
                query = query.join(Video).filter(Video.exercise_type == exercise_type)
            
            form_checks = query.all()
            
            # Calculate metrics
            total_count = len(form_checks)
            completed_analyses = len([fc for fc in form_checks if fc.status == FormCheckStatus.COMPLETED])
            
            scores = [fc.score for fc in form_checks if fc.score is not None]
            average_score = sum(scores) / len(scores) if scores else None
            
            # Calculate improvement trend (compare first half vs second half)
            improvement_trend = "stable"
            if len(scores) >= 4:
                mid_point = len(scores) // 2
                early_avg = sum(scores[:mid_point]) / mid_point
                recent_avg = sum(scores[mid_point:]) / (len(scores) - mid_point)
                
                if recent_avg > early_avg + 5:
                    improvement_trend = "improving"
                elif recent_avg < early_avg - 5:
                    improvement_trend = "declining"
            
            # Get most common exercise type
            if not exercise_type:
                exercise_counts = {}
                for fc in form_checks:
                    if fc.video and fc.video.exercise_type:
                        exercise_counts[fc.video.exercise_type] = exercise_counts.get(fc.video.exercise_type, 0) + 1
                most_common_exercise = max(exercise_counts.keys(), key=exercise_counts.get) if exercise_counts else None
            else:
                most_common_exercise = exercise_type
            
            # Get latest activity
            latest_activity = form_checks[0].created_at if form_checks else None
            
            return UserTimelineMetrics(
                user_id=user_id,
                total_videos=total_count,
                completed_analyses=completed_analyses,
                average_score=average_score,
                improvement_trend=improvement_trend,
                most_common_exercise=most_common_exercise,
                latest_activity=latest_activity
            )
            
        except Exception as e:
            logger.error(f"Error in form check performance timeline query: {e}")
            raise
    
    async def get_feedback_timeline(
        self,
        db: Session,
        form_check_id: UUID,
        severity_filter: Optional[str] = None
    ) -> TemporalQueryResult:
        """
        Get feedback timeline for a specific form check.
        
        Utilizes: idx_feedback_temporal, idx_feedback_severity_temporal
        
        Args:
            db: Database session
            form_check_id: Form check ID to query
            severity_filter: Optional severity level filter
            
        Returns:
            Temporal query result with feedback timeline
        """
        import time
        start_time = time.time()
        
        try:
            # Build query with feedback temporal ordering
            query = db.query(FeedbackItem).filter(FeedbackItem.form_check_id == form_check_id)
            
            index_used = "idx_feedback_temporal"
            if severity_filter:
                query = query.filter(FeedbackItem.severity == severity_filter)
                index_used = "idx_feedback_severity_temporal"
            
            # Order by timestamp for timeline reconstruction
            query = query.order_by(asc(FeedbackItem.timestamp))
            
            # Get total count
            count_query = db.query(func.count(FeedbackItem.id)).filter(
                FeedbackItem.form_check_id == form_check_id
            )
            if severity_filter:
                count_query = count_query.filter(FeedbackItem.severity == severity_filter)
            
            total_count = count_query.scalar()
            results = query.all()
            
            query_time = (time.time() - start_time) * 1000
            
            return TemporalQueryResult(
                total_count=total_count,
                results=results,
                query_time_ms=query_time,
                index_used=index_used
            )
            
        except Exception as e:
            logger.error(f"Error in feedback timeline query: {e}")
            raise
    
    async def query_pose_data_by_json_path(
        self,
        db: Session,
        json_path: str,
        value_filter: Any = None,
        limit: int = 50
    ) -> TemporalQueryResult:
        """
        Query videos by JSON pose data paths using GIN indexes.
        
        Utilizes: idx_videos_pose_data_gin
        
        Args:
            db: Database session
            json_path: JSON path to query (e.g., '$[0][0].x')
            value_filter: Optional value to filter by
            limit: Maximum number of results
            
        Returns:
            Temporal query result with matching videos
        """
        import time
        start_time = time.time()
        
        try:
            # Use PostgreSQL JSON operators with GIN index
            if value_filter is not None:
                # Query with value filter
                query = db.query(Video).filter(
                    text(f"pose_data::jsonb #> '{{{json_path}}}' = :value")
                ).params(value=str(value_filter))
            else:
                # Query for existence of path
                query = db.query(Video).filter(
                    text(f"pose_data::jsonb #> '{{{json_path}}}' IS NOT NULL")
                )
            
            # Order by created_at for temporal consistency
            query = query.order_by(desc(Video.created_at)).limit(limit)
            
            results = query.all()
            
            # Get count (simplified for performance)
            total_count = len(results)
            
            query_time = (time.time() - start_time) * 1000
            
            return TemporalQueryResult(
                total_count=total_count,
                results=results,
                query_time_ms=query_time,
                index_used="idx_videos_pose_data_gin"
            )
            
        except Exception as e:
            logger.error(f"Error in JSON pose data query: {e}")
            raise
    
    async def get_exercise_performance_trends(
        self,
        db: Session,
        exercise_type: str,
        days_back: int = 30,
        group_by_days: int = 7
    ) -> ExercisePerformanceTrend:
        """
        Get exercise performance trends over time.
        
        Utilizes: idx_videos_exercise_temporal, idx_form_checks_exercise_temporal
        
        Args:
            db: Database session
            exercise_type: Exercise type to analyze
            days_back: Number of days to analyze
            group_by_days: Group results by this many days
            
        Returns:
            Exercise performance trend data
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_back)
            
            # Query form checks with exercise temporal ordering
            results = db.query(
                func.date_trunc('week', FormCheck.created_at).label('week'),
                func.avg(FormCheck.score).label('avg_score'),
                func.count(FormCheck.id).label('session_count')
            ).join(Video).filter(
                and_(
                    Video.exercise_type == exercise_type,
                    FormCheck.created_at >= cutoff_date,
                    FormCheck.score.isnot(None)
                )
            ).group_by(
                func.date_trunc('week', FormCheck.created_at)
            ).order_by(
                func.date_trunc('week', FormCheck.created_at)
            ).all()
            
            # Build trend data
            score_trend = [(result.week, float(result.avg_score)) for result in results]
            total_sessions = sum(result.session_count for result in results)
            
            # Calculate improvement rate
            improvement_rate = 0.0
            if len(score_trend) >= 2:
                first_score = score_trend[0][1]
                last_score = score_trend[-1][1]
                weeks_span = len(score_trend)
                improvement_rate = (last_score - first_score) / weeks_span if weeks_span > 0 else 0.0
            
            return ExercisePerformanceTrend(
                exercise_type=exercise_type,
                time_period=f"{days_back} days",
                score_trend=score_trend,
                improvement_rate=improvement_rate,
                total_sessions=total_sessions
            )
            
        except Exception as e:
            logger.error(f"Error in exercise performance trends query: {e}")
            raise
    
    async def get_storage_optimization_metrics(
        self,
        db: Session,
        days_back: int = 30
    ) -> Dict[str, Any]:
        """
        Get storage optimization metrics using storage format indexes.
        
        Utilizes: idx_videos_storage_format, idx_videos_compression_stats
        
        Args:
            db: Database session
            days_back: Number of days to analyze
            
        Returns:
            Storage optimization metrics
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_back)
            
            # Query with storage format optimization index
            results = db.query(
                Video.pose_storage_format,
                func.count(Video.id).label('video_count'),
                func.avg(Video.storage_optimization_ratio).label('avg_optimization'),
                func.sum(Video.original_json_size - Video.optimized_size).label('total_space_saved')
            ).filter(
                and_(
                    Video.created_at >= cutoff_date,
                    Video.pose_storage_format.isnot(None)
                )
            ).group_by(Video.pose_storage_format).all()
            
            # Query compression statistics
            compression_stats = db.query(
                func.avg(Video.compression_ratio).label('avg_compression_ratio'),
                func.sum(Video.original_pose_size).label('total_original_size'),
                func.sum(Video.compressed_pose_size).label('total_compressed_size')
            ).filter(
                and_(
                    Video.created_at >= cutoff_date,
                    Video.compression_ratio.isnot(None)
                )
            ).first()
            
            # Format results
            format_metrics = {}
            total_space_saved = 0
            
            for result in results:
                format_metrics[result.pose_storage_format] = {
                    'video_count': result.video_count,
                    'avg_optimization': float(result.avg_optimization) if result.avg_optimization else 0.0,
                    'total_space_saved_bytes': int(result.total_space_saved) if result.total_space_saved else 0
                }
                total_space_saved += result.total_space_saved or 0
            
            return {
                'time_period_days': days_back,
                'format_metrics': format_metrics,
                'total_space_saved_mb': total_space_saved / (1024 * 1024),
                'compression_metrics': {
                    'avg_compression_ratio': float(compression_stats.avg_compression_ratio) if compression_stats.avg_compression_ratio else 0.0,
                    'total_original_size_mb': (compression_stats.total_original_size or 0) / (1024 * 1024),
                    'total_compressed_size_mb': (compression_stats.total_compressed_size or 0) / (1024 * 1024)
                }
            }
            
        except Exception as e:
            logger.error(f"Error in storage optimization metrics query: {e}")
            raise


# Global service instance
temporal_query_service: Optional[TemporalQueryService] = None


def get_temporal_query_service() -> TemporalQueryService:
    """Get or create the global temporal query service instance."""
    global temporal_query_service
    
    if temporal_query_service is None:
        temporal_query_service = TemporalQueryService()
    
    return temporal_query_service