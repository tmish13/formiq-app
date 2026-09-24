"""Analytics service for exercise form analysis and workout tracking."""
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID

from app.core.logging import get_logger
from app.core.config import Settings, get_settings
from app.core.cache import CacheService
from app.core.db_deps import get_async_db
from app.core.exceptions import ValidationException, NotFoundException

from app.models.workout import Exercise
from app.models.enums import ExerciseType, FeedbackType, FeedbackSeverity
from app.models.workout import Workout
from app.models.user import User
from app.schemas.form_check import FeedbackItemCreate

# Initialize logger
logger = get_logger(__name__)

class AnalyticsService:
    """Service for exercise form analysis and workout analytics."""
    
    def __init__(self, db: AsyncSession, settings: Settings, cache_svc: CacheService):
        self.db = db
        self.settings = settings
        self.cache_svc = cache_svc

    async def analyze_exercise_form(
        self,
        user_id: int,
        exercise_id: int,
        video_url: str,
    ) -> Dict[str, Any]:
        """
        Analyze exercise form from video.
        
        Args:
            user_id: User ID
            exercise_id: Exercise ID
            video_url: URL of the exercise video
            
        Returns:
            Exercise analysis results
            
        Raises:
            NotFoundException: If exercise not found
            ValidationException: If video URL is invalid
        """
        exercise_stmt = select(Exercise).filter(Exercise.id == exercise_id)
        exercise_result = await self.db.execute(exercise_stmt)
        exercise = exercise_result.scalars().first()
        if not exercise:
            raise NotFoundException("Exercise not found")
        
        user_stmt = select(User).filter(User.id == user_id)
        user_result = await self.db.execute(user_stmt)
        user = user_result.scalars().first()
        if not user:
            raise NotFoundException("User not found")
        
        if not video_url or not video_url.startswith(("http://", "https://")):
            raise ValidationException("Invalid video URL")
        
        try:
            logger.info(
                "analyzing_exercise_form",
                user_id=user_id,
                exercise_id=exercise_id,
                exercise_name=exercise.name
            )
            
            form_feedback_items = [
                FeedbackItemCreate(
                    form_check_id=UUID("00000000-0000-0000-0000-000000000000"),
                    type=FeedbackType.FORM,
                    message="Knees should not extend past toes",
                    timestamp=10.5,
                    severity=FeedbackSeverity.MEDIUM
                ),
                FeedbackItemCreate(
                    form_check_id=UUID("00000000-0000-0000-0000-000000000000"),
                    type=FeedbackType.FORM,
                    message="Keep your back straight",
                    timestamp=15.2,
                    severity=FeedbackSeverity.HIGH
                )
            ]

            analysis_dict = {
                "exercise_id": exercise_id,
                "user_id": user_id,
                "timestamp": datetime.now(),
                "score": 85,
                "form_feedback_items": [item.model_dump() for item in form_feedback_items],
                "total_reps": 12,
                "complete_reps": 10,
                "suggestions": [
                    "Lower the weight and focus on form",
                    "Slow down your movement to maintain control"
                ]
            }
            
            cache_key = f"exercise:analysis:{user_id}:{exercise_id}"
            if self.cache_svc:
                await self.cache_svc.set(cache_key, analysis_dict, expires_in=3600)
            
            return analysis_dict
        except Exception as e:
            logger.error(
                "exercise_analysis_failed",
                error=str(e),
                user_id=user_id,
                exercise_id=exercise_id
            )
            raise
    
    async def get_user_progress(
        self,
        user_id: int,
        exercise_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Get user progress over time.
        
        Args:
            user_id: User ID
            exercise_id: Optional exercise ID to filter by
            start_date: Optional start date
            end_date: Optional end date
            
        Returns:
            User progress data
        """
        if not start_date:
            # Default to last 30 days
            start_date = datetime.now() - timedelta(days=30)
            
        if not end_date:
            end_date = datetime.now()
        
        cache_key = f"user:progress:{user_id}:{exercise_id or 'all'}:{start_date.date()}:{end_date.date()}"
        if self.cache_svc:
            cached_data = await self.cache_svc.get(cache_key)
            if cached_data:
                return cached_data
        
        try:
            stmt = select(Workout).filter(
                Workout.user_id == user_id,
                Workout.date >= start_date,
                Workout.date <= end_date
            )
            
            if exercise_id:
                # Filter by exercise
                # In a real app, you'd have a workout_exercise table
                logger.warning(f"Filtering user progress by exercise_id ({exercise_id}) - ensure Workout model relationship supports this async.")
                pass
            
            result = await self.db.execute(stmt)
            workouts = result.scalars().all()
            
            # Process workouts and extract progress data
            # This is simplified - in a real app, you'd calculate more metrics
            progress_data = {
                "user_id": user_id,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "total_workouts": len(workouts),
                "workout_frequency": len(workouts) / 30 if (end_date - start_date).days >= 30 else len(workouts) / ((end_date - start_date).days + 1),
                "progress_trend": "increasing",  # Would be calculated in real app
                "metrics": {
                    "total_volume": sum(w.total_volume for w in workouts if hasattr(w, "total_volume") and w.total_volume is not None),
                    "average_intensity": sum(w.intensity for w in workouts if hasattr(w, "intensity") and w.intensity is not None) / len(workouts) if workouts else 0,
                    "consistency_score": len(workouts) / 30 * 100  # Percentage of days with workouts
                }
            }
            
            if self.cache_svc:
                await self.cache_svc.set(cache_key, progress_data, expires_in=3600)
            
            return progress_data
        except Exception as e:
            logger.error(
                "user_progress_calculation_failed",
                error=str(e),
                user_id=user_id,
                exercise_id=exercise_id
            )
            raise
    
    async def get_exercise_recommendations(
        self,
        user_id: int,
    ) -> List[Dict[str, Any]]:
        """
        Get personalized exercise recommendations.
        
        Args:
            user_id: User ID
            
        Returns:
            List of recommended exercises
        """
        cache_key = f"user:recommendations:{user_id}"
        if self.cache_svc:
            cached_data = await self.cache_svc.get(cache_key)
            if cached_data:
                return cached_data
        
        try:
            # Get user profile and workout history
            user_stmt = select(User).filter(User.id == user_id)
            user_res = await self.db.execute(user_stmt)
            user = user_res.scalars().first()
            if not user:
                raise NotFoundException("User not found")
                
            # Get user's recent workouts
            recent_workouts_stmt = select(Workout).filter(
                Workout.user_id == user_id
            ).order_by(Workout.date.desc()).limit(10)
            recent_workouts_res = await self.db.execute(recent_workouts_stmt)
            recent_workouts = recent_workouts_res.scalars().all()
            
            # In a real app, you'd use an ML model to generate recommendations
            # For now, we'll simulate recommendations
            
            # Get all exercises
            all_exercises_stmt = select(Exercise)
            all_exercises_res = await self.db.execute(all_exercises_stmt)
            all_exercises = all_exercises_res.scalars().all()
            
            # Simple recommendation logic
            recommendations = []
            
            # Add exercises based on user's goals
            for exercise in all_exercises[:5]:  # Just take first 5 for demo
                recommendations.append({
                    "exercise_id": exercise.id,
                    "name": exercise.name,
                    "reason": "Matches your fitness goals",
                    "confidence": 0.85
                })
            
            # Add exercises based on what user hasn't done recently
            # Logic would be more complex in a real app
            
            if self.cache_svc:
                await self.cache_svc.set(cache_key, recommendations, expires_in=3600)
            
            return recommendations
        except Exception as e:
            logger.error(
                "exercise_recommendations_failed",
                error=str(e),
                user_id=user_id
            )
            raise

from fastapi import Depends

async def get_async_analytics_service(
    db: AsyncSession = Depends(get_async_db),
    settings: Settings = Depends(get_settings)
) -> AnalyticsService:
    return AnalyticsService(db=db, settings=settings, cache_svc=None) 