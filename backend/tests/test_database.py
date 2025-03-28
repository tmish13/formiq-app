import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import QueuePool
from ..database import get_db, optimize_query, Base
import logging
import time
from contextlib import contextmanager

# Test database URL - using SQLite for testing
TEST_DATABASE_URL = "sqlite:///./test.db"

@pytest.fixture(scope="session")
def test_engine():
    """Create a test database engine"""
    engine = create_engine(
        TEST_DATABASE_URL,
        poolclass=QueuePool,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=1800
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def test_session(test_engine):
    """Create a new database session for a test"""
    connection = test_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def test_db(test_session):
    """Provide the database session"""
    return test_session

def test_get_db(test_engine, caplog):
    """Test the get_db context manager"""
    with caplog.at_level(logging.INFO):
        with get_db() as db:
            # Test that we can execute a simple query
            result = db.execute(text("SELECT 1")).scalar()
            assert result == 1
        
        # Check that the session was properly closed
        assert any(
            record.levelname == "INFO" and "Database session closed" in record.message
            for record in caplog.records
        )

def test_get_db_error_handling(test_engine, caplog):
    """Test error handling in get_db context manager"""
    with caplog.at_level(logging.ERROR):
        try:
            with get_db() as db:
                raise Exception("Test error")
        except Exception:
            pass
        
        # Check that the session was properly closed even with error
        assert any(
            record.levelname == "ERROR" and "Error in database operation" in record.message
            for record in caplog.records
        )

def test_optimize_query(test_db):
    """Test query optimization function"""
    # Create a test query
    query = test_db.query(Base)
    
    # Test that the function returns execution plan
    plan = optimize_query(query)
    assert isinstance(plan, dict)
    assert "plan" in plan

def test_connection_pool(test_engine):
    """Test database connection pooling"""
    # Test that we can get multiple connections
    connections = []
    for _ in range(5):
        conn = test_engine.connect()
        connections.append(conn)
    
    # Check that all connections are valid
    for conn in connections:
        result = conn.execute(text("SELECT 1")).scalar()
        assert result == 1
    
    # Clean up
    for conn in connections:
        conn.close()

def test_pool_overflow(test_engine):
    """Test pool overflow handling"""
    connections = []
    try:
        # Try to get more connections than pool_size + max_overflow
        for _ in range(20):
            conn = test_engine.connect()
            connections.append(conn)
    except Exception as e:
        assert "pool is at maximum capacity" in str(e).lower()
    finally:
        # Clean up
        for conn in connections:
            conn.close()

def test_connection_recycle(test_engine):
    """Test connection recycling"""
    with test_engine.connect() as conn:
        # Execute query to establish connection
        conn.execute(text("SELECT 1"))
        
        # Wait for recycle time (using small value for test)
        time.sleep(1)
        
        # Connection should still work after recycle
        result = conn.execute(text("SELECT 1")).scalar()
        assert result == 1

def test_concurrent_transactions(test_engine):
    """Test handling of concurrent transactions"""
    @contextmanager
    def get_transaction():
        connection = test_engine.connect()
        transaction = connection.begin()
        try:
            yield connection
        finally:
            transaction.rollback()
            connection.close()
    
    # Start two concurrent transactions
    with get_transaction() as conn1, get_transaction() as conn2:
        # Both connections should work independently
        result1 = conn1.execute(text("SELECT 1")).scalar()
        result2 = conn2.execute(text("SELECT 2")).scalar()
        assert result1 == 1
        assert result2 == 2

def test_session_scope(test_engine, caplog):
    """Test session scope and cleanup"""
    with caplog.at_level(logging.INFO):
        def nested_operation():
            with get_db() as db:
                return db.execute(text("SELECT 1")).scalar()
        
        result = nested_operation()
        assert result == 1
        
        # Check that session was cleaned up
        assert any(
            record.levelname == "INFO" and "Database session closed" in record.message
            for record in caplog.records
        )

def test_long_running_query(test_engine, caplog):
    """Test handling of long-running queries"""
    with caplog.at_level(logging.WARNING):
        with get_db() as db:
            # Simulate a slow query
            time.sleep(0.6)  # More than 500ms threshold
            db.execute(text("SELECT 1"))
        
        # Check that slow query was logged
        assert any(
            record.levelname == "WARNING" and "Slow query detected" in record.message
            for record in caplog.records
        )

def test_query_error_logging(test_engine, caplog):
    """Test logging of query errors"""
    with caplog.at_level(logging.ERROR):
        with pytest.raises(Exception):
            with get_db() as db:
                # Execute invalid SQL
                db.execute(text("SELECT * FROM nonexistent_table"))
        
        # Check that error was logged
        assert any(
            record.levelname == "ERROR" and "Database error occurred" in record.message
            for record in caplog.records
        )

def test_optimize_query_with_joins(test_db):
    """Test query optimization with complex joins"""
    # Create a more complex query with joins
    query = test_db.query(Base).join(Base)
    
    # Test optimization
    plan = optimize_query(query)
    assert isinstance(plan, dict)
    assert "plan" in plan
    assert "joins" in str(plan["plan"]).lower()

def test_connection_timeout(test_engine):
    """Test connection timeout handling"""
    with pytest.raises(Exception) as exc_info:
        with test_engine.connect() as conn:
            # Simulate a timeout by sleeping longer than pool_timeout
            time.sleep(35)  # More than pool_timeout (30s)
            conn.execute(text("SELECT 1"))
    
    assert "timeout" in str(exc_info.value).lower() 