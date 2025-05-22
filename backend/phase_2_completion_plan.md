# Backend Cleanup: Phase 2 Completion Plan

This document outlines the tasks required to complete **Phase 2: Core Architecture Alignment** of the backend cleanup, as defined in `backend_cleanup_plan.md`.
The primary goals are to consolidate the service layer, standardize API endpoint organization, and implement consistent service patterns.

## Phase 2 Objectives (from `backend_cleanup_plan.md`):

*   Consolidate service layer.
*   Standardize API endpoint organization.
*   Implement consistent service patterns.

## Detailed Task Breakdown:

### 1. Service Layer Consolidation & Standardization

**Background (from `backend_cleanup_plan.md` > Detailed Cleanup Tasks > 1.1, 1.2, 1.3):**
*   Standardize service naming to `_service.py` and remove duplicates.
*   Standardize service inheritance from a `BaseService`.
*   Move common CRUD operations to `BaseService`.
*   Ensure business logic resides in services, not models or controllers (endpoints).

**Tasks:**

*   **1.1. Identify and Remove Duplicate/Old Service Files:**
    *   **Objective:** Ensure only standardized `_service.py` files remain for each service domain.
    *   **Status Update:**
        *   ✅ Deleted `app/services/base.py` (superseded by `base_service.py`).
        *   ✅ Renamed `storage.py` to `storage_service.py`.
        *   ✅ Renamed `scheduler.py` to `scheduler_service.py`.
        *   ✅ Renamed `video_processing.py` to `video_processing_service.py`.
        *   ✅ Renamed `health.py` to `health_service.py`.
        *   ✅ Renamed `biomechanics.py` to `biomechanics_service.py`.
        *   ✅ Verified other specific old duplicates (e.g., `auth.py`, `video.py` in `app/services`) are not present.
        *   ✅ `tasks.py` kept as is (assumed Celery task definitions).
        *   🔄 **Pending:** Codebase-wide check for any import errors due to renames (though Python might handle many cases).
    *   **Action:**
        1.  Scan `backend/app/services/` for any remaining non-`_service.py` suffixed files that are duplicates of existing `_service.py` files (e.g., `user.py` vs `user_service.py`, `email.py` vs `email_service.py`, etc.).
        2.  For each identified duplicate:
            *   Verify the `_service.py` version contains all necessary logic from the non-suffixed version.
            *   Merge any missing logic into the `_service.py` file.
            *   Update all imports across the codebase that point to the old file to now point to the `_service.py` file.
            *   Delete the old non-suffixed file.
        3.  Specifically check and address (if they exist and are duplicates):
            *   `app/services/auth.py` (vs `auth_service.py` - `auth_service.py` is now primary)
            *   `app/services/video.py` (vs `video_service.py` - `video_service.py` is now primary)
            *   `app/services/form_analysis.py` (vs `form_analysis_service.py` - `form_analysis_service.py` is now primary)
            *   `app/services/user.py` (vs `user_service.py`)
            *   `app/services/subscription.py` (vs `subscription_service.py`)
            *   `app/services/workout.py` (vs `workout_service.py`)
            *   `app/services/email.py` (vs `email_service.py`)
    *   **Verification:** No redundant/old service files (non-`_service.py` duplicates) exist in `backend/app/services/`.

*   **1.2. Standardize Service Inheritance from `BaseService`:**
    *   **Objective:** All services should inherit from a common `BaseService` to promote consistency and code reuse.
    *   **Action:**
        1.  Review/Update `backend/app/services/base_service.py`:
            *   Ensure it provides a solid foundation (e.g., constructor taking `AsyncSession` and/or `Repository`).
            *   Identify common CRUD operations (create, get by ID, get multiple, update, delete) that can be generalized and implement them in `BaseService` using an abstract repository pattern or generic SQLAlchemy operations.
        2.  For each primary service file in `backend/app/services/` (e.g., `auth_service.py`, `user_service.py`, `video_service.py`, `form_analysis_service.py`, `subscription_service.py`, etc.):
            *   Modify the service class to inherit from `BaseService`.
            *   Refactor existing CRUD-like methods to utilize or delegate to the `BaseService` methods where appropriate.
            *   Adjust service constructors if needed to align with `BaseService` (e.g., passing repository instances).
    *   **Verification:** All key services inherit from `BaseService` and leverage its common functionalities.

