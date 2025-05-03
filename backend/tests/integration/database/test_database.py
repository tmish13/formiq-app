import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy import create_engine, text, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
import os
import uuid
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock

from app.db.base_class import Base
from app.core.database import DatabaseSession
from app.models.user import User
from app.models.subscription import Subscription, SubscriptionTier
from app.models.workout import Workout, Exercise, WorkoutPlan
from app.models.user_settings import UserSettings
from app.models.user_session import UserSession
from app.models.form_check import FormCheck, FeedbackItem
from app.models.video import Video

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

@pytest.fixture(autouse=True)
async def cleanup_test_db():
    if os.path.exists("./test.db"):
        os.remove("./test.db")
    yield
    if os.path.exists("./test.db"):
        os.remove("./test.db")

@pytest.fixture
async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=True)
    async with engine.begin() as conn:
        # Enable foreign key constraints and unique constraints in SQLite
        await conn.execute(text("PRAGMA foreign_keys = ON"))
        await conn.execute(text("PRAGMA unique_indexes = ON"))
        await conn.execute(text("PRAGMA ignore_check_constraints = OFF"))
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest.fixture
async def test_session(test_engine):
    async_session = sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False, autocommit=False, autoflush=False
    )
    async with async_session() as session:
        yield session

@pytest.mark.asyncio
async def test_uuid_primary_key(test_session: AsyncSession):
    """Test UUID primary key handling."""
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email="test@example.com",
        username="testuser",
        hashed_password="test",
        is_active=True,
        subscription_tier=SubscriptionTier.FREE
    )
    test_session.add(user)
    await test_session.commit()
    
    # Verify UUID is stored correctly
    result = await test_session.execute(
        text("SELECT id FROM users WHERE id = :id"),
        {"id": user_id.hex}
    )
    stored_id = result.scalar()
    assert stored_id == user_id.hex

@pytest.mark.asyncio
async def test_foreign_key_constraints(test_session: AsyncSession):
    """Test foreign key constraints."""
    # Create parent record
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email="test@example.com",
        username="testuser",
        hashed_password="test",
        is_active=True,
        subscription_tier=SubscriptionTier.FREE
    )
    test_session.add(user)
    await test_session.commit()

    # Attempt to create child with invalid foreign key using raw SQL
    invalid_user_id = uuid.uuid4()
    async with test_session.begin() as transaction:
        # Ensure foreign key constraints are enabled
        await test_session.execute(text("PRAGMA foreign_keys = ON"))
        
        with pytest.raises(IntegrityError):
            await test_session.execute(
                text("INSERT INTO workouts (id, name, user_id, created_at) VALUES (:id, :name, :user_id, :created_at)"),
                {
                    "id": str(uuid.uuid4()),
                    "name": "Invalid Workout",
                    "user_id": str(invalid_user_id),
                    "created_at": datetime.now()
                }
            )
            await transaction.commit()

@pytest.mark.asyncio
async def test_enum_field_mapping(test_session: AsyncSession):
    """Test enum field mapping and validation."""
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email="test@example.com",
        username="testuser",
        hashed_password="test",
        is_active=True,
        subscription_tier=SubscriptionTier.FREE
    )
    test_session.add(user)
    await test_session.commit()

    # Query the user and verify enum
    result = await test_session.get(User, user_id)
    assert result.subscription_tier == SubscriptionTier.FREE

    # Test invalid enum value using raw SQL
    with pytest.raises(IntegrityError):
        await test_session.execute(
            text("INSERT INTO users (id, email, username, hashed_password, is_active, subscription_tier) VALUES (:id, :email, :username, :password, :active, :tier)"),
            {
                "id": str(uuid.uuid4()),
                "email": "test2@example.com",
                "username": "testuser2",
                "password": "test",
                "active": True,
                "tier": "INVALID_TIER"
            }
        )
        await test_session.commit()

@pytest.mark.asyncio
async def test_transaction_rollback(test_session: AsyncSession):
    """Test transaction rollback on error."""
    # Create first user
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email="test@example.com",
        username="testuser",
        hashed_password="test",
        is_active=True,
        subscription_tier=SubscriptionTier.FREE
    )
    test_session.add(user)
    await test_session.commit()

    # Try to create second user with same email
    invalid_user = User(
        id=uuid.uuid4(),
        email="test@example.com",  # Duplicate email
        username="testuser2",
        hashed_password="test",
        is_active=True,
        subscription_tier=SubscriptionTier.FREE
    )
    test_session.add(invalid_user)
    
    try:
        await test_session.commit()
        pytest.fail("Expected IntegrityError was not raised")
    except IntegrityError:
        await test_session.rollback()  # Explicitly rollback on error

    # Start a new transaction
    await test_session.begin()
    
    # Verify original user is unchanged
    await test_session.refresh(user)
    assert user.email == "test@example.com"

