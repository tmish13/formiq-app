"""
Cache monitoring and performance analytics service.

This service provides comprehensive monitoring of cache performance including:
- Hit rate tracking and analysis
- Performance metrics and trends
- Cache efficiency recommendations
- Automated cache optimization suggestions
- Real-time monitoring and alerting
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import statistics

from app.services.cache_service import CacheService, get_cache_service
from app.core.config import Settings

logger = logging.getLogger(__name__)


@dataclass
class CachePerformanceSnapshot:
    """Snapshot of cache performance at a specific time."""
    timestamp: datetime
    hit_rate_percent: float
    average_response_time_ms: float
    total_operations: int
    cache_size_estimate: int
    circuit_breaker_state: str
    redis_memory_used: str
    errors_count: int


@dataclass
class CacheOptimizationRecommendation:
    """Recommendation for cache optimization."""
    category: str  # "performance", "memory", "configuration", "invalidation"
    priority: str  # "high", "medium", "low"
    title: str
    description: str
    action: str
    estimated_impact: str


class CacheMonitoringService:
    """
    Advanced cache monitoring service with performance analytics and optimization recommendations.
    
    Features:
    - Real-time performance tracking
    - Trend analysis and predictions
    - Automated optimization recommendations
    - Cache efficiency scoring
    - Memory usage monitoring
    """
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.cache_service: Optional[CacheService] = None
        self._monitoring_active = False
        
        # Performance tracking
        self.performance_history: deque = deque(maxlen=1000)  # Last 1000 snapshots
        self.operation_types = defaultdict(lambda: {"hits": 0, "misses": 0, "errors": 0})
        
        # Configuration
        self.monitoring_interval = getattr(settings, 'CACHE_MONITORING_INTERVAL', 60)  # seconds
        self.recommendation_threshold = getattr(settings, 'CACHE_RECOMMENDATION_THRESHOLD', 0.7)  # hit rate
        
    async def initialize(self) -> bool:
        """Initialize cache monitoring service."""
        try:
            self.cache_service = await get_cache_service(self.settings)
            if self.cache_service:
                logger.info("Cache monitoring service initialized successfully")
                return True
            else:
                logger.warning("Cache monitoring service initialization failed - cache service unavailable")
                return False
        except Exception as e:
            logger.error(f"Cache monitoring service initialization error: {e}")
            return False
    
    async def start_monitoring(self) -> None:
        """Start continuous cache monitoring."""
        if not self.cache_service:
            logger.warning("Cannot start monitoring - cache service not available")
            return
            
        self._monitoring_active = True
        logger.info(f"Starting cache monitoring with {self.monitoring_interval}s interval")
        
        while self._monitoring_active:
            try:
                await self._collect_performance_snapshot()
                await asyncio.sleep(self.monitoring_interval)
            except Exception as e:
                logger.error(f"Error during cache monitoring: {e}")
                await asyncio.sleep(self.monitoring_interval)
    
    def stop_monitoring(self) -> None:
        """Stop cache monitoring."""
        self._monitoring_active = False
        logger.info("Cache monitoring stopped")
    
    async def _collect_performance_snapshot(self) -> None:
        """Collect a performance snapshot from the cache service."""
        if not self.cache_service:
            return
            
        try:
            stats = await self.cache_service.get_cache_stats()
            health = await self.cache_service.health_check()
            
            snapshot = CachePerformanceSnapshot(
                timestamp=datetime.utcnow(),
                hit_rate_percent=stats.get('hit_rate_percent', 0.0),
                average_response_time_ms=stats.get('average_response_time_ms', 0.0),
                total_operations=stats.get('total_operations', 0),
                cache_size_estimate=0,  # TODO: Implement cache size estimation
                circuit_breaker_state=stats.get('circuit_breaker_state', 'unknown'),
                redis_memory_used=stats.get('redis_memory_used', 'N/A'),
                errors_count=stats.get('errors', 0)
            )
            
            self.performance_history.append(snapshot)
            
            # Log significant performance changes
            if len(self.performance_history) >= 2:
                prev_snapshot = self.performance_history[-2]
                if abs(snapshot.hit_rate_percent - prev_snapshot.hit_rate_percent) > 10:
                    logger.info(f"Significant hit rate change: {prev_snapshot.hit_rate_percent:.1f}% → {snapshot.hit_rate_percent:.1f}%")
                    
        except Exception as e:
            logger.error(f"Failed to collect performance snapshot: {e}")
    
    async def get_performance_summary(self, hours: int = 1) -> Dict[str, Any]:
        """Get performance summary for the specified time period."""
        if not self.performance_history:
            return {"error": "No performance data available"}
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        recent_snapshots = [
            snapshot for snapshot in self.performance_history 
            if snapshot.timestamp >= cutoff_time
        ]
        
        if not recent_snapshots:
            return {"error": f"No data available for the last {hours} hours"}
        
        # Calculate metrics
        hit_rates = [s.hit_rate_percent for s in recent_snapshots]
        response_times = [s.average_response_time_ms for s in recent_snapshots]
        operations = [s.total_operations for s in recent_snapshots]
        
        current_snapshot = recent_snapshots[-1]
        
        summary = {
            "period_hours": hours,
            "snapshots_count": len(recent_snapshots),
            "current_metrics": {
                "hit_rate_percent": current_snapshot.hit_rate_percent,
                "average_response_time_ms": current_snapshot.average_response_time_ms,
                "total_operations": current_snapshot.total_operations,
                "circuit_breaker_state": current_snapshot.circuit_breaker_state,
                "redis_memory_used": current_snapshot.redis_memory_used
            },
            "period_metrics": {
                "avg_hit_rate_percent": statistics.mean(hit_rates) if hit_rates else 0,
                "min_hit_rate_percent": min(hit_rates) if hit_rates else 0,
                "max_hit_rate_percent": max(hit_rates) if hit_rates else 0,
                "avg_response_time_ms": statistics.mean(response_times) if response_times else 0,
                "min_response_time_ms": min(response_times) if response_times else 0,
                "max_response_time_ms": max(response_times) if response_times else 0,
                "total_operations_delta": operations[-1] - operations[0] if len(operations) >= 2 else 0
            }
        }
        
        # Add trend analysis
        if len(hit_rates) >= 3:
            summary["trends"] = {
                "hit_rate_trend": self._calculate_trend(hit_rates),
                "response_time_trend": self._calculate_trend(response_times)
            }
        
        return summary
    
    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend direction from a list of values."""
        if len(values) < 3:
            return "insufficient_data"
        
        # Simple trend calculation using first and last values
        start_avg = statistics.mean(values[:len(values)//3])
        end_avg = statistics.mean(values[-len(values)//3:])
        
        change_percent = ((end_avg - start_avg) / start_avg * 100) if start_avg > 0 else 0
        
        if change_percent > 5:
            return "improving"
        elif change_percent < -5:
            return "declining"
        else:
            return "stable"
    
    async def generate_optimization_recommendations(self) -> List[CacheOptimizationRecommendation]:
        """Generate cache optimization recommendations based on performance data."""
        recommendations = []
        
        if not self.performance_history:
            return recommendations
        
        current_snapshot = self.performance_history[-1]
        
        # Analyze hit rate
        if current_snapshot.hit_rate_percent < 50:
            recommendations.append(CacheOptimizationRecommendation(
                category="performance",
                priority="high",
                title="Low Cache Hit Rate",
                description=f"Current hit rate is {current_snapshot.hit_rate_percent:.1f}%, below optimal threshold",
                action="Review cache TTL settings and increase cache duration for stable data",
                estimated_impact="20-40% performance improvement"
            ))
        elif current_snapshot.hit_rate_percent < 70:
            recommendations.append(CacheOptimizationRecommendation(
                category="performance",
                priority="medium", 
                title="Moderate Cache Hit Rate",
                description=f"Hit rate of {current_snapshot.hit_rate_percent:.1f}% has room for improvement",
                action="Analyze cache key strategies and consider pre-warming frequently accessed data",
                estimated_impact="10-20% performance improvement"
            ))
        
        # Analyze response time
        if current_snapshot.average_response_time_ms > 5.0:
            recommendations.append(CacheOptimizationRecommendation(
                category="performance",
                priority="medium",
                title="Slow Cache Response Time",
                description=f"Average response time is {current_snapshot.average_response_time_ms:.2f}ms",
                action="Check Redis server performance and network latency",
                estimated_impact="Faster user experience"
            ))
        
        # Circuit breaker analysis
        if current_snapshot.circuit_breaker_state == "open":
            recommendations.append(CacheOptimizationRecommendation(
                category="configuration",
                priority="high",
                title="Circuit Breaker Open",
                description="Cache circuit breaker is open, indicating connectivity issues",
                action="Check Redis server status and network connectivity",
                estimated_impact="Restore cache functionality"
            ))
        
        # Memory usage analysis (if available)
        if current_snapshot.redis_memory_used != "N/A":
            try:
                memory_str = current_snapshot.redis_memory_used
                if "M" in memory_str:
                    memory_mb = float(memory_str.replace("M", ""))
                    if memory_mb > 1000:  # > 1GB
                        recommendations.append(CacheOptimizationRecommendation(
                            category="memory",
                            priority="medium",
                            title="High Memory Usage",
                            description=f"Redis is using {memory_str} of memory",
                            action="Review cache TTL settings and implement cache size limits",
                            estimated_impact="Reduced memory usage and costs"
                        ))
            except ValueError:
                pass  # Skip if memory parsing fails
        
        # Trend-based recommendations
        if len(self.performance_history) >= 10:
            recent_hit_rates = [s.hit_rate_percent for s in self.performance_history[-10:]]
            trend = self._calculate_trend(recent_hit_rates)
            
            if trend == "declining":
                recommendations.append(CacheOptimizationRecommendation(
                    category="performance",
                    priority="medium",
                    title="Declining Cache Performance",
                    description="Cache hit rate has been declining over recent periods",
                    action="Review recent application changes and cache invalidation patterns",
                    estimated_impact="Prevent further performance degradation"
                ))
        
        return recommendations
    
    async def get_cache_efficiency_score(self) -> Dict[str, Any]:
        """Calculate overall cache efficiency score and breakdown."""
        if not self.performance_history:
            return {"error": "No performance data available"}
        
        current_snapshot = self.performance_history[-1]
        
        # Scoring criteria (each out of 100)
        hit_rate_score = min(100, current_snapshot.hit_rate_percent * 1.25)  # 80% = 100 points
        response_time_score = max(0, 100 - (current_snapshot.average_response_time_ms * 10))  # <1ms = 100 points
        reliability_score = 100 if current_snapshot.circuit_breaker_state == "closed" else 0
        error_rate_score = max(0, 100 - (current_snapshot.errors_count * 10))
        
        # Weighted overall score
        overall_score = (
            hit_rate_score * 0.4 +
            response_time_score * 0.3 +
            reliability_score * 0.2 +
            error_rate_score * 0.1
        )
        
        return {
            "overall_score": round(overall_score, 1),
            "grade": self._get_performance_grade(overall_score),
            "breakdown": {
                "hit_rate_score": round(hit_rate_score, 1),
                "response_time_score": round(response_time_score, 1),
                "reliability_score": round(reliability_score, 1),
                "error_rate_score": round(error_rate_score, 1)
            },
            "current_metrics": {
                "hit_rate_percent": current_snapshot.hit_rate_percent,
                "average_response_time_ms": current_snapshot.average_response_time_ms,
                "circuit_breaker_state": current_snapshot.circuit_breaker_state,
                "errors_count": current_snapshot.errors_count
            }
        }
    
    def _get_performance_grade(self, score: float) -> str:
        """Get letter grade for cache performance score."""
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"
    
    async def export_performance_data(self, format: str = "json") -> Dict[str, Any]:
        """Export performance data in specified format."""
        if format == "json":
            # Convert snapshots to dict and handle datetime serialization
            snapshots_data = []
            for snapshot in self.performance_history:
                snapshot_dict = asdict(snapshot)
                # Convert datetime to ISO string
                snapshot_dict['timestamp'] = snapshot_dict['timestamp'].isoformat()
                snapshots_data.append(snapshot_dict)
                
            return {
                "export_timestamp": datetime.utcnow().isoformat(),
                "snapshots_count": len(self.performance_history),
                "snapshots": snapshots_data
            }
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    async def reset_metrics(self) -> None:
        """Reset all monitoring metrics and history."""
        self.performance_history.clear()
        self.operation_types.clear()
        logger.info("Cache monitoring metrics reset")


# Global monitoring service instance
monitoring_service: Optional[CacheMonitoringService] = None


async def get_cache_monitoring_service(settings: Settings) -> Optional[CacheMonitoringService]:
    """Get or create the global cache monitoring service instance."""
    global monitoring_service
    
    if monitoring_service is None:
        monitoring_service = CacheMonitoringService(settings)
        success = await monitoring_service.initialize()
        if not success:
            monitoring_service = None
            logger.warning("Cache monitoring service initialization failed")
    
    return monitoring_service


async def start_cache_monitoring(settings: Settings) -> None:
    """Start cache monitoring as a background task."""
    service = await get_cache_monitoring_service(settings)
    if service:
        # Start monitoring in background
        asyncio.create_task(service.start_monitoring())
        logger.info("Cache monitoring started as background task")
    else:
        logger.warning("Failed to start cache monitoring - service unavailable")


async def cleanup_cache_monitoring() -> None:
    """Cleanup the global cache monitoring service."""
    global monitoring_service
    
    if monitoring_service:
        monitoring_service.stop_monitoring()
        monitoring_service = None
        logger.info("Cache monitoring service cleaned up")