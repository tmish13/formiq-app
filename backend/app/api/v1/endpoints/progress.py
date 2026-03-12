"""Progress tracking endpoints for user exercise progress."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from uuid import UUID

from app.api import deps
from app.models.user import User
from app.models.form_check import FormCheck
from app.core.logging import get_logger
from sqlalchemy import select, func, and_, or_

# Initialize logger
logger = get_logger(__name__)

# Initialize router
router = APIRouter(prefix="/progress", tags=["progress"])


@router.get("/overview", response_model=Dict[str, Any])
async def get_progress_overview(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: User = Depends(deps.get_current_user),
    exercise_type: Optional[str] = Query(None, description="Filter by exercise type (e.g. 'squat')")
) -> Dict[str, Any]:
    """
    Get progress overview with streaks and key metrics.

    Returns:
        Progress overview data including streaks and statistics
    """
    try:
        # Get user's form checks for calculations
        query = select(FormCheck).filter(FormCheck.user_id == current_user.id)
        if exercise_type:
            query = query.filter(
                or_(
                    FormCheck.exercise_type == exercise_type,
                    FormCheck.classified_exercise_slug == exercise_type,
                )
            )
        result = await db.execute(query)
        form_checks = result.scalars().all()
        
        completed_checks = [fc for fc in form_checks if fc.status == 'completed' and fc.score is not None]
        
        # Calculate current streak
        current_streak = await _calculate_streak(current_user.id, db)
        
        # Calculate average score
        if completed_checks:
            total_score = sum(fc.score for fc in completed_checks)
            average_score = total_score / len(completed_checks)
        else:
            average_score = 0
        
        # Calculate total sessions
        total_sessions = len(completed_checks)
        
        # Calculate weekly improvement
        weekly_improvement = await _calculate_weekly_improvement(current_user.id, db)
        
        return {
            "currentStreak": current_streak,
            "averageScore": round(average_score, 1),
            "totalSessions": total_sessions,
            "weeklyImprovement": round(weekly_improvement, 1)
        }
        
    except Exception as e:
        logger.error(f"Error getting progress overview: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting progress overview: {str(e)}"
        )


@router.get("/history", response_model=List[Dict[str, Any]])
async def get_progress_history(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: User = Depends(deps.get_current_user),
    exercise_type: Optional[str] = Query(None, description="Filter by exercise type"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
) -> List[Dict[str, Any]]:
    """
    Get historical progress data with optional filtering.
    
    Args:
        exercise_type: Optional exercise type filter
        start_date: Optional start date filter
        end_date: Optional end date filter
        limit: Maximum number of records
        offset: Number of records to skip
        
    Returns:
        List of progress data points
    """
    try:
        # Build query
        query = select(FormCheck).filter(FormCheck.user_id == current_user.id)
        
        if exercise_type:
            query = query.filter(FormCheck.exercise_type == exercise_type)
        
        if start_date:
            start_dt = datetime.fromisoformat(start_date)
            query = query.filter(FormCheck.created_at >= start_dt)
        
        if end_date:
            end_dt = datetime.fromisoformat(end_date)
            query = query.filter(FormCheck.created_at <= end_dt)
        
        query = query.order_by(FormCheck.created_at.desc()).offset(offset).limit(limit)
        
        result = await db.execute(query)
        form_checks = result.scalars().all()
        
        # Convert to progress data format
        progress_data = []
        for fc in form_checks:
            progress_data.append({
                "id": str(fc.id),
                "userId": str(fc.user_id),
                "exerciseType": fc.exercise_type,
                "score": fc.score,
                "feedback": fc.feedback or [],
                "riskLevel": _calculate_risk_level(fc.score) if fc.score else "medium",
                "createdAt": fc.created_at.isoformat(),
                "videoUrl": fc.video_url
            })
        
        return progress_data
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date format: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error getting progress history: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting progress history: {str(e)}"
        )


@router.get("/stats", response_model=Dict[str, Any])
async def get_progress_stats(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: User = Depends(deps.get_current_user),
    time_range: Optional[str] = Query(None, description="Time range (7d, 30d, 90d, 1y)"),
    exercise_type: Optional[str] = Query(None, description="Filter by exercise type (e.g. 'squat')")
) -> Dict[str, Any]:
    """
    Get progress statistics and metrics.

    Args:
        time_range: Time range filter
        exercise_type: Optional exercise type filter

    Returns:
        Progress statistics
    """
    try:
        # Calculate time filter
        cutoff_date = _get_cutoff_date(time_range)

        # Get user's form checks
        query = select(FormCheck).filter(FormCheck.user_id == current_user.id)
        if cutoff_date:
            query = query.filter(FormCheck.created_at >= cutoff_date)
        if exercise_type:
            query = query.filter(
                or_(
                    FormCheck.exercise_type == exercise_type,
                    FormCheck.classified_exercise_slug == exercise_type,
                )
            )
        
        result = await db.execute(query)
        form_checks = result.scalars().all()
        
        completed_checks = [fc for fc in form_checks if fc.status == 'completed' and fc.score is not None]
        
        # Calculate basic stats
        total_analyses = len(completed_checks)
        if completed_checks:
            scores = [fc.score for fc in completed_checks]
            average_score = sum(scores) / len(scores)
        else:
            average_score = 0
        
        # Calculate exercise type breakdown
        exercise_breakdown = {}
        for fc in completed_checks:
            key = fc.classified_exercise_slug or "unknown"
            if key not in exercise_breakdown:
                exercise_breakdown[key] = 0
            exercise_breakdown[key] += 1
        
        # Calculate improvement rate
        improvement_rate = await _calculate_improvement_rate(current_user.id, db)
        
        # Determine recent trend
        recent_trend = _determine_recent_trend(improvement_rate)
        
        # Include streak so callers can avoid a second round-trip
        current_streak = await _calculate_streak(current_user.id, db)

        return {
            "averageScore": round(average_score, 1),
            "improvementRate": round(improvement_rate, 1),
            "totalAnalyses": total_analyses,
            "exerciseTypeBreakdown": exercise_breakdown,
            "recentTrend": recent_trend,
            "currentStreak": current_streak,
        }

    except Exception as e:
        logger.error(f"Error getting progress stats: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting progress stats: {str(e)}"
        )


@router.get("/trends", response_model=Dict[str, Any])
async def get_progress_trends(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: User = Depends(deps.get_current_user),
    days: int = Query(30, ge=7, le=365, description="Number of days to analyze")
) -> Dict[str, Any]:
    """
    Get progress trends grouped by ISO week.

    Args:
        days: Number of days to look back (default 30).

    Returns:
        {
            "weekly_progress": [
                {"week_start": "2026-02-10", "avg_score": 82.5, "sessions": 3},
                ...
            ],
            "improvement_rate": 8.97   # % change first→last week; 0 if <2 weeks of data
        }
    """
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        query = select(FormCheck).filter(
            and_(
                FormCheck.user_id == current_user.id,
                FormCheck.created_at >= start_date,
                FormCheck.created_at <= end_date,
                FormCheck.status == 'completed',
                FormCheck.score.isnot(None)
            )
        ).order_by(FormCheck.created_at)

        result = await db.execute(query)
        form_checks = result.scalars().all()

        # Group by ISO week (Monday = start of week)
        weekly: Dict[str, Dict[str, Any]] = {}
        for fc in form_checks:
            # Monday of the week containing fc.created_at
            iso_monday = fc.created_at.date() - timedelta(days=fc.created_at.weekday())
            key = iso_monday.isoformat()
            if key not in weekly:
                weekly[key] = {"week_start": key, "scores": [], "sessions": 0}
            weekly[key]["scores"].append(fc.score)
            weekly[key]["sessions"] += 1

        weekly_progress = []
        for key in sorted(weekly):
            entry = weekly[key]
            avg_score = sum(entry["scores"]) / len(entry["scores"])
            weekly_progress.append({
                "week_start": entry["week_start"],
                "avg_score": round(avg_score, 1),
                "sessions": entry["sessions"],
            })

        # Improvement rate: % change from first week avg to last week avg
        improvement_rate = 0.0
        if len(weekly_progress) >= 2:
            first_avg = weekly_progress[0]["avg_score"]
            last_avg = weekly_progress[-1]["avg_score"]
            if first_avg > 0:
                improvement_rate = round(((last_avg - first_avg) / first_avg) * 100, 2)

        return {
            "weekly_progress": weekly_progress,
            "improvement_rate": improvement_rate,
        }

    except Exception as e:
        logger.error(f"Error getting progress trends: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting progress trends: {str(e)}"
        )


@router.get("/analytics", response_model=Dict[str, Any])
async def get_progress_analytics(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: User = Depends(deps.get_current_user),
    exercise_type: Optional[str] = Query(None),
    limit: int = Query(10, ge=3, le=20),
) -> Dict[str, Any]:
    """Last N sessions with component scores, trend via linear regression."""
    try:
        query = (
            select(FormCheck)
            .where(
                FormCheck.user_id == current_user.id,
                FormCheck.status == "completed",
                FormCheck.posture_score.isnot(None),
            )
        )
        if exercise_type:
            query = query.where(
                or_(
                    FormCheck.exercise_type == exercise_type,
                    FormCheck.classified_exercise_slug == exercise_type,
                )
            )
        query = query.order_by(FormCheck.created_at.desc()).limit(limit)
        result = await db.execute(query)
        checks = list(reversed(result.scalars().all()))  # chronological order

        sessions = []
        for fc in checks:
            pv1 = (fc.results or {}).get("posture_v1", {})
            sessions.append({
                "id": str(fc.id),
                "date": fc.created_at.isoformat(),
                "posture_score": fc.posture_score,
                "named_scores": pv1.get("named_scores"),
                "score_band": pv1.get("score_band"),
                "decision": pv1.get("decision"),
            })

        scores = [s["posture_score"] for s in sessions if s["posture_score"] is not None]
        trend_label = "Plateau"
        if len(scores) >= 3:
            xs = list(range(len(scores)))
            n = len(xs)
            sx, sy = sum(xs), sum(scores)
            sxy = sum(x * y for x, y in zip(xs, scores))
            sxx = sum(x * x for x in xs)
            denom = n * sxx - sx * sx
            slope = (n * sxy - sx * sy) / denom if denom != 0 else 0.0
            if slope > 0.5:
                trend_label = "Improving"
            elif slope < -0.5:
                trend_label = "Declining"

        best_score = max(scores) if scores else None
        avg_last_5 = round(sum(scores[-5:]) / min(len(scores), 5), 1) if scores else None
        improvement = round(scores[-1] - scores[0], 1) if len(scores) >= 2 else None

        # Weight trend (only sessions where user entered weight)
        weight_data = [
            {"date": fc.created_at.isoformat(), "weight_kg": fc.weight_kg}
            for fc in checks
            if getattr(fc, 'weight_kg', None) is not None
        ]
        best_weight = max((w["weight_kg"] for w in weight_data), default=None)

        return {
            "sessions": sessions,
            "trend": trend_label,
            "best_score_ever": best_score,
            "avg_last_5": avg_last_5,
            "improvement_since_first": improvement,
            "session_count": len(sessions),
            "weight_trend": weight_data,
            "best_weight": best_weight,
        }
    except Exception as e:
        logger.error(f"Error getting progress analytics: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting progress analytics: {str(e)}",
        )


@router.post("/save", response_model=Dict[str, Any])
async def save_progress(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: User = Depends(deps.get_current_user),
    progress_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Save new progress data.
    
    Args:
        progress_data: Progress data to save
        
    Returns:
        Saved progress data
    """
    try:
        # This would typically create or update a progress record
        # For now, we'll simulate saving progress by returning the data with ID
        import uuid
        saved_data = {
            "id": str(uuid.uuid4()),
            "userId": str(current_user.id),
            "createdAt": datetime.now().isoformat(),
            **progress_data
        }
        
        logger.info(f"Progress data saved for user {current_user.id}")
        return saved_data
        
    except Exception as e:
        logger.error(f"Error saving progress: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error saving progress: {str(e)}"
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


async def _calculate_streak(user_id: UUID, db_session: AsyncSession) -> int:
    """Calculate current streak of consecutive days with workouts."""
    try:
        # Get all completed form checks ordered by date
        query = select(FormCheck).filter(
            and_(
                FormCheck.user_id == user_id,
                FormCheck.status == 'completed'
            )
        ).order_by(FormCheck.created_at.desc())
        
        result = await db_session.execute(query)
        form_checks = result.scalars().all()
        
        if not form_checks:
            return 0
        
        # Calculate streak
        streak = 0
        today = datetime.now().date()
        current_date = today
        
        # Group form checks by date
        dates_with_workouts = set()
        for fc in form_checks:
            dates_with_workouts.add(fc.created_at.date())
        
        # Count consecutive days starting from today
        while current_date in dates_with_workouts:
            streak += 1
            current_date -= timedelta(days=1)
        
        return streak
        
    except Exception as e:
        logger.error(f"Error calculating streak: {str(e)}", exc_info=True)
        return 0


async def _calculate_weekly_improvement(user_id: UUID, db_session: AsyncSession) -> float:
    """Calculate weekly improvement percentage."""
    try:
        now = datetime.now()
        one_week_ago = now - timedelta(days=7)
        two_weeks_ago = now - timedelta(days=14)
        
        # Get this week's scores
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
        
        # Get last week's scores
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
        logger.error(f"Error calculating weekly improvement: {str(e)}", exc_info=True)
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


def _calculate_risk_level(score: float) -> str:
    """Calculate risk level based on score."""
    if score >= 80:
        return "low"
    elif score >= 60:
        return "medium"
    else:
        return "high"


def _determine_recent_trend(improvement_rate: float) -> str:
    """Determine recent trend based on improvement rate."""
    if improvement_rate > 5:
        return "improving"
    elif improvement_rate < -5:
        return "declining"
    else:
        return "stable"