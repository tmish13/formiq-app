"""Form check repository implementation with optimized queries and caching."""
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import desc, and_, or_
from app.models.form_check import FormCheck
from app.repositories.base import BaseRepository
from app.models.enums import FormCheckStatus

class FormCheckRepository(BaseRepository[FormCheck]):
    """
    Repository for form check operations with optimized queries.
    
    Features:
    - Optimized relationship loading
    - Status-based filtering
    - Exercise type filtering
    - Advanced search capabilities
    """
    
    def __init__(self):
        super().__init__(FormCheck)

    def get_by_user(
        self,
        db: Session,
        *,
        user_id: UUID,
        skip: int = 0,
        limit: int = 100,
        include_relations: List[str] = None,
        status: Optional[FormCheckStatus] = None,
        exercise_type: Optional[str] = None,
        order_by: List[str] = None
    ) -> List[FormCheck]:
        """
        Get form checks for a specific user with advanced filtering.
        
        Args:
            db: Database session
            user_id: User's UUID
            skip: Number of records to skip
            limit: Maximum number of records to return
            include_relations: Optional list of relationships to eager load
            status: Optional status filter
            exercise_type: Optional exercise type filter
            order_by: Optional list of fields to order by
        """
        try:
            filters = {"user_id": user_id}
            
            if status:
                filters["status"] = status
            if exercise_type:
                filters["exercise_type"] = exercise_type

            return self.get_multi(
                db,
                skip=skip,
                limit=limit,
                filters=filters,
                include_relations=include_relations,
                order_by=order_by or ["-created_at"]
            )
        except Exception as e:
            self._handle_error(e, "get_by_user")

    def get_by_exercise_type(
        self,
        db: Session,
        *,
        user_id: UUID,
        exercise_type: str,
        include_relations: List[str] = None
    ) -> List[FormCheck]:
        """
        Get form checks for a specific exercise type.
        
        Args:
            db: Database session
            user_id: User's UUID
            exercise_type: Type of exercise
            include_relations: Optional list of relationships to eager load
        """
        try:
            filters = {
                "user_id": user_id,
                "exercise_type": exercise_type,
                "status": FormCheckStatus.COMPLETED
            }
            
            return self.get_multi(
                db,
                filters=filters,
                include_relations=include_relations,
                order_by=["-created_at"]
            )
        except Exception as e:
            self._handle_error(e, "get_by_exercise_type")

    def get_latest_by_user(
        self,
        db: Session,
        *,
        user_id: UUID,
        limit: int = 5,
        include_relations: List[str] = None,
        status: Optional[FormCheckStatus] = None
    ) -> List[FormCheck]:
        """
        Get latest form checks for a user.
        
        Args:
            db: Database session
            user_id: User's UUID
            limit: Maximum number of records to return
            include_relations: Optional list of relationships to eager load
            status: Optional status filter
        """
        try:
            filters = {"user_id": user_id}
            if status:
                filters["status"] = status

            return self.get_multi(
                db,
                limit=limit,
                filters=filters,
                include_relations=include_relations,
                order_by=["-created_at"]
            )
        except Exception as e:
            self._handle_error(e, "get_latest_by_user")

    def get_pending_analysis(
        self,
        db: Session,
        *,
        limit: int = 10,
        include_relations: List[str] = None
    ) -> List[FormCheck]:
        """
        Get form checks pending analysis.
        
        Args:
            db: Database session
            limit: Maximum number of records to return
            include_relations: Optional list of relationships to eager load
        """
        try:
            filters = {"status": FormCheckStatus.PENDING}
            return self.get_multi(
                db,
                limit=limit,
                filters=filters,
                include_relations=include_relations,
                order_by=["created_at"]  # Process oldest first
            )
        except Exception as e:
            self._handle_error(e, "get_pending_analysis")

    def update_status(
        self,
        db: Session,
        *,
        form_check: FormCheck,
        status: FormCheckStatus,
        analysis_data: Optional[Dict[str, Any]] = None
    ) -> FormCheck:
        """
        Update form check status and analysis data.
        
        Args:
            db: Database session
            form_check: FormCheck object
            status: New status
            analysis_data: Optional analysis results
        """
        try:
            update_data = {
                "status": status,
                "updated_at": datetime.utcnow()
            }
            
            if analysis_data:
                update_data["analysis_data"] = analysis_data
            
            return self.update(db, db_obj=form_check, obj_in=update_data)
        except Exception as e:
            self._handle_error(e, "update_status")

    def search_form_checks(
        self,
        db: Session,
        *,
        user_id: UUID,
        query: str,
        skip: int = 0,
        limit: int = 10,
        include_relations: List[str] = None
    ) -> List[FormCheck]:
        """
        Search form checks by exercise type or feedback.
        
        Args:
            db: Database session
            user_id: User's UUID
            query: Search query string
            skip: Number of records to skip
            limit: Maximum number of records to return
            include_relations: Optional list of relationships to eager load
        """
        try:
            db_query = db.query(self.model).filter(self.model.user_id == user_id)
            
            if include_relations:
                for relation in include_relations:
                    db_query = db_query.options(selectinload(getattr(self.model, relation)))
            
            search_filter = or_(
                self.model.exercise_type.ilike(f"%{query}%"),
                self.model.feedback.cast(str).ilike(f"%{query}%")
            )
            
            return (
                db_query.filter(search_filter)
                .order_by(desc(self.model.created_at))
                .offset(skip)
                .limit(limit)
                .all()
            )
        except Exception as e:
            self._handle_error(e, "search_form_checks") 