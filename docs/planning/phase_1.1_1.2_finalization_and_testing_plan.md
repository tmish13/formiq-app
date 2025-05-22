# AI Pipeline: Steps 1.1 & 1.2 Finalization and Testing Plan

This document outlines the detailed steps to resolve outstanding schema issues, finalize the setup for AI Pipeline Steps 1.1 (Video Processing) and 1.2 (Pose Detection), and conduct thorough testing to ensure their correctness and robustness before proceeding to Step 1.3.

## Phase 1: Alembic Environment and Schema Finalization

**Goal:** Ensure the Alembic environment is correctly configured to allow for schema migrations, and that the `Video` model and its database schema fully support all requirements for pipeline Steps 1.1 and 1.2.

**Status: COMPLETED**

**Tasks:**

1.  **Resolve Alembic `ModuleNotFoundError: No module named 'app'`:**
    *   **Status: COMPLETED.** Verified virtual environment activation and `sys.path` in `env.py`. Alembic commands now run successfully from the project root.
    *   **Objective:** Enable successful execution of `alembic revision` and `alembic upgrade` commands.
    *   **Sub-Tasks:**
        *   [x] **Verify Project Virtual Environment Activation:**
            *   Identified correct virtual environment path (`venv/`) and ensured it's used for Alembic commands.
        *   [x] **Review and Confirm `backend/alembic/env.py` `sys.path` Modification:**
            *   Logic confirmed to correctly add `backend` directory to `sys.path`.
        *   [x] **Verify `__init__.py` Files:**
            *   `backend/app/__init__.py` and `backend/app/models/__init__.py` confirmed to exist.
        *   [x] **Test Alembic Command from Project Root:**
            *   Successfully executed `alembic revision` and `alembic upgrade` commands.

2.  **Add `object_key` to `Video` Model and Generate Migration:**
    *   **Status: COMPLETED.** Model field was present. Migration `a79158613924_add_object_key_to_videos_table_take_4.py` generated, manually corrected, and successfully applied.
    *   **Objective:** Persist the unique storage identifier for each video.
    *   **Sub-Tasks:**
        *   [x] **Update `Video` Model (`backend/app/models/video.py`):**
            *   `object_key = Column(String, nullable=True, unique=True)` field was confirmed present.
        *   [x] **Generate Alembic Migration Script:**
            *   Successfully ran: `alembic -c backend/config/alembic.ini revision -m "add_object_key_to_videos_table_take_4"` generating `a79158613924...`.
        *   [x] **Review Generated Migration Script:**
            *   Script `a79158613924...` was reviewed and manually corrected as autogenerate failed to populate `upgrade`/`downgrade`.
        *   [x] **Apply the Migration:**
            *   Successfully ran: `alembic -c backend/config/alembic.ini upgrade head`.
            *   `object_key` column confirmed added to the database schema.

3.  **Confirm Other `Video` Model Fields and Migrations (Audit):**
    *   **Status: COMPLETED.** All key fields for Steps 1.1 and 1.2 are confirmed in the model and their corresponding database columns are now aligned with Alembic's migration history.
    *   **Objective:** Ensure all other fields used by Steps 1.1 and 1.2 are present in the model and covered by existing migrations.
    *   **Sub-Tasks:**
        *   [x] **Inspect `b0eba72b99a6_add_video_processing_fields_and_update_.py`:**
            *   Verified it adds `processed_frame_paths` (JSON), `processed_frame_count` (Integer). Noted it did not add `processing_errors`.
        *   [x] **Inspect `5408027f4e1a_add_raw_pose_data_to_video_model.py`:**
            *   Verified it adds `raw_pose_data` (JSON).
        *   [x] **Identify & Address Gaps (`processing_errors`):** 
            *   `processing_errors` field was confirmed present in the `Video` model.
            *   Migration `def6422f27f8_add_processing_errors_to_videos_table.py` was generated.
            *   Script `def6422f27f8...` was reviewed and manually corrected as autogenerate failed.
            *   The database column for `processing_errors` was found to pre-exist. The migration `def6422f27f8` was successfully stamped using `alembic stamp head` to align Alembic's history.

## Phase 2: Testing of AI Pipeline Steps 1.1 & 1.2

