"""Session management service."""
import json
import time
from typing import Dict, Optional, List
from uuid import uuid4

from fastapi import HTTPException
from redis import Redis

from app.core.config import settings
from app.core.security import create_jwt_token, decode_jwt_token
from app.schemas.session import SessionCreate, SessionData
from app.models.session import UserSession
from app.models.user import User
from app.core.exceptions import ValidationError, AuthenticationError
from app.repositories.session_repository import SessionRepository

class SessionService:
    """Session management service using Redis."""
    
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.prefix = "session:"
        self.expiry = settings.SESSION_EXPIRY_HOURS * 3600  # Convert to seconds
        self.repository = SessionRepository()

    def _get_session_key(self, session_id: str) -> str:
        """Get Redis key for session."""
        return f"{self.prefix}{session_id}"
    
    def create_session(self, session_data: SessionCreate) -> Dict[str, str]:
        """Create a new session and return session token."""
        session_id = str(uuid4())
        timestamp = int(time.time())
        
        # Create session data
        data = SessionData(
            user_id=session_data.user_id,
            created_at=timestamp,
            device_info=session_data.device_info,
            is_active=True
        )
        
        # Store in Redis
        session_key = self._get_session_key(session_id)
        try:
            self.redis.setex(
                session_key,
                self.expiry,
                json.dumps(data.dict()).encode()
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create session: {str(e)}"
            )
        
        # Generate JWT token
        token_data = {"session_id": session_id, "user_id": session_data.user_id}
        token = create_jwt_token(token_data)
        
        return {"session_id": session_id, "token": token}
    
    def verify_session(self, token: str) -> Optional[SessionData]:
        """Verify session token and return session data if valid."""
        try:
            # Decode token
            payload = decode_jwt_token(token)
            session_id = payload.get("session_id")
            if not session_id:
                return None
            
            # Get session data from Redis
            session_key = self._get_session_key(session_id)
            data = self.redis.get(session_key)
            if not data:
                return None
            
            # Parse session data
            session_dict = json.loads(data.decode())
            session = SessionData(**session_dict)
            
            # Check if session is active
            if not session.is_active:
                return None
                
            return session
            
        except Exception:
            return None
    
    def deactivate_session(self, session_id: str) -> bool:
        """Deactivate a specific session."""
        session_key = self._get_session_key(session_id)
        try:
            data = self.redis.get(session_key)
            if not data:
                return False
            
            session_dict = json.loads(data.decode())
            session_dict["is_active"] = False
            
            self.redis.setex(
                session_key,
                self.expiry,
                json.dumps(session_dict).encode()
            )
            return True
        except Exception:
            return False
    
    def deactivate_all_sessions(self, user_id: int) -> bool:
        """Deactivate all sessions for a user."""
        try:
            # Get all sessions for user
            pattern = f"{self.prefix}*"
            for key in self.redis.scan_iter(match=pattern):
                data = self.redis.get(key)
                if data:
                    session_dict = json.loads(data.decode())
                    if session_dict.get("user_id") == user_id:
                        session_dict["is_active"] = False
                        self.redis.setex(
                            key,
                            self.expiry,
                            json.dumps(session_dict).encode()
                        )
            return True
        except Exception:
            return False
    
    def cleanup_expired_sessions(self) -> None:
        """Remove expired sessions from Redis.
        
        Note: Redis automatically removes expired keys, so this is just
        a backup cleanup method.
        """
        pass  # Redis handles expiry automatically

    async def get_session(self, session_id: str) -> Optional[UserSession]:
        """Get a session by ID.
        
        Args:
            session_id: Session ID
            
        Returns:
            Optional[UserSession]: Session if found, None otherwise
        """
        return await self.repository.get_by_session_id(session_id)

    async def get_active_sessions(self, user_id: int) -> List[UserSession]:
        """Get all active sessions for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            List[UserSession]: List of active sessions
        """
        return await self.repository.get_active_sessions(user_id)

    async def update_last_activity(self, session_id: str) -> None:
        """Update session's last activity timestamp.
        
        Args:
            session_id: Session ID
        """
        session = await self.get_session(session_id)
        if session:
            session.last_activity = datetime.utcnow()
            await self.repository.update(session)

    async def validate_session(
        self,
        session_id: str,
        user_id: int
    ) -> bool:
        """Validate a session.
        
        Args:
            session_id: Session ID
            user_id: User ID
            
        Returns:
            bool: True if session is valid, False otherwise
        """
        session = await self.get_session(session_id)
        if not session:
            return False
            
        if not session.is_active:
            return False
            
        if session.user_id != user_id:
            return False
            
        if session.expires_at < datetime.utcnow():
            await self.deactivate_session(session.id)
            return False
            
        # Update last activity
        await self.update_last_activity(session.id)
        return True 