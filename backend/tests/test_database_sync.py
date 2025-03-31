import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from app.core.database import DatabaseSession, SessionLocal
from app.core.exceptions import DatabaseError
from sqlalchemy.orm import sessionmaker

# Create test engine
test_engine = create_engine("sqlite:///:memory:")
test_session_factory = sessionmaker(test_engine)

def test_sync_session_context():
    """Test sync session context manager."""
    with DatabaseSession(test_session_factory) as session:
        result = session.execute_sync(text("SELECT 1"))
        assert result.scalar() == 1

def test_sync_session_execution():
    """Test sync session execution."""
    with DatabaseSession(test_session_factory) as session:
        result = session.execute_sync(text("SELECT 1"))
        assert result.scalar() == 1

def test_sync_session_reuse():
    """Test that session cannot be reused after closure."""
    session = DatabaseSession(test_session_factory)
    with session:
        session.execute_sync(text("SELECT 1"))
    
    with pytest.raises(DatabaseError) as exc_info:
        session.execute_sync(text("SELECT 1"))
    assert "Session is closed" in str(exc_info.value)
    assert exc_info.value.status_code == 500

def test_sync_session_cleanup_error():
    """Test error handling during session cleanup."""
    class MockSession:
        def commit(self):
            pass
        def rollback(self):
            pass
        def close(self):
            raise SQLAlchemyError("Cleanup error")
    
    def mock_factory():
        return MockSession()
    
    with pytest.raises(DatabaseError) as exc_info:
        with DatabaseSession(mock_factory):
            pass
    assert "Cleanup error" in str(exc_info.value)
    assert exc_info.value.status_code == 500

def test_sync_commit_failure():
    """Test error handling during commit."""
    class MockSession:
        def commit(self):
            raise SQLAlchemyError("Commit error")
        def rollback(self):
            pass
        def close(self):
            pass
    
    def mock_factory():
        return MockSession()
    
    with pytest.raises(DatabaseError) as exc_info:
        with DatabaseSession(mock_factory):
            pass
    assert "Failed to commit transaction" in str(exc_info.value)
    assert exc_info.value.status_code == 500

def test_sync_rollback_failure():
    """Test error handling during rollback."""
    class MockSession:
        def commit(self):
            raise SQLAlchemyError("Commit error")
        def rollback(self):
            raise SQLAlchemyError("Rollback error")
        def close(self):
            pass
    
    def mock_factory():
        return MockSession()
    
    with pytest.raises(DatabaseError) as exc_info:
        with DatabaseSession(mock_factory):
            pass
    assert "Failed to rollback transaction" in str(exc_info.value)
    assert exc_info.value.status_code == 500

def test_sync_session_with_async_factory():
    """Test that async session factory cannot be used in sync context."""
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    async_engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async_factory = async_sessionmaker(async_engine)
    
    with pytest.raises(SQLAlchemyError):
        with DatabaseSession(async_factory):
            pass

def test_sync_session_attribute_access():
    """Test attribute access on sync session."""
    with DatabaseSession(test_session_factory) as session:
        assert hasattr(session, 'execute_sync')
        assert not hasattr(session, 'execute')

def test_sync_session_closed_attribute_access():
    """Test attribute access on closed session."""
    session = DatabaseSession(test_session_factory)
    with session:
        session.execute_sync(text("SELECT 1"))
    
    with pytest.raises(DatabaseError) as exc_info:
        session.execute_sync(text("SELECT 1"))
    assert "Session is closed" in str(exc_info.value)
    assert exc_info.value.status_code == 500 