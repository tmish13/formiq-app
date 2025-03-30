# Development Guide

## Overview

This guide provides information for developers working on the Formiq application, including coding standards, development workflow, and best practices.

## Development Environment

### 1. Required Tools

- Python 3.9 or higher
- PostgreSQL 13 or higher
- Redis 6 or higher
- Git
- Docker (optional)
- VS Code (recommended)

### 2. VS Code Extensions

Recommended extensions:
- Python
- Pylance
- Black Formatter
- isort
- GitLens
- Docker
- REST Client
- Thunder Client

### 3. Development Tools

1. Install pre-commit hooks:
```bash
pre-commit install
```

2. Install development dependencies:
```bash
pip install -r requirements-dev.txt
```

## Code Style

### 1. Python Code Style

- Follow PEP 8 guidelines
- Use Black for code formatting
- Use isort for import sorting
- Use mypy for type checking
- Maximum line length: 88 characters (Black default)

### 2. Type Hints

- Use type hints for all function parameters and return values
- Use Optional[] for nullable values
- Use List[], Dict[], etc. for collections
- Use Union[] for multiple types
- Use Any[] sparingly

Example:
```python
from typing import List, Optional, Union
from datetime import datetime

def get_user(
    user_id: str,
    include_deleted: bool = False
) -> Optional[User]:
    pass

def get_users(
    skip: int = 0,
    limit: int = 100
) -> List[User]:
    pass

def update_user(
    user_id: str,
    data: Union[dict, UserUpdate]
) -> User:
    pass
```

### 3. Documentation

1. Module docstrings:
```python
"""Module description.

This module provides functionality for user management.
"""

from typing import List
```

2. Class docstrings:
```python
class UserService:
    """Service for managing users.
    
    This service provides methods for user CRUD operations,
    authentication, and authorization.
    """
```

3. Function docstrings:
```python
def create_user(
    email: str,
    password: str,
    full_name: str
) -> User:
    """Create a new user.
    
    Args:
        email: User's email address
        password: User's password
        full_name: User's full name
        
    Returns:
        User: Created user object
        
    Raises:
        HTTPException: If user with email already exists
    """
```

### 4. Error Handling

1. Use custom exceptions:
```python
class UserNotFoundError(Exception):
    """Raised when a user is not found."""
    pass

class InvalidCredentialsError(Exception):
    """Raised when credentials are invalid."""
    pass
```

2. Handle exceptions in services:
```python
try:
    user = await self.repository.get(user_id)
    if not user:
        raise UserNotFoundError(f"User {user_id} not found")
except Exception as e:
    logger.error(f"Error getting user: {str(e)}")
    raise
```

3. Handle exceptions in API endpoints:
```python
@router.get("/users/{user_id}")
async def get_user(
    user_id: str,
    user_service: UserService = Depends(get_user_service)
):
    try:
        return await user_service.get_user(user_id)
    except UserNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"User {user_id} not found"
        )
```

## Development Workflow

### 1. Git Workflow

1. Create feature branch:
```bash
git checkout -b feature/your-feature-name
```

2. Make changes and commit:
```bash
git add .
git commit -m "feat: add your feature"
```

3. Push changes:
```bash
git push origin feature/your-feature-name
```

4. Create Pull Request

### 2. Commit Messages

Follow conventional commits:
- feat: New feature
- fix: Bug fix
- docs: Documentation changes
- style: Code style changes
- refactor: Code refactoring
- test: Test changes
- chore: Maintenance tasks

Example:
```
feat: add user authentication
fix: resolve database connection issue
docs: update API documentation
```

### 3. Code Review Process

1. Self-review:
   - Run tests
   - Check code style
   - Verify documentation
   - Test edge cases

2. Pull Request:
   - Clear description
   - Link related issues
   - Add screenshots if UI changes
   - Request reviewers

3. Review checklist:
   - Code style
   - Tests
   - Documentation
   - Performance
   - Security
   - Edge cases

## Testing

### 1. Unit Tests

1. Test structure:
```python
def test_create_user():
    # Arrange
    user_data = {
        "email": "test@example.com",
        "password": "password123"
    }
    
    # Act
    user = user_service.create_user(**user_data)
    
    # Assert
    assert user.email == user_data["email"]
    assert user.is_active is True
```

