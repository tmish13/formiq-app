# Phase 2: Task 1.2 - Service Standardization (BaseService Inheritance)

This document tracks the progress of refactoring services in `backend/app/services/` to inherit from the common `BaseService` (`backend/app/services/base_service.py`) where applicable. The goal is to promote consistency, reduce boilerplate, and improve maintainability.

## `BaseService` Refactoring Pattern

For each candidate service that manages a primary SQLAlchemy model:

1.  **Inheritance**: Change class signature to `MyService(BaseService[MyModel]):`.
2.  **Constructor**: Update to `__init__(self, db: Union[AsyncSession, Session], settings: Settings):` and call `super().__init__(db=db, settings=settings, model=MyModel)`.
3.  **Session Usage**: Remove `db: Session = Depends(get_db)` from method parameters. All database operations should use `self.db` (typically an `AsyncSession`).
4.  **CRUD Operations**:
    *   Replace direct model creation/commits with `await super().create_async(obj_in=data_dict_or_schema)`.
    *   Replace direct fetching by ID with `await super().get_async(id=...)`.
    *   Replace direct multi-record fetching with `await super().get_multi_async(skip=..., limit=..., filters=...)`.
    *   Replace direct model updates/commits with `await super().update_async(db_obj=model_instance, obj_in=data_dict_or_schema)`.
    *   Replace direct model deletion/commits with `await super().delete_async(id=...)` or `await super().delete_async(db_obj=model_instance)`.
5.  **Custom Repository Logic**: If the service used a repository with custom query logic, this logic should be integrated into the service itself as private or public `async` methods, using `self.db` and SQLAlchemy core select statements (e.g., `await self.db.execute(select(...))`).
6.  **Return Types**: Ensure service methods that return data entities return Pydantic response schemas (e.g., `MyModelResponse.from_orm(db_obj)`).
7.  **Imports**: Clean up unused imports (old BaseService versions, direct repository imports, `get_db` from `fastapi.Depends` contexts within service methods).
8.  **Dependency Injectors**: Add standard `get_async_SERVICE_service` and a cautious `get_SERVICE_service` (for sync contexts, with warnings) at the end of the service file. These should inject `db: AsyncSession` (or `Session`) and `settings: Settings`.
9.  **`api/deps.py` Update**: Ensure that any existing dependency providers in `backend/app/api/deps.py` for the service are updated to use the new constructor and inject `db` and `settings`, or that new providers are registered if they didn't exist.

## Service Standardization Status

