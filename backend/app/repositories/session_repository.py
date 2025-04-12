"""Session repository module."""
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from sqlalchemy import select, and_
from sqlalchemy.orm import Session

from app.models.session import UserSession
from app.repositories.base import BaseRepository

class SessionRepository(BaseRepository[UserSession]):
    """Repository for managing user sessions."""
    
    def __init__(self, db: Session):
        """Initialize repository with database session."""
        super().__init__(db, UserSession)

    async def get_by_session_id(self, session_id: str) -> Optional[UserSession]:
        """Get a session by session ID.
        
        Args:
            session_id: Session ID
            
        Returns:
            Optional[UserSession]: Session if found, None otherwise
        """
        query = select(UserSession).where(UserSession.session_id == session_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_active_sessions(self, user_id: UUID) -> List[UserSession]:
        """Get all active sessions for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            List[UserSession]: List of active sessions
        """
        query = select(UserSession).where(
            and_(
                UserSession.user_id == user_id,
                UserSession.is_active == True,
                UserSession.expires_at > datetime.utcnow()
            )
        )
        result = await self.db.execute(query)
        return result.scalars().all()

    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions.
        
        Returns:
            int: Number of sessions cleaned up
        """
        query = select(UserSession).where(
            and_(
                UserSession.is_active == True,
                UserSession.expires_at <= datetime.utcnow()
            )
        )
        result = await self.db.execute(query)
        expired_sessions = result.scalars().all()
        
        for session in expired_sessions:
            session.is_active = False
            self.db.add(session)
        
        await self.db.commit()
        return len(expired_sessions) 