"""User sessions model for managing authenticated user sessions."""
import uuid
from sqlalchemy import Column, String, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
from app.models.base import BaseModel


class UserSession(BaseModel):
    """
    UserSession model for storing active user sessions.
    
    This model handles:
    - Session tracking for users
    - Authentication tokens (now session_id)
    - Session expiration
    
    Relationships:
    - Many-to-one with User
    
    Attributes:
        user_id (UUID): Foreign key to user
        session_id (UUID): Unique session identifier (formerly token)
        user_agent (str): User agent from request
        ip_address (str): IP address 
        auth_method (str): Method used for authentication
        device_token (str): Specific device token, if any
        expires_at (datetime): When the session expires
        last_active (datetime): When user was last active
    """
    __tablename__ = "user_sessions"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = Column(PGUUID(as_uuid=True), unique=True, index=True, nullable=False, default=uuid.uuid4)
    user_agent = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    auth_method = Column(String, nullable=True)
    device_token = Column(String, nullable=True, index=True)
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