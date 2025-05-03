"""User sessions model for managing authenticated user sessions."""
import uuid
from sqlalchemy import Column, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
from app.models.base import BaseModel, SQLiteUUID


class UserSession(BaseModel):
    """
    UserSession model for storing active user sessions.
    
    This model handles:
    - Session tracking for users
    - Authentication tokens
    - Session expiration
    
    Relationships:
    - Many-to-one with User
    
    Attributes:
        user_id (UUID): Foreign key to user
        token (str): Authentication token
        user_agent (str): User agent from request
        ip_address (str): IP address 
        expires_at (datetime): When the session expires
        last_active (datetime): When user was last active
    """
    __tablename__ = "user_sessions"

    id = Column(SQLiteUUID(), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(SQLiteUUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token = Column(String, unique=True, index=True, nullable=False)
    user_agent = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    expires_at = Column(DateTime, default=lambda: datetime.utcnow() + timedelta(days=7))
    last_active = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship back to user
    user = relationship("User", back_populates="sessions")

    def __repr__(self) -> str:
        return f"<UserSession {self.id} for user {self.user_id}>"
        
    @property
    def is_expired(self) -> bool:
        """Check if the session is expired."""
        return datetime.utcnow() > self.expires_at
        
    def extend_session(self, days: int = 7) -> None:
        """Extend the session validity."""
        self.expires_at = datetime.utcnow() + timedelta(days=days)
        self.last_active = datetime.utcnow() 