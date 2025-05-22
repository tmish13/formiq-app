"""Progress tracking service for exercise form analysis."""
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timedelta
import json
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from app.core.config import Settings
from app.models.progress import ExerciseProgress
from app.schemas.progress import ProgressMetrics, ProgressResponse, ProgressSummary, ProgressUpdate
from app.core.monitoring import track_progress_update
from app.services.base_service import BaseService
from fastapi import Depends
from app.core.logging import logger

class ProgressService(BaseService[ExerciseProgress, ProgressMetrics, ProgressUpdate]):
    """Service for tracking user exercise progress."""
    
    def __init__(self, db: Union[AsyncSession, Session], settings: Settings):
        """Initialize progress service."""
        super().__init__(db=db, model=ExerciseProgress, settings=settings)
    
    async def update_progress_async(
        self,
        user_id: int,
        exercise_type: str,
        metrics: ProgressMetrics
    ) -> ProgressResponse:
        """
        Update user's exercise progress.
        
        Args:
            user_id: ID of the user
            exercise_type: Type of exercise
            metrics: Progress metrics
            
        Returns:
            Updated progress record
        """
        stmt = select(self.model).filter(
            self.model.user_id == user_id,
            self.model.exercise_type == exercise_type
        )
        result = await self.db.execute(stmt)
        progress = result.scalars().first()
        
        if not progress:
            progress = self.model(
                user_id=user_id,
                exercise_type=exercise_type,
                form_score=metrics.form_score,
                consistency_score=metrics.consistency_score,
                total_reps=metrics.reps,
                improvement_areas=json.dumps(metrics.improvement_areas or []),
                last_updated=datetime.utcnow()
            )
            self.db.add(progress)
        else:
            # Update existing progress with custom logic
            progress.form_score = (progress.form_score * 0.7 + metrics.form_score * 0.3)
            progress.consistency_score = (progress.consistency_score * 0.7 + metrics.consistency_score * 0.3)
            progress.total_reps += metrics.reps
            
            current_areas = json.loads(progress.improvement_areas or '[]')
            for area in metrics.improvement_areas:
                if area not in current_areas:
                    current_areas.append(area)
            progress.improvement_areas = json.dumps(current_areas)
            
            progress.last_updated = datetime.utcnow()
            self.db.add(progress) # Add to session to mark as dirty for commit
        
        try:
            await self.db.commit()
            await self.db.refresh(progress)
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error committing progress update for user {user_id}, exercise {exercise_type}: {e}", exc_info=True)
            raise
        
        track_progress_update(
            user_id=user_id,
            exercise_type=exercise_type,
            metrics_updated=len(metrics.improvement_areas)
        )
        
        return ProgressResponse.from_orm(progress)
    
    async def get_progress_async(
        self,
        user_id: int,
        exercise_type: Optional[str] = None,
        time_range: Optional[timedelta] = None
    ) -> List[ProgressResponse]:
        """
        Get user's exercise progress.
        
        Args:
            user_id: ID of the user
            exercise_type: Optional exercise type filter
            time_range: Optional time range filter
            
        Returns:
            List of progress records
        """
        stmt = select(self.model).filter(self.model.user_id == user_id)
        
        if exercise_type:
            stmt = stmt.filter(self.model.exercise_type == exercise_type)
        
        if time_range:
            cutoff = datetime.utcnow() - time_range
            stmt = stmt.filter(self.model.last_updated >= cutoff)
        
        stmt = stmt.order_by(self.model.last_updated.desc())
        result = await self.db.execute(stmt)
        progress_records = result.scalars().all()
        
        return [ProgressResponse.from_orm(record) for record in progress_records]
    
    async def get_improvement_suggestions_async(
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
        stmt = select(self.model).filter(
            self.model.user_id == user_id,
            self.model.exercise_type == exercise_type
        )
        result = await self.db.execute(stmt)
        progress = result.scalars().first()
        
        if not progress:
            return ["Start tracking your progress to get personalized suggestions"]
        
        suggestions = []
        try:
            improvement_areas = json.loads(progress.improvement_areas or '[]')
        except json.JSONDecodeError:
            improvement_areas = [] # Handle case where JSON string might be malformed
            logger.warning(f"Could not parse improvement_areas JSON for user {user_id}, exercise {exercise_type}. Value: {progress.improvement_areas}")

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
            # Add more specific suggestions based on areas if desired
        
        if not suggestions and improvement_areas:
            suggestions.append("Continue working on areas like: " + ", ".join(improvement_areas) + ". Great job!")
        elif not suggestions:
            suggestions.append("Keep up the great work! No specific new improvement areas noted recently.")

        return suggestions
    
    async def get_progress_summary_async(
        self,
        user_id: int,
        time_range: timedelta = timedelta(days=30)
    ) -> ProgressSummary:
        """
        Get summary of user's progress across all exercises.
        
        Args:
            user_id: ID of the user
            time_range: Time range for summary
            
        Returns:
            Progress summary
        """
        cutoff = datetime.utcnow() - time_range
        stmt = select(self.model).filter(
            self.model.user_id == user_id,
            self.model.last_updated >= cutoff
        )
        result = await self.db.execute(stmt)
        progress_records = result.scalars().all()
        
        total_exercises = len(set(record.exercise_type for record in progress_records)) # Count unique exercises
        total_reps = sum(record.total_reps for record in progress_records)
        avg_form_score = sum(record.form_score for record in progress_records) / len(progress_records) if progress_records else 0.0
        avg_consistency_score = sum(record.consistency_score for record in progress_records) / len(progress_records) if progress_records else 0.0
        
        exercises_summary = {
            record.exercise_type: {
                "form_score": record.form_score,
                "consistency_score": record.consistency_score,
                "total_reps": record.total_reps,
                "last_updated": record.last_updated.isoformat()
            }
            for record in progress_records
        }
        
        return ProgressSummary(
            total_exercises=total_exercises,
            total_reps=total_reps,
            average_form_score=avg_form_score,
            average_consistency_score=avg_consistency_score,
            exercises=exercises_summary
        )

# Dependency Injectors
async def get_async_progress_service(
    # db: AsyncSession = Depends(get_async_db), # Comment out/remove original Depends here
    # settings: Settings = Depends(get_settings) # Comment out/remove original Depends here
) -> ProgressService:
    from app.core.deps import get_async_db, get_settings # Import locally
    db_session: AsyncSession = Depends(get_async_db)
    current_app_settings: Settings = Depends(get_settings)
    return ProgressService(db=db_session, settings=current_app_settings)

def get_progress_service(
    # db: Session = Depends(get_db), # Comment out/remove original Depends here
    # settings: Settings = Depends(get_settings) # Comment out/remove original Depends here
) -> ProgressService:
    from app.core.deps import get_db, get_settings # Import locally
    db_session: Session = Depends(get_db)
    current_app_settings: Settings = Depends(get_settings)
    logger.warning("Instantiating ProgressService with a synchronous DB session. Async methods will require event loop management.")
    return ProgressService(db=db_session, settings=current_app_settings) 