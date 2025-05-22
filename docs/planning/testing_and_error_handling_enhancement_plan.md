# AI Pipeline Testing and Error Handling Enhancement Plan

**Goal:** Achieve a robustly tested and resilient AI pipeline for Steps 1.1 and 1.2, enabling confident progression to Step 1.3. This involves completing the test suite, enhancing error handling and validation mechanisms, and ensuring codebase health.

---

**Phase 0: Codebase Health Check & Test Suite Preparation**

**Objective:** Ensure the codebase is clean, well-structured, and the existing test setup is sound before adding new tests or features.

*   **Task 0.1: Resolve `backend/backend` Directory Anomaly**
    *   **Status: [x] Done**
    *   **Action:** Investigate the `backend/backend/app` directory. Determine if it's a duplicate, outdated, or serves a specific purpose.
    *   **If Duplicate/Outdated:** Plan and execute its removal, ensuring no critical, unique code is lost. This might involve comparing its contents with `backend/app`.
    *   **Tooling:** Use `list_dir` and `read_file` to compare contents if necessary. Use `delete_file` or `edit_file` (to remove references) if deletion is confirmed.
    *   **Rationale:** Eliminates potential for using incorrect code versions and simplifies the project structure.

*   **Task 0.2: Clarify and Consolidate Test Locations**
    *   **Status: [x] Done**
    *   **Action:** Review the purpose of `backend/app/tests` versus `backend/tests/unit`.
    *   **Decision:** Decide on a single, clear location for unit tests (preferably `backend/tests/unit` for consistency with integration tests).
    *   **Action (if needed):** Migrate any tests from `backend/app/tests` to `backend/tests/unit`, updating paths and imports.
    *   **Tooling:** `list_dir`, `read_file`, `edit_file` (for moving and updating tests).
    *   **Rationale:** Standardizes test locations, making them easier to find and manage.

*   **Task 0.3: Review Existing Test Files and `conftest.py`**
    *   **Status: [x] Done (Initial Review Complete)**
    *   **Action:** Briefly scan key files in `backend/tests/` (e.g., `conftest.py`, representative unit/integration tests) for:
        *   Consistent formatting and style.
        *   Proper use of fixtures and test helpers.
        *   Clarity and readability.
        *   Absence of obvious anti-patterns.
    *   **Output:** Note any immediate, minor refactoring opportunities that would improve the existing test codebase or prevent issues with new tests.
    *   **Tooling:** `read_file`.
    *   **Rationale:** Ensures new tests are built upon a solid and consistent foundation.

---

**Phase 1: Unit Testing Completion**

**Objective:** Ensure individual components of `VideoProcessingService` and `AIService` function correctly in isolation.
*Refer to `phase_1.1_1.2_finalization_and_testing_plan.md` for specific test cases.*

*   **Task 1.1: Complete Unit Tests for `VideoProcessingService` (`backend/app/services/video_processing_service.py`)**
    *   **Status: [ ] To Do**
    *   **Location:** `backend/tests/unit/services/test_video_processing_service.py` (create if not existing or standardizing).
    *   **Sub-Tasks:**
        *   [ ] Test `process_video` with valid video data (various formats if possible, mock external calls like S3 if any).
        *   [ ] Test `process_video` with invalid/corrupt video data, asserting appropriate custom exceptions (e.g., `VideoReadError`, `VideoValidationError`).
        *   [ ] Test `process_video` with `save_processed_frames=True` and `save_processed_frames=False`, verifying outputs/side effects.
        *   [ ] Test `_normalize_video_with_ffmpeg` (mock `subprocess.run`), covering success/failure of FFmpeg command.
        *   [ ] Test `_validate_video` with various video properties (e.g., duration, resolution, codec if validated).
        *   [ ] Test `_extract_frames`, `_select_key_frames`, `_preprocess_frames` with sample frame data/mocks.
    *   **Success Criteria:** High code coverage for `VideoProcessingService`; all specified logic paths and error conditions tested.

