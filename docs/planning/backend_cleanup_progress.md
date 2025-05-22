# Backend Cleanup & Alignment Progress

This document tracks the progress of cleaning up and aligning the backend codebase with the `backend_ai_pipeline_integration_plan.md`.

---

**Phase 1: Resolve Critical Conflicts & Structural Anomalies (Highest Priority)**
*   **[X] Task 1.1: Resolve `UserSession` Model Conflicts**
    *   Consolidated `UserSession` model definition (likely in `app/models/user_session.py`).
    *   Generated and applied Alembic migration to reflect the consolidated schema.
    *   Verified PostgreSQL ENUM types are handled correctly (e.g., `CREATE TYPE IF NOT EXISTS`).
*   **[X] Task 1.2: Consolidate `FormAnalysis` and `FormCheck` Models**
    *   Merged `FormAnalysis` (old) into `FormCheck` (current). `FormCheck` is now the primary model for analysis results.
    *   All related services and schemas updated to use `FormCheck`.
    *   Alembic migration created and applied.
    *   Deleted old `FormAnalysis` model file (`app/models/form_analysis.py`).
*   **[X] Task 1.3: Consolidate API Route Definitions**
    *   Compared `app/routers/` with `app/api/v1/endpoints/`.
    *   Migrated unique/necessary routes from `app/routers/` to `app/api/v1/endpoints/`.
    *   Updated `main.py` to only include routers from `app/api/v1/`.
    *   Deleted redundant router files and the `app/routers/` directory.
*   **[X] Task 1.4: Address Misplaced Files/Directories**
    *   Removed `app/services/tasks.py` (placeholder).
    *   Investigated and removed `app/models/migrations/` and its contents.
    *   Removed `app/models/database/` directory (if empty after model consolidation).

**Phase 2: Service Layer Alignment & Refinement**

**Objective:** Ensure all services align with the consolidated data models, current business logic, and AI pipeline integration plan. Remove redundant services and clarify roles.

