"""Exercise service module."""
from typing import List, Optional
from uuid import UUID
from fastapi import Depends

from app.models.exercise import ExerciseTemplate
from app.repositories.exercise_repository import ExerciseRepository, get_exercise_repository
from app.services.base import BaseService


class ExerciseService(BaseService):
    """Service for managing exercises."""

    def __init__(self, repository: ExerciseRepository):
        """Initialize the service."""
        super().__init__(repository)

    async def get_by_id(self, exercise_id: UUID) -> Optional[ExerciseTemplate]:
        """Get an exercise by ID."""
        return await self.repository.get_by_id(exercise_id)

    async def get_all(self) -> List[ExerciseTemplate]:
        """Get all exercises."""
        return await self.repository.get_all()

    async def create(self, exercise: ExerciseTemplate) -> ExerciseTemplate:
        """Create a new exercise."""
        return await self.repository.create(exercise)

    async def update(self, exercise: ExerciseTemplate) -> ExerciseTemplate:
        """Update an exercise."""
        return await self.repository.update(exercise)

    async def delete(self, exercise_id: UUID) -> bool:
        """Delete an exercise."""
        return await self.repository.delete(exercise_id)


def get_exercise_service(
    repository: ExerciseRepository = Depends(get_exercise_repository),
) -> ExerciseService:
    """Get exercise service instance.
    
    Args:
        repository: Exercise repository instance
        
    Returns:
        Exercise service instance
    """
    return ExerciseService(repository=repository) 