**Goal:** Verify the correctness, robustness, and integration of the video processing and pose detection pipeline segments.

**General Testing Setup:**
*   All tests should reside in the `backend/tests/` directory, organized appropriately (e.g., `tests/unit/services`, `tests/integration/tasks`).
*   Use `pytest` as the test runner.
*   Employ mocking for external dependencies (e.g., S3 storage, other services not under direct test) where appropriate, especially for unit tests.
*   For integration tests, aim to use real database sessions (e.g., a test database) to verify data persistence and Celery worker behavior (potentially with `task_always_eager=True` for simpler synchronous testing of Celery task logic).

**Tasks:**

1.  **Unit Tests for `VideoProcessingService` (`backend/app/services/video_processing_service.py`):**
    *   **Objective:** Isolate and test the core video processing logic.
    *   **Sub-Tasks (Illustrative):**
        *   [ ] Test `process_video` with valid video data:
            *   Assert correct frame extraction and preprocessing.
            *   Verify output structure (`frames_data`, `frames_are_paths`, etc.).
            *   Test with `save_processed_frames=True` and `save_processed_frames=False`.
        *   [ ] Test `process_video` with invalid/corrupt video data:
            *   Assert appropriate exceptions are raised (e.g., `VideoReadError`, `VideoValidationError`, `VideoProcessingError`).
        *   [ ] Test `_normalize_video_with_ffmpeg` (mock `subprocess.run`):
            *   Verify correct FFmpeg command construction.
            *   Test success and failure scenarios from FFmpeg.
        *   [ ] Test `_validate_video` with various video properties.
        *   [ ] Test `_extract_frames`, `_select_key_frames`, `_preprocess_frames` with sample frame data.
    *   **Success Criteria:** High code coverage for `VideoProcessingService`; all key logic paths and error conditions tested.

2.  **Unit Tests for `AIService` (`backend/app/services/ai_service.py`):**
    *   **Objective:** Isolate and test pose detection, smoothing, and interpolation logic.
    *   **Sub-Tasks (Illustrative):**
        *   [ ] Test `process_frames_for_pose`:
            *   With ideal frame data: verify correct landmark extraction and formatting.
            *   With frames having low overall confidence: verify `None` is returned for those frames.
            *   With frames having low individual landmark visibility: verify those landmarks are `None` in the output.
            *   With empty `frame_paths` or unreadable frames.
        *   [ ] Test `smooth_and_interpolate_poses`:
            *   With a sequence containing `None` frames: verify behavior.
            *   With sequences missing some individual landmarks: verify interpolation logic.
            *   With sequences having jittery landmark data: verify smoothing effect.
            *   Test edge cases (e.g., very short sequences, large gaps for interpolation).
        *   [ ] Test `_interpolate_landmark` helper directly.
    *   **Success Criteria:** High code coverage for `AIService`; robust testing of data transformation and algorithmic logic.

3.  **Integration Tests for `process_video_celery_task` (`backend/app/tasks/video_tasks.py`):**
    *   **Objective:** Test the Celery task responsible for Step 1.1, including its interaction with `VideoProcessingService` and `VideoService`.
    *   **Sub-Tasks (Illustrative):**
        *   [ ] Test successful video processing flow:
            *   Enqueue task with valid video data/path.
            *   Mock `VideoProcessingService.process_video` to return successful output.
            *   Verify `VideoService` is called to update video status (e.g., to `PROCESSING`, then `PROCESSED` or `PENDING_POSE_DETECTION`).
            *   Verify `detect_pose_celery_task` is enqueued with correct arguments.
            *   Verify video record in DB has correct final status, frame paths/count (if applicable).
        *   [ ] Test flow where `VideoProcessingService.process_video` raises an exception:
            *   Verify `VideoService` is called to update video status to `PROCESSING_FAILED` or `VIDEO_PROCESSING_FAILED`.
            *   Verify error details are stored in `processing_errors`.
            *   Verify `detect_pose_celery_task` is NOT enqueued.
        *   [ ] Test Celery retry mechanisms if applicable (may require more complex setup or specific Celery testing utilities).
    *   **Success Criteria:** Task reliably orchestrates Step 1.1, handles success and errors correctly, and integrates with dependent services.