*   **1.3. Ensure Business Logic Placement:**
    *   **Objective:** Confirm that complex business logic primarily resides within service methods.
    *   **Action:** (This is more of a review and ongoing principle)
        1.  Review key services to ensure methods encapsulate distinct business operations.
        2.  During other refactoring (like endpoint consolidation), ensure that any business logic found in endpoints is moved into the appropriate service method.
    *   **Verification:** Services act as the primary layer for business logic orchestration.

### 2. API Endpoint Standardization

**Background (from `backend_cleanup_plan.md` > Detailed Cleanup Tasks > 3.1, 3.2):**
*   Consolidate all API endpoints to `app/api/v1/endpoints/`.
*   Standardize endpoint patterns and ensure they primarily delegate to services.

**Tasks:**

*   **2.1. Consolidate All API Endpoints to `app/api/v1/endpoints/`:**
    *   **Objective:** All API endpoint router files must reside in `backend/app/api/v1/endpoints/`.
    *   **Action:**
        1.  Identify any remaining router files in `backend/app/routers/` (e.g., `admin.py`, `training_data.py` were mentioned in `api.py`).
        2.  Identify any router files in other locations like `backend/app/api/endpoints/` (e.g., `exercise_config.py` was mentioned).
        3.  For each identified router file:
            *   Move the file to `backend/app/api/v1/endpoints/`.
            *   Update its `APIRouter` prefix if necessary to align with `/api/v1/...` structure (if not already handled by the main `api_router` include).
            *   Refactor its dependencies (`get_db`, `get_current_user`, service injections) to use `AsyncSession` and providers from `app.api.deps`.
            *   Ensure its endpoint handlers delegate logic to appropriate services (may require creating/enhancing service methods).
        4.  Update `backend/app/api/v1/api.py` to import these routers from their new location (`app.api.v1.endpoints`).
    *   **Verification:** The `backend/app/routers/` directory is empty and can be deleted. All active API routers are located in `backend/app/api/v1/endpoints/` and correctly registered in `api.py`.

*   **2.2. Standardize API Endpoint Patterns:**
    *   **Objective:** Ensure all API endpoints follow consistent design patterns.
    *   **Action:** (Ongoing throughout endpoint consolidation)
        1.  For each endpoint being moved/reviewed:
            *   Ensure consistent dependency injection (using `Depends(...)` with providers from `app.api.deps`).
            *   Verify standardized error handling (using FastAPI's HTTPException, custom exceptions handled by middleware).
            *   Ensure consistent response formatting (using Pydantic response_models).
            *   Confirm endpoints primarily delegate to service layer methods, keeping endpoint logic minimal (request/response handling, auth checks via dependencies).
            *   Review and improve OpenAPI documentation (docstrings, `summary`, `description`, `tags`, Pydantic schema examples).
    *   **Verification:** API endpoints are lean, consistent, and well-documented, relying on services for core logic.

### 3. Final Verification for Phase 2 Completion

Once all tasks in this plan are completed:
1.  Confirm the service layer is consolidated, with standardized naming and inheritance.
2.  Confirm all API endpoints are located in `app/api/v1/endpoints/` and the `app/routers/` directory is removed.
3.  Confirm API endpoints follow consistent patterns and delegate to services.
4.  Re-verify all original Phase 2 objectives from `backend_cleanup_plan.md` have been met.

## Phase 2 Follow-up Items:

*   **(Placeholder for items identified during Phase 2 work)** 