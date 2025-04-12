"""User session model."""
from datetime import datetime
from typing import Dict, Any
from uuid import UUID, uuid4
from sqlalchemy import Column, ForeignKey, String, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import relationship

from app.models.base import Base

class UserSession(Base):
    """User session model."""
    
    __tablename__ = "user_sessions"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    session_id = Column(String(64), unique=True, nullable=False)
    device_info = Column(JSONB, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    last_activity = Column(DateTime, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="sessions")
    
    def __repr__(self) -> str:
        """String representation."""
        return f"<UserSession {self.session_id} (User: {self.user_id})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "session_id": self.session_id,
            "device_info": self.device_info,
            "is_active": self.is_active,
            "last_activity": self.last_activity.isoformat() if self.last_activity else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        } 