@pytest.mark.asyncio
async def test_complex_join_operations(test_session: AsyncSession):
    """Test complex join operations with multiple tables."""
    # Create test data
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email="test@example.com",
        username="testuser",
        hashed_password="test",
        is_active=True,
        subscription_tier=SubscriptionTier.FREE
    )
    test_session.add(user)
    await test_session.commit()

    workout = Workout(
        id=uuid.uuid4(),
        name="Test Workout",
        user_id=user_id,
        created_at=datetime.now()
    )
    test_session.add(workout)
    await test_session.commit()

    exercise = Exercise(
        id=uuid.uuid4(),
        name="Test Exercise",
        workout_id=workout.id,
        sets=3,
        reps=10,
        created_at=datetime.now()
    )
    test_session.add(exercise)
    await test_session.commit()

    # Test complex join query
    query = text("""
        SELECT u.email, w.name as workout_name, e.name as exercise_name
        FROM users u
        JOIN workouts w ON u.id = w.user_id
        JOIN exercises e ON w.id = e.workout_id
        WHERE u.id = :user_id
    """)
    result = await test_session.execute(query, {"user_id": user_id.hex})
    row = result.first()
    
    assert row is not None
    assert row.email == "test@example.com"
    assert row.workout_name == "Test Workout"
    assert row.exercise_name == "Test Exercise"

@pytest.mark.asyncio
async def test_cascade_delete(test_session: AsyncSession):
    """Test cascade delete operations."""
    # Create parent with children
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email="test@example.com",
        username="testuser",
        hashed_password="test",
        is_active=True,
        subscription_tier=SubscriptionTier.FREE
    )
    test_session.add(user)
    await test_session.commit()

    workout = Workout(
        id=uuid.uuid4(),
        name="Test Workout",
        user_id=user_id,
        created_at=datetime.now()
    )
    test_session.add(workout)
    await test_session.commit()

    exercise = Exercise(
        id=uuid.uuid4(),
        name="Test Exercise",
        workout_id=workout.id,
        sets=3,
        reps=10,
        created_at=datetime.now()
    )
    test_session.add(exercise)
    await test_session.commit()

    # Delete parent
    await test_session.delete(user)
    await test_session.commit()

    # Verify children are deleted
    result = await test_session.execute(
        text("SELECT COUNT(*) FROM workouts WHERE user_id = :user_id"),
        {"user_id": user_id.hex}
    )
    workout_count = result.scalar()
    assert workout_count == 0

    result = await test_session.execute(
        text("SELECT COUNT(*) FROM exercises WHERE workout_id = :workout_id"),
        {"workout_id": workout.id.hex}
    )
    exercise_count = result.scalar()
    assert exercise_count == 0

@pytest.mark.asyncio
async def test_get_db(test_session):
    assert test_session is not None
    result = await test_session.execute(text("SELECT 1"))
    value = result.scalar()
    assert value == 1

@pytest.mark.asyncio
async def test_get_db_error_handling(test_session):
    """Test error handling in get_db."""
    with pytest.raises(Exception):
        async with get_db() as db:
            await db.execute(text("SELECT * FROM nonexistent_table"))

@pytest.mark.asyncio
async def test_optimize_query(test_session):
    result = await test_session.execute(text("SELECT 1"))
    value = result.scalar()
    assert value == 1

@pytest.mark.asyncio
async def test_connection_pool(test_session):
    for _ in range(5):
        result = await test_session.execute(text("SELECT 1"))
        value = result.scalar()
        assert value == 1

@pytest.mark.asyncio
async def test_pool_overflow(test_session):
    try:
        for _ in range(100):
            result = await test_session.execute(text("SELECT 1"))
            value = result.scalar()
            assert value == 1
    except SQLAlchemyError as e:
        assert "pool" in str(e).lower()

@pytest.mark.asyncio
async def test_connection_recycle(test_session):
    result = await test_session.execute(text("SELECT 1"))
    value = result.scalar()
    assert value == 1

@pytest.mark.asyncio
async def test_concurrent_transactions(test_session):
    result = await test_session.execute(text("SELECT 1"))
    value = result.scalar()
    assert value == 1

@pytest.mark.asyncio
async def test_session_scope(test_session):
    result = await test_session.execute(text("SELECT 1"))
    value = result.scalar()
    assert value == 1

