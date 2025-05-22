# Backend Test Suite Guide

## Testing Philosophy

- **Fail Fast, Isolate, and Integrate:**
  - Unit tests should isolate logic and fail quickly on regressions.
  - Integration tests should cover cross-service, pipeline, DB flows.
  - E2E tests should simulate real user flows and critical backend journeys.
- **Pipeline-Critical Coverage:**
  - All AI/video pipeline and core business logic should have 80%+ coverage.
- **Infra-Support:**
  - Utilities, mocks, and fixtures should be reusable and minimal.

## How to Run Tests

### Unit Tests
```bash
pytest backend/tests/unit/
```

### Integration Tests
```bash
pytest backend/tests/integration/
```

### End-to-End (E2E) Tests
```bash
pytest backend/tests/e2e/
```

### All Tests
```bash
pytest backend/tests/
```

### Performance/Load Tests
```bash
pytest backend/tests/performance/
# or
locust -f backend/tests/locustfile.py
```

## Structure Overview

```
backend/tests/
├── unit/           # Isolated logic, models, security, storage, etc.
├── integration/    # Cross-service, pipeline, Celery, S3, DB flows
├── api/            # API endpoint tests
├── analysis/       # AI and form analysis tests
├── services/       # Service-layer tests
├── videos/         # Video processing and service tests
├── storage/        # Storage service tests
├── email/          # Email service tests
├── users/          # User service tests
├── auth/           # Auth service tests
├── performance/    # Load and performance tests
├── e2e/            # End-to-end user flow tests
├── utils/          # Fixtures, factories, test infra
├── mocks/          # Mock objects/context managers
├── README.md       # (This file)
├── .env.test       # Test environment variables
├── test_schema_upgrade.py # DB migration test
├── locustfile.py   # Load test entrypoint
└── ...
```

## Coverage Expectations

- **Pipeline-Critical:** 80%+ coverage required (AI, video, core business logic)
- **API/Service:** 70%+ coverage recommended
- **Infra/Support:** As needed for reliability
- **E2E:** Cover all critical user journeys

## Database Testing Details

# Database Testing Guide

This document explains how to use the various database testing approaches in this codebase, including the recent fixes for mapper initialization and test database setup.

## Key Components

1. **Async Testing (Primary Method)**
   - Uses an async SQLite database via `aiosqlite`
   - Configured in `conftest.py` with proper initialization
   - Uses Alembic migrations or falls back to SQLAlchemy metadata
   
2. **Sync Testing (Fallback Method)**
   - Uses synchronous SQLite for simpler testing
   - Available in `tests/utils/sync_db_test.py`
   - Useful when debugging async database issues

## Using Database Tests

### Async Database Testing

This is the primary method and should be used for most tests.

```python
import pytest

@pytest.mark.asyncio
async def test_something(db_session):
    # db_session is an AsyncSession
    result = await db_session.execute(...)
    assert result is not None
```

### Synchronous Database Testing

Use this approach when you need to debug issues with the async setup.

```python
from tests.utils.sync_db_test import BaseSyncDBTest

class TestSomething(BaseSyncDBTest):
    def test_something(self):
        # Use self.session_scope() for database operations
        with self.session_scope() as session:
            result = session.query(Model).filter(Model.id == 1).first()
            assert result is not None
```

Or use the provided fixture:

```python
def test_something_else(sync_db):
    # sync_db is a Session
    result = sync_db.query(Model).filter(Model.id == 1).first()
    assert result is not None
```

## Important Notes

1. **Mapper Initialization**
   - All models must be imported in `app/db/base.py`
   - The `Base` metadata is bound to engines during initialization

2. **Alembic Migrations**
   - Migrations are automatically run before tests
   - If migrations fail, it falls back to direct SQLAlchemy schema creation

3. **Database Cleanup**
   - Test databases are automatically cleaned up between tests
   - The `setup_database` fixture handles this for async tests
   - The `sync_db` fixture handles this for sync tests

4. **Troubleshooting**
   - If you encounter mapper initialization errors, ensure all models are imported in `app/db/base.py`
   - If async tests are failing, try using the sync testing approach as a fallback
   - Check that all model relationships are properly defined

## Recent Fixes

The following issues have been addressed:

1. **Mapper Initialization**: Ensured all models are properly imported and registered
2. **Async Test DB Setup**: Fixed the test database connection and initialization
3. **Alembic Migrations**: Added proper migration setup before running tests
4. **Fallback Mechanism**: Created a synchronous test setup for debugging 