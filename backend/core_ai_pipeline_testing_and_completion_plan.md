# Core AI Pipeline: Testing and Completion Plan

This document outlines the structured approach to test and complete the foundational stages of the FormIQ AI pipeline, ensuring robust integration before proceeding to advanced features or extensive backend cleanup. This plan prioritizes sequential development and testing of each pipeline component.

## Phase I: Solidify Foundational AI Pipeline Stages (Video Processing, Pose Detection, Angle Calculation)

This phase focuses on completing and testing Steps 1.1, 1.2, and 1.3 from the `backend_ai_pipeline_integration_plan.md`.

### Task 1.1: Complete and Test Video Processing (`VideoProcessingService` & Celery Task)

**Objective:** Ensure reliable asynchronous video processing (frame extraction, normalization, compression).

**Relevant Files:**
*   `app/services/video_processing_service.py`
*   `app/tasks/video_tasks.py` (for `process_video_celery_task` or equivalent)
*   `app/services/video_service.py` (for enqueuing and handling task callbacks)
*   `app/models/video.py` & `app/models/enums.py` (for `VideoStatus`)
*   `app/core/celery_app.py`

**Development & Configuration Tasks:**
1.  **Full Celery App Wiring:** Verify `process_video_celery_task` is correctly configured, registered, and discoverable by Celery workers.
2.  **DB Session/Settings in Task:** Implement robust database session and application settings management within the Celery task environment (e.g., using `SessionLocal`, `get_settings_override`).
3.  **`VideoService` Callbacks:** Implement methods in `VideoService` to handle success and failure callbacks from the `process_video_celery_task` (e.g., updating video status, logging errors).
4.  **Alembic Migrations:** Create and apply any necessary Alembic migrations for the `Video` model to support new status values or fields required by this processing step (e.g., path to processed frames if applicable).
5.  **Error Handling:** Ensure the Celery task has robust error handling and retry mechanisms.

**Testing for Task 1.1:**
1.  **Unit Tests:** Comprehensive unit tests for `VideoProcessingService` core logic (ffmpeg/OpenCV usage, error handling for corrupt videos, output format).
2.  **Celery Task Integration Tests:**
    *   **Enqueue:** Verify that a video upload (or a direct call to `VideoService` method responsible for starting processing) correctly enqueues the `process_video_celery_task`.
    *   **Successful Processing:** Test with a sample video. Confirm:
        *   The task is picked up and completes successfully.
        *   Frames are extracted, normalized, and compressed as per specifications.
        *   `Video.status` is updated correctly through its lifecycle (e.g., `PENDING_PROCESSING` -> `PROCESSING` -> `PROCESSED_VIDEO_FRAMES_READY`).
        *   Output (e.g., path to processed frames, metadata) is stored or passed on correctly.
    *   **Failed Processing:** Test with a corrupt or invalid video file. Confirm:
        *   The task handles the error gracefully.
        *   `Video.status` is updated to an appropriate failure state (e.g., `VIDEO_PROCESSING_FAILED`).
        *   Error details are logged.

### Task 1.2: Complete and Test Pose Detection (`AIService` & Celery Task)

**Objective:** Ensure reliable asynchronous pose detection from processed video frames.

**Relevant Files:**
*   `app/services/ai_service.py` (for MediaPipe/MoveNet logic)
*   `app/tasks/ai_tasks.py` (or a new relevant task file, e.g., `app/tasks/pose_detection_tasks.py` for `detect_pose_task`)
*   `app/models/video.py`

**Development & Configuration Tasks:**
1.  **Celery Task Implementation:** Finalize/Implement the Celery task for pose detection (e.g., `detect_pose_task`).
    *   It should consume output from Task 1.1 (e.g., path to processed frames).
    *   Utilize `AIService` for 33+ keypoint extraction using MediaPipe or MoveNet.
    *   Incorporate keypoint confidence thresholds and consistency checks.
2.  **Task Chaining/Triggering:** Ensure the pose detection task is automatically triggered after the successful completion of `process_video_celery_task`.
3.  **Keypoint Storage:** Implement logic to store extracted raw keypoint data. This could be a JSON field in the `Video` model, a separate table if voluminous, or temporary storage accessible by the next step.
4.  **Status Updates:** Update `Video.status` (e.g., `PENDING_POSE_DETECTION`, `POSE_DETECTING`, `POSE_DETECTED`, `POSE_DETECTION_FAILED`).
5.  **Error Handling:** Robust error handling and retries for the Celery task.

