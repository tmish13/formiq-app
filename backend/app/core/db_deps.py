from typing import Generator, AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from app.core.database import get_async_db as core_get_async_db, SessionLocal

import logging
logger = logging.getLogger(__name__)


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session as a FastAPI-compatible async generator dependency."""
    async for session in core_get_async_db():
        yield session


def get_db() -> Generator[Session, None, None]:
    """Get a synchronous database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