*   **Task 1.2: Complete Unit Tests for `AIService` (`backend/app/services/ai_service.py`)**
    *   **Status: [ ] To Do**
    *   **Location:** `backend/tests/unit/services/test_ai_service.py` (create if not existing or standardizing).
    *   **Sub-Tasks:**
        *   [ ] Test `process_frames_for_pose`:
            *   With ideal frame data.
            *   With frames resulting in low overall confidence.
            *   With frames having low individual landmark visibility.
            *   With empty `frame_paths` or unreadable frame data.
        *   [ ] Test `smooth_and_interpolate_poses`:
            *   With sequences containing `None` (missing) poses.
            *   With sequences missing individual landmarks.
            *   With sequences having jittery landmark data.
            *   Edge cases (e.g., very short sequences, large gaps for interpolation).
        *   [ ] Test `_interpolate_landmark` helper directly.
    *   **Success Criteria:** High code coverage for relevant `AIService` methods; robust testing of pose detection, smoothing, and interpolation logic.

---

**Phase 2: Integration Testing Completion**

**Objective:** Verify interactions between services and tasks, and correct data flow for Steps 1.1 & 1.2.
*Use a test database and consider `task_always_eager=True` or appropriate Celery testing utilities.*

*   **Task 2.1: Integration Tests for `process_video_celery_task` (`backend/app/tasks/video_tasks.py`)**
    *   **Status: [ ] To Do**
    *   **Location:** `backend/tests/integration/tasks/test_video_tasks.py`.
    *   **Sub-Tasks:**
        *   [ ] Test successful video processing flow:
            *   Enqueue task with valid video ID/path.
            *   Mock `VideoProcessingService.process_video` to return successful output.
            *   Verify `VideoService` updates `Video` status (e.g., `PROCESSING` -> `PROCESSED` or `PENDING_POSE_DETECTION`).
            *   Verify `detect_pose_celery_task` is enqueued with correct arguments.
            *   Verify `Video` record in DB has correct final status, frame paths/count.
        *   [ ] Test flow where `VideoProcessingService.process_video` raises an exception:
            *   Verify `VideoService` updates `Video` status to `PROCESSING_FAILED` (or similar).
            *   Verify error details are stored in `Video.processing_errors`.
            *   Verify `detect_pose_celery_task` is NOT enqueued.
        *   [ ] Test Celery retry mechanisms for this task (e.g., simulate transient errors and verify retry attempts).

*   **Task 2.2: Integration Tests for `detect_pose_celery_task` (`backend/app/tasks/ai_tasks.py`)**
    *   **Status: [ ] To Do**
    *   **Location:** `backend/tests/integration/tasks/test_ai_tasks.py`.
    *   **Sub-Tasks:**
        *   [ ] Test successful pose detection flow:
            *   Enqueue task (e.g., with video ID and frame paths).
            *   Mock `AIService.process_frames_for_pose` and `AIService.smooth_and_interpolate_poses` to return valid data.
            *   Verify `VideoService` updates `Video` status (e.g., `POSE_DETECTION_IN_PROGRESS` -> `POSE_DETECTED`).
            *   Verify `raw_pose_data` is correctly stored in the `Video` record.
        *   [ ] Test flow where `AIService` methods raise exceptions:
            *   Verify `VideoService` updates `Video` status to `POSE_DETECTION_FAILED`.
            *   Verify error details are stored in `Video.processing_errors`.
        *   [ ] Test Celery retry mechanisms for this task.

---

**Phase 3: Pipeline Segment Integration Test**

**Objective:** Verify the end-to-end data flow and successful handoff from Step 1.1 to Step 1.2.

*   **Task 3.1: Implement End-to-End Test (Step 1.1 -> Step 1.2)**
    *   **Status: [ ] To Do**
    *   **Location:** `backend/tests/integration/pipelines/test_video_to_pose_pipeline.py` (or similar).
    *   **Sub-Tasks:**
        *   [ ] Setup: Create a `Video` record simulating an uploaded video.
        *   [ ] Trigger `process_video_celery_task` for this video.
        *   [ ] Mock `VideoProcessingService.process_video` to "succeed" and return expected frame paths/data.
        *   [ ] Verify `detect_pose_celery_task` is enqueued correctly.
        *   [ ] Allow `detect_pose_celery_task` to run (mock `AIService` methods to "succeed" using frame paths from the previous step).
        *   [ ] Assert final state of the `Video` record: status `POSE_DETECTED`, `raw_pose_data` populated, `processed_frame_paths` present.

---

**Phase 4: Error Handling and Validation Enhancement**

**Objective:** Implement a standardized, robust error handling and input validation strategy across the pipeline.

