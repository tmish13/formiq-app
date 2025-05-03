"""
Synchronous DB test utilities.

This module provides a fallback synchronous database testing setup 
that can be used when the async test setup is not working properly.
"""
import os
import pytest
from typing import Generator, Any, Dict, List
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from app.core.database import Base
from app.core.config import settings

# Create a synchronous in-memory SQLite engine for tests
sync_test_engine = create_engine(
    "sqlite:///./test_sync.db",
    connect_args={"check_same_thread": False},
    poolclass=NullPool,
    echo=False
)

# Create a session factory
SyncTestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=sync_test_engine
)

def _import_all_models():
    """Import all models to ensure they're registered with Base.metadata."""
    # Import these here to avoid circular imports
    from app.models.user import User
    from app.models.exercise import ExerciseTemplate
    from app.models.form_check import FormCheck, FeedbackItem
    from app.models.workout import Workout, Exercise, WorkoutPlan
    from app.models.subscription import Subscription
    from app.models.video import Video
    
    return [User, ExerciseTemplate, FormCheck, FeedbackItem, Workout, 
            Exercise, WorkoutPlan, Subscription, Video]

@contextmanager
def get_sync_test_db() -> Generator[Session, None, None]:
    """Get a synchronous test database session."""
    db = SyncTestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_sync_test_db():
    """Initialize synchronous test database."""
    # Ensure all models are imported
    _import_all_models()
    
    # Create all tables
    Base.metadata.create_all(sync_test_engine)

def drop_sync_test_db():
    """Drop synchronous test database."""
    # Drop all tables
    Base.metadata.drop_all(sync_test_engine)
    
    # Remove the file if it exists
    if os.path.exists("./test_sync.db"):
        os.remove("./test_sync.db")

@pytest.fixture(scope="function")
def sync_db() -> Generator[Session, None, None]:
    """
    Fixture for synchronous database testing.
    
    Use this fixture as a fallback when async DB fixtures are not working.
    """
    # Initialize database
    init_sync_test_db()
    
    # Get session
    with get_sync_test_db() as db:
        try:
            yield db
        finally:
            # Roll back any pending transactions
            db.rollback()
    
    # Drop database
    drop_sync_test_db()

class BaseSyncDBTest:
    """
    Base class for synchronous database tests.
    
    This class provides utility methods for common database operations
    in test cases.
    """
    
    @staticmethod
    @contextmanager
    def session_scope() -> Generator[Session, None, None]:
        """Provide a transactional scope around a series of operations."""
        with get_sync_test_db() as session:
            try:
                yield session
                session.commit()
            except Exception as e:
                session.rollback()
                raise e
    
    @classmethod
    def setup_class(cls):
        """Set up test database before test case."""
        init_sync_test_db()
    
    @classmethod
    def teardown_class(cls):
        """Clean up test database after test case."""
        drop_sync_test_db()
    
    def setup_method(self):
        """Set up before each test method."""
        # Clear data before each test
        with self.session_scope() as session:
            for table in reversed(Base.metadata.sorted_tables):
                session.execute(f"DELETE FROM {table.name}")
                session.commit()
    
    def add_entity(self, entity: Any) -> Any:
        """Add entity to database and return refreshed instance."""
        with self.session_scope() as session:
            session.add(entity)
            session.commit()
            session.refresh(entity)
            return entity
    
    def add_entities(self, entities: List[Any]) -> List[Any]:
        """Add multiple entities to database and return refreshed instances."""
        with self.session_scope() as session:
            session.add_all(entities)
            session.commit()
            for entity in entities:
                session.refresh(entity)
            return entities
    
    def delete_entity(self, entity: Any) -> None:
        """Delete entity from database."""
        with self.session_scope() as session:
            session.delete(entity)
            session.commit()
    
    def query(self, model_class, **filters) -> List[Any]:
        """Query database for entities matching filters."""
        with self.session_scope() as session:
            query = session.query(model_class)
            for key, value in filters.items():
                query = query.filter(getattr(model_class, key) == value)
            return query.all()
    
    def get_by_id(self, model_class, entity_id: Any) -> Any:
        """Get entity by ID."""
        with self.session_scope() as session:
            return session.query(model_class).get(entity_id) 