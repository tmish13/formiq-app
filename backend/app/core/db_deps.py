import contextlib
from typing import Generator, AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from app.core.database import get_async_db as core_get_async_db, SessionLocal

# It's good practice to have a logger available if needed for cleanup issues
import logging
logger = logging.getLogger(__name__)

@contextlib.asynccontextmanager
async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session using the core function, compatible with `async with`."""
    # core_get_async_db() from app.core.database is an async generator that yields one session
    # from an `async with async_session_factory()` block, which handles session commit/rollback/close.
    underlying_session_generator = core_get_async_db()
    session: Optional[AsyncSession] = None
    try:
        session = await underlying_session_generator.__anext__() # Get the single yielded session
        yield session
    except StopAsyncIteration: # Should not happen if core_get_async_db behaves as expected
        raise RuntimeError("core_get_async_db did not yield a session")
    finally:
        if session is not None:
            # The `finally` block in `app.core.database.get_async_db` handles session.close().
            # We need to ensure that generator is driven to completion or closed to trigger its finally block.
            try:
                await underlying_session_generator.__anext__() # Drive to StopAsyncIteration
            except StopAsyncIteration:
                pass # Expected, means the underlying generator finished its cleanup.
            except Exception as e:
                # Log unexpected error during cleanup of the underlying generator
                logger.error(f"Error during cleanup of underlying session generator from core_get_async_db: {e}", exc_info=True)
            # If the generator has `aclose`, call it as a more direct cleanup.
            if hasattr(underlying_session_generator, 'aclose'):
                try:
                    await underlying_session_generator.aclose()
                except Exception as e_aclose:
                    logger.error(f"Error calling aclose on underlying session generator: {e_aclose}", exc_info=True)

def get_db() -> Generator[Session, None, None]:
    """Get a synchronous database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 