*   **[X] Task 2.1: Clarify Roles of Ambiguous Services**
    *   **[X] Sub-Task 2.1.1: Review `form_analysis_service.py` and `dynamic_form_analysis_service.py`**
        *   Identified `DynamicFormAnalysisService` as the core rule engine (good).
        *   Identified `FormAnalysisService` as an orchestrator tied to old `FormAnalysis` model and API.
        *   **Refactoring `FormAnalysisService`:**
            *   Changed to use `FormCheck` model.
            *   Updated `create_analysis_request_async` to handle `UploadFile`, resolve `exercise_id` (by querying `ExerciseTemplate.name`), use `StorageService` (currently direct, see VideoService review).
            *   Updated `update_analysis_result_async` to create `FeedbackItem` records.
            *   Added `delete_form_check_async` for full deletion (DB record, feedback, video file).
            *   Modified `get_analysis_history_for_user_async` to support date filters (via BaseService update) and exercise type filter (custom query with JOIN to `ExerciseTemplate` on `name`).
            *   Attempted to modify `get_analysis_by_id_async` to return rich ORM object (FormCheck with eager-loaded relationships). API layer adapted based on this assumption. (Service layer change needs verification if tool failed to apply).
        *   **API Endpoints (`form_analysis.py`):**
            *   Adapted to use refactored async `FormAnalysisService`.
            *   GET `/{analysis_id}` and GET `/history` now map more detailed data to `FormAnalysisResult` (partially done, relies on service providing richer objects or further API-side fetching).
            *   DELETE `/{analysis_id}` uses new service deletion method.
            *   Date filters in GET `/history` are parsed and passed to service.
        *   **BaseService:**
            *   `get_multi_async` updated to support `filter_conditions` list and `order_by`.
        *   **Remaining work for these services (FormAnalysisService context):**
            *   Verify/ensure service methods (`get_analysis_by_id_async`, `get_analysis_history_for_user_async`) return rich ORM objects with relationships loaded. API layer needs to be robust to what service returns.
            *   Complete mapping for `metrics`, `risk_level`, etc., in API responses for form analysis.
            *   Implement background task for actual analysis (calling `DynamicFormAnalysisService`).
            *   Update/write tests.
    *   **[X] Sub-Task 2.1.2: Review `exercise_service.py`**
        *   Purpose: Manages `ExerciseTemplate` CRUD. This is the model linked by `FormCheck` and `ExerciseConfig`.
        *   Role is clear and distinct from `ExerciseConfigService`.
        *   Uses current models (`ExerciseTemplate`) and schemas.
        *   `FormAnalysisService` corrected to query `ExerciseTemplate.name` for resolving `exercise_id`.
    *   **[X] Sub-Task 2.1.3: Review `user_service.py`**
        *   Purpose: Manages `User` model CRUD (profile, email, password hashing on create/update, subscription status).
        *   Does not handle `UserSession` management (done by `SessionService`) or core authentication logic (done by `AuthService`), which is a good separation of concerns.
        *   Role is clear and aligned with current models.
    *   **[X] Sub-Task 2.1.4: Review `video_service.py`**
        *   Purpose: Manages `Video` model CRUD, its lifecycle (upload, status tracking), metadata, and triggers initial video processing (e.g., Celery task for pose estimation).
        *   Essential service, should not be removed.
        *   Uses `StorageService` for file operations.
        *   **Refinement Needed:** `FormAnalysisService` currently bypasses `VideoService` for uploads. It should instead use `VideoService` to create `Video` records and manage the upload process. This would ensure `Video` metadata and lifecycle are properly tracked centrally by `VideoService` before a `FormCheck` is created linking to it.
    *   **[X] Sub-Task 2.1.5: Review `storage_service.py`**
        *   Purpose: Abstraction layer for file storage operations (S3, Minio, etc.). Handles uploads, downloads, deletions, presigned URLs.
        *   Mostly async and well-structured.
        *   Relies on a pluggable `StorageProvider` (from `app.core.storage`).
        *   One synchronous method `get_file_url` (for download URLs) was noted; its implications depend on the provider's implementation (blocking or not). Ideally, it should be async if the provider's operation can block.
        *   Generally fit for purpose and used by `VideoService` and `FormAnalysisService`.
    *   **[X] Sub-Task 2.1.6: Define role for `app.services.ai_service.AIService`**
        *   Purpose: Foundational AI service providing pose estimation (MediaPipe), PyTorch model inference, rule-based analysis augmentation, and various video/sequence processing utilities (frame extraction, phase detection, smoothing).
        *   Uses `asyncio.to_thread` for CPU-bound AI tasks, making it suitable for async environments.
        *   It's a critical building block for AI capabilities. Not redundant.
        *   Expected to be heavily used by Celery tasks for video processing (pose extraction) and by `DynamicFormAnalysisService` (which would consume its outputs like pose sequences and apply exercise-specific configurable rules).
        *   Contains many methods, some ofwhich suggest broader AI capabilities beyond immediate form analysis (e.g., workout generation) that might be future scope or placeholders.
    *   **[X] Sub-Task 2.1.7: Define role for `app.services.cache_service.CacheService` (from `app.core.cache`)**
        *   Purpose: Provides an application-wide, Redis-backed (with in-memory fallback) caching layer. It is implemented as a singleton instance (`cache_service`).
        *   Handles connection management (including retries and startup/shutdown integration with FastAPI), JSON serialization/deserialization, and key expiration.
        *   Fully async, using `redis.asyncio`.
        *   Essential for performance and not redundant.
        *   Older functional Redis utilities in the same file might be legacy.
    *   **[X] Sub-Task 2.1.8: Define role for `app.services.notification_service.NotificationService` (fulfilled by `app.services.email_service.EmailService`)**
        *   Purpose: `EmailService` handles sending transactional and notification emails (e.g., account verification, password reset, analysis completion) using `fastapi-mail` and Jinja2 templates.
        *   It is fully async and uses static methods, relying on a globally configured `fast_mail` instance.
        *   Depends on `User` and `Video` model schemas for personalizing emails.
        *   Covers the email channel for notifications. Other channels (e.g., push) would require additional services or expansion.
        *   Not redundant and essential for user communication.
    *   **[X] Sub-Task 2.1.9: Define role for `app.services.feedback_service.FeedbackService`**
        *   Purpose: Manages real-time exercise feedback and session state via WebSockets. Handles subscriptions, broadcasting feedback, and lifecycle of live exercise tracking.
        *   Distinct from `FormAnalysisService` as it deals with transient, real-time WebSocket messages, not persistent `FeedbackItem` database CRUD.
        *   Not redundant, serves a unique real-time interaction role.
        *   **Key Gap:** Its core real-time pose analysis capability (`process_pose_update`) is incomplete due to a missing/unresolved `PoseAnalysisService` dependency; currently uses placeholders. This needs to be addressed by integrating an actual pose analysis component (e.g., `AIService` or `DynamicFormAnalysisService` adapted for real-time).
        *   Stateful nature (in-memory `active_connections` and `feedback_history`) needs consideration for deployment (likely singleton per worker process).
*   **[X] Task 2.2: Remove Unnecessary Services**

**Phase 3: Model Layer Alignment (Beyond Critical Conflicts)**
*   **[ ] Task 3.1: Align Models with Kept Services**
*   **[ ] Task 3.2: Remove Unnecessary Models**

**Phase 4: API Endpoint Refinement (Beyond Consolidation)**
*   **[ ] Task 4.1: Clarify Specific API Endpoints**
    *   [ ] Purpose of `training_data.py` routes.
    *   [ ] `form_check.py` (singular) vs. `form_checks.py` (plural) API endpoints.
*   **[ ] Task 4.2: Remove Unnecessary API Endpoints**

**Phase 5: Task Layer Alignment**
*   **[ ] Task 5.1: Review Celery Tasks in `app/tasks/`**
    *   [ ] Clarify role of `form_analysis.py` (task file).
    *   [ ] Ensure alignment with pipeline plan.

**Phase 6: Supporting Code Review (Schemas, Repositories, Utils)**
*   **[ ] Task 6.1: Align `app/schemas/`**
*   **[ ] Task 6.2: Align `app/repositories/`**
*   **[ ] Task 6.3: Review `app/utils/`, `app/core/`, `app/db/`, `app/middleware/`, `app/templates/`**

**Phase 7: Top-Level Backend Files & Folders Review**
*   **[ ] Task 7.1: Clean Up Top-Level Directory**
    *   [ ] Delete temporary/generated files not in `.gitignore`.
    *   [ ] Remove `formiq.egg-info/`.
    *   [ ] Review `backend/config/` contents.
    *   [ ] Review custom migration scripts, `setup.py`.

--- 