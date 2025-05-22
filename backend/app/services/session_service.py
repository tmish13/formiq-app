"""Session management service."""
import json
import time
from typing import Dict, Optional, List, Union
from uuid import uuid4, UUID
from datetime import datetime, timedelta

from fastapi import HTTPException
from redis import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import Session
from jose import jwt, JWTError

from app.core.config import settings, Settings
from app.core.security import create_session_token, verify_session_token_and_get_payload
from app.schemas.session import SessionCreate, SessionData
from app.models.user_session import UserSession
from app.core.exceptions import ValidationError, AuthenticationError, NotFoundError
from app.core.db_deps import get_async_db
from app.core.config import get_settings
from app.core.redis import get_redis as get_redis_client
from fastapi import Depends
from app.core.logging import logger
from app.models.user import User
from app.repositories.user_repository import UserRepository

class SessionService:
    """Session management service using Redis for active sessions and DB for persistence."""
    
    def __init__(self, redis_client: Redis, db: Union[AsyncSession, Session], app_settings: Settings):
        self.redis = redis_client
        self.db = db
        self.settings = app_settings
        self.prefix = "session:"
        self.expiry = self.settings.SESSION_EXPIRY_HOURS * 3600  # Convert to seconds

    def _get_session_key(self, session_id: str) -> str:
        """Get Redis key for session."""
        return f"{self.prefix}{session_id}"
    
    def create_redis_session(self, session_create_data: SessionCreate) -> Dict[str, str]:
        """Create a new session in Redis and return session token."""
        session_id = str(uuid4())
        timestamp = int(time.time())
        
        redis_session_data = SessionData(
            user_id=session_create_data.user_id,
            created_at=timestamp,
            device_info=session_create_data.device_info,
            is_active=True
        )
        
        session_key = self._get_session_key(session_id)
        try:
            self.redis.setex(
                session_key,
                self.expiry,
                json.dumps(redis_session_data.model_dump()).encode()
            )
        except Exception as e:
            logger.error(f"Failed to create redis session {session_id}: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create session: {str(e)}"
            )
        
        token, _ = create_session_token(
            user_id=str(session_create_data.user_id),
            session_id=session_id,
            device_info=session_create_data.device_info,
            expires_delta=timedelta(seconds=self.expiry)
        )
        
        logger.info(f"Redis session created: {session_id} for user {session_create_data.user_id}")
        return {"session_id": session_id, "token": token}
    
    def verify_redis_session(self, token: str) -> Optional[SessionData]:
        """Verify session token and return session data from Redis if valid."""
        try:
            payload = verify_session_token_and_get_payload(token, self.redis)
            if not payload:
                logger.warning(f"Token verification failed or token invalid/blacklisted. Token: {token[:20]}...")
                return None
            
            session_id = payload.get("sid")
            user_id_from_token = payload.get("sub")

            if not session_id or not user_id_from_token:
                logger.warning(f"Token verification failed: missing session_id (sid) or user_id (sub) in payload. Token: {token[:20]}...")
                return None
            
            session_key = self._get_session_key(session_id)
            data = self.redis.get(session_key)
            if not data:
                logger.warning(f"Redis session not found or expired: {session_id}")
                return None
            
            session_dict = json.loads(data.decode())
            redis_session = SessionData(**session_dict)
            
            if str(redis_session.user_id) != str(user_id_from_token):
                logger.error(f"User ID mismatch in session. Token user: {user_id_from_token}, Session user: {redis_session.user_id}, Session ID: {session_id}")
                return None

            if not redis_session.is_active:
                logger.warning(f"Redis session found but inactive: {session_id}")
                return None
                
            return redis_session
            
        except Exception as e:
            logger.error(f"Error verifying redis session: {str(e)}", exc_info=True)
            return None
    
    def deactivate_redis_session(self, session_id: str) -> bool:
        """Deactivate a specific session in Redis."""
        session_key = self._get_session_key(session_id)
        try:
            data = self.redis.get(session_key)
            if not data:
                logger.warning(f"Attempted to deactivate non-existent redis session: {session_id}")
                return False
            
            session_dict = json.loads(data.decode())
            session_dict["is_active"] = False
            
            self.redis.setex(
                session_key,
                self.expiry,
                json.dumps(session_dict).encode()
            )
            logger.info(f"Redis session deactivated: {session_id}")
            return True
        except Exception as e:
            logger.error(f"Error deactivating redis session {session_id}: {str(e)}", exc_info=True)
            return False
    
    def delete_redis_session(self, session_id: str) -> bool:
        """Deletes a session directly from Redis (e.g. on logout)."""
        session_key = self._get_session_key(session_id)
        try:
            deleted_count = self.redis.delete(session_key)
            if deleted_count > 0:
                logger.info(f"Redis session deleted: {session_id}")
                return True
            logger.warning(f"Attempted to delete non-existent redis session: {session_id}")
            return False
        except Exception as e:
            logger.error(f"Error deleting redis session {session_id}: {str(e)}", exc_info=True)
            return False

    def deactivate_all_redis_sessions_for_user(self, user_id: UUID) -> bool:
        """Deactivate all Redis sessions for a user."""
        success_count = 0
        fail_count = 0
        user_id_str = str(user_id)
        try:
            pattern = f"{self.prefix}*"
            for key_bytes in self.redis.scan_iter(match=pattern):
                key = key_bytes.decode('utf-8')
                data = self.redis.get(key)
                if data:
                    try:
                        session_dict = json.loads(data.decode())
                        if str(session_dict.get("user_id")) == user_id_str:
                            session_dict["is_active"] = False
                            self.redis.setex(key, self.expiry, json.dumps(session_dict).encode())
                            success_count += 1
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to decode JSON for key {key} during deactivation sweep.")
                        fail_count += 1
            logger.info(f"Deactivated {success_count} redis sessions for user {user_id}. Failed to process: {fail_count}")
            return success_count > 0 or (success_count == 0 and fail_count == 0)
        except Exception as e:
            logger.error(f"Error deactivating all redis sessions for user {user_id}: {str(e)}", exc_info=True)
            return False
    
    async def create_db_session_async(self, session_id: str, user_id: UUID, session_data: SessionData, jwt_token: str) -> UserSession:
        """Persist session details to the database."""
        db_session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "user_agent": session_data.device_info.get("user_agent") if session_data.device_info else None,
            "ip_address": session_data.device_info.get("ip_address") if session_data.device_info else None,
            "device_info": session_data.device_info,
            "created_at": datetime.fromtimestamp(session_data.created_at),
            "expires_at": datetime.fromtimestamp(session_data.created_at + self.expiry),
            "last_activity": datetime.utcnow(),
            "is_active": True,
            "jwt_token": jwt_token
        }
        db_obj = UserSession(**db_session_data)
        self.db.add(db_obj)
        await self.db.commit()
        await self.db.refresh(db_obj)
        logger.info(f"DB session persisted: {session_id} for user {user_id}")
        return db_obj

    async def get_db_session_async(self, session_id: str) -> Optional[UserSession]:
        """Get a session by session_id from the database."""
        stmt = select(UserSession).where(UserSession.session_id == session_id)
        
        # Debugging prints
        print(f"DEBUG: In get_db_session_async, type(self.db) = {type(self.db)}")
        print(f"DEBUG: In get_db_session_async, hasattr(self.db, 'execute') = {hasattr(self.db, 'execute')}")
        # print(f"DEBUG: In get_db_session_async, dir(self.db) = {dir(self.db)}") # Uncomment for more detail if needed
        
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_active_db_sessions_for_user_async(self, user_id: UUID) -> List[UserSession]:
        """Get all active sessions for a user from the database."""
        stmt = select(UserSession).where(
            and_(
                UserSession.user_id == user_id,
                UserSession.is_active == True,
                UserSession.expires_at > datetime.utcnow()
            )
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def update_db_session_last_activity_async(self, session_id: str) -> Optional[UserSession]:
        """Update session's last activity timestamp in the database."""
        session = await self.get_db_session_async(session_id)
        if session and session.is_active:
            session.last_activity = datetime.utcnow()
            self.db.add(session)
            await self.db.commit()
            await self.db.refresh(session)
            return session
        return None
    
    async def deactivate_db_session_async(self, session_id: str) -> bool:
        """Deactivates a session in the database."""
        session = await self.get_db_session_async(session_id)
        if session:
            if session.is_active:
                session.is_active = False
                session.deactivated_at = datetime.utcnow()
                self.db.add(session)
                await self.db.commit()
                logger.info(f"DB session deactivated: {session_id}")
                return True
            return True
        return False

    async def validate_db_session_async(self, session_id: str, user_id: UUID) -> bool:
        """Validate a session against the database record."""
        session = await self.get_db_session_async(session_id)
        if not session:
            return False
        if not session.is_active:
            return False
        if session.user_id != user_id:
            return False
        if session.expires_at < datetime.utcnow():
            await self.deactivate_db_session_async(session.session_id)
            return False
        await self.update_db_session_last_activity_async(session.session_id)
        return True
    
    async def cleanup_expired_db_sessions_async(self) -> int:
        """Deactivates expired sessions in the database based on their expires_at field."""
        stmt = select(UserSession).where(
            and_(
                UserSession.is_active == True,
                UserSession.expires_at <= datetime.utcnow()
            )
        )
        result = await self.db.execute(stmt)
        expired_sessions = result.scalars().all()
        
        count = 0
        for session in expired_sessions:
            session.is_active = False
            session.deactivated_at = datetime.utcnow()
            self.db.add(session)
            count += 1
        
        if count > 0:
            await self.db.commit()
            logger.info(f"Deactivated {count} expired DB sessions.")
        return count

async def get_async_session_service(
    redis_client: Redis = Depends(get_redis_client),
    db: AsyncSession = Depends(get_async_db),
    app_settings: Settings = Depends(get_settings)
) -> SessionService:
    """Dependency provider for async SessionService."""
    return SessionService(redis_client=redis_client, db=db, app_settings=app_settings)

def get_session_service_redis_only(
    redis_client: Redis = Depends(get_redis_client),
    app_settings: Settings = Depends(get_settings)
) -> SessionService:
    """Dependency provider for SessionService with Redis only (dummy DB)."""
    # Create a dummy DB session or pass None if SessionService handles it
    class DummyDBSession:
        def __getattr__(self, name):
            # Prevent AttributeError for common SQLAlchemy session methods
            # if any part of SessionService accidentally tries to use db without full async context
            def dummy_method(*args, **kwargs):
                logger.warning(f"DummyDBSession method {name} called in redis_only SessionService")
                if name in ["execute", "scalars", "first", "all", "commit", "refresh", "rollback", "add", "delete", "query"]:
                    # For methods that might return awaitables or chain, return a dummy awaitable or self
                    async def dummy_awaitable(): return None
                    if name in ["execute"] : return dummy_awaitable() # Simplification
                    return None # Or raise an error
                return None # Or raise an error
            return dummy_method

    return SessionService(redis_client=redis_client, db=DummyDBSession(), app_settings=app_settings) 