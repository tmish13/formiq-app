"""
Form check repository for database operations.
"""
from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.form_check import FormCheck, FeedbackItem
from app.models.enums import FormCheckStatus

class FormCheckRepository:
    """
    Repository for form check CRUD operations.
    """

    @staticmethod
    def create(
        db: Session,
        user_id: UUID,
        exercise_id: UUID,
        video_url: str
    ) -> FormCheck:
        """
        Create a new form check.
        
        Args:
            db (Session): Database session
            user_id (UUID): User ID
            exercise_id (UUID): Exercise ID
            video_url (str): URL to the uploaded video
            
        Returns:
            FormCheck: Created form check
        """
        # Create the form check
        form_check = FormCheck(
            user_id=user_id,
            exercise_id=exercise_id,
            video_url=video_url,
            status=FormCheckStatus.pending
        )
        
        # Add to database
        db.add(form_check)
        db.commit()
        db.refresh(form_check)
        
        return form_check

    @staticmethod
    def get_by_id(db: Session, form_check_id: UUID) -> Optional[FormCheck]:
        """
        Get a form check by ID.
        
        Args:
            db (Session): Database session
            form_check_id (UUID): Form check ID
            
        Returns:
            Optional[FormCheck]: Found form check or None
        """
        return db.query(FormCheck).filter(FormCheck.id == form_check_id).first()

    @staticmethod
    def get_by_user(
        db: Session,
        user_id: UUID,
        skip: int = 0,
        limit: int = 100,
        status: Optional[FormCheckStatus] = None
    ) -> List[FormCheck]:
        """
        Get all form checks for a user.
        
        Args:
            db (Session): Database session
            user_id (UUID): User ID
            skip (int): Number of records to skip
            limit (int): Maximum number of records to return
            status (Optional[FormCheckStatus]): Filter by status
            
        Returns:
            List[FormCheck]: List of form checks
        """
        query = db.query(FormCheck).filter(FormCheck.user_id == user_id)
        
        if status:
            query = query.filter(FormCheck.status == status)
            
        return query.order_by(desc(FormCheck.created_at)).offset(skip).limit(limit).all()

    @staticmethod
    def update(
        db: Session,
        form_check_id: UUID,
        updates: Dict[str, Any]
    ) -> Optional[FormCheck]:
        """
        Update a form check.
        
        Args:
            db (Session): Database session
            form_check_id (UUID): Form check ID
            updates (Dict[str, Any]): Fields to update
            
        Returns:
            Optional[FormCheck]: Updated form check or None if not found
        """
        form_check = db.query(FormCheck).filter(FormCheck.id == form_check_id).first()
        if not form_check:
            return None
            
        # Update fields
        for key, value in updates.items():
            if hasattr(form_check, key):
                setattr(form_check, key, value)
                
        db.commit()
        db.refresh(form_check)
        
        return form_check

    @staticmethod
    def delete(db: Session, form_check_id: UUID) -> bool:
        """
        Delete a form check.
        
        Args:
            db (Session): Database session
            form_check_id (UUID): Form check ID
            
        Returns:
            bool: Success status
        """
        form_check = db.query(FormCheck).filter(FormCheck.id == form_check_id).first()
        if not form_check:
            return False
            
        db.delete(form_check)
        db.commit()
        
        return True

    @staticmethod
    def create_feedback_item(
        db: Session,
        form_check_id: UUID,
        feedback_item: Dict[str, Any]
    ) -> FeedbackItem:
        """
        Create a feedback item for a form check.
        
        Args:
            db (Session): Database session
            form_check_id (UUID): Form check ID
            feedback_item (Dict[str, Any]): Feedback item data
            
        Returns:
            FeedbackItem: Created feedback item
        """
        # Create the feedback item
        feedback_model = FeedbackItem(
            form_check_id=form_check_id,
            **feedback_item
        )
        
        # Add to database
        db.add(feedback_model)
        db.commit()
        db.refresh(feedback_model)
        
        return feedback_model

    @staticmethod
    def get_feedback_items(
        db: Session,
        form_check_id: UUID
    ) -> List[FeedbackItem]:
        """
        Get all feedback items for a form check.
        
        Args:
            db (Session): Database session
            form_check_id (UUID): Form check ID
            
        Returns:
            List[FeedbackItem]: List of feedback items
        """
        return db.query(FeedbackItem).filter(FeedbackItem.form_check_id == form_check_id).all() 