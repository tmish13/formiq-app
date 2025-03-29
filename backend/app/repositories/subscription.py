"""Subscription repository implementation."""
from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from datetime import datetime

from app.repositories.base import BaseRepository
from app.models.subscription import Subscription
from app.core.logging import get_logger

# Initialize logger
logger = get_logger(__name__)

class SubscriptionRepository(BaseRepository[Subscription]):
    """Repository for managing subscription records."""

    async def get_active_subscription(
        self,
        db: Session,
        *,
        user_id: UUID
    ) -> Optional[Subscription]:
        """
        Get user's active subscription.
        
        Args:
            db: Database session
            user_id: User's ID
            
        Returns:
            Optional[Subscription]: Active subscription if exists
        """
        return db.query(self.model).filter(
            and_(
                self.model.user_id == user_id,
                self.model.status.in_(["active", "trialing"]),
                or_(
                    self.model.current_period_end > datetime.utcnow(),
                    self.model.trial_end > datetime.utcnow()
                )
            )
        ).first()

    async def get_by_stripe_id(
        self,
        db: Session,
        *,
        stripe_id: str
    ) -> Optional[Subscription]:
        """
        Get subscription by Stripe subscription ID.
        
        Args:
            db: Database session
            stripe_id: Stripe subscription ID
            
        Returns:
            Optional[Subscription]: Subscription if exists
        """
        return db.query(self.model).filter(
            self.model.stripe_subscription_id == stripe_id
        ).first()

    async def get_latest_subscription(
        self,
        db: Session,
        *,
        user_id: UUID
    ) -> Optional[Subscription]:
        """
        Get user's latest subscription.
        
        Args:
            db: Database session
            user_id: User's ID
            
        Returns:
            Optional[Subscription]: Latest subscription if exists
        """
        return db.query(self.model).filter(
            self.model.user_id == user_id
        ).order_by(self.model.created_at.desc()).first()

    async def count_monthly_submissions(
        self,
        db: Session,
        *,
        user_id: UUID
    ) -> int:
        """
        Count user's form check submissions in current month.
        
        Args:
            db: Database session
            user_id: User's ID
            
        Returns:
            int: Number of submissions this month
        """
        start_of_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return db.query(self.model).filter(
            and_(
                self.model.user_id == user_id,
                self.model.created_at >= start_of_month
            )
        ).count() 