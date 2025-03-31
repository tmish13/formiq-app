"""Exercise repository module."""
from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session

from app.models.exercise import ExerciseTemplate
from app.repositories.base import BaseRepository


class ExerciseRepository(BaseRepository):
    """Repository for managing exercises."""

    def __init__(self, db: Session):
        """Initialize the repository."""
        super().__init__(db, ExerciseTemplate)

    async def get_by_id(self, exercise_id: UUID) -> Optional[ExerciseTemplate]:
        """Get an exercise by ID."""
        return await self._get_by_id(exercise_id)

    async def get_all(self) -> List[ExerciseTemplate]:
        """Get all exercises."""
        return await self._get_all()

    async def create(self, exercise: ExerciseTemplate) -> ExerciseTemplate:
        """Create a new exercise."""
        return await self._create(exercise)

    async def update(self, exercise: ExerciseTemplate) -> ExerciseTemplate:
        """Update an exercise."""
        return await self._update(exercise)

    async def delete(self, exercise_id: UUID) -> bool:
        """Delete an exercise."""
        return await self._delete(exercise_id) 