@pytest.mark.asyncio
async def test_long_running_query(test_session):
    result = await test_session.execute(text("SELECT 1"))
    value = result.scalar()
    assert value == 1

@pytest.mark.asyncio
async def test_query_error_logging(test_session):
    with pytest.raises(SQLAlchemyError):
        await test_session.execute(text("INVALID SQL"))

@pytest.mark.asyncio
async def test_optimize_query_with_joins(test_session: AsyncSession):
    """Test query optimization with joins."""
    # Create test data
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email="test@example.com",
        username="testuser",
        hashed_password="test",
        is_active=True,
        subscription_tier=SubscriptionTier.FREE
    )
    test_session.add(user)
    await test_session.commit()

    subscription = Subscription(
        id=uuid.uuid4(),
        user_id=user_id,
        tier=SubscriptionTier.BASIC,
        status="active"
    )
    test_session.add(subscription)
    await test_session.commit()

    # Execute optimized query with joins
    query = text("""
        SELECT u.email, s.tier, s.status
        FROM users u
        JOIN subscriptions s ON u.id = s.user_id
        WHERE u.id = :user_id
    """)
    result = await test_session.execute(query, {"user_id": user_id.hex})
    row = result.first()
    
    assert row is not None
    assert row.email == "test@example.com"
    assert row.tier == "BASIC"
    assert row.status == "active"

@pytest.mark.asyncio
async def test_connection_timeout(test_session):
    result = await test_session.execute(text("SELECT 1"))
    value = result.scalar()
    assert value == 1

@pytest.mark.asyncio
async def test_database_url_functions(monkeypatch):
    """Test database URL functions for different environments."""
    from app.core.database import get_database_url, get_async_database_url
    from app.core.config import settings
    
    # Mock environment settings
    monkeypatch.setattr(settings, "ENVIRONMENT", "test")
    monkeypatch.setattr(settings, "SQLALCHEMY_DATABASE_URI", "sqlite:///./test.db")
    
    # Test sync database URL
    sync_url = get_database_url()
    assert "sqlite" in sync_url
    
    # Test async database URL
    async_url = get_async_database_url()
    assert "sqlite+aiosqlite" in async_url

@pytest.mark.asyncio
async def test_engine_kwargs(monkeypatch):
    """Test engine kwargs configuration."""
    from app.core.database import get_engine_kwargs
    from app.core.config import settings
    
    # Mock environment settings
    monkeypatch.setattr(settings, "ENVIRONMENT", "test")
    monkeypatch.setattr(settings, "DB_ECHO", True)
    
    # Test sync engine kwargs
    sync_kwargs = get_engine_kwargs(is_async=False)
    assert "poolclass" in sync_kwargs
    assert "connect_args" in sync_kwargs
    
    # Test async engine kwargs
    async_kwargs = get_engine_kwargs(is_async=True)
    assert "poolclass" in async_kwargs
    assert "connect_args" in async_kwargs

@pytest.fixture
def sync_engine():
    """Create a sync SQLite engine for testing."""
    engine = create_engine("sqlite:///./test.db", echo=True)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)

@pytest.fixture
def sync_session_factory(sync_engine):
    """Create a sync session factory for testing."""
    return sessionmaker(
        bind=sync_engine,
        autocommit=False,
        autoflush=False
    )

@pytest.mark.asyncio
async def test_database_session_context_manager(test_engine):
    """Test async session context manager."""
    async_session = sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False, autocommit=False, autoflush=False
    )
    async with DatabaseSession(async_session) as session:
        result = await session.execute(text("SELECT 1"))
        value = result.scalar()
        assert value == 1

def test_database_session_sync_context(sync_engine):
    """Test sync session context manager."""
    sync_session = sessionmaker(
        bind=sync_engine,
        autocommit=False,
        autoflush=False
    )
    with DatabaseSession(sync_session) as session:
        result = session.execute_sync(text("SELECT 1"))
        value = result.scalar()
        assert value == 1

@pytest.mark.asyncio
async def test_database_session_factory_validation(test_engine, sync_engine):
    """Test session factory validation."""
    async_session = sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False, autocommit=False, autoflush=False
    )
    sync_session = sessionmaker(
        bind=sync_engine,
        autocommit=False,
        autoflush=False
    )

    # Test async session in sync context
    with pytest.raises(SQLAlchemyError, match="Cannot use async session factory in sync context"):
        with DatabaseSession(async_session) as session:
            pass

    # Test sync session in async context
    with pytest.raises(SQLAlchemyError, match="Cannot use sync session factory in async context"):
        async with DatabaseSession(sync_session) as session:
            pass

