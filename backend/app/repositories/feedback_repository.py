"""Feedback repository module."""
from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session

from app.models.form_check import FeedbackItem
from app.repositories.base import BaseRepository


class FeedbackRepository(BaseRepository[FeedbackItem]):
    """Repository for feedback item operations."""

    def __init__(self, db: Session):
        """Initialize repository with database session."""
        super().__init__(db, FeedbackItem)

    def get(self, id: int) -> Optional[FeedbackItem]:
        """
        Get feedback item by ID.
        
        Args:
            id: Feedback item ID
            
        Returns:
            Feedback item if found, None otherwise
        """
        return self.db.query(FeedbackItem).filter(FeedbackItem.id == id).first()

    def get_by_form_check(self, form_check_id: UUID) -> List[FeedbackItem]:
        """
        Get all feedback items for a form check.
        
        Args:
            form_check_id: Form check ID
            
        Returns:
            List of feedback items
        """
        return self.db.query(FeedbackItem).filter(
            FeedbackItem.form_check_id == form_check_id
        ).order_by(FeedbackItem.timestamp).all()

    def create(self, obj_in: Dict[str, Any]) -> FeedbackItem:
        """
        Create a new feedback item.
        
        Args:
            obj_in: Feedback item data
            
        Returns:
            Created feedback item
        """
        db_obj = FeedbackItem(**obj_in)
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def update(self, db_obj: FeedbackItem, obj_in: Dict[str, Any]) -> FeedbackItem:
        """
        Update a feedback item.
        
        Args:
            db_obj: Feedback item to update
            obj_in: Data to update
            
        Returns:
            Updated feedback item
        """
        for field in obj_in:
            if field in obj_in:
                setattr(db_obj, field, obj_in[field])
        
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def delete(self, id: int) -> None:
        """
        Delete a feedback item.
        
        Args:
            id: Feedback item ID
        """
        obj = self.db.query(FeedbackItem).get(id)
        if obj:
            self.db.delete(obj)
            self.db.commit() 