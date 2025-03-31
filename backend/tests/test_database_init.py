import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy.exc import SQLAlchemyError
from app.core.database import init_db, close_db, Base
from app.core.exceptions import DatabaseError
from unittest.mock import MagicMock, patch

@pytest.fixture
def setup_test_db():
    """Set up test database with SQLite."""
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    return test_engine

@pytest.mark.asyncio
async def test_init_db_success(setup_test_db):
    """Test successful database initialization."""
    with patch('app.core.database.async_engine', setup_test_db):
        await init_db()
        # Verify that tables were created
        async with setup_test_db.begin() as conn:
            result = await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
            tables = [row[0] for row in result]
            assert len(tables) > 0

@pytest.mark.asyncio
async def test_init_db_failure(setup_test_db):
    """Test database initialization failure."""
    mock_engine = MagicMock(spec=AsyncEngine)
    mock_engine.begin.side_effect = SQLAlchemyError("Initialization error")
    
    with patch('app.core.database.async_engine', mock_engine):
        with pytest.raises(DatabaseError) as exc_info:
            await init_db()
        assert "Failed to initialize database" in str(exc_info.value)
        assert exc_info.value.status_code == 500

@pytest.mark.asyncio
async def test_close_db_success(setup_test_db):
    """Test successful database closure."""
    # Create a connection first to ensure the engine is in use
    async with setup_test_db.begin() as conn:
        await conn.execute(text("SELECT 1"))
    
    with patch('app.core.database.async_engine', setup_test_db):
        await close_db()
        # Verify that the engine is disposed
        with pytest.raises(DatabaseError) as exc_info:
            async with setup_test_db.begin() as conn:
                await conn.execute(text("SELECT 1"))
        assert "Database is closed" in str(exc_info.value)
        assert exc_info.value.status_code == 500

@pytest.mark.asyncio
async def test_close_db_failure(setup_test_db):
    """Test database closure failure."""
    mock_engine = MagicMock(spec=AsyncEngine)
    mock_engine.dispose.side_effect = SQLAlchemyError("Dispose error")
    
    with patch('app.core.database.async_engine', mock_engine):
        with pytest.raises(DatabaseError) as exc_info:
            await close_db()
        assert "Error closing database connections" in str(exc_info.value)
        assert exc_info.value.status_code == 500

@pytest.mark.asyncio
async def test_database_url_configuration():
    """Test database URL configuration based on environment."""
    from app.core.database import get_database_url, get_async_database_url
    
    # Test sync URL in test environment
    with patch('app.core.config.settings.ENVIRONMENT', 'test'):
        assert get_database_url() == "sqlite:///./test.db"
    
    # Test async URL in test environment
    with patch('app.core.config.settings.ENVIRONMENT', 'test'):
        assert get_async_database_url() == "sqlite+aiosqlite:///./test.db"
    
    # Test sync URL in production
    with patch('app.core.config.settings.ENVIRONMENT', 'production'), \
         patch('app.core.config.settings.SQLALCHEMY_DATABASE_URI', 'postgresql://user:pass@localhost/db'):
        assert get_database_url() == 'postgresql://user:pass@localhost/db'
    
    # Test async URL in production
    with patch('app.core.config.settings.ENVIRONMENT', 'production'), \
         patch('app.core.config.settings.SQLALCHEMY_DATABASE_URI', 'postgresql://user:pass@localhost/db'):
        assert get_async_database_url() == 'postgresql+asyncpg://user:pass@localhost/db'
    
    # Test missing database URL
    with patch('app.core.config.settings.SQLALCHEMY_DATABASE_URI', None):
        with pytest.raises(DatabaseError) as exc_info:
            get_database_url()
        assert "Database URL not configured" in str(exc_info.value)
        assert exc_info.value.status_code == 500
    
    # Test unsupported database type for async
    with patch('app.core.config.settings.SQLALCHEMY_DATABASE_URI', 'mysql://user:pass@localhost/db'):
        with pytest.raises(DatabaseError) as exc_info:
            get_async_database_url()
        assert "Unsupported database type for async operations" in str(exc_info.value)
        assert exc_info.value.status_code == 500

@pytest.mark.asyncio
async def test_engine_kwargs_configuration():
    """Test engine kwargs configuration based on environment."""
    from app.core.database import get_engine_kwargs
    
    # Test kwargs in test environment
    with patch('app.core.config.settings.ENVIRONMENT', 'test'):
        sync_kwargs = get_engine_kwargs(is_async=False)
        assert sync_kwargs['poolclass'] == NullPool
        assert sync_kwargs['connect_args'] == {'check_same_thread': False}
        
        async_kwargs = get_engine_kwargs(is_async=True)
        assert async_kwargs['poolclass'] == NullPool
        assert async_kwargs['connect_args'] == {}
    
    # Test kwargs in production
    with patch('app.core.config.settings.ENVIRONMENT', 'production'):
        sync_kwargs = get_engine_kwargs(is_async=False)
        assert sync_kwargs['poolclass'] == QueuePool
        assert sync_kwargs['pool_size'] == settings.DB_POOL_SIZE
        assert sync_kwargs['max_overflow'] == settings.DB_MAX_OVERFLOW
        assert sync_kwargs['pool_timeout'] == settings.DB_POOL_TIMEOUT
        assert sync_kwargs['pool_recycle'] == settings.DB_POOL_RECYCLE
        assert sync_kwargs['pool_pre_ping'] is True
        assert 'connect_args' not in sync_kwargs
        
        async_kwargs = get_engine_kwargs(is_async=True)
        assert async_kwargs['poolclass'] == QueuePool
        assert async_kwargs['connect_args'] == {'command_timeout': 10} 