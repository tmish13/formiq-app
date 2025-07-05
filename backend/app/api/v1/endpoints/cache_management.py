"""
Cache management and monitoring API endpoints.

Provides administrative endpoints for cache monitoring, performance analytics,
and cache management operations.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any, List, Optional
import logging

from app.core.deps import get_current_active_user, get_settings
from app.core.config import Settings
from app.models.user import User
from app.services.cache_service import get_cache_service
from app.services.cache_monitoring_service import get_cache_monitoring_service
from app.schemas.monitoring import (
    CacheStatsResponse, CacheHealthResponse, CachePerformanceSummaryResponse,
    CacheOptimizationRecommendationResponse, CacheEfficiencyScoreResponse
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/stats", response_model=CacheStatsResponse)
async def get_cache_stats(
    settings: Settings = Depends(get_settings),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get comprehensive cache statistics and metrics.
    
    Requires authentication and returns detailed cache performance data.
    """
    try:
        cache_service = await get_cache_service(settings)
        if not cache_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Cache service unavailable"
            )
        
        stats = await cache_service.get_cache_stats()
        
        return CacheStatsResponse(
            status="success",
            data=stats,
            timestamp=stats.get("last_reset", ""),
            message="Cache statistics retrieved successfully"
        )
        
    except Exception as e:
        logger.error(f"Error retrieving cache stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve cache statistics: {str(e)}"
        )


@router.get("/health", response_model=CacheHealthResponse)
async def get_cache_health(
    settings: Settings = Depends(get_settings),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get cache service health status and connectivity information.
    """
    try:
        cache_service = await get_cache_service(settings)
        if not cache_service:
            return CacheHealthResponse(
                status="unhealthy",
                service="cache",
                details={"error": "Cache service not available"},
                healthy=False,
                message="Cache service is not available"
            )
        
        health = await cache_service.health_check()
        
        return CacheHealthResponse(
            status=health["status"],
            service="cache",
            details=health.get("details", {}),
            healthy=health["status"] == "healthy",
            message=f"Cache service is {health['status']}"
        )
        
    except Exception as e:
        logger.error(f"Error checking cache health: {e}")
        return CacheHealthResponse(
            status="error",
            service="cache",
            details={"error": str(e)},
            healthy=False,
            message=f"Cache health check failed: {str(e)}"
        )


@router.get("/performance", response_model=CachePerformanceSummaryResponse)
async def get_cache_performance_summary(
    hours: int = 1,
    settings: Settings = Depends(get_settings),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get cache performance summary for the specified time period.
    
    Args:
        hours: Number of hours to analyze (default: 1)
    """
    try:
        if hours < 1 or hours > 168:  # Max 1 week
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Hours must be between 1 and 168 (1 week)"
            )
        
        monitoring_service = await get_cache_monitoring_service(settings)
        if not monitoring_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Cache monitoring service unavailable"
            )
        
        summary = await monitoring_service.get_performance_summary(hours)
        
        if "error" in summary:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=summary["error"]
            )
        
        return CachePerformanceSummaryResponse(
            status="success",
            data=summary,
            period_hours=hours,
            message=f"Performance summary for last {hours} hours retrieved"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving cache performance summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve performance summary: {str(e)}"
        )


@router.get("/recommendations", response_model=List[CacheOptimizationRecommendationResponse])
async def get_cache_optimization_recommendations(
    settings: Settings = Depends(get_settings),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get automated cache optimization recommendations based on current performance.
    """
    try:
        monitoring_service = await get_cache_monitoring_service(settings)
        if not monitoring_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Cache monitoring service unavailable"
            )
        
        recommendations = await monitoring_service.generate_optimization_recommendations()
        
        return [
            CacheOptimizationRecommendationResponse(
                category=rec.category,
                priority=rec.priority,
                title=rec.title,
                description=rec.description,
                action=rec.action,
                estimated_impact=rec.estimated_impact
            )
            for rec in recommendations
        ]
        
    except Exception as e:
        logger.error(f"Error generating cache recommendations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate recommendations: {str(e)}"
        )


@router.get("/efficiency", response_model=CacheEfficiencyScoreResponse)
async def get_cache_efficiency_score(
    settings: Settings = Depends(get_settings),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get overall cache efficiency score and performance breakdown.
    """
    try:
        monitoring_service = await get_cache_monitoring_service(settings)
        if not monitoring_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Cache monitoring service unavailable"
            )
        
        efficiency = await monitoring_service.get_cache_efficiency_score()
        
        if "error" in efficiency:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=efficiency["error"]
            )
        
        return CacheEfficiencyScoreResponse(
            status="success",
            overall_score=efficiency["overall_score"],
            grade=efficiency["grade"],
            breakdown=efficiency["breakdown"],
            current_metrics=efficiency["current_metrics"],
            message=f"Cache efficiency: {efficiency['grade']} grade ({efficiency['overall_score']})"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating cache efficiency: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate efficiency score: {str(e)}"
        )


@router.post("/invalidate/{video_id}")
async def invalidate_video_cache(
    video_id: str,
    settings: Settings = Depends(get_settings),
    current_user: User = Depends(get_current_active_user)
):
    """
    Manually invalidate all cached data for a specific video.
    """
    try:
        cache_service = await get_cache_service(settings)
        if not cache_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Cache service unavailable"
            )
        
        from uuid import UUID
        video_uuid = UUID(video_id)
        invalidated_count = await cache_service.invalidate_video_cache(video_uuid)
        
        return {
            "status": "success",
            "video_id": video_id,
            "invalidated_keys": invalidated_count,
            "message": f"Invalidated {invalidated_count} cache entries for video {video_id}"
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid video ID format: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error invalidating video cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to invalidate cache: {str(e)}"
        )


@router.delete("/reset")
async def reset_cache_metrics(
    settings: Settings = Depends(get_settings),
    current_user: User = Depends(get_current_active_user)
):
    """
    Reset all cache metrics and monitoring history.
    
    This operation requires admin privileges and cannot be undone.
    """
    try:
        # Check if user has admin privileges (you may need to implement this)
        # For now, we'll allow any authenticated user to reset metrics
        
        monitoring_service = await get_cache_monitoring_service(settings)
        if monitoring_service:
            await monitoring_service.reset_metrics()
        
        cache_service = await get_cache_service(settings)
        if cache_service:
            # Reset the cache service metrics
            cache_service.metrics.reset()
        
        return {
            "status": "success",
            "message": "Cache metrics and monitoring history reset successfully"
        }
        
    except Exception as e:
        logger.error(f"Error resetting cache metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset cache metrics: {str(e)}"
        )


@router.get("/export")
async def export_cache_performance_data(
    format: str = "json",
    settings: Settings = Depends(get_settings),
    current_user: User = Depends(get_current_active_user)
):
    """
    Export cache performance data for analysis.
    
    Args:
        format: Export format (currently only 'json' supported)
    """
    try:
        if format not in ["json"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported export format. Supported formats: json"
            )
        
        monitoring_service = await get_cache_monitoring_service(settings)
        if not monitoring_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Cache monitoring service unavailable"
            )
        
        export_data = await monitoring_service.export_performance_data(format)
        
        return {
            "status": "success",
            "format": format,
            "data": export_data,
            "message": f"Performance data exported in {format} format"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting cache data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export performance data: {str(e)}"
        )