**Testing for Task 1.2:**
1.  **Unit Tests:** For `AIService` methods related to pose detection (keypoint extraction accuracy for known poses, confidence handling).
2.  **Celery Task Integration Tests:**
    *   **Triggering:** Verify the pose detection task is correctly enqueued and started after video processing (Task 1.1) completes.
    *   **Successful Detection:** Test with sample processed frames. Confirm:
        *   The task completes successfully.
        *   33+ keypoints are accurately extracted per frame.
        *   Keypoint data is stored correctly and associated with the `Video` record.
        *   `Video.status` is updated to `POSE_DETECTED`.
    *   **Failed Detection:** Test with scenarios causing detection failure (e.g., empty frames, problematic video). Confirm:
        *   The task handles errors gracefully.
        *   `Video.status` is updated to `POSE_DETECTION_FAILED`.
        *   Errors are logged.

### Task 1.3: Complete and Test Angle Calculation (Integrated with or following Pose Detection)

**Objective:** Ensure accurate calculation and storage of joint angles from detected keypoints.

**Relevant Files:**
*   `app/services/ai_service.py` or `app/services/biomechanics_service.py`
*   Celery Task from Task 1.2 (if integrated) or a new subsequent task.
*   `app/models/video.py` (for storing `angle_data`)

**Development & Configuration Tasks:**
1.  **Integration:** Integrate angle calculation logic (using NumPy, custom geometry utils from `AIService` or `BiomechanicsService`) into the pose detection Celery task or as a separate, automatically triggered subsequent Celery task.
2.  **Smoothing:** Implement/verify trajectory smoothing for the calculated joint angles.
3.  **Storage:** Ensure the calculated angle trajectories are stored in the `Video.angle_data` JSON field in the structure expected by `DynamicFormAnalysisService`.
4.  **Status Updates (Optional):** If a separate task, manage `Video.status` (e.g., `PENDING_ANGLE_CALCULATION`, `CALCULATING_ANGLES`, `ANGLES_CALCULATED`, `ANGLE_CALCULATION_FAILED`). If integrated into pose detection, `POSE_DETECTED` might imply angles are also ready if `angle_data` is populated.

**Testing for Task 1.3:**
1.  **Unit Tests:** For angle calculation algorithms and trajectory smoothing logic.
2.  **Integration Tests:**
    *   **Successful Calculation:** After pose detection (Task 1.2) successfully produces keypoints, verify:
        *   Angle calculation logic runs automatically.
        *   `Video.angle_data` is populated with correctly structured and accurate joint angle data for sample poses.
        *   If status updates are used, `Video.status` reflects `ANGLES_CALCULATED`.
    *   **Failed Calculation:** Test scenarios that might cause angle calculation to fail (e.g., missing critical keypoints). Confirm:
        *   Errors are handled.
        *   `Video.status` is updated appropriately (e.g., `ANGLE_CALCULATION_FAILED` or `POSE_DETECTION_FAILED` if part of the same task and unrecoverable).
        *   Errors are logged.

## Phase II: Validate Dynamic Form Analysis System

This phase leverages the outputs from Phase I to test the `DynamicFormAnalysisService` and its related API endpoints.

### Task 2.1: Unit & API Test Execution

**Objective:** Confirm all existing unit and API tests for the dynamic form analysis components are passing.

**Actions:**
1.  **Run Unit Tests:** Execute all tests in `backend/tests/unit/services/test_dynamic_form_analysis_service.py`. Address any failures.
2.  **Run API Tests:** Execute all tests in `backend/tests/api/test_form_check_endpoints.py`. Address any failures.
    *   Note: The success of some API tests (e.g., successfully triggering analysis that then runs to completion) implicitly depends on a working Celery setup, even if the task's internal logic is mocked for specific API endpoint tests.

### Task 2.2: Full End-to-End (E2E) Test of the AI Pipeline (Video Upload to Analysis Result)

**Objective:** Validate the seamless flow of data and operations from initial video upload through video processing, pose/angle calculation, and finally dynamic form analysis, culminating in results accessible via the API.