| Service File                         | Manages DB Model? | Primary Model(s)        | Current Status                                      | Notes                                                                                                                                       |
| ------------------------------------ | ----------------- | ----------------------- | --------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| `user_service.py`                  | Yes               | `User`                  | ✅ Refactored (Task 1.2)                            | Inherits `BaseService`.                                                                                                                     |
| `subscription_service.py`          | Yes               | `Subscription`          | ✅ Refactored (Task 1.2)                            | Inherits `BaseService`. Complex Stripe logic.                                                                                             |
| `workout_service.py`               | Yes               | `Workout`, `WorkoutPlan`| ✅ Refactored (Task 1.2)                            | Inherits `BaseService[Workout]`. Manages `WorkoutPlan` directly via `self.db`. Transaction handling for `Workout`+`Exercise` addressed. |
| `session_service.py`               | Yes (and Redis)   | `UserSession` (DB)      | ✅ DB part refactored (Task 1.2)                    | Does not inherit `BaseService` due to primary Redis use. DB interactions standardized (`self.db`, `self.settings`).                      |
| `video_service.py`                 | Yes               | `Video`                 | ✅ Refactored (Task 1.2)                            | Inherits `BaseService`, manages `Video` model, interacts with `StorageService` and Celery. Provider added.                                |
| `form_analysis_service.py`       | Yes               | `FormAnalysis`          | ✅ Refactored (Task 1.2)                            | Inherits `BaseService`. Manages `FormAnalysis` records. Provider added to `api/deps.py`.                                                   |
| `form_check_service.py`            | Yes               | `FormCheck`             | 🔄 Pending Review                                   | Strong candidate for `BaseService`. May also interact with `FeedbackItem`.                                                                |
| `exercise_config_service.py`     | Yes               | `ExerciseConfiguration`?| 🔄 Pending Review                                   | Likely candidate if it manages an `ExerciseConfiguration` model.                                                                              |
| `progress_service.py`              | Yes               | `ExerciseProgress`      | ✅ Refactored (Task 1.2)                            | Inherits `BaseService`. Custom upsert logic for `update_progress_async`. Returns Pydantic schemas. Provider added to `api/deps.py`.      |
| `exercise_service.py`              | Yes               | `ExerciseTemplate`      | ✅ Refactored (Task 1.2)                            | Inherits `BaseService`. Uses Pydantic schemas `ExerciseCreate`, `ExerciseUpdate`, `ExerciseResponse`. Provider added to `api/deps.py`. |
| `feedback_service.py`              | No (uses Redis)   | -                       | ⏹️ Not a candidate                                  | Manages WebSockets & in-memory state. Constructor updated to inject `VideoProcessingService`, removed unused `db`. `PoseAnalysisService` dependency noted as TODO. Provider added to `api/deps.py`. |
| --- Non-Candidate Services (for `BaseService` inheritance) --- | ---               | ---                     | ---                                                 | ---                                                                                                                                         |
| `auth_service.py`                  | Yes (reads User)  | -                       | ⏹️ Not a candidate                                  | Orchestration service, not primary CRUD on one model. DB interactions should be consistent.                                                 |
| `ai_service.py`                    | ? (reads/writes?) | -                       | ⏹️ Not a candidate                                  | Interacts with AI models. DB use likely for I/O or logging, not direct model CRUD. Review DB interaction patterns.                      |
| `email_service.py`                 | No                | -                       | ⏹️ Not a candidate                                  | Sends emails.                                                                                                                               |
| `storage_service.py`               | No                | -                       | ⏹️ Not a candidate                                  | Manages file storage.                                                                                                                       |
| `scheduler_service.py`             | ? (reads/writes?) | -                       | ⏹️ Not a candidate                                  | Manages scheduled tasks. Might use DB for task state. Review DB interaction patterns.                                                       |
| `dynamic_form_analysis_service.py` | No                | -                       | ✅ Refactored. Not a `BaseService` candidate. Converted to async, uses `AsyncSession` and `ExerciseConfigService` via DI. Provider added to `api/deps.py`.
| `video_processing_service.py`      | Yes (updates Video) | -                     | ⏹️ Not a candidate                                  | Background processing. Updates `Video` status, not its primary CRUD manager.                                                                |
| `monitoring_service.py`            | No                | -                       | ✅ Refactored. Not a `BaseService` candidate. Singleton removed. Uses DI for Settings, RedisClient. Provider added.
| `personalized_feedback_service.py` | No                | -                       | ✅ Refactored. Not a `BaseService` candidate. Uses `AsyncSession`, `Settings` via DI. DB queries made async. Provider added.
| `health_service.py`                | No                | -                       | ✅ Refactored. Not a `BaseService` candidate. Uses `AsyncSession`, `Settings`, `CacheService` via DI. Checks made async. Provider updated.
| `analytics_service.py`             | No                | -                       | ✅ Refactored. Not a `BaseService` candidate. Converted to async, uses `AsyncSession`, `Settings`, `CacheService` via DI. Provider added.
| `biomechanics_service.py`          | No                | -                       | ✅ Reviewed. Not a `BaseService` candidate. In-memory/hardcoded knowledge base. DI provider added.
| `tasks.py`                         | N/A               | -                       | ⏹️ Not applicable                                   | Celery tasks definitions.                                                                                                                   |
| `rate_limiter_service.py`          | No                | -                       | ⏹️ Not a candidate. Standalone utility.

**Legend:**
*   ✅: Completed
*   🔄: Pending Review / In Progress
*   ⏹️: Not a candidate for `BaseService` inheritance (but DB interactions should still be reviewed for consistency if applicable)
*   ?: Model existence/management needs confirmation

### Service Files Status (Task 1.2)

