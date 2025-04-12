"""Progress tracking service for exercise form analysis."""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json
from sqlalchemy.orm import Session
from app.models.progress import ExerciseProgress
from app.schemas.progress import ProgressMetrics, ProgressUpdate
from app.core.monitoring import track_progress_update

class ProgressService:
    """Service for tracking user exercise progress."""
    
    def __init__(self, db: Session):
        """Initialize progress service."""
        self.db = db
    
    async def update_progress(
        self,
        user_id: int,
        exercise_type: str,
        metrics: ProgressMetrics
    ) -> ExerciseProgress:
        """
        Update user's exercise progress.
        
        Args:
            user_id: ID of the user
            exercise_type: Type of exercise
            metrics: Progress metrics
            
        Returns:
            Updated progress record
        """
        # Get existing progress or create new
        progress = self.db.query(ExerciseProgress).filter(
            ExerciseProgress.user_id == user_id,
            ExerciseProgress.exercise_type == exercise_type
        ).first()
        
        if not progress:
            progress = ExerciseProgress(
                user_id=user_id,
                exercise_type=exercise_type,
                form_score=metrics.form_score,
                consistency_score=metrics.consistency_score,
                total_reps=metrics.reps,
                improvement_areas=json.dumps(metrics.improvement_areas),
                last_updated=datetime.utcnow()
            )
            self.db.add(progress)
        else:
            # Update existing progress
            progress.form_score = (progress.form_score * 0.7 + metrics.form_score * 0.3)
            progress.consistency_score = (progress.consistency_score * 0.7 + metrics.consistency_score * 0.3)
            progress.total_reps += metrics.reps
            
            # Update improvement areas
            current_areas = json.loads(progress.improvement_areas)
            for area in metrics.improvement_areas:
                if area not in current_areas:
                    current_areas.append(area)
            progress.improvement_areas = json.dumps(current_areas)
            
            progress.last_updated = datetime.utcnow()
        
        self.db.commit()
        
        # Track metrics
        track_progress_update(
            user_id=user_id,
            exercise_type=exercise_type,
            metrics_updated=len(metrics.improvement_areas)
        )
        
        return progress
    
    async def get_progress(
        self,
        user_id: int,
        exercise_type: Optional[str] = None,
        time_range: Optional[timedelta] = None
    ) -> List[Dict[str, Any]]:
        """
        Get user's exercise progress.
        
        Args:
            user_id: ID of the user
            exercise_type: Optional exercise type filter
            time_range: Optional time range filter
            
        Returns:
            List of progress records
        """
        query = self.db.query(ExerciseProgress).filter(
            ExerciseProgress.user_id == user_id
        )
        
        if exercise_type:
            query = query.filter(ExerciseProgress.exercise_type == exercise_type)
        
        if time_range:
            cutoff = datetime.utcnow() - time_range
            query = query.filter(ExerciseProgress.last_updated >= cutoff)
        
        progress_records = query.all()
        
        return [
            {
                "exercise_type": record.exercise_type,
                "form_score": record.form_score,
                "consistency_score": record.consistency_score,
                "total_reps": record.total_reps,
                "improvement_areas": json.loads(record.improvement_areas),
                "last_updated": record.last_updated.isoformat()
            }
            for record in progress_records
        ]
    
    async def get_improvement_suggestions(
        self,
        user_id: int,
        exercise_type: str
    ) -> List[str]:
        """
        Get personalized improvement suggestions.
        
        Args:
            user_id: ID of the user
            exercise_type: Type of exercise
            
        Returns:
            List of improvement suggestions
        """
        progress = self.db.query(ExerciseProgress).filter(
            ExerciseProgress.user_id == user_id,
            ExerciseProgress.exercise_type == exercise_type
        ).first()
        
        if not progress:
            return ["Start tracking your progress to get personalized suggestions"]
        
        suggestions = []
        improvement_areas = json.loads(progress.improvement_areas)
        
        # Generate suggestions based on improvement areas
        for area in improvement_areas:
            if area == "form":
                suggestions.append(
                    "Focus on maintaining proper form throughout the exercise"
                )
            elif area == "consistency":
                suggestions.append(
                    "Try to maintain a consistent tempo during your sets"
                )
            elif area == "range":
                suggestions.append(
                    "Work on achieving full range of motion in your movements"
                )
            elif area == "balance":
                suggestions.append(
                    "Practice exercises that improve your balance and stability"
                )
        
        return suggestions
    
    async def get_progress_summary(
        self,
        user_id: int,
        time_range: timedelta = timedelta(days=30)
    ) -> Dict[str, Any]:
        """
        Get summary of user's progress across all exercises.
        
        Args:
            user_id: ID of the user
            time_range: Time range for summary
            
        Returns:
            Progress summary
        """
        cutoff = datetime.utcnow() - time_range
        progress_records = self.db.query(ExerciseProgress).filter(
            ExerciseProgress.user_id == user_id,
            ExerciseProgress.last_updated >= cutoff
        ).all()
        
        summary = {
            "total_exercises": len(progress_records),
            "total_reps": sum(record.total_reps for record in progress_records),
            "average_form_score": sum(record.form_score for record in progress_records) / len(progress_records) if progress_records else 0,
            "average_consistency_score": sum(record.consistency_score for record in progress_records) / len(progress_records) if progress_records else 0,
            "exercises": {
                record.exercise_type: {
                    "form_score": record.form_score,
                    "consistency_score": record.consistency_score,
                    "total_reps": record.total_reps,
                    "last_updated": record.last_updated.isoformat()
                }
                for record in progress_records
            }
        }
        
        return summary 