**Prerequisites:**
*   Phases 1.1, 1.2, and 1.3 are completed, and their respective Celery tasks are functional and chained/triggered correctly.
*   Backend server, Celery workers (for video processing, pose/angle calculation, and form analysis queues) are running.
*   API client and database inspection tools are available.

**E2E Test Scenario:**
1.  **Video Upload:**
    *   Use the appropriate API endpoint to upload a new test video (e.g., a short 5-10 second clip of a squat).
    *   This should trigger `VideoService` and enqueue the `process_video_celery_task` (from Task 1.1).
2.  **Monitor Pipeline Execution (Celery Logs & DB Status):**
    *   **Video Processing (Task 1.1 Output):** Confirm `process_video_celery_task` completes. `Video.status` should update (e.g., to `PROCESSED_VIDEO_FRAMES_READY`).
    *   **Pose Detection (Task 1.2 Output):** Confirm `detect_pose_task` is triggered and completes. `Video.status` should update (e.g., to `POSE_DETECTED`). Raw keypoints should be stored (as per your implementation).
    *   **Angle Calculation (Task 1.3 Output):** Confirm angle calculation completes and `Video.angle_data` is populated correctly. `Video.status` should reflect `ANGLES_CALCULATED` (or equivalent).
3.  **Trigger Dynamic Form Analysis:**
    *   Once `Video.angle_data` is populated, make a `POST` request to `/api/v1/analysis/analyze-form/{video_id}` (where `{video_id}` is the ID of the uploaded video).
4.  **Monitor Form Analysis Task (Celery Logs & DB Status):**
    *   Confirm `perform_form_analysis_celery_task` is enqueued, picked up, and completes successfully.
    *   Check for the structured metrics logs from `DynamicFormAnalysisService`.
    *   The `FormCheck` record associated with the video should have its status updated to `analysis_complete`.
5.  **Poll and Validate API Results:**
    *   Make `GET` requests to `/api/v1/form-checks/{video_id}`.
    *   Once `FormCheck.status` is `analysis_complete`, validate the entire `FormCheckDetailedResponse` schema:
        *   `overall_score` (expected range, sensible value for the test video).
        *   `overall_feedback` (present and seems appropriate).
        *   `reps_detected` (accurate count for the test video).
        *   `reps_per_minute`.
        *   `feedback_items` (list with correct timestamps, messages, severities, types).
        *   `exercise_name` and other relevant fields.

### Task 2.3: Test Backfill Script (`backfill_form_analysis.py`)

**Objective:** Ensure the backfill script correctly identifies and enqueues videos for analysis.

**Actions:**
1.  **Prepare Data:** Manually set up `Video` records in the database in various states:
    *   Videos with `angle_data` but no `FormCheck` record.
    *   Videos with `angle_data` and a `FormCheck` record where `overall_score` is NULL.
    *   Videos with `angle_data` and a `FormCheck` record where `overall_score` is NOT NULL (should be skipped).
    *   Videos without `angle_data` (should be skipped).
2.  **Execute Script:** Run `python backend/scripts/backfill_form_analysis.py`.
3.  **Verify:**
    *   Check logs to confirm the script identifies the correct videos.
    *   Verify that `perform_form_analysis_celery_task.delay()` was called (mock if necessary for local testing without live Celery workers) only for the appropriate videos.

## Phase III: Backend Cleanup and Further AI Pipeline Enhancements

**Objective:** Improve codebase health and proceed with more advanced AI features once the core pipeline is stable.

1.  **Targeted Cleanup (If Blocking Issues Found in Phase I/II):**
    *   Address any specific legacy code or structural issues that directly caused failures during Phase I or II testing.
2.  **Broader Backend Cleanup:**
    *   Once Phase I and II are stable and tests are passing, dedicate a phase to address tasks outlined in `backend_cleanup_progress.md` (remaining Phase 2, and Phases 3-7).
    *   Focus on aligning services with consolidated models, removing redundant code, and clarifying component roles.
3.  **Proceed with Advanced AI Features:**
    *   After cleanup, continue with further steps from `backend_ai_pipeline_integration_plan.md`, such as:
        *   Step 5: Exercise Classification
        *   Step 7: Feedback Generation (Langflow/OpenAI Integration)
        *   Step 8: Visual Comparison Backend Support

This plan provides a clear path forward. Let me know when you're ready to start with Phase I, Task 1.1 or if you have any adjustments! 