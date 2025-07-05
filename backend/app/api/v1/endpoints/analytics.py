"""Analytics endpoints for form analysis insights and statistics."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List, Optional
from uuid import UUID

from app.api import deps
from app.models.user import User
from app.models.form_check import FormCheck
from app.models.video import Video, VideoStatus
from app.core.logging import get_logger
from app.core.exceptions import NotFoundException
from sqlalchemy import select, func, and_, desc
from datetime import datetime, timedelta

# Initialize logger
logger = get_logger(__name__)

# Initialize router
router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview", response_model=Dict[str, Any])
async def get_analytics_overview(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: User = Depends(deps.get_current_user),
    time_range: Optional[str] = Query(None, description="Time range filter (7d, 30d, 90d, 1y)")
) -> Dict[str, Any]:
    """
    Get analytics overview for dashboard.
    
    Args:
        time_range: Time range filter (7d, 30d, 90d, 1y)
        
    Returns:
        Analytics overview data
    """
    try:
        # Calculate time filter
        cutoff_date = _get_cutoff_date(time_range)
        
        # Get user's form checks
        query = select(FormCheck).filter(FormCheck.user_id == current_user.id)
        if cutoff_date:
            query = query.filter(FormCheck.created_at >= cutoff_date)
        
        result = await db.execute(query)
        form_checks = result.scalars().all()
        
        # Calculate basic stats
        total_sessions = len(form_checks)
        completed_checks = [fc for fc in form_checks if fc.status == 'completed' and fc.score is not None]
        
        # Calculate average score
        if completed_checks:
            total_score = sum(fc.score for fc in completed_checks)
            average_score = total_score / len(completed_checks)
        else:
            average_score = 0
        
        # Find best exercise
        exercise_scores = {}
        for fc in completed_checks:
            if fc.exercise_type not in exercise_scores:
                exercise_scores[fc.exercise_type] = []
            exercise_scores[fc.exercise_type].append(fc.score)
        
        best_exercise = None
        best_avg = 0
        for exercise, scores in exercise_scores.items():
            avg = sum(scores) / len(scores)
            if avg > best_avg:
                best_avg = avg
                best_exercise = exercise
        
        # Calculate weekly progress
        weekly_progress = await _calculate_weekly_progress(current_user.id, db)
        
        # Calculate improvement rate
        improvement_rate = await _calculate_improvement_rate(current_user.id, db)
        
        return {
            "totalSessions": total_sessions,
            "averageScore": round(average_score, 1),
            "bestExercise": best_exercise,
            "weeklyProgress": round(weekly_progress, 1),
            "improvementRate": round(improvement_rate, 1)
        }
        
    except Exception as e:
        logger.error(f"Error getting analytics overview: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting analytics overview: {str(e)}"
        )


@router.get("/exercise-stats", response_model=List[Dict[str, Any]])
async def get_exercise_statistics(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: User = Depends(deps.get_current_user),
    time_range: Optional[str] = Query(None, description="Time range filter")
) -> List[Dict[str, Any]]:
    """
    Get exercise-specific statistics.
    
    Args:
        time_range: Time range filter
        
    Returns:
        List of exercise statistics
    """
    try:
        # Calculate time filter
        cutoff_date = _get_cutoff_date(time_range)
        
        # Get user's form checks grouped by exercise
        query = select(FormCheck).filter(FormCheck.user_id == current_user.id)
        if cutoff_date:
            query = query.filter(FormCheck.created_at >= cutoff_date)
        
        result = await db.execute(query)
        form_checks = result.scalars().all()
        
        # Group by exercise type
        exercise_groups = {}
        for fc in form_checks:
            if fc.exercise_type not in exercise_groups:
                exercise_groups[fc.exercise_type] = []
            exercise_groups[fc.exercise_type].append(fc)
        
        exercise_stats = []
        for exercise_type, checks in exercise_groups.items():
            completed_checks = [fc for fc in checks if fc.status == 'completed' and fc.score is not None]
            
            if completed_checks:
                scores = [fc.score for fc in completed_checks]
                avg_score = sum(scores) / len(scores)
                best_score = max(scores)
                
                # Calculate improvement
                improvement = _calculate_exercise_improvement(completed_checks)
                trend = 'up' if improvement > 5 else 'down' if improvement < -5 else 'stable'
            else:
                avg_score = 0
                best_score = 0
                improvement = 0
                trend = 'stable'
            
            exercise_stats.append({
                "exercise_type": exercise_type,
                "count": len(completed_checks),
                "avg_score": round(avg_score, 1),
                "best_score": round(best_score, 1),
                "improvement": round(improvement, 1),
                "trend": trend
            })
        
        return exercise_stats
        
    except Exception as e:
        logger.error(f"Error getting exercise statistics: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting exercise statistics: {str(e)}"
        )


@router.get("/time-series", response_model=List[Dict[str, Any]])
async def get_time_series_data(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: User = Depends(deps.get_current_user),
    time_range: Optional[str] = Query(None, description="Time range filter")
) -> List[Dict[str, Any]]:
    """
    Get time series data for charts.
    
    Args:
        time_range: Time range filter
        
    Returns:
        Time series data points
    """
    try:
        # Calculate time filter
        cutoff_date = _get_cutoff_date(time_range)
        
        # Get user's form checks
        query = select(FormCheck).filter(FormCheck.user_id == current_user.id)
        if cutoff_date:
            query = query.filter(FormCheck.created_at >= cutoff_date)
        
        result = await db.execute(query)
        form_checks = result.scalars().all()
        
        # Group by date
        daily_data = {}
        for fc in form_checks:
            date_str = fc.created_at.strftime("%Y-%m-%d")
            if date_str not in daily_data:
                daily_data[date_str] = {
                    "date": date_str,
                    "scores": [],
                    "posture_scores": [],
                    "stability_scores": [],
                    "depth_scores": [],
                    "session_count": 0
                }
            
            day_data = daily_data[date_str]
            day_data["session_count"] += 1
            
            if fc.score is not None:
                day_data["scores"].append(fc.score)
            # Note: Need to add these columns to FormCheck model if they don't exist
            if hasattr(fc, 'posture_score') and fc.posture_score is not None:
                day_data["posture_scores"].append(fc.posture_score)
            if hasattr(fc, 'stability_score') and fc.stability_score is not None:
                day_data["stability_scores"].append(fc.stability_score)
            if hasattr(fc, 'depth_score') and fc.depth_score is not None:
                day_data["depth_scores"].append(fc.depth_score)
        
        # Convert to time series format
        time_series = []
        for date_str, day_data in sorted(daily_data.items()):
            time_series.append({
                "date": date_str,
                "overall_score": round(sum(day_data["scores"]) / len(day_data["scores"]), 1) if day_data["scores"] else 0,
                "posture_score": round(sum(day_data["posture_scores"]) / len(day_data["posture_scores"]), 1) if day_data["posture_scores"] else 0,
                "stability_score": round(sum(day_data["stability_scores"]) / len(day_data["stability_scores"]), 1) if day_data["stability_scores"] else 0,
                "depth_score": round(sum(day_data["depth_scores"]) / len(day_data["depth_scores"]), 1) if day_data["depth_scores"] else 0,
                "session_count": day_data["session_count"]
            })
        
        return time_series
        
    except Exception as e:
        logger.error(f"Error getting time series data: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting time series data: {str(e)}"
        )


@router.get("/performance", response_model=Dict[str, Any])
async def get_performance_metrics(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: User = Depends(deps.get_current_user),
    time_range: Optional[str] = Query(None, description="Time range filter")
) -> Dict[str, Any]:
    """
    Get performance metrics summary.
    
    Args:
        time_range: Time range filter
        
    Returns:
        Performance metrics
    """
    try:
        # Calculate time filter
        cutoff_date = _get_cutoff_date(time_range)
        
        # Get user's form checks
        query = select(FormCheck).filter(FormCheck.user_id == current_user.id)
        if cutoff_date:
            query = query.filter(FormCheck.created_at >= cutoff_date)
        
        result = await db.execute(query)
        form_checks = result.scalars().all()
        
        completed_checks = [fc for fc in form_checks if fc.status == 'completed' and fc.score is not None]
        
        if not completed_checks:
            return {
                "consistency": 0,
                "weakestArea": None,
                "strongestArea": None,
                "targetRecommendations": []
            }
        
        # Calculate consistency (standard deviation of scores)
        scores = [fc.score for fc in completed_checks]
        avg_score = sum(scores) / len(scores)
        variance = sum((score - avg_score) ** 2 for score in scores) / len(scores)
        std_dev = variance ** 0.5
        consistency = max(0, 100 - (std_dev * 10))  # Convert to consistency percentage
        
        # Analyze strongest and weakest areas
        area_scores = {
            'posture': [],
            'stability': [],
            'depth': []
        }
        
        for fc in completed_checks:
            # Note: Need to add these columns to FormCheck model if they don't exist
            if hasattr(fc, 'posture_score') and fc.posture_score is not None:
                area_scores['posture'].append(fc.posture_score)
            if hasattr(fc, 'stability_score') and fc.stability_score is not None:
                area_scores['stability'].append(fc.stability_score)
            if hasattr(fc, 'depth_score') and fc.depth_score is not None:
                area_scores['depth'].append(fc.depth_score)
        
        area_averages = {}
        for area, scores in area_scores.items():
            if scores:
                area_averages[area] = sum(scores) / len(scores)
        
        if area_averages:
            strongest_area = max(area_averages, key=area_averages.get)
            weakest_area = min(area_averages, key=area_averages.get)
        else:
            strongest_area = None
            weakest_area = None
        
        # Generate recommendations
        recommendations = []
        if weakest_area:
            if weakest_area == 'posture':
                recommendations.append("Focus on maintaining neutral spine alignment")
                recommendations.append("Practice core strengthening exercises")
            elif weakest_area == 'stability':
                recommendations.append("Work on balance and coordination drills")
                recommendations.append("Strengthen stabilizing muscles")
            elif weakest_area == 'depth':
                recommendations.append("Practice mobility and flexibility exercises")
                recommendations.append("Work on achieving proper range of motion")
        
        return {
            "consistency": round(consistency, 1),
            "weakestArea": weakest_area,
            "strongestArea": strongest_area,
            "targetRecommendations": recommendations
        }
        
    except Exception as e:
        logger.error(f"Error getting performance metrics: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting performance metrics: {str(e)}"
        )


@router.get("/export", response_class=bytes)
async def export_analytics_data(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: User = Depends(deps.get_current_user),
    format: str = Query(..., description="Export format (csv, json, pdf)"),
    time_range: Optional[str] = Query(None, description="Time range filter")
):
    """
    Export analytics data in specified format.
    
    Args:
        format: Export format (csv, json, pdf)
        time_range: Time range filter
        
    Returns:
        Exported data as bytes
    """
    try:
        # Get form checks data
        cutoff_date = _get_cutoff_date(time_range)
        
        query = select(FormCheck).filter(FormCheck.user_id == current_user.id)
        if cutoff_date:
            query = query.filter(FormCheck.created_at >= cutoff_date)
        
        result = await db.execute(query)
        form_checks = result.scalars().all()
        
        if format == 'json':
            import json
            from fastapi.responses import Response
            
            data = []
            for fc in form_checks:
                data.append({
                    "date": fc.created_at.isoformat(),
                    "exercise_type": fc.exercise_type,
                    "score": fc.score,
                    "status": fc.status,
                    "posture_score": getattr(fc, 'posture_score', None),
                    "stability_score": getattr(fc, 'stability_score', None),
                    "depth_score": getattr(fc, 'depth_score', None)
                })
            
            json_data = json.dumps(data, indent=2)
            return Response(
                content=json_data,
                media_type="application/json",
                headers={"Content-Disposition": "attachment; filename=analytics.json"}
            )
        
        elif format == 'csv':
            import csv
            import io
            from fastapi.responses import Response
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow([
                'Date', 'Exercise Type', 'Score', 'Posture Score', 
                'Stability Score', 'Depth Score', 'Status'
            ])
            
            # Write data
            for fc in form_checks:
                writer.writerow([
                    fc.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    fc.exercise_type,
                    fc.score or '',
                    getattr(fc, 'posture_score', '') or '',
                    getattr(fc, 'stability_score', '') or '',
                    getattr(fc, 'depth_score', '') or '',
                    fc.status
                ])
            
            csv_data = output.getvalue()
            return Response(
                content=csv_data,
                media_type="text/csv",
                headers={"Content-Disposition": "attachment; filename=analytics.csv"}
            )
        
        elif format == 'pdf':
            # Simple text-based PDF alternative (would need proper PDF library for production)
            from fastapi.responses import Response
            
            text_data = f"FormIQ Analytics Report\n\nTotal Sessions: {len(form_checks)}\n\n"
            for fc in form_checks:
                text_data += f"{fc.created_at.strftime('%Y-%m-%d')} - {fc.exercise_type} - Score: {fc.score or 'N/A'}\n"
            
            return Response(
                content=text_data,
                media_type="text/plain",
                headers={"Content-Disposition": "attachment; filename=analytics.txt"}
            )
        
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported export format: {format}"
            )
            
    except Exception as e:
        logger.error(f"Error exporting analytics data: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error exporting analytics data: {str(e)}"
        )


# Helper functions

def _get_cutoff_date(time_range: Optional[str]) -> Optional[datetime]:
    """Get cutoff date based on time range."""
    if not time_range:
        return None
    
    now = datetime.now()
    if time_range == '7d':
        return now - timedelta(days=7)
    elif time_range == '30d':
        return now - timedelta(days=30)
    elif time_range == '90d':
        return now - timedelta(days=90)
    elif time_range == '1y':
        return now - timedelta(days=365)
    else:
        return None


async def _calculate_weekly_progress(user_id: UUID, db_session: AsyncSession) -> float:
    """Calculate weekly progress percentage."""
    try:
        now = datetime.now()
        one_week_ago = now - timedelta(days=7)
        two_weeks_ago = now - timedelta(days=14)
        
        # Get this week's form checks
        this_week_query = select(FormCheck).filter(
            and_(
                FormCheck.user_id == user_id,
                FormCheck.created_at >= one_week_ago,
                FormCheck.status == 'completed',
                FormCheck.score.isnot(None)
            )
        )
        this_week_result = await db_session.execute(this_week_query)
        this_week_checks = this_week_result.scalars().all()
        
        # Get last week's form checks
        last_week_query = select(FormCheck).filter(
            and_(
                FormCheck.user_id == user_id,
                FormCheck.created_at >= two_weeks_ago,
                FormCheck.created_at < one_week_ago,
                FormCheck.status == 'completed',
                FormCheck.score.isnot(None)
            )
        )
        last_week_result = await db_session.execute(last_week_query)
        last_week_checks = last_week_result.scalars().all()
        
        if not this_week_checks or not last_week_checks:
            return 0
        
        this_week_avg = sum(fc.score for fc in this_week_checks) / len(this_week_checks)
        last_week_avg = sum(fc.score for fc in last_week_checks) / len(last_week_checks)
        
        if last_week_avg == 0:
            return 0
        
        return ((this_week_avg - last_week_avg) / last_week_avg) * 100
        
    except Exception as e:
        logger.error(f"Error calculating weekly progress: {str(e)}", exc_info=True)
        return 0


async def _calculate_improvement_rate(user_id: UUID, db_session: AsyncSession) -> float:
    """Calculate overall improvement rate."""
    try:
        query = select(FormCheck).filter(
            and_(
                FormCheck.user_id == user_id,
                FormCheck.status == 'completed',
                FormCheck.score.isnot(None)
            )
        ).order_by(FormCheck.created_at)
        
        result = await db_session.execute(query)
        form_checks = result.scalars().all()
        
        if len(form_checks) < 5:
            return 0
        
        # Compare first 5 vs last 5 sessions
        early_checks = form_checks[:5]
        recent_checks = form_checks[-5:]
        
        early_avg = sum(fc.score for fc in early_checks) / len(early_checks)
        recent_avg = sum(fc.score for fc in recent_checks) / len(recent_checks)
        
        if early_avg == 0:
            return 0
        
        return ((recent_avg - early_avg) / early_avg) * 100
        
    except Exception as e:
        logger.error(f"Error calculating improvement rate: {str(e)}", exc_info=True)
        return 0


def _calculate_exercise_improvement(checks: List[FormCheck]) -> float:
    """Calculate improvement for a specific exercise."""
    if len(checks) < 3:
        return 0
    
    # Sort by date
    sorted_checks = sorted(checks, key=lambda x: x.created_at)
    
    # Compare first third vs last third
    third = len(sorted_checks) // 3
    first_third = sorted_checks[:third] if third > 0 else sorted_checks[:1]
    last_third = sorted_checks[-third:] if third > 0 else sorted_checks[-1:]
    
    first_avg = sum(fc.score for fc in first_third) / len(first_third)
    last_avg = sum(fc.score for fc in last_third) / len(last_third)
    
    if first_avg == 0:
        return 0
    
    return ((last_avg - first_avg) / first_avg) * 100