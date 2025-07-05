"""
Database indexing service for temporal pose sequence queries.

This service optimizes database query performance for time-series pose data analysis
by creating specialized indexes for common query patterns.

Features:
- Temporal range queries (videos by date range)
- User-specific historical data queries  
- Exercise type filtering with temporal ordering
- Form check analysis aggregation queries
- Status-based filtering for processing pipelines
- Composite indexes for multi-column queries
- JSON/JSONB path indexing for nested data
- Partial indexes for active data
"""

import logging
import time
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from sqlalchemy import text, Index, func
from sqlalchemy.orm import Session
from sqlalchemy.engine import Engine
from app.core.database import get_db
from app.core.config import Settings

logger = logging.getLogger(__name__)


@dataclass
class IndexCreationResult:
    """Result of index creation operation."""
    index_name: str
    table_name: str
    columns: List[str]
    creation_time_ms: float
    success: bool
    error_message: Optional[str] = None
    size_estimate_kb: Optional[int] = None


@dataclass
class QueryPerformanceMetrics:
    """Metrics for query performance analysis."""
    query_name: str
    execution_time_ms: float
    rows_examined: int
    rows_returned: int
    index_used: Optional[str] = None
    query_plan: Optional[str] = None


class DatabaseIndexingService:
    """
    Service for managing database indexes to optimize temporal pose sequence queries.
    
    This service creates and manages specialized indexes for:
    - Time-based filtering and sorting
    - User-specific data access patterns
    - Exercise type analysis
    - Status-based processing queries
    - JSON data path queries
    """
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self._index_definitions = self._get_index_definitions()
        
    def _get_index_definitions(self) -> Dict[str, Dict[str, Any]]:
        """Define all database indexes for temporal pose sequence queries."""
        return {
            # Core temporal indexes for Videos table
            "idx_videos_temporal_user": {
                "table": "videos",
                "columns": ["user_id", "created_at DESC"],
                "name": "idx_videos_temporal_user",
                "comment": "Optimize user-specific video queries ordered by creation time",
                "partial_condition": None
            },
            
            "idx_videos_exercise_temporal": {
                "table": "videos", 
                "columns": ["exercise_type", "created_at DESC"],
                "name": "idx_videos_exercise_temporal",
                "comment": "Optimize exercise type filtering with temporal ordering",
                "partial_condition": "exercise_type IS NOT NULL"
            },
            
            "idx_videos_status_temporal": {
                "table": "videos",
                "columns": ["status", "updated_at DESC"],
                "name": "idx_videos_status_temporal", 
                "comment": "Optimize status-based queries for processing pipeline",
                "partial_condition": None
            },
            
            "idx_videos_user_exercise_temporal": {
                "table": "videos",
                "columns": ["user_id", "exercise_type", "created_at DESC"],
                "name": "idx_videos_user_exercise_temporal",
                "comment": "Optimize user + exercise type queries with temporal ordering",
                "partial_condition": "exercise_type IS NOT NULL"
            },
            
            "idx_videos_processing_temporal": {
                "table": "videos",
                "columns": ["status", "created_at DESC"],
                "name": "idx_videos_processing_temporal",
                "comment": "Optimize processing status queries with creation ordering",
                "partial_condition": "status IN ('uploaded', 'processing', 'processed', 'analyzing')"
            },
            
            # Form check temporal indexes
            "idx_form_checks_temporal_user": {
                "table": "form_checks",
                "columns": ["user_id", "created_at DESC"],
                "name": "idx_form_checks_temporal_user",
                "comment": "Optimize user form check history queries",
                "partial_condition": None
            },
            
            "idx_form_checks_video_temporal": {
                "table": "form_checks",
                "columns": ["video_id", "created_at DESC"],
                "name": "idx_form_checks_video_temporal",
                "comment": "Optimize video-specific form check queries",
                "partial_condition": "video_id IS NOT NULL"
            },
            
            "idx_form_checks_exercise_temporal": {
                "table": "form_checks",
                "columns": ["exercise_id", "created_at DESC"],
                "name": "idx_form_checks_exercise_temporal",
                "comment": "Optimize exercise-specific form check analysis",
                "partial_condition": None
            },
            
            "idx_form_checks_status_temporal": {
                "table": "form_checks",
                "columns": ["status", "updated_at DESC"],
                "name": "idx_form_checks_status_temporal",
                "comment": "Optimize form check processing status queries",
                "partial_condition": None
            },
            
            "idx_form_checks_scores_temporal": {
                "table": "form_checks",
                "columns": ["user_id", "score DESC", "created_at DESC"],
                "name": "idx_form_checks_scores_temporal",
                "comment": "Optimize user performance analysis queries",
                "partial_condition": "score IS NOT NULL"
            },
            
            # Feedback items temporal indexes
            "idx_feedback_temporal": {
                "table": "feedback_items",
                "columns": ["form_check_id", "timestamp"],
                "name": "idx_feedback_temporal",
                "comment": "Optimize feedback timeline queries within form checks",
                "partial_condition": None
            },
            
            "idx_feedback_severity_temporal": {
                "table": "feedback_items",
                "columns": ["form_check_id", "severity", "timestamp"],
                "name": "idx_feedback_severity_temporal",
                "comment": "Optimize severity-based feedback analysis",
                "partial_condition": None
            },
            
            # JSON data path indexes (PostgreSQL specific)
            "idx_videos_pose_data_gin": {
                "table": "videos",
                "type": "gin",
                "expression": "pose_data",
                "name": "idx_videos_pose_data_gin",
                "comment": "GIN index for pose data JSON queries",
                "postgresql_only": True
            },
            
            "idx_videos_analysis_results_gin": {
                "table": "videos",
                "type": "gin", 
                "expression": "analysis_results",
                "name": "idx_videos_analysis_results_gin",
                "comment": "GIN index for analysis results JSON queries",
                "postgresql_only": True
            },
            
            "idx_form_checks_results_gin": {
                "table": "form_checks",
                "type": "gin",
                "expression": "results",
                "name": "idx_form_checks_results_gin", 
                "comment": "GIN index for form check results JSON queries",
                "postgresql_only": True
            },
            
            # Performance optimization indexes
            "idx_videos_size_temporal": {
                "table": "videos",
                "columns": ["size DESC", "created_at DESC"],
                "name": "idx_videos_size_temporal",
                "comment": "Optimize queries by video size for storage analysis",
                "partial_condition": "size IS NOT NULL"
            },
            
            "idx_videos_duration_temporal": {
                "table": "videos",
                "columns": ["duration DESC", "created_at DESC"], 
                "name": "idx_videos_duration_temporal",
                "comment": "Optimize queries by video duration for analysis",
                "partial_condition": "duration IS NOT NULL"
            },
            
            # Storage optimization indexes
            "idx_videos_compression_stats": {
                "table": "videos",
                "columns": ["compression_ratio", "original_pose_size DESC"],
                "name": "idx_videos_compression_stats",
                "comment": "Optimize storage efficiency analysis queries",
                "partial_condition": "compression_ratio IS NOT NULL"
            },
            
            "idx_videos_storage_format": {
                "table": "videos",
                "columns": ["pose_storage_format", "storage_optimization_ratio DESC"],
                "name": "idx_videos_storage_format",
                "comment": "Optimize storage format performance queries",
                "partial_condition": "pose_storage_format IS NOT NULL"
            }
        }
    
    async def create_all_indexes(self, db: Session) -> List[IndexCreationResult]:
        """
        Create all defined indexes for temporal pose sequence queries.
        
        Args:
            db: Database session
            
        Returns:
            List of index creation results
        """
        results = []
        
        logger.info("Creating database indexes for temporal pose sequence optimization...")
        
        for index_name, definition in self._index_definitions.items():
            try:
                result = await self._create_index(db, definition)
                results.append(result)
                
                if result.success:
                    logger.info(f"✅ Created index {index_name} in {result.creation_time_ms:.1f}ms")
                else:
                    logger.warning(f"⚠️ Failed to create index {index_name}: {result.error_message}")
                    
            except Exception as e:
                logger.error(f"❌ Error creating index {index_name}: {e}")
                results.append(IndexCreationResult(
                    index_name=index_name,
                    table_name=definition.get("table", "unknown"),
                    columns=definition.get("columns", []),
                    creation_time_ms=0.0,
                    success=False,
                    error_message=str(e)
                ))
        
        # Summary
        successful = len([r for r in results if r.success])
        total = len(results)
        logger.info(f"Index creation completed: {successful}/{total} successful")
        
        return results
    
    async def _create_index(self, db: Session, definition: Dict[str, Any]) -> IndexCreationResult:
        """
        Create a single index based on definition.
        
        Args:
            db: Database session
            definition: Index definition dictionary
            
        Returns:
            Index creation result
        """
        start_time = time.time()
        
        try:
            # Check if this is a PostgreSQL-only index
            if definition.get("postgresql_only", False):
                # Check if we're using PostgreSQL
                dialect_name = db.get_bind().dialect.name
                if dialect_name != 'postgresql':
                    return IndexCreationResult(
                        index_name=definition["name"],
                        table_name=definition["table"],
                        columns=definition.get("columns", []),
                        creation_time_ms=0.0,
                        success=True,  # Skip but consider successful
                        error_message=f"Skipped PostgreSQL-only index on {dialect_name}"
                    )
            
            # Check if index already exists
            if await self._index_exists(db, definition["name"]):
                return IndexCreationResult(
                    index_name=definition["name"],
                    table_name=definition["table"],
                    columns=definition.get("columns", []),
                    creation_time_ms=0.0,
                    success=True,
                    error_message="Index already exists"
                )
            
            # Build CREATE INDEX statement
            sql = self._build_create_index_sql(definition)
            
            # Execute index creation
            db.execute(text(sql))
            db.commit()
            
            creation_time = (time.time() - start_time) * 1000
            
            # Get index size estimate
            size_estimate = await self._get_index_size_estimate(db, definition["name"])
            
            return IndexCreationResult(
                index_name=definition["name"],
                table_name=definition["table"],
                columns=definition.get("columns", []),
                creation_time_ms=creation_time,
                success=True,
                size_estimate_kb=size_estimate
            )
            
        except Exception as e:
            creation_time = (time.time() - start_time) * 1000
            return IndexCreationResult(
                index_name=definition["name"],
                table_name=definition["table"],
                columns=definition.get("columns", []),
                creation_time_ms=creation_time,
                success=False,
                error_message=str(e)
            )
    
    def _build_create_index_sql(self, definition: Dict[str, Any]) -> str:
        """
        Build CREATE INDEX SQL statement from definition.
        
        Args:
            definition: Index definition dictionary
            
        Returns:
            SQL statement string
        """
        index_name = definition["name"]
        table_name = definition["table"]
        
        # Handle different index types
        if definition.get("type") == "gin":
            # GIN index for JSON data
            expression = definition["expression"]
            sql = f"CREATE INDEX CONCURRENTLY IF NOT EXISTS {index_name} ON {table_name} USING gin ({expression})"
        else:
            # Regular B-tree index
            columns = definition["columns"]
            columns_str = ", ".join(columns)
            sql = f"CREATE INDEX CONCURRENTLY IF NOT EXISTS {index_name} ON {table_name} ({columns_str})"
        
        # Add partial index condition if specified
        if definition.get("partial_condition"):
            sql += f" WHERE {definition['partial_condition']}"
        
        return sql
    
    async def _index_exists(self, db: Session, index_name: str) -> bool:
        """
        Check if an index already exists.
        
        Args:
            db: Database session
            index_name: Name of the index to check
            
        Returns:
            True if index exists, False otherwise
        """
        try:
            # PostgreSQL specific query
            result = db.execute(text("""
                SELECT 1 FROM pg_indexes 
                WHERE indexname = :index_name
                LIMIT 1
            """), {"index_name": index_name})
            
            return result.fetchone() is not None
            
        except Exception:
            # Fallback for non-PostgreSQL databases
            try:
                # Generic approach - try to get index info
                result = db.execute(text(f"""
                    SELECT 1 FROM information_schema.statistics 
                    WHERE index_name = '{index_name}'
                    LIMIT 1
                """))
                return result.fetchone() is not None
            except Exception:
                # If we can't check, assume it doesn't exist
                return False
    
    async def _get_index_size_estimate(self, db: Session, index_name: str) -> Optional[int]:
        """
        Get estimated size of an index in KB.
        
        Args:
            db: Database session
            index_name: Name of the index
            
        Returns:
            Index size in KB, or None if unavailable
        """
        try:
            # PostgreSQL specific query
            result = db.execute(text("""
                SELECT pg_size_pretty(pg_relation_size(:index_name))
            """), {"index_name": index_name})
            
            size_str = result.fetchone()
            if size_str:
                # Parse size string (e.g., "123 kB" -> 123)
                size_str = size_str[0]
                if "kB" in size_str:
                    return int(size_str.replace(" kB", ""))
                elif "MB" in size_str:
                    return int(float(size_str.replace(" MB", "")) * 1024)
            
            return None
            
        except Exception:
            return None
    
    async def analyze_query_performance(
        self, 
        db: Session, 
        test_queries: Dict[str, str]
    ) -> List[QueryPerformanceMetrics]:
        """
        Analyze query performance with and without indexes.
        
        Args:
            db: Database session
            test_queries: Dictionary of query names to SQL statements
            
        Returns:
            List of performance metrics for each query
        """
        results = []
        
        logger.info("Analyzing query performance with temporal indexes...")
        
        for query_name, sql in test_queries.items():
            try:
                metrics = await self._measure_query_performance(db, query_name, sql)
                results.append(metrics)
                
                logger.info(
                    f"Query '{query_name}': {metrics.execution_time_ms:.1f}ms, "
                    f"{metrics.rows_returned} rows returned"
                )
                
            except Exception as e:
                logger.error(f"Error analyzing query '{query_name}': {e}")
                
        return results
    
    async def _measure_query_performance(
        self, 
        db: Session, 
        query_name: str, 
        sql: str
    ) -> QueryPerformanceMetrics:
        """
        Measure performance of a single query.
        
        Args:
            db: Database session
            query_name: Name of the query for identification
            sql: SQL statement to execute
            
        Returns:
            Query performance metrics
        """
        # Get query execution plan (PostgreSQL specific)
        try:
            plan_result = db.execute(text(f"EXPLAIN (FORMAT JSON) {sql}"))
            query_plan = plan_result.fetchone()
            if query_plan:
                query_plan = str(query_plan[0])
        except Exception:
            query_plan = None
        
        # Measure execution time
        start_time = time.time()
        result = db.execute(text(sql))
        rows = result.fetchall()
        execution_time = (time.time() - start_time) * 1000
        
        # Extract index information from query plan if available
        index_used = None
        if query_plan:
            # Simple extraction - look for "Index" in the plan
            if "Index Scan" in query_plan:
                index_used = "index_scan"
            elif "Seq Scan" in query_plan:
                index_used = "sequential_scan"
        
        return QueryPerformanceMetrics(
            query_name=query_name,
            execution_time_ms=execution_time,
            rows_examined=len(rows),  # Simplified - actual examined rows may be different
            rows_returned=len(rows),
            index_used=index_used,
            query_plan=query_plan
        )
    
    def get_recommended_test_queries(self) -> Dict[str, str]:
        """
        Get recommended test queries for performance analysis.
        
        Returns:
            Dictionary of query names to SQL statements
        """
        return {
            "user_recent_videos": """
                SELECT id, filename, created_at, status 
                FROM videos 
                WHERE user_id = '123e4567-e89b-12d3-a456-426614174000'
                ORDER BY created_at DESC 
                LIMIT 20
            """,
            
            "exercise_type_analysis": """
                SELECT exercise_type, COUNT(*), AVG(score) as avg_score
                FROM videos v
                LEFT JOIN form_checks fc ON v.id = fc.video_id
                WHERE exercise_type = 'squat'
                AND v.created_at >= NOW() - INTERVAL '30 days'
                GROUP BY exercise_type
            """,
            
            "processing_status_queue": """
                SELECT id, status, created_at, updated_at
                FROM videos 
                WHERE status IN ('uploaded', 'processing', 'analyzing')
                ORDER BY created_at ASC
                LIMIT 100
            """,
            
            "user_performance_timeline": """
                SELECT fc.created_at, fc.score, fc.posture_score, fc.stability_score, fc.depth_score
                FROM form_checks fc
                WHERE fc.user_id = '123e4567-e89b-12d3-a456-426614174000'
                AND fc.score IS NOT NULL
                ORDER BY fc.created_at DESC
                LIMIT 50
            """,
            
            "feedback_timeline_analysis": """
                SELECT fi.timestamp, fi.severity, fi.type, fi.message
                FROM feedback_items fi
                JOIN form_checks fc ON fi.form_check_id = fc.id
                WHERE fc.id = '123e4567-e89b-12d3-a456-426614174001'
                ORDER BY fi.timestamp ASC
            """,
            
            "storage_efficiency_analysis": """
                SELECT 
                    pose_storage_format,
                    COUNT(*) as videos_count,
                    AVG(storage_optimization_ratio) as avg_optimization,
                    SUM(original_json_size - optimized_size) as total_space_saved
                FROM videos 
                WHERE pose_storage_format IS NOT NULL
                GROUP BY pose_storage_format
            """,
            
            "temporal_range_analysis": """
                SELECT 
                    DATE_TRUNC('day', created_at) as date,
                    COUNT(*) as videos_created,
                    COUNT(CASE WHEN status = 'analysis_complete' THEN 1 END) as completed_analysis
                FROM videos
                WHERE created_at >= NOW() - INTERVAL '7 days'
                GROUP BY DATE_TRUNC('day', created_at)
                ORDER BY date DESC
            """
        }
    
    async def drop_all_indexes(self, db: Session) -> List[bool]:
        """
        Drop all created indexes (useful for testing/cleanup).
        
        Args:
            db: Database session
            
        Returns:
            List of success flags for each index drop operation
        """
        results = []
        
        logger.info("Dropping temporal pose sequence indexes...")
        
        for index_name, definition in self._index_definitions.items():
            try:
                if await self._index_exists(db, definition["name"]):
                    db.execute(text(f"DROP INDEX CONCURRENTLY IF EXISTS {definition['name']}"))
                    db.commit()
                    logger.info(f"✅ Dropped index {index_name}")
                    results.append(True)
                else:
                    logger.info(f"⚠️ Index {index_name} does not exist")
                    results.append(True)  # Consider success
                    
            except Exception as e:
                logger.error(f"❌ Error dropping index {index_name}: {e}")
                results.append(False)
        
        return results
    
    async def get_index_usage_statistics(self, db: Session) -> Dict[str, Dict[str, Any]]:
        """
        Get usage statistics for created indexes.
        
        Args:
            db: Database session
            
        Returns:
            Dictionary of index statistics
        """
        stats = {}
        
        try:
            # PostgreSQL specific index usage stats
            result = db.execute(text("""
                SELECT 
                    schemaname,
                    tablename,
                    indexname,
                    idx_scan as scans,
                    idx_tup_read as tuples_read,
                    idx_tup_fetch as tuples_fetched
                FROM pg_stat_user_indexes 
                WHERE indexname LIKE 'idx_%'
                ORDER BY idx_scan DESC
            """))
            
            for row in result:
                index_name = row.indexname
                stats[index_name] = {
                    "table": row.tablename,
                    "scans": row.scans,
                    "tuples_read": row.tuples_read,
                    "tuples_fetched": row.tuples_fetched,
                    "efficiency": row.tuples_fetched / max(row.tuples_read, 1)
                }
                
        except Exception as e:
            logger.warning(f"Could not retrieve index usage statistics: {e}")
            
        return stats


# Global service instance
indexing_service: Optional[DatabaseIndexingService] = None


def get_database_indexing_service(settings: Settings) -> DatabaseIndexingService:
    """Get or create the global database indexing service instance."""
    global indexing_service
    
    if indexing_service is None:
        indexing_service = DatabaseIndexingService(settings)
    
    return indexing_service