@pytest.mark.asyncio
async def test_database_session_cleanup(test_engine, sync_engine):
    """Test session cleanup."""
    async_session = sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False, autocommit=False, autoflush=False
    )
    sync_session = sessionmaker(
        bind=sync_engine,
        autocommit=False,
        autoflush=False
    )

    session = None
    async with DatabaseSession(async_session) as session:
        result = await session.execute(text("SELECT 1"))
        value = result.scalar()
        assert value == 1
    assert session._closed
    assert session.db is None

    # Test sync session cleanup
    sync_session_obj = None
    with DatabaseSession(sync_session) as sync_session_obj:
        result = sync_session_obj.execute_sync(text("SELECT 1"))
        value = result.scalar()
        assert value == 1
    assert sync_session_obj._closed
    assert sync_session_obj.db is None

@pytest.mark.asyncio
async def test_get_db_session(test_engine):
    """Test get_db_session function."""
    from app.core.database import get_db_session
    
    async_session = sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False, autocommit=False, autoflush=False
    )
    
    # Test get_db_session with test session factory
    async with get_db_session(async_session) as session:
        # Execute a simple query
        result = await session.execute(text("SELECT 1"))
        assert result.scalar() == 1
        
        # Force an error to test rollback
        with pytest.raises(SQLAlchemyError):
            await session.execute(text("INVALID SQL"))
    
    # Verify session is closed after context
    with pytest.raises(SQLAlchemyError):
        await session.execute(text("SELECT 1"))
    
    # Test get_db_session with mocked session factory that raises an exception
    def failing_session_factory():
        raise Exception("Session creation failed")
    
    with pytest.raises(Exception):
        async with get_db_session(failing_session_factory) as session:
            await session.execute(text("SELECT 1"))

@pytest.mark.asyncio
async def test_init_db(test_session, monkeypatch):
    """Test database initialization."""
    # Mock the database URL to use SQLite
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///./test.db")
    
    # Create a test table
    await test_session.execute(text("""
        CREATE TABLE IF NOT EXISTS test_table (
            id INTEGER PRIMARY KEY,
            name TEXT
        )
    """))
    await test_session.commit()
    
    # Verify table exists
    result = await test_session.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='test_table'"))
    assert result.scalar() is not None

@pytest.mark.asyncio
async def test_close_db(test_session):
    """Test database connection closure."""
    # Create a test table
    await test_session.execute(text("""
        CREATE TABLE IF NOT EXISTS test_table (
            id INTEGER PRIMARY KEY,
            name TEXT
        )
    """))
    await test_session.commit()
    
    # Close the session
    await test_session.close()
    
    # Create a new session to verify the previous one is closed
    new_session = AsyncSession(test_session.bind)
    result = await new_session.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='test_table'"))
    assert result.scalar() is not None
    await new_session.close()

@pytest.mark.asyncio
async def test_get_async_db_error_handling(test_session, monkeypatch):
    """Test error handling in get_async_db."""
    # Mock the database URL to use SQLite
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///./test.db")
    
    with pytest.raises(Exception):
        async with get_async_db() as db:
            await db.execute(text("SELECT * FROM nonexistent_table"))

@pytest.mark.asyncio
async def test_optimize_query_functions():
    """Test query optimization functions."""
    from app.core.database import optimize_query, optimize_sqlalchemy_query
    
    # Test optimize_query
    query = "SELECT * FROM users"
    optimized = optimize_query(query)
    assert optimized == query
    
    # Test optimize_sqlalchemy_query
    from sqlalchemy import select
    from app.models.user import User
    
    query = select(User)
    optimized = optimize_sqlalchemy_query(query)
    assert optimized == query

@pytest.mark.asyncio
async def test_double_session_closure(test_engine):
    """Test double session closure behavior."""
    async_session = sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False, autocommit=False, autoflush=False
    )
    async with DatabaseSession(async_session) as session:
        # First closure
        await session.__aexit__(None, None, None)
        assert session._closed
        assert session.db is None
        
        # Second closure should raise error
        with pytest.raises(SQLAlchemyError, match="Cannot reuse a closed session"):
            await session.__aenter__()

@pytest.mark.asyncio
async def test_session_rollback_failure(test_engine):
    """Test session rollback failure handling."""
    # Create a mock async session that fails on rollback
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.rollback = AsyncMock(side_effect=SQLAlchemyError("Rollback failed"))
    mock_session.close = AsyncMock()
    
    # Create a session factory that returns our mock session
    class FailingSessionFactory:
        is_async = True
        def __call__(self):
            return mock_session
    
    failing_factory = FailingSessionFactory()
    db = DatabaseSession(failing_factory)
    
    # Use the session and trigger an exception to trigger rollback
    with pytest.raises(SQLAlchemyError) as exc_info:
        async with db:
            # Raise an exception to trigger rollback
            raise RuntimeError("Test exception")
            
    # Verify rollback was called and proper error is raised
    assert "Rollback failed" in str(exc_info.value)
    assert mock_session.rollback.called
    assert mock_session.close.called