2. Test fixtures:
```python
@pytest.fixture
def test_user():
    return User(
        email="test@example.com",
        hashed_password="hashed_password"
    )

@pytest.fixture
def test_db():
    return SessionLocal()
```

### 2. Integration Tests

1. Test API endpoints:
```python
def test_create_user_api(client):
    response = client.post(
        "/api/users",
        json={
            "email": "test@example.com",
            "password": "password123"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
```

2. Test database operations:
```python
def test_user_repository(test_db):
    repo = UserRepository(test_db)
    user = repo.create(
        email="test@example.com",
        hashed_password="hashed_password"
    )
    assert user.email == "test@example.com"
```

### 3. Performance Tests

1. Use Locust for load testing:
```python
from locust import HttpUser, task, between

class UserBehavior(HttpUser):
    wait_time = between(1, 3)
    
    @task
    def get_user(self):
        self.client.get("/api/users/me")
```

2. Run performance tests:
```bash
locust -f tests/locustfile.py
```

## Debugging

### 1. Logging

1. Use structured logging:
```python
logger.info(
    "User created",
    extra={
        "user_id": user.id,
        "email": user.email
    }
)
```

2. Log levels:
- DEBUG: Detailed information
- INFO: General information
- WARNING: Warning messages
- ERROR: Error messages
- CRITICAL: Critical errors

### 2. Debug Tools

1. VS Code debugger:
```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: FastAPI",
            "type": "python",
            "request": "launch",
            "module": "uvicorn",
            "args": [
                "app.main:app",
                "--reload"
            ],
            "jinja": true,
            "justMyCode": true
        }
    ]
}
```

2. Debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Performance Optimization

### 1. Database Optimization

1. Use indexes:
```python
class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True)
    email = Column(String, unique=True, index=True)
```

2. Use eager loading:
```python
user = await db.query(User).options(
    joinedload(User.subscription)
).get(user_id)
```

### 2. Caching

1. Use Redis cache:
```python
@cache(ttl=300)
async def get_user(user_id: str) -> User:
    return await user_repository.get(user_id)
```

2. Cache invalidation:
```python
@cache_invalidate("user")
async def update_user(user_id: str, data: dict) -> User:
    return await user_repository.update(user_id, data)
```

### 3. API Optimization

1. Use pagination:
```python
@router.get("/users")
async def get_users(
    skip: int = 0,
    limit: int = 100
):
    return await user_service.get_users(skip, limit)
```

2. Use field selection:
```python
@router.get("/users/{user_id}")
async def get_user(
    user_id: str,
    fields: List[str] = Query(None)
):
    return await user_service.get_user(user_id, fields)
```

## Security

### 1. Authentication

1. Use JWT tokens:
```python
@router.post("/login")
async def login(
    credentials: LoginCredentials,
    auth_service: AuthService = Depends(get_auth_service)
):
    return await auth_service.login(credentials)
```

2. Token validation:
```python
async def validate_token(token: str) -> User:
    try:
        payload = jwt.decode(token, settings.jwt_secret)
        return await user_service.get_user(payload["sub"])
    except jwt.JWTError:
        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )
```

### 2. Authorization

1. Use dependency injection:
```python
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    user_service: UserService = Depends(get_user_service)
) -> User:
    return await validate_token(token)
```

2. Use role-based access:
```python
@router.get("/admin/users")
async def get_all_users(
    current_user: User = Depends(get_current_admin)
):
    return await user_service.get_all_users()
```

## Deployment

### 1. Docker

1. Build image:
```bash
docker build -t formiq-api .
```

2. Run container:
```bash
docker run -p 8000:8000 formiq-api
```

### 2. Kubernetes

1. Apply resources:
```bash
kubectl apply -f k8s/
```

2. Monitor deployment:
```bash
kubectl get pods -n formiq
```

## Support

For development support:
- Check the [API Documentation](../api/README.md)
- Review the [Setup Guide](../setup/README.md)
- Check the [Deployment Guide](../deployment/README.md)
- Contact dev@formiq.com 