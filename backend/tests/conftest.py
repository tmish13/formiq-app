import pytest
import os
from typing import Dict, Generator
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient
from app.core.config import settings
from app.core.database import Base, get_db
from app.core.security import create_access_token, get_password_hash
from app.core.constants import Roles
from app.models.user import User
from app.core.logging import get_logger
import logging

from app.main import app

logger = get_logger(__name__)

# Test database URL
TEST_DATABASE_URL = "sqlite:///./test.db"

@pytest.fixture(scope="session")
def db_engine():
    """Fixture for creating a test database engine."""
    engine = create_engine(
        TEST_DATABASE_URL, connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def db(db_engine) -> Generator[Session, None, None]:
    """Fixture for creating a new database session for each test function."""
    connection = db_engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()
    
    # Begin a nested transaction (savepoint)
    nested = connection.begin_nested()
    
    # If the connection is invalidated, reconnect
    @event.listens_for(session, "after_transaction_end")
    def end_savepoint(session, transaction):
        nonlocal nested
        if not nested.is_active:
            nested = connection.begin_nested()
    
    yield session
    
    # Close the session and the transaction
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture(scope="function")
def client(db: Session) -> Generator[TestClient, None, None]:
    """Fixture for creating a test client."""
    def override_get_db():
        try:
            yield db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    
    # Reset dependency overrides
    app.dependency_overrides = {}

@pytest.fixture(scope="session", autouse=True)
def setup_test_logging():
    """Configure logging for tests."""
    logging.basicConfig(level=logging.DEBUG)
    yield
    logging.basicConfig(level=logging.INFO)

@pytest.fixture(scope="function")
def superuser_token_headers(client: TestClient) -> Dict[str, str]:
    """Fixture for creating a superuser token."""
    access_token = create_access_token(subject=1)
    return {"Authorization": f"Bearer {access_token}"}

@pytest.fixture(scope="function")
def normal_user_token_headers(client: TestClient, db: Session) -> Dict[str, str]:
    """Fixture for creating a normal user token."""
    user = User(
        email="test@example.com",
        hashed_password=get_password_hash("password"),
        full_name="Test User",
        is_active=True,
        role=Roles.USER
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    access_token = create_access_token(subject=user.id)
    return {"Authorization": f"Bearer {access_token}"}

@pytest.fixture(scope="function")
def create_test_user(db: Session):
    """Fixture for creating a test user."""
    def _create_test_user(
        email: str = "test@example.com",
        password: str = "password",
        role: str = Roles.USER,
        is_active: bool = True
    ) -> User:
        user = User(
            email=email,
            hashed_password=get_password_hash(password),
            full_name="Test User",
            is_active=is_active,
            role=role
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    
    return _create_test_user 