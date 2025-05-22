"""Repository for FeedbackItem model."""
from typing import Union
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from fastapi import Depends

from app.models.form_check import FeedbackItem
from app.repositories.base_repository import BaseRepository
from app.core.db_deps import get_async_db, get_db # Ensure these are correct paths


class FeedbackItemRepository(BaseRepository[FeedbackItem]):
    """Repository for FeedbackItem database operations."""

    def __init__(self, db: Union[Session, AsyncSession]):
        """Initialize repository with database session."""
        super().__init__(FeedbackItem, db)

    # Add specific methods for FeedbackItem if needed in the future
    # For now, BaseRepository methods (get_async, create_async, etc.) will be inherited.

def get_feedback_item_repository(db: Session = Depends(get_db)) -> FeedbackItemRepository:
    """
    Get FeedbackItem repository instance for synchronous operations.
    """
    return FeedbackItemRepository(db=db)

def get_async_feedback_item_repository(db: AsyncSession = Depends(get_async_db)) -> FeedbackItemRepository:
    """
    Get FeedbackItem repository instance for asynchronous operations.
    """
    return FeedbackItemRepository(db=db) 