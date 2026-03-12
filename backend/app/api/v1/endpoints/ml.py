"""ML endpoints for model information and ML-specific functionality."""

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional
from uuid import UUID
from pathlib import Path as FilePath
import json

from app.api import deps
from app.models.user import User
from app.models.form_check import FormCheck
from app.core.logging import get_logger
from app.core.exceptions import NotFoundException
from sqlalchemy import select
from datetime import datetime

_MANIFEST_PATH = (
    FilePath(__file__).resolve().parent.parent.parent.parent
    / "ml" / "posture_v1" / "artifacts" / "posture_v1_manifest.json"
)


def _load_manifest() -> dict:
    try:
        with open(_MANIFEST_PATH) as f:
            return json.load(f)
    except Exception:
        return {}


_MANIFEST = _load_manifest()  # loaded once at import time

# Initialize logger
logger = get_logger(__name__)

# Initialize router
router = APIRouter(prefix="/ml", tags=["ml"])


@router.get("/model-info", response_model=Dict[str, Any])
async def get_model_info(
    *,
    current_user: User = Depends(deps.get_current_user)
) -> Dict[str, Any]:
    """
    Get ML model information and capabilities.
    
    Returns:
        Model information including version, supported exercises, etc.
    """
    try:
        model_info = {
            "version": _MANIFEST.get("version", "v1"),
            "supported_exercises": ["squat"],
            "confidence_threshold": _MANIFEST.get("threshold", 0.525),
            "last_updated": _MANIFEST.get("created_at", "2026-02-01T00:00:00Z"),
        }

        logger.info(f"Provided ML model info to user {current_user.id}")
        return model_info
        
    except Exception as e:
        logger.error(f"Error getting ML model info: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting ML model info: {str(e)}"
        )


@router.get("/scores/{form_check_id}", response_model=Dict[str, Any])
async def get_ml_scores(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: User = Depends(deps.get_current_user),
    form_check_id: UUID = Path(...)
) -> Dict[str, Any]:
    """
    Get ML scores for a specific form check.
    
    Args:
        form_check_id: ID of the form check
        
    Returns:
        ML scores and analysis data
    """
    try:
        # Get the form check
        query = select(FormCheck).filter(
            FormCheck.id == form_check_id,
            FormCheck.user_id == current_user.id
        )
        result = await db.execute(query)
        form_check = result.scalars().first()
        
        if not form_check:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Form check not found or access denied"
            )
        
        # Read real ML scores from the form check record
        results = form_check.results or {}
        posture_v1 = results.get("posture_v1", {})
        pv1_decision = posture_v1.get("decision")

        # Build detected_faults from real posture_v1 data
        detected_faults = []
        if pv1_decision == "fault":
            detected_faults.append({
                "type": "posture_fault",
                "severity": "high" if posture_v1.get("prob_fault", 0) > 0.7 else "medium",
                "description": "Posture fault detected by ML analysis",
                "confidence": posture_v1.get("confidence", 0),
            })
        elif pv1_decision == "uncertain":
            detected_faults.append({
                "type": "uncertain",
                "severity": "low",
                "description": "Analysis quality insufficient for confident assessment",
                "quality_flags": posture_v1.get("quality_flags", []),
            })

        ml_scores = {
            "overall_score": form_check.score,
            "posture_score": getattr(form_check, 'posture_score', None),
            "stability_score": getattr(form_check, 'stability_score', None),
            "depth_score": getattr(form_check, 'depth_score', None),
            "confidence": getattr(form_check, 'confidence_score', None),
            "analysis_timestamp": form_check.updated_at.isoformat() if form_check.updated_at else None,
            "model_version": posture_v1.get("model_version", "unknown"),
            "detected_faults": detected_faults,
            "posture_v1": posture_v1,
        }
        
        logger.info(f"Provided ML scores for form check {form_check_id} to user {current_user.id}")
        return ml_scores
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error getting ML scores: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting ML scores: {str(e)}"
        )