*   `user_service.py`: ✅ Refactored (Task 1.2) - Inherits `BaseService`, async methods, uses `UserPublic`.
*   `subscription_service.py`: ✅ Refactored (Task 1.2) - Inherits `BaseService`, async methods, uses `SubscriptionResponse`.
*   `workout_service.py`: ✅ Refactored (Task 1.2) - Inherits `BaseService`, async methods, uses `WorkoutResponse`.
*   `session_service.py`: ✅ Refactored (Task 1.2) - Inherits `BaseService`, async methods. Manages `Session` model. Provider updated.
*   `exercise_service.py`: ✅ Refactored (Task 1.2) - Inherits `BaseService`, async methods, uses `ExerciseResponse`. `get_exercises_by_ids` added.
*   `progress_service.py`: ✅ Refactored (Task 1.2) - Inherits `BaseService`, async methods, uses `ProgressResponse`. Provider added.
*   `form_analysis_service.py`: ✅ Refactored (Task 1.2) - Inherits `BaseService`, manages `FormAnalysis` records. Provider added to `api/deps.py`.
*   `exercise_config_service.py`: ✅ Refactored (Task 1.2) - Inherits `BaseService`, manages `ExerciseConfig` records, handles defaults and versioning. Provider added to `api/deps.py`.
*   `video_service.py`: ✅ Refactored (Task 1.2) - Inherits `BaseService`, manages `Video` model, interacts with `StorageService` and Celery. Provider added.
*   `form_check_service.py`: ✅ Refactored (Task 1.2) - Inherits `BaseService[FormCheck]`. Manages `FeedbackItem` via `self.db`. Integrates `AIService`, `StorageService`, `CacheService`. `cv2` processing offloaded. Provider updated. (Manual review for helper method removal & ExerciseType mapping recommended).
*   `auth_service.py`: ✅ Reviewed. Not a `BaseService` candidate. Uses `AsyncSession` and other services. `last_login` update moved to `UserService`.
*   `ai_service.py`: 🟡 `analyze_form` method made async. Does not appear to directly manage a primary DB model itself for CRUD; acts as a computational/helper service. Review if any part of it should use `BaseService` (unlikely). Mark as ⏹️ for `BaseService` inheritance, but ✅ for async method update.
*   `email_service.py`: ✅ Reviewed. Not a `BaseService` candidate. Uses static async methods for sending emails. No DB interaction.
*   `scheduler_service.py`: ✅ Reviewed. Not a `BaseService` candidate. Custom in-memory async task scheduler. Tasks it runs would need their own DB session management.
*   `feedback_service.py`: ⏹️ Not a candidate. Manages WebSockets and in-memory state. Constructor updated, unused `db` param removed. Provider added.
*   `video_processing_service.py`: ⏹️ Not a candidate (coordinates tasks/external calls primarily). Constructor updated, no params. Provider added.
*   `storage_service.py`: ⏹️ Not a candidate for `BaseService` (Abstracts file storage, not a DB model service). Provider `get_storage_service` used.
*   `cache_service.py`: ⏹️ Not a candidate for `BaseService` (Wraps cache client). Provider `get_cache_service` assumed for injection.
*   `rate_limiter_service.py`: ⏹️ Not a candidate. Standalone utility.
*   `tasks.py`: ⏹️ Not a service file, contains Celery task definitions.
*   `dynamic_form_analysis_service.py`: ✅ Refactored. Not a `BaseService` candidate. Converted to async, uses `AsyncSession` and `ExerciseConfigService` via DI. Provider added to `api/deps.py`.
*   `base_service.py`: N/A (This is the base class itself).
*   `monitoring_service.py`: ✅ Refactored. Not a `BaseService` candidate. Singleton removed. Uses DI for Settings, RedisClient. Provider added.
*   `personalized_feedback_service.py`: ✅ Refactored. Not a `BaseService` candidate. Uses `AsyncSession`, `Settings` via DI. DB queries made async. Provider added.
*   `health_service.py`: ✅ Refactored. Not a `BaseService` candidate. Uses `AsyncSession`, `Settings`, `CacheService` via DI. Checks made async. Provider updated.
*   `analytics_service.py`: ✅ Refactored. Not a `BaseService` candidate. Converted to async, uses `AsyncSession`, `Settings`, `CacheService` via DI. Provider added.
*   `biomechanics_service.py`: ✅ Reviewed. Not a `BaseService` candidate. In-memory/hardcoded knowledge base. DI provider added.

**Removed from list (not found in `backend/app/services/`):**
*   `notification_service.py`
*   `payment_service.py`
*   `report_service.py`
*   `leaderboard_service.py`
*   `gamification_service.py`
*   `user_activity_service.py`
*   `settings_service.py`
*   `goal_service.py`
*   `admin_service.py`
*   `search_service.py`