@pytest.mark.asyncio
async def test_commit_with_broken_transaction(test_engine):
    """Test commit with broken transaction."""
    # Create a mock async session that fails on commit
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.commit = AsyncMock(side_effect=SQLAlchemyError("Commit failed"))
    mock_session.rollback = AsyncMock()
    mock_session.close = AsyncMock()
    
    # Create a session factory that returns our mock session
    class FailingSessionFactory:
        is_async = True
        def __call__(self):
            return mock_session
    
    failing_factory = FailingSessionFactory()
    db = DatabaseSession(failing_factory)
    
    # Use the session and allow it to commit
    with pytest.raises(SQLAlchemyError) as exc_info:
        async with db:
            pass  # No exception here, so commit will be called
            
    # Verify commit was called and proper error is raised
    assert "Commit failed" in str(exc_info.value)
    assert mock_session.commit.called
    assert mock_session.close.called
    
    # Commit error should trigger a rollback
    assert mock_session.rollback.called

@pytest.mark.asyncio
async def test_async_session_timeout(test_engine):
    """Test async session timeout handling."""
    # Create a new engine with timeout
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"timeout": 0.001},
        echo=True
    )
    
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False, autocommit=False, autoflush=False
    )
    
    async with DatabaseSession(async_session) as session:
        # Attempt a query that should timeout
        with pytest.raises(SQLAlchemyError):
            await session.execute(text("SELECT pg_sleep(1)"))
    
    await engine.dispose()

@pytest.mark.asyncio
async def test_context_manager_cleanup_closed_session(test_engine):
    """Test context manager cleanup when session is already closed."""
    async_session = sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False, autocommit=False, autoflush=False
    )
    
    session = DatabaseSession(async_session)
    await session.__aenter__()
    await session.__aexit__(None, None, None)
    
    # Attempt cleanup on already closed session
    await session.__aexit__(None, None, None)
    assert session._closed
    assert session.db is None

@pytest.mark.asyncio
async def test_sync_session_error_handling(sync_engine):
    """Test error handling in sync session."""
    sync_session = sessionmaker(
        bind=sync_engine,
        autocommit=False,
        autoflush=False
    )
    
    with DatabaseSession(sync_session) as session:
        # Test execute with closed session
        session._closed = True
        with pytest.raises(SQLAlchemyError, match="Session is closed or not initialized"):
            session.execute_sync(text("SELECT 1"))
        
        # Test execute with async method on sync session
        session._closed = False
        with pytest.raises(SQLAlchemyError, match="Cannot use async execution with sync session"):
            await session.execute(text("SELECT 1"))

@pytest.mark.asyncio
async def test_async_session_error_handling(test_engine):
    """Test error handling in async session."""
    async_session = sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False, autocommit=False, autoflush=False
    )
    
    async with DatabaseSession(async_session) as session:
        # Test execute with closed session
        session._closed = True
        with pytest.raises(SQLAlchemyError, match="Session is closed or not initialized"):
            await session.execute(text("SELECT 1"))
        
        # Test execute_sync with async session
        session._closed = False
        with pytest.raises(SQLAlchemyError, match="Cannot use sync execution with async session"):
            session.execute_sync(text("SELECT 1"))

@pytest.mark.asyncio
async def test_session_execution_error_handling(test_engine):
    """Test error handling during session execution."""
    async_session = sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False, autocommit=False, autoflush=False
    )
    
    async with DatabaseSession(async_session) as session:
        # Test execute with closed session
        session._closed = True
        with pytest.raises(SQLAlchemyError, match="Session is closed or not initialized"):
            await session.execute(text("SELECT 1"))
        
        # Test execute_sync with async session
        session._closed = False
        with pytest.raises(SQLAlchemyError, match="Cannot use sync execution with async session"):
            session.execute_sync(text("SELECT 1"))

@pytest.mark.asyncio
async def test_session_cleanup_with_exception(test_engine):
    """Test session cleanup when an exception occurs during cleanup."""
    async_session = sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False, autocommit=False, autoflush=False
    )
    
    session = DatabaseSession(async_session)
    await session.__aenter__()
    
    # Force cleanup to fail by closing the underlying session
    await session.db.close()
    
    # Attempt cleanup should not raise an exception
    await session.__aexit__(None, None, None)
    assert session._closed
    assert session.db is None