*   **Task 4.1: Standardize Exception Handling & Logging**
    *   **Status: [ ] To Do**
    *   **Sub-Tasks:**
        *   [ ] Review `backend/app/exceptions.py`. Define a clear hierarchy of custom exceptions for domain-specific errors (e.g., `VideoProcessingError`, `PoseDetectionError`, `InvalidInputError`).
        *   [ ] Refactor services (`VideoProcessingService`, `AIService`) and tasks (`video_tasks.py`, `ai_tasks.py`) to consistently raise these specific exceptions.
        *   [ ] Implement/enhance centralized structured logging (e.g., using `structlog` or configuring Python's `logging` module) to capture:
            *   Timestamp, log level, logger name.
            *   Relevant context (e.g., `video_id`, task ID, input parameters).
            *   Stack traces for unhandled exceptions.
        *   [ ] Ensure Celery task failures are logged with sufficient detail to diagnose issues.

*   **Task 4.2: Robust Celery Task Error Management**
    *   **Status: [ ] To Do**
    *   **Sub-Tasks:**
        *   [ ] For `process_video_celery_task` and `detect_pose_celery_task`:
            *   Configure appropriate `max_retries`, `default_retry_delay`, and potentially exponential backoff for transient errors (e.g., temporary network issues, DB deadlocks).
            *   Ensure that on final failure (after retries), the `Video` status is updated to a definitive error state (e.g., `VIDEO_PROCESSING_FAILED`, `POSE_DETECTION_FAILED`).
            *   Ensure `Video.processing_errors` is populated with a clear error message and type.
            *   Consider a dead-letter queue (DLQ) strategy or alerting mechanism for tasks that fail consistently after retries.

*   **Task 4.3: Enhance Input and Data Validation**
    *   **Status: [ ] To Do**
    *   **Sub-Tasks:**
        *   [ ] **`VideoProcessingService`**:
            *   Strengthen video validation (`_validate_video` or a dedicated validation step): check for supported file types/codecs, reasonable duration/resolution limits to prevent resource exhaustion. Raise specific exceptions for invalid inputs.
        *   [ ] **`AIService` / Pose Detection**:
            *   Add rigorous validation for input frame data (e.g., expected format from `VideoProcessingService`, non-empty).
            *   Keypoint confidence threshold (0.70) enforcement: ensure this is consistently applied.
            *   Outlier detection for keypoints/angles: Implement basic checks to flag or smooth obviously erroneous keypoint data before further processing or storage.
            *   Pose consistency checks: Refine or implement checks for erratic pose changes between frames.
            *   Frame interpolation for drops: Ensure this logic is robust and handles edge cases.
        *   [ ] **Data Saving**: Before saving processed data (frames, poses) to the database or passing to the next stage, validate its integrity (e.g., not null where unexpected, correct data types). Discard or flag noisy/low-confidence data as per defined rules.

---

**Phase 5: Documentation, Review, and Handoff**

**Objective:** Ensure the testing and error handling enhancements are well-documented and the system is ready for Step 1.3.

*   **Task 5.1: Update/Create Test Documentation**
    *   **Status: [ ] To Do**
    *   **Action:** Document new test suites, key test cases, and any specific setup required (e.g., in `backend/tests/README.md`).
    *   **Rationale:** Makes it easier for the team to understand and maintain tests.

*   **Task 5.2: Document Error Handling Standards**
    *   **Status: [ ] To Do**
    *   **Action:** Create a small document or update existing developer guidelines outlining:
        *   Custom exception hierarchy and when to use them.
        *   Logging conventions and expected information in logs.
        *   Celery task error handling patterns (retries, final failure states).
    *   **Rationale:** Promotes consistency in error handling across the codebase.

*   **Task 5.3: Final Review and Code Coverage Check**
    *   **Status: [ ] To Do**
    *   **Action:** Conduct a final peer review of all new tests and error handling implementations.
    *   **Action:** Check code coverage reports (e.g., using `coverage.py`) for `VideoProcessingService`, `AIService`, and related tasks. Aim to meet project standards.
    *   **Rationale:** Quality assurance before moving to the next development phase.

*   **Task 5.4: Green Light for Step 1.3**
    *   **Status: [ ] To Do**
    *   **Action:** Once Phases 0-4 are satisfactorily completed and tests are passing, formally confirm readiness to proceed with "Step 1.3: Initial Angle Calculation."

--- 