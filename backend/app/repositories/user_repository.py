"""User repository implementation with optimized queries and caching."""
from typing import Optional, List, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import or_
from app.models.user import User
from app.repositories.base import BaseRepository
from app.core.security import get_password_hash

class UserRepository(BaseRepository[User]):
    """
    Repository for user operations with optimized queries.
    
    Features:
    - Optimized relationship loading
    - Email and token-based lookups
    - Password management
    - Stripe integration
    """
    
    def __init__(self):
        super().__init__(User)

    def get_by_email(self, db: Session, *, email: str, include_relations: List[str] = None) -> Optional[User]:
        """
        Get user by email with optional relationship loading.
        
        Args:
            db: Database session
            email: User's email address
            include_relations: Optional list of relationships to eager load
        """
        try:
            query = db.query(self.model)
            
            if include_relations:
                for relation in include_relations:
                    query = query.options(selectinload(getattr(self.model, relation)))
            
            return query.filter(self.model.email == email).first()
        except Exception as e:
            self._handle_error(e, "get_by_email")

    def get_by_verification_token(self, db: Session, *, token: str) -> Optional[User]:
        """Get user by verification token."""
        try:
            return db.query(self.model).filter(self.model.verification_token == token).first()
        except Exception as e:
            self._handle_error(e, "get_by_verification_token")

    def get_by_reset_token(self, db: Session, *, token: str) -> Optional[User]:
        """Get user by password reset token."""
        try:
            return db.query(self.model).filter(self.model.reset_password_token == token).first()
        except Exception as e:
            self._handle_error(e, "get_by_reset_token")

    def get_by_stripe_customer(self, db: Session, *, customer_id: str) -> Optional[User]:
        """Get user by Stripe customer ID."""
        try:
            return db.query(self.model).filter(self.model.stripe_customer_id == customer_id).first()
        except Exception as e:
            self._handle_error(e, "get_by_stripe_customer")

    def get_by_stripe_subscription(self, db: Session, *, subscription_id: str) -> Optional[User]:
        """Get user by Stripe subscription ID."""
        try:
            return db.query(self.model).filter(self.model.stripe_subscription_id == subscription_id).first()
        except Exception as e:
            self._handle_error(e, "get_by_stripe_subscription")

    def create_with_password(self, db: Session, *, obj_in: Dict[str, Any]) -> User:
        """
        Create a new user with hashed password.
        
        Args:
            db: Database session
            obj_in: User data including plain password
        """
        try:
            self._ensure_transaction(db)
            if "password" in obj_in:
                obj_in["hashed_password"] = get_password_hash(obj_in.pop("password"))
            return self.create(db, obj_in=obj_in)
        except Exception as e:
            db.rollback()
            self._handle_error(e, "create_with_password")

    def update_password(self, db: Session, *, user: User, new_password: str) -> User:
        """
        Update user's password.
        
        Args:
            db: Database session
            user: User object
            new_password: New plain password
        """
        try:
            self._ensure_transaction(db)
            hashed_password = get_password_hash(new_password)
            return self.update(
                db,
                db_obj=user,
                obj_in={"hashed_password": hashed_password},
                exclude_fields=["email", "is_active", "is_superuser"]
            )
        except Exception as e:
            db.rollback()
            self._handle_error(e, "update_password")

    def search_users(
        self,
        db: Session,
        *,
        query: str,
        skip: int = 0,
        limit: int = 10,
        include_relations: List[str] = None
    ) -> List[User]:
        """
        Search users by email or full name.
        
        Args:
            db: Database session
            query: Search query string
            skip: Number of records to skip
            limit: Maximum number of records to return
            include_relations: Optional list of relationships to eager load
        """
        try:
            db_query = db.query(self.model)
            
            if include_relations:
                for relation in include_relations:
                    db_query = db_query.options(selectinload(getattr(self.model, relation)))
            
            search_filter = or_(
                self.model.email.ilike(f"%{query}%"),
                self.model.full_name.ilike(f"%{query}%")
            )
            
            return (
                db_query.filter(search_filter)
                .offset(skip)
                .limit(limit)
                .all()
            )
        except Exception as e:
            self._handle_error(e, "search_users")

    def get_active_users(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        include_relations: List[str] = None
    ) -> List[User]:
        """
        Get active users with optional relationship loading.
        
        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return
            include_relations: Optional list of relationships to eager load
        """
        try:
            filters = {"is_active": True}
            return self.get_multi(
                db,
                skip=skip,
                limit=limit,
                filters=filters,
                include_relations=include_relations
            )
        except Exception as e:
            self._handle_error(e, "get_active_users") 