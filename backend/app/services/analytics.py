from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.core.logging import logger
from app.core.cache import cache_service
from app.core.exceptions import ValidationException, NotFoundException
from app.models.exercise import Exercise
from app.models.workout import Workout
from app.models.user import User
from app.schemas.exercise import ExerciseAnalysis, FormFeedback
from app.services.crud import CRUDBase

class AnalyticsService:
    """Service for exercise form analysis and workout analytics."""
    
    @staticmethod
    def analyze_exercise_form(
        user_id: int,
        exercise_id: int,
        video_url: str,
        db: Session
    ) -> ExerciseAnalysis:
        """
        Analyze exercise form from video.
        
        Args:
            user_id: User ID
            exercise_id: Exercise ID
            video_url: URL of the exercise video
            db: Database session
            
        Returns:
            Exercise analysis results
            
        Raises:
            NotFoundException: If exercise not found
            ValidationException: If video URL is invalid
        """
        # Check if exercise exists
        exercise = db.query(Exercise).filter(Exercise.id == exercise_id).first()
        if not exercise:
            raise NotFoundException("Exercise not found")
        
        # Check if user exists
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise NotFoundException("User not found")
        
        # Validate video URL
        if not video_url or not video_url.startswith(("http://", "https://")):
            raise ValidationException("Invalid video URL")
        
        try:
            # In a real application, you would call an external ML service here
            # For now, we'll simulate the analysis
            logger.info(
                "analyzing_exercise_form",
                user_id=user_id,
                exercise_id=exercise_id,
                exercise_name=exercise.name
            )
            
            # Simulated analysis result
            analysis = ExerciseAnalysis(
                exercise_id=exercise_id,
                user_id=user_id,
                timestamp=datetime.now(),
                score=85,  # Simulated score
                form_feedback=[
                    FormFeedback(
                        timestamp=10.5,
                        body_part="knee",
                        message="Knees should not extend past toes",
                        severity="medium"
                    ),
                    FormFeedback(
                        timestamp=15.2,
                        body_part="back",
                        message="Keep your back straight",
                        severity="high"
                    )
                ],
                total_reps=12,
                complete_reps=10,
                suggestions=[
                    "Lower the weight and focus on form",
                    "Slow down your movement to maintain control"
                ]
            )
            
            # Store analysis in cache for quick retrieval
            cache_key = f"exercise:analysis:{user_id}:{exercise_id}"
            cache_service.set(cache_key, analysis.dict(), expire=3600)
            
            return analysis
        except Exception as e:
            logger.error(
                "exercise_analysis_failed",
                error=str(e),
                user_id=user_id,
                exercise_id=exercise_id
            )
            raise
    
    @staticmethod
    def get_user_progress(
        user_id: int,
        exercise_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        db: Session = None
    ) -> Dict[str, Any]:
        """
        Get user progress over time.
        
        Args:
            user_id: User ID
            exercise_id: Optional exercise ID to filter by
            start_date: Optional start date
            end_date: Optional end date
            db: Database session
            
        Returns:
            User progress data
        """
        if not start_date:
            # Default to last 30 days
            start_date = datetime.now() - timedelta(days=30)
            
        if not end_date:
            end_date = datetime.now()
        
        # Check cache first
        cache_key = f"user:progress:{user_id}:{exercise_id or 'all'}:{start_date.date()}:{end_date.date()}"
        cached_data = cache_service.get(cache_key)
        if cached_data:
            return cached_data
        
        try:
            # Query workouts
            query = db.query(Workout).filter(
                Workout.user_id == user_id,
                Workout.date >= start_date,
                Workout.date <= end_date
            )
            
            if exercise_id:
                # Filter by exercise
                # In a real app, you'd have a workout_exercise table
                query = query.filter(Workout.exercises.any(id=exercise_id))
                
            workouts = query.all()
            
            # Process workouts and extract progress data
            # This is simplified - in a real app, you'd calculate more metrics
            progress_data = {
                "user_id": user_id,
                "start_date": start_date,
                "end_date": end_date,
                "total_workouts": len(workouts),
                "workout_frequency": len(workouts) / 30,  # Workouts per day
                "progress_trend": "increasing",  # Would be calculated in real app
                "metrics": {
                    "total_volume": sum(w.total_volume for w in workouts if hasattr(w, "total_volume")),
                    "average_intensity": sum(w.intensity for w in workouts if hasattr(w, "intensity")) / len(workouts) if workouts else 0,
                    "consistency_score": len(workouts) / 30 * 100  # Percentage of days with workouts
                }
            }
            
            # Store in cache
            cache_service.set(cache_key, progress_data, expire=3600)
            
            return progress_data
        except Exception as e:
            logger.error(
                "user_progress_calculation_failed",
                error=str(e),
                user_id=user_id,
                exercise_id=exercise_id
            )
            raise
    
    @staticmethod
    def get_exercise_recommendations(
        user_id: int,
        db: Session
    ) -> List[Dict[str, Any]]:
        """
        Get personalized exercise recommendations.
        
        Args:
            user_id: User ID
            db: Database session
            
        Returns:
            List of recommended exercises
        """
        # Check cache first
        cache_key = f"user:recommendations:{user_id}"
        cached_data = cache_service.get(cache_key)
        if cached_data:
            return cached_data
        
        try:
            # Get user profile and workout history
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise NotFoundException("User not found")
                
            # Get user's recent workouts
            recent_workouts = db.query(Workout).filter(
                Workout.user_id == user_id
            ).order_by(Workout.date.desc()).limit(10).all()
            
            # In a real app, you'd use an ML model to generate recommendations
            # For now, we'll simulate recommendations
            
            # Get all exercises
            all_exercises = db.query(Exercise).all()
            
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
            
            # Store in cache
            cache_service.set(cache_key, recommendations, expire=3600)
            
            return recommendations
        except Exception as e:
            logger.error(
                "exercise_recommendations_failed",
                error=str(e),
                user_id=user_id
            )
            raise

analytics_service = AnalyticsService() 