4.  **Integration Tests for `detect_pose_celery_task` (`backend/app/tasks/ai_tasks.py`):**
    *   **Objective:** Test the Celery task responsible for Step 1.2, including its interaction with `AIService` and `VideoService`.
    *   **Sub-Tasks (Illustrative):**
        *   [ ] Test successful pose detection flow:
            *   Enqueue task with valid frame paths.
            *   Mock `AIService.process_frames_for_pose` and `AIService.smooth_and_interpolate_poses` to return valid processed pose data.
            *   Verify `VideoService` is called to update video status (e.g., to `POSE_DETECTION_IN_PROGRESS`, then `POSE_DETECTED`).
            *   Verify `raw_pose_data` is correctly stored in the video record.
        *   [ ] Test flow where `AIService` methods raise exceptions:
            *   Verify `VideoService` is called to update video status to `POSE_DETECTION_FAILED`.
            *   Verify error details are stored in `processing_errors`.
        *   [ ] Test Celery retry mechanisms.
    *   **Success Criteria:** Task reliably orchestrates Step 1.2, handles success and errors correctly, and integrates with dependent services.

5.  **Pipeline Segment Integration Test (Step 1.1 -> Step 1.2):**
    *   **Objective:** Verify the successful handoff and data flow from the video processing task to the pose detection task.
    *   **Sub-Tasks (Illustrative):**
        *   [ ] Set up a test scenario that starts with triggering `process_video_celery_task` (e.g., simulating a video upload confirmation).
        *   Allow `process_video_celery_task` to run (potentially mocking `VideoProcessingService` to ensure it "succeeds" and returns expected frame paths).
        *   Verify that `detect_pose_celery_task` is enqueued as a result.
        *   Allow `detect_pose_celery_task` to run (potentially mocking `AIService` to ensure it "succeeds" with the frame paths from the previous step).
        *   Assert the final state of the `Video` record in the database (e.g., status is `POSE_DETECTED`, `raw_pose_data` is populated, `processed_frame_paths` from Step 1.1 are present).
    *   **Success Criteria:** End-to-end flow from video processing initiation to pose detection completion is verified for a successful path.

## Success Criteria for Steps 1.1 & 1.2 Completion:

Steps 1.1 (Video Processing) and 1.2 (Pose Detection) will be considered "fully finished" when:
1.  **Alembic Environment and Schema Finalized:** All tasks in "Phase 1: Alembic Environment and Schema Finalization" of this plan (including `object_key` addition and verification of other necessary `Video` model fields) are complete and verified.
2.  **Testing Suite Executed and Passing:**
    *   **Integration Tests for Celery Tasks (Completed):**
        *   Comprehensive integration tests for `process_video_celery_task` (covering Step 1.1 orchestration) are written and pass consistently.
        *   Comprehensive integration tests for `detect_pose_celery_task` (covering Step 1.2 orchestration) are written and pass consistently.
    *   **Unit Tests (To Be Confirmed/Completed):**
        *   Unit tests for `VideoProcessingService` (as outlined in Phase 2, Task 1 of this plan) are confirmed complete and pass, or are completed and pass.
        *   Unit tests for `AIService` methods relevant to pose detection, smoothing, and interpolation (as outlined in Phase 2, Task 2) are confirmed complete (many were developed) and pass, or are finalized and pass.
        *   **Pipeline Segment Integration Test (To Be Implemented):** The specific end-to-end test for Step 1.1 -> Step 1.2 data flow (as outlined in Phase 2, Task 5) is implemented and passes consistently.
3.  **Code Coverage:** Code coverage for the relevant services (`VideoProcessingService`, `AIService`) and Celery tasks (`process_video_celery_task`, `detect_pose_celery_task`) meets project standards.
4.  **Functionality Verified:** All core functionalities described in the `backend_ai_pipeline_integration_plan.md` for Steps 1.1 (video processing and frame extraction) and 1.2 (pose detection, smoothing, interpolation, and data storage) are confirmed to be implemented and covered by the passing tests.

Once these criteria are met, we can confidently proceed to Step 1.3: "Initial Angle Calculation." 