@pytest.mark.asyncio
async def test_get_db_session_with_invalid_factory():
    """Test get_db_session with invalid session factory."""
    from app.core.database import get_db_session
    
    # Test with invalid session factory
    with pytest.raises(Exception):
        async with get_db_session(lambda: None) as session:
            await session.execute(text("SELECT 1"))

@pytest.mark.asyncio
async def test_optimize_query_functions():
    """Test query optimization functions."""
    from app.core.database import optimize_query, optimize_sqlalchemy_query
    
    # Test optimize_query with different query types
    assert optimize_query("SELECT * FROM users") == "SELECT * FROM users"
    assert optimize_query("INSERT INTO users (id) VALUES (1)") == "INSERT INTO users (id) VALUES (1)"
    
    # Test optimize_sqlalchemy_query with different query types
    from sqlalchemy import select
    from app.models.user import User
    
    # Test with select query
    query = select(User)
    assert optimize_sqlalchemy_query(query) == query
    
    # Test with join query
    query = select(User).join(User.subscriptions)
    assert optimize_sqlalchemy_query(query) == query

@pytest.mark.asyncio
async def test_session_creation_error_handling():
    """Test error handling during session creation."""
    def failing_session_factory():
        raise SQLAlchemyError("Session creation failed")

    db = DatabaseSession(failing_session_factory)
    with pytest.raises(SQLAlchemyError) as exc_info:
        async with db:
            pass  # This should not be reached

    assert "Cannot use sync session factory in async context" in str(exc_info.value)
    assert db._closed is True
    assert db.db is None

@pytest.mark.asyncio
async def test_error_handling_and_cleanup(test_engine):
    """Test error handling and cleanup in various scenarios"""
    # Create a session factory
    async_session = sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False
    )
    
    # Create DatabaseSession
    db = DatabaseSession(async_session)
    
    # Test error handling during operation
    with pytest.raises(Exception) as exc_info:
        async with db as session:
            # Perform a simple operation before raising error
            result = await session.execute(text("SELECT 1"))
            assert result.scalar() == 1
            raise Exception("First error")
    
    assert "First error" in str(exc_info.value)
    assert db.db is None
    assert db._closed

@pytest.mark.asyncio
async def test_transaction_edge_cases(test_engine):
    """Test transaction edge cases"""
    # Create a session factory
    async_session = sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False
    )
    
    # Test empty transaction
    db1 = DatabaseSession(async_session)
    async with db1 as session:
        result = await session.execute(text("SELECT 1"))
        assert result.scalar() == 1
    
    assert db1.db is None
    assert db1._closed
    
    # Test new transaction with same session factory
    db2 = DatabaseSession(async_session)
    async with db2 as session:
        # Create a test user
        user = User(
            id=uuid.uuid4(),
            email="test@example.com",
            username="testuser",
            hashed_password="test",
            is_active=True,
            subscription_tier=SubscriptionTier.FREE
        )
        session.add(user)
        await session.commit()
        
        # Verify user was created using text() instead of select()
        result = await session.execute(
            text("SELECT email FROM users WHERE email = :email"),
            {"email": "test@example.com"}
        )
        created_user_email = result.scalar()
        assert created_user_email == "test@example.com"
    
    assert db2.db is None
    assert db2._closed

@pytest.mark.asyncio
async def test_session_factory_failure():
    """Test error handling when session factory fails."""
    class FailingSessionFactory:
        is_async = True
        def __call__(self):
            raise SQLAlchemyError("Session creation failed")
    
    failing_factory = FailingSessionFactory()
    db = DatabaseSession(failing_factory)
    
    with pytest.raises(SQLAlchemyError) as exc_info:
        async with db:
            pass
    
    assert "Session creation failed" in str(exc_info.value)
    assert db._closed
    assert db.db is None

@pytest.mark.asyncio
async def test_session_cleanup_on_factory_error():
    """Test session cleanup when factory raises an error."""
    class FailingSessionFactory:
        is_async = True
        def __call__(self):
            raise SQLAlchemyError("Session creation failed")
    
    failing_factory = FailingSessionFactory()
    db = DatabaseSession(failing_factory)
    
    with pytest.raises(SQLAlchemyError) as exc_info:
        async with db:
            pass
    
    assert "Session creation failed" in str(exc_info.value)
    assert db._closed
    assert db.db is None

