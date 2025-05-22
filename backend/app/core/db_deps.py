from typing import Generator, AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from backend.app.core.database import get_async_db as core_get_async_db, SessionLocal

async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session using the core function."""
    async for session in core_get_async_db():
        yield session

def get_db() -> Generator[Session, None, None]:
    """Get a synchronous database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 