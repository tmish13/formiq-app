"""Exercise service module."""
from typing import List, Optional, Union
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.models.exercise import ExerciseTemplate
from app.schemas.exercise import ExerciseCreate, ExerciseUpdate, ExerciseResponse
from fastapi import Depends
from app.core.exceptions import NotFoundException
from app.core.logging import logger

from app.services.base_service import BaseService


class ExerciseService(BaseService[ExerciseTemplate, ExerciseCreate, ExerciseUpdate]):
    """Service for managing exercise templates."""

    def __init__(self, db: Union[AsyncSession, Session], settings: Settings):
        """Initialize the service."""
        super().__init__(db=db, model=ExerciseTemplate, settings=settings)

    async def get_by_id_async(self, exercise_id: UUID) -> Optional[ExerciseResponse]:
        """Get an exercise template by ID."""
        db_obj = await super().get_async(id=exercise_id)
        return ExerciseResponse.from_orm(db_obj) if db_obj else None

    async def get_all_async(self, skip: int = 0, limit: int = 100) -> List[ExerciseResponse]:
        """Get all exercise templates."""
        db_objs = await super().get_multi_async(skip=skip, limit=limit)
        return [ExerciseResponse.from_orm(obj) for obj in db_objs]

    async def create_async(self, exercise_in: ExerciseCreate) -> ExerciseResponse:
        """Create a new exercise template."""
        db_obj = await super().create_async(obj_in=exercise_in)
        return ExerciseResponse.from_orm(db_obj)

    async def update_async(self, exercise_id: UUID, exercise_in: ExerciseUpdate) -> Optional[ExerciseResponse]:
        """Update an exercise template."""
        db_obj_to_update = await super().get_async(id=exercise_id)
        updated_db_obj = await super().update_async(db_obj=db_obj_to_update, obj_in=exercise_in)
        return ExerciseResponse.from_orm(updated_db_obj)

    async def delete_async(self, exercise_id: UUID) -> bool:
        """Delete an exercise template. Returns True if deleted, False if not found or error."""
        try:
            return await super().delete_async(id=exercise_id)
        except NotFoundException:
            return False


async def get_async_exercise_service(
    # db: AsyncSession = Depends(get_async_db),
    # settings: Settings = Depends(get_settings)
) -> ExerciseService:
    """Get async exercise service instance."""
    from app.core.deps import get_async_db, get_settings
    db_session: AsyncSession = Depends(get_async_db)
    current_app_settings: Settings = Depends(get_settings)
    return ExerciseService(db=db_session, settings=current_app_settings)

def get_exercise_service(
    # db: Session = Depends(get_db),
    # settings: Settings = Depends(get_settings)
) -> ExerciseService:
    """Get sync exercise service instance. Note: uses async methods internally if called."""
    from app.core.deps import get_db, get_settings
    db_session: Session = Depends(get_db)
    current_app_settings: Settings = Depends(get_settings)
    logger.warning("Instantiating ExerciseService with a synchronous DB session. Async methods will require event loop management if called from sync code.")
    return ExerciseService(db=db_session, settings=current_app_settings) 