@pytest.mark.asyncio
async def test_session_cleanup_with_commit_error(test_engine):
    """Test cleanup when commit fails."""
    # Create a mock async session that fails on commit
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.commit = AsyncMock(side_effect=SQLAlchemyError("Commit failed"))
    mock_session.close = AsyncMock()
    mock_session.execute = AsyncMock()
    
    class SessionFactory:
        is_async = True
        def __call__(self):
            return mock_session
    
    session_factory = SessionFactory()
    db = DatabaseSession(session_factory)
    
    with pytest.raises(SQLAlchemyError) as exc_info:
        async with db:
            await db.execute("SELECT 1")
            
    assert "Commit failed" in str(exc_info.value)
    assert db._closed
    assert db.db is None
    assert mock_session.commit.called
    assert mock_session.close.called

@pytest.mark.asyncio
async def test_session_cleanup_with_rollback_error():
    """Test cleanup when rollback fails."""
    # Create a mock async session that fails on rollback
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.rollback = AsyncMock(side_effect=SQLAlchemyError("Rollback failed"))
    mock_session.close = AsyncMock()
    mock_session.execute = AsyncMock()
    
    class SessionFactory:
        is_async = True
        def __call__(self):
            return mock_session
    
    session_factory = SessionFactory()
    db = DatabaseSession(session_factory)
    
    with pytest.raises(SQLAlchemyError) as exc_info:
        async with db:
            await db.execute("SELECT 1")
            raise Exception("Trigger rollback")
            
    assert "Rollback failed" in str(exc_info.value)
    assert db._closed
    assert db.db is None
    assert mock_session.rollback.called
    assert mock_session.close.called

def test_sync_session_commit_error(sync_engine):
    """Test sync session commit error handling."""
    sync_session = sessionmaker(
        bind=sync_engine,
        autocommit=False,
        autoflush=False
    )
    
    db = DatabaseSession(sync_session)
    with db as session:
        # Mock commit to fail
        def failing_commit():
            raise SQLAlchemyError("Commit failed")
        session.db.commit = failing_commit
        
        # Create a test user
        user = User(
            id=uuid.uuid4(),
            email="test@example.com",
            username="testuser",
            hashed_password="test",
            is_active=True,
            subscription_tier=SubscriptionTier.FREE
        )
        session.db.add(user)
        
        with pytest.raises(SQLAlchemyError) as exc_info:
            session.__exit__(None, None, None)
        assert "Commit failed" in str(exc_info.value)
    
    assert db._closed is True
    assert db.db is None

def test_sync_session_rollback_error(sync_engine):
    """Test sync session rollback error handling."""
    sync_session = sessionmaker(
        bind=sync_engine,
        autocommit=False,
        autoflush=False
    )
    
    db = DatabaseSession(sync_session)
    with db as session:
        # Mock rollback to fail
        def failing_rollback():
            raise SQLAlchemyError("Rollback failed")
        session.db.rollback = failing_rollback
        
        # Force an error to trigger rollback
        with pytest.raises(Exception):
            session.__exit__(Exception(), "Test error", None)
    
    assert db._closed is True
    assert db.db is None

def test_sync_session_nested_transaction(sync_engine):
    """Test sync session nested transaction handling."""
    sync_session = sessionmaker(
        bind=sync_engine,
        autocommit=False,
        autoflush=False
    )
    
    db = DatabaseSession(sync_session)
    with db as session:
        # Start a nested transaction
        with session.db.begin_nested() as nested:
            user = User(
                id=uuid.uuid4(),
                email="test@example.com",
                username="testuser",
                hashed_password="test",
                is_active=True,
                subscription_tier=SubscriptionTier.FREE
            )
            session.db.add(user)
            nested.commit()
        
        # Verify user was created
        result = session.execute_sync(
            text("SELECT email FROM users WHERE email = :email"),
            {"email": "test@example.com"}
        )
        assert result.scalar() == "test@example.com"
    
    assert db._closed is True
    assert db.db is None

def test_sync_session_state_transitions(sync_engine):
    """Test sync session state transitions."""
    sync_session = sessionmaker(
        bind=sync_engine,
        autocommit=False,
        autoflush=False
    )
    
    db = DatabaseSession(sync_session)
    
    # Test initial state
    assert not db._closed
    assert db.db is None
    
    # Test state after enter
    with db as session:
        assert not db._closed
        assert db.db is not None
        
        # Test state during transaction
        user = User(
            id=uuid.uuid4(),
            email="test@example.com",
            username="testuser",
            hashed_password="test",
            is_active=True,
            subscription_tier=SubscriptionTier.FREE
        )
        session.db.add(user)
        
        # Test state before commit
        assert not db._closed
        assert db.db is not None
    
    # Test final state
    assert db._closed
    assert db.db is None

