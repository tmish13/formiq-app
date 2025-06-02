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

# AI Pipeline Test File Summary

This document provides a quick reference to the test files associated with the different stages of the FormIQ AI pipeline.

## Phase 1.0: Initial Video Upload and Service Validation

*   **`VideoService` Unit Tests:**
    *   File: `backend/tests/unit/services/test_video_service.py`
    *   Description: Contains unit tests for the `VideoService`, covering presigned URL generation, `Video` model interactions, upload completion handling, metadata association, and error handling.
*   **Video Upload API Tests:**
    *   File: `backend/tests/api/test_video_endpoints.py`
    *   Description: Contains API tests for video uploading endpoints (e.g., `/videos/upload-url`, `/videos/upload-complete`), covering successful uploads, error conditions, and database state validation.

## Phase 1.1: Strengthening Core Processing and Asynchronicity

### Step 1.1.1: Solidify `video_processing_service.py` & Celery Integration

*   **`VideoProcessingService` Unit Tests:**
    *   File: `backend/tests/unit/services/test_video_processing_service.py`
    *   Description: Unit tests for `VideoProcessingService`, ensuring correct use of ffmpeg/OpenCV for frame extraction, normalization, compression, and error handling.
*   **`video_tasks.py` Integration Tests:**
    *   File: `backend/tests/integration/tasks/test_video_tasks.py`
    *   Description: Integration tests for Celery tasks related to video processing defined in `app/tasks/video_tasks.py`, including `process_video_celery_task`. Tests cover task enqueuing, execution, retry mechanisms, logging, and database status updates.

### Step 1.1.2: Enhance `ai_service.py` for Pose Detection & Celery Integration

*   **`AIService` Unit Tests (Core Pose Detection Logic):**
    *   File: `backend/tests/analysis/test_ai_service.py` (Note: Path mentioned in summary, may also be `backend/tests/unit/services/test_ai_service.py` or similar depending on project structure for service unit tests)
    *   Description: Unit tests for the core pose detection logic within `AIService`, including MediaPipe/MoveNet integration, keypoint extraction, confidence thresholding, and output formatting.
*   **`ai_tasks.py` Integration Tests (including `detect_pose_celery_task`):**
    *   File: `backend/tests/integration/tasks/test_ai_tasks.py`
    *   Description: Integration tests for Celery tasks related to AI processing defined in `app/tasks/ai_tasks.py`. This includes tests for `detect_pose_celery_task`, covering input handling, `AIService` method invocation, retries, logging, and results storage.

### Step 1.1.3: Initial Angle Calculation in `ai_service.py` or `biomechanics_service.py`

*   **`AIService` Unit Tests (Core Angle Calculation Logic):**
    *   File: `backend/tests/analysis/test_ai_service.py` (Same as for pose detection, assuming angle calculation methods are part of `AIService`)
    *   Description: Unit tests for angle calculation logic within `AIService`, covering computations from keypoints and trajectory smoothing.
*   **`ai_tasks.py` Integration Tests (including `calculate_angles_celery_task`):**
    *   File: `backend/tests/integration/tasks/test_ai_tasks.py`
    *   Description: Integration tests for Celery tasks in `app/tasks/ai_tasks.py`. This includes tests for `calculate_angles_celery_task`, ensuring it correctly integrates angle calculation logic, stores results, and manages status transitions.

## Phase 1.2: Implementing Core Analysis and Feedback Logic

### Step 1.2.1: Mature Rule-Based Validation (`dynamic_form_analysis_service.py`)

*   **`DynamicFormAnalysisService` Unit Tests:**
    *   File: `backend/tests/services/test_dynamic_form_analysis_service.py`
    *   Description: Contains unit tests for the `DynamicFormAnalysisService`, focusing on methods like `segment_repetitions`, `evaluate_rep`, and the various private `_apply_*_rules` methods (`_apply_joint_angle_rules`, `_apply_rom_rules`, `_apply_posture_rules`, `_apply_symmetry_rules`).
*   **`ExerciseConfigService` Unit Tests (Dependency for `DynamicFormAnalysisService`):**
    *   File: `backend/tests/unit/services/test_exercise_config_service.py`
    *   Description: Unit tests for `ExerciseConfigService` ensuring it can correctly store and retrieve exercise configurations used by the dynamic analysis service.
*   **Integration and E2E Tests for Rule-Based Validation Flow (using `DynamicFormAnalysisService`):**
    *   Directory: `backend/tests/analysis/tests_1_2_1_ai_pipeline/`
    *   Files:
        *   `test_analyze_form_dynamically_advanced_cases.py`: Tests `analyze_form_dynamically` with advanced/specific input scenarios.
        *   `test_analyze_form_dynamically_e2e.py`: End-to-end tests for the `analyze_form_dynamically` flow, simulating realistic usage.
        *   `test_analyze_form_dynamically_error_cases.py`: Tests `analyze_form_dynamically` with various error conditions and edge cases.
        *   `test_evaluate_rep.py`: Focused tests for the `evaluate_rep` method, crucial for validating per-repetition rule application.
    *   Description: These tests collectively ensure that `DynamicFormAnalysisService.analyze_form_dynamically` correctly processes video data, applies configured rules, and generates appropriate feedback and scores under various conditions.

## Phase 1.3: Advanced AI Features - Classification and LLM Feedback (Future Test Locations)

*   **`AIService` Unit Tests (Exercise Classification Logic):**
    *   Expected: `backend/tests/analysis/test_ai_service.py` or specific model testing scripts.
*   **`PersonalizedFeedbackService` / Langflow Client Unit Tests:**
    *   Expected: `backend/tests/unit/services/test_personalized_feedback_service.py` or `backend/tests/unit/services/test_langflow_client_service.py`.
*   **Integration Tests for Feedback Generation:**
    *   Expected: Task-specific integration tests (e.g., in `test_ai_tasks.py` or `test_feedback_tasks.py`) and/or API-level tests.

## Phase 1.4: Enhancing User Experience and Delivery (Future Test Locations)

*   **Backend Visual Comparison Logic Unit/Integration Tests:**
    *   Expected: Within `test_ai_service.py` or a new `test_visual_analysis_service.py` (unit) and relevant API/integration tests.
*   **`FeedbackService` (WebSockets) Tests:**
    *   Expected: `backend/tests/unit/services/test_feedback_service.py` and API/integration tests for WebSocket functionality.

---
*This document should be updated as new tests are added or existing ones are restructured.* 