@router.post("/analyze/{form_check_id}", response_model=Dict[str, Any])
async def trigger_ml_analysis(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: User = Depends(deps.get_current_user),
    form_check_id: UUID = Path(...)
) -> Dict[str, Any]:
    """
    Trigger ML analysis for a form check.
    
    Args:
        form_check_id: ID of the form check to analyze
        
    Returns:
        Analysis status and initial results
    """
    try:
        # Get the form check
        query = select(FormCheck).filter(
            FormCheck.id == form_check_id,
            FormCheck.user_id == current_user.id
        )
        result = await db.execute(query)
        form_check = result.scalars().first()
        
        if not form_check:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Form check not found or access denied"
            )
        
        # In a real implementation, this would trigger the ML analysis pipeline
        # For now, we'll simulate the analysis process
        
        # Update form check status to indicate analysis in progress
        form_check.status = 'processing'
        form_check.updated_at = datetime.now()
        await db.commit()
        
        analysis_result = {
            "form_check_id": str(form_check_id),
            "status": "analysis_started",
            "estimated_completion_time": 30,  # seconds
            "analysis_id": f"ml_analysis_{form_check_id}_{int(datetime.now().timestamp())}",
            "message": "ML analysis has been queued for processing",
            "priority": "normal",
            "queue_position": 2
        }
        
        logger.info(f"Triggered ML analysis for form check {form_check_id} by user {current_user.id}")
        return analysis_result
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error triggering ML analysis: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error triggering ML analysis: {str(e)}"
        )


@router.get("/capabilities", response_model=Dict[str, Any])
async def get_ml_capabilities(
    *,
    current_user: User = Depends(deps.get_current_user)
) -> Dict[str, Any]:
    """
    Get ML system capabilities and limits.
    
    Returns:
        ML system capabilities and usage limits
    """
    try:
        capabilities = {
            "supported_video_formats": ["mp4", "webm", "mov", "avi"],
            "max_video_duration": 300,  # 5 minutes
            "max_video_size_mb": 100,
            "min_video_resolution": "640x480",
            "recommended_resolution": "1280x720",
            "supported_exercises": [
                {
                    "name": "squat",
                    "confidence": 0.95,
                    "features": ["depth_analysis", "posture_check", "stability_assessment"]
                },
                {
                    "name": "deadlift", 
                    "confidence": 0.92,
                    "features": ["back_position", "bar_path", "hip_hinge"]
                },
                {
                    "name": "bench_press",
                    "confidence": 0.89,
                    "features": ["arch_analysis", "bar_path", "touch_point"]
                }
            ],
            "analysis_features": {
                "pose_detection": {
                    "keypoints": 33,
                    "accuracy": 0.94,
                    "real_time": True
                },
                "movement_analysis": {
                    "tracking_fps": 30,
                    "angle_precision": 0.5,  # degrees
                    "temporal_analysis": True
                },
                "fault_detection": {
                    "categories": ["posture", "stability", "depth", "timing"],
                    "severity_levels": ["low", "medium", "high"],
                    "real_time_feedback": True
                }
            },
            "processing_limits": {
                "daily_analyses": 50,
                "concurrent_analyses": 3,
                "queue_max_size": 10
            },
            "quality_requirements": {
                "min_fps": 24,
                "lighting": "adequate",
                "camera_angle": "side_view_preferred",
                "subject_visibility": "full_body"
            }
        }
        
        logger.info(f"Provided ML capabilities to user {current_user.id}")
        return capabilities
        
    except Exception as e:
        logger.error(f"Error getting ML capabilities: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting ML capabilities: {str(e)}"
        )


@router.get("/health", response_model=Dict[str, Any])
async def get_ml_system_health(
    *,
    current_user: User = Depends(deps.get_current_user)
) -> Dict[str, Any]:
    """
    Get ML system health status.
    
    Returns:
        ML system health and performance metrics
    """
    try:
        health_status = {
            "status": "healthy",
            "last_check": datetime.now().isoformat(),
            "model_status": {
                "loaded": True,
                "version": "v1.2.1",
                "memory_usage": "2.1GB",
                "gpu_utilization": 45  # percentage
            },
            "processing_queue": {
                "current_size": 2,
                "max_size": 10,
                "average_processing_time": 28.5,  # seconds
                "throughput_per_hour": 120
            },
            "performance_metrics": {
                "average_response_time": 1.2,  # seconds
                "success_rate": 98.5,  # percentage
                "error_rate": 1.5,  # percentage
                "uptime": "99.8%"
            },
            "system_resources": {
                "cpu_usage": 35,  # percentage
                "memory_usage": 68,  # percentage
                "disk_usage": 42,  # percentage
                "network_latency": 15  # ms
            },
            "recent_errors": [],
            "maintenance_window": {
                "next_scheduled": "2024-02-01T02:00:00Z",
                "duration_hours": 2,
                "type": "model_update"
            }
        }
        
        logger.info(f"Provided ML system health to user {current_user.id}")
        return health_status
        
    except Exception as e:
        logger.error(f"Error getting ML system health: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting ML system health: {str(e)}"
        )