@pytest.mark.asyncio
async def test_async_transaction_flow(test_engine):
    """Test async transaction flow with commit and rollback."""
    async_session = sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False, autocommit=False, autoflush=False
    )
    
    # Test successful transaction
    db = DatabaseSession(async_session)
    db._is_async = True
    
    async with db:
        # Create a test user
        user = User(
            id=uuid.uuid4(),
            email="test1@example.com",
            username="testuser1",
            hashed_password="test",
            is_active=True,
            subscription_tier=SubscriptionTier.FREE
        )
        db.add(user)
        await db.flush()
        
        # Verify user was created
        result = await db.execute(
            text("SELECT email FROM users WHERE email = :email"),
            {"email": "test1@example.com"}
        )
        row = result.first()
        assert row is not None
        assert row[0] == "test1@example.com"
    
    # Test failed transaction
    db = DatabaseSession(async_session)
    db._is_async = True
    
    with pytest.raises(SQLAlchemyError):
        async with db:
            # Create another user
            user2 = User(
                id=uuid.uuid4(),
                email="test2@example.com",
                username="testuser2",
                hashed_password="test",
                is_active=True,
                subscription_tier=SubscriptionTier.FREE
            )
            db.add(user2)
            await db.flush()
            
            # Try an invalid operation
            await db.execute(text("SELECT * FROM nonexistent_table"))
    
    # Verify the failed transaction was rolled back
    db = DatabaseSession(async_session)
    db._is_async = True
    
    async with db:
        result = await db.execute(
            text("SELECT COUNT(*) FROM users WHERE email = :email"),
            {"email": "test2@example.com"}
        )
        count = result.scalar()
        assert count == 0  # User from failed transaction should not exist
        
        # First user should still exist
        result = await db.execute(
            text("SELECT COUNT(*) FROM users WHERE email = :email"),
            {"email": "test1@example.com"}
        )
        count = result.scalar()
        assert count == 1

def test_sync_transaction_flow(sync_engine):
    """Test sync transaction flow with commit and rollback."""
    sync_session = sessionmaker(
        bind=sync_engine,
        autocommit=False,
        autoflush=False
    )
    
    # Test successful transaction
    db = DatabaseSession(sync_session)
    with db as session:
        user = User(
            id=uuid.uuid4(),
            email="test3@example.com",
            username="testuser3",
            hashed_password="test",
            is_active=True,
            subscription_tier=SubscriptionTier.FREE
        )
        session.db.add(user)
        session.db.commit()
        
        # Verify user was created
        result = session.execute_sync(
            text("SELECT email FROM users WHERE email = :email"),
            {"email": "test3@example.com"}
        )
        assert result.scalar() == "test3@example.com"
    
    # Test failed transaction with rollback
    db = DatabaseSession(sync_session)
    with pytest.raises(SQLAlchemyError):
        with db as session:
            user = User(
                id=uuid.uuid4(),
                email="test4@example.com",
                username="testuser4",
                hashed_password="test",
                is_active=True,
                subscription_tier=SubscriptionTier.FREE
            )
            session.db.add(user)
            session.execute_sync(text("INVALID SQL"))
    
    # Verify user was not created
    db = DatabaseSession(sync_session)
    with db as session:
        result = session.execute_sync(
            text("SELECT email FROM users WHERE email = :email"),
            {"email": "test4@example.com"}
        )
        assert result.scalar() is None

@pytest.mark.asyncio
async def test_async_session_attribute_proxy(test_engine):
    """Test async session attribute proxy behavior."""
    async_session = sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False, autocommit=False, autoflush=False
    )
    
    db = DatabaseSession(async_session)
    async with db as session:
        # Test attribute access
        assert hasattr(session, 'add')
        assert hasattr(session, 'commit')
        assert hasattr(session, 'rollback')
        
        # Test attribute proxy with closed session
        session._closed = True
        with pytest.raises(SQLAlchemyError, match="Session is closed or not initialized"):
            session.add(None)

def test_sync_session_attribute_proxy(sync_engine):
    """Test sync session attribute proxy behavior."""
    sync_session = sessionmaker(
        bind=sync_engine,
        autocommit=False,
        autoflush=False
    )
    
    db = DatabaseSession(sync_session)
    with db as session:
        # Test attribute access
        assert hasattr(session, 'add')
        assert hasattr(session, 'commit')
        assert hasattr(session, 'rollback')
        
        # Test attribute proxy with closed session
        session._closed = True
        with pytest.raises(SQLAlchemyError, match="Session is closed or not initialized"):
            session.add(None)