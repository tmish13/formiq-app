# FormIQ Backend AI Pipeline Integration Plan

This document outlines the current state of backend services in relation to the AI pipeline requirements defined in `formiq_ai_pipeline_description.md`, and provides a detailed plan to achieve full integration.

## Part 1: Analysis of Current Backend Services vs. AI Pipeline Requirements

### 1.1 Existing Backend Services

The following services are currently present in `backend/app/services/`:

*   `auth_service.py`
*   `form_check_service.py`
*   `ai_service.py`
*   `video_service.py`
*   `exercise_config_service.py`
*   `form_analysis_service.py`
*   `feedback_service.py`
*   `video_processing_service.py`
*   `progress_service.py`
*   `exercise_service.py`
*   `session_service.py`
*   `workout_service.py`
*   `subscription_service.py`
*   `user_service.py`
*   `email_service.py`
*   `storage_service.py`
*   `scheduler_service.py`
*   `tasks.py`
*   `dynamic_form_analysis_service.py`
*   `base_service.py`
*   `monitoring_service.py`
*   `personalized_feedback_service.py`
*   `health_service.py`
*   `analytics_service.py`
*   `biomechanics_service.py`

### 1.2. AI Pipeline Requirements vs. Service Coverage

| Pipeline Step                     | Requirement Description                                                                 | Relevant Existing Service(s)                                                                                                | Coverage & Notes                                                                                                                                                                                                                                                                                                                                                          |
| :-------------------------------- | :-------------------------------------------------------------------------------------- | :-------------------------------------------------------------------------------------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **1. Video Upload**               | User uploads video via presigned S3 URL. Optional exercise metadata. Tools: FastAPI, AWS S3 | `video_service.py`, `storage_service.py`                                                                                    | **Likely Covered.** `video_service.py` likely handles metadata and orchestrates with `storage_service.py` which should manage S3 interactions (presigned URLs).                                                                                                                                                                                                    |
| **2. Video Processing**           | Extract frames (30fps), normalize, compress. Tools: ffmpeg, OpenCV                      | `video_processing_service.py`, `tasks.py` (for Celery)                                                                      | **Partially Covered.** `video_processing_service.py` is the natural place for this. Celery integration (`tasks.py`) is a backend goal. The actual use of ffmpeg/OpenCV needs to be confirmed within `video_processing_service.py`.                                                                                                                                           |
| **3. Pose Detection**             | Detect 33+ keypoints. Tools: MediaPipe, MoveNet                                         | `ai_service.py`, `biomechanics_service.py` (?)                                                                                | **Likely Partially Covered.** `ai_service.py` is the most probable candidate for integrating MediaPipe/MoveNet. `biomechanics_service.py` might contain related logic or be a consumer. The specifics of keypoint detection (33+) and model choice would be within `ai_service.py`.                                                                                     |
| **4. Angle Calculation**          | Compute joint angles, smooth trajectories. Tools: NumPy, Custom Geometry Utils        | `ai_service.py`, `biomechanics_service.py`, `dynamic_form_analysis_service.py`                                              | **Likely Partially Covered.** This is core biomechanical analysis. `ai_service.py` might do initial calculations post-pose detection. `biomechanics_service.py` seems highly relevant for custom geometry utils. `dynamic_form_analysis_service.py` also mentions angle checks.                                                                                            |
| **5. Exercise Classification**    | Predict exercise if metadata missing (LSTM+CNN/Transformer). Tools: PyTorch, TensorFlow | `ai_service.py`                                                                                                             | **Potentially Low Coverage/Gap.** While `ai_service.py` is the place for ML models, it's unclear if it currently implements exercise classification with time-series models (LSTM/CNN/Transformer). This is a significant ML feature.                                                                                                                                             |
| **6. Rule-Based Validation**      | Evaluate form using hard-coded biomechanical rules. Tools: Custom Rules Engine          | `dynamic_form_analysis_service.py`, `exercise_config_service.py`, `form_check_service.py`                                     | **Likely Covered.** `dynamic_form_analysis_service.py` appears designed for this, using rules from `exercise_config_service.py`. `form_check_service.py` likely orchestrates or consumes this.                                                                                                                                                                     |
| **7. Feedback Generation**        | Generate natural language feedback. Tools: Langflow, OpenAI                             | `ai_service.py` (Langflow context mentioned), `feedback_service.py`, `personalized_feedback_service.py`                     | **Partially Covered/Gap.** Integration with Langflow/OpenAI is a specific requirement. `ai_service.py` might prepare data for Langflow. `feedback_service.py` (real-time) and `personalized_feedback_service.py` would be consumers or orchestrators. Direct Langflow/OpenAI client integration might be missing or nascent.                                       |
| **8. Visual Comparison**          | Overlay user pose vs. reference, annotate faults. Tools: Backend Image Proc, Frontend | `ai_service.py` (potentially for backend image processing), (No specific backend service for generating visual overlays)        | **Backend Part - Gap.** While the frontend handles display, the backend needs to prepare data or even generate annotated images/frames if complex overlays are done server-side. No existing service explicitly states "backend image processing" for overlays. `ai_service.py` might provide raw data.                                                                    |
| **9. Results Storage**            | Store joint angles, score, feedback in Postgres. Tools: SQLAlchemy, PostgreSQL        | `form_analysis_service.py`, `form_check_service.py`, `progress_service.py`, various services using `BaseService`                | **Likely Covered.** Many services interact with the DB. `form_analysis_service.py` (for analysis results), `form_check_service.py` (for check details including feedback), and `progress_service.py` are key. The "robust database schema" goal is crucial.                                                                                                            |
| **10. Results Delivery**          | Deliver via REST API or WebSocket. Tools: FastAPI, WebSocket                             | `feedback_service.py` (WebSockets), various API endpoint files calling services.                                              | **Likely Covered.** FastAPI is the framework. `feedback_service.py` explicitly mentions WebSockets, likely for real-time feedback. Other results via standard REST endpoints.                                                                                                                                                                                                   |

### 1.3. Overall Backend Goals Assessment

*   **Integrate Celery for async tasks (`video_processing`, `pose_detection`, `form_analysis`):**
    *   `tasks.py` exists. `video_processing_service.py` is a candidate. `ai_service.py` (for pose detection & form analysis) would need Celery integration.
    *   **Status:** In progress/Partially covered. The framework exists, but deep integration into ML pipeline steps needs verification.
*   **Robust database schema for video, pose, feedback metadata:**
    *   Models exist (e.g., `Video`, `FormAnalysis`, `FormCheck`, `FeedbackItem`). `BaseService` helps with CRUD.
    *   **Status:** Likely covered, but "robustness" needs continuous review against detailed requirements (e.g., storing all necessary pose data, joint angles). The note about `postgresql.UUID` is important.
*   **Integrate Langflow agent for feedback generation:**
    *   Mentioned as a tool for "Feedback Generation."
    *   **Status:** Gap/Needs specific implementation. No service explicitly states it *is* the Langflow agent or manages that direct integration. `ai_service.py` or `personalized_feedback_service.py` are candidates.
*   **Provide fallback exercise classification if user input is missing:**
    *   Tied to "Exercise Classification" step.
    *   **Status:** Gap, if the primary classification model itself is a gap.
*   **Add retry logic for failed analysis:**
    *   Likely needs implementation within Celery tasks or service orchestration.
    *   **Status:** Needs specific implementation. Could be part of `ai_service.py` or the orchestrating service for analysis tasks.
*   **Ensure support for both desktop and mobile uploads:**
    *   Primarily a frontend/API contract concern, but backend (e.g. `video_service.py`) must handle the uploads.
    *   **Status:** Likely covered at the API level.

### 1.4. Key Gaps & Areas for Deeper Review

1.  **Exercise Classification (Step 5):** The requirement for a sophisticated time-series model (LSTM/CNN/Transformer) for exercise classification if metadata is missing seems like a major ML component. It's unclear if `ai_service.py` currently has this capability or if it's planned.
2.  **Langflow/OpenAI Integration (Step 7 & Backend Goal):** Specific integration for natural language feedback generation using Langflow/OpenAI needs to be explicitly present in a service.
3.  **Backend Visual Comparison Logic (Step 8):** If the backend is responsible for generating annotated frames or complex data for visual overlays (beyond sending raw keypoints), there isn't a clear service for this "backend image processing."
4.  **Celery Integration Depth:** While `tasks.py` exists, ensuring that `video_processing`, `pose_detection`, and `form_analysis` are truly robust, retriable Celery tasks is crucial.
5.  **Custom Geometry Utils & Rules Engine:** The tools (`NumPy`, `Custom Geometry Utils`, `Custom Rules Engine`) imply significant custom logic. `biomechanics_service.py` and `dynamic_form_analysis_service.py` are likely homes for these, but their maturity and completeness against requirements need review.

### 1.5. Conclusion of Current State

The existing backend services provide a foundational structure for many parts of the described AI pipeline. Services like `video_service.py`, `storage_service.py`, `video_processing_service.py`, `ai_service.py`, `dynamic_form_analysis_service.py`, and `form_check_service.py` cover significant ground.

However, there are potentially critical gaps, especially in:
*   Advanced exercise classification.
*   Direct Langflow/OpenAI integration for feedback.
*   Specific backend image processing for visual comparison.

The "Backend Goals" are reasonably addressed in principle by the service-oriented architecture, but the *depth* of implementation for features like Celery-based ML steps and a truly "robust" schema needs ongoing validation against these detailed requirements.

## Part 2: Detailed Step-by-Step Plan for Full AI Pipeline Integration

This section outlines the steps to enhance existing services and potentially introduce new components to meet all requirements from `formiq_ai_pipeline_description.md`. The approach emphasizes iterative enhancements to maintain stability.

### Phase 1.0: Initial Video Upload and Service Validation

**Goal:** Ensure the initial video upload mechanism is robust, correctly interacts with storage, updates database state, and has comprehensive passing tests. This forms the entry point of the AI pipeline.

**Relevant Analysis from Part 1:**
*   **Pipeline Step 1: Video Upload:** "User uploads video via presigned S3 URL. Optional exercise metadata. Tools: FastAPI, AWS S3. Relevant Existing Service(s): `video_service.py`, `storage_service.py`. Coverage & Notes: Likely Covered. `video_service.py` likely handles metadata and orchestrates with `storage_service.py` which should manage S3 interactions (presigned URLs)."

**Objective:** Validate and confirm the functionality of `VideoService` and `StorageService` in handling video uploads, including presigned URL generation, metadata handling, and initial `Video` model persistence.

**Tasks:**
1.  **Review `VideoService` and `StorageService`:**
    *   Confirm `StorageService` correctly generates presigned S3 URLs for uploads.
    *   Verify `VideoService` handles requests for upload URLs, potentially creates an initial `Video` record in the database with a status like `PENDING_UPLOAD` or `AWAITING_UPLOAD`.
    *   Ensure `VideoService` correctly processes confirmation of upload completion (e.g., via a separate callback endpoint or S3 event notification), updates the `Video` model status (e.g., to `UPLOADED` or `PENDING_PROCESSING`), and stores any provided metadata (like `exercise_id`, `user_id`).
    *   Confirm error handling for issues like invalid metadata or failures in communicating with `StorageService`.
2.  **Confirm Unit Test Coverage and Success: ✅**
    *   Locate and execute unit tests for `VideoService` (e.g., in `backend/tests/unit/services/test_video_service.py`).
    *   Ensure tests cover:
        *   Presigned URL generation logic (possibly by mocking `StorageService`).
        *   `Video` model creation and initial status setting.
        *   Upload completion handling and status updates.
        *   Metadata association.
        *   Error handling scenarios.
    *   Address any failing unit tests.
3.  **Confirm API Test Coverage and Success: ✅**
    *   Locate and execute API tests related to video uploading (e.g., in `backend/tests/api/test_video_endpoints.py` or similar, covering endpoints like `/videos/upload-url` and `/videos/upload-complete`).
    *   Ensure tests cover:
        *   Successful generation of upload URLs.
        *   Successful video upload (mocked S3 interaction) and subsequent confirmation.
        *   Correct HTTP status codes and response payloads.
        *   Validation of `Video` record state in the database after API calls.
        *   Authentication and authorization if applicable.
        *   Handling of invalid requests or error conditions.
    *   Address any failing API tests.

**Impacted Services:** `video_service.py`, `storage_service.py`, API endpoint modules for video.
**Validation:** All unit and API tests related to video upload pass. The system reliably handles video uploads, creating `Video` records with correct initial status and metadata. The video object is ready for the next step in the pipeline (processing).

### Phase 1.1: Strengthening Core Processing and Asynchronicity

**Goal:** Ensure video processing, pose detection, and basic analysis are robustly handled asynchronously.

**Step 1.1.1: Solidify `video_processing_service.py` & Celery Integration**
    *   **Status:** Foundational work largely complete. `VideoProcessingService` refactored for Celery-friendly output. Conceptual Celery task (`process_video_celery_task` in `app.tasks.video_tasks.py`) defined. `VideoService` updated to enqueue this task. Celery app (`app.core.celery_app.py`) initialized. `Video` model and `VideoStatus` enum updated. Helper for Celery DB session created. Outstanding tasks involve full Celery app wiring, implementation of DB session/settings helpers in task, `VideoService` method implementations for task callbacks, Alembic migrations for `Video` model, and testing.
    *   **Objective:** Ensure `video_processing_service.py` reliably extracts frames, normalizes, and compresses using ffmpeg/OpenCV via Celery.
    *   **Tasks:**
        1.  **Review `video_processing_service.py`: ✅ (Unit tests passed with 88% coverage for the service file)**
            *   Confirm `ffmpeg` and `OpenCV` are used for frame extraction (target 30fps), normalization, and compression as per pipeline spec.
            *   Ensure robust error handling for video file issues (corrupt, wrong format).
            *   Verify that output (e.g., path to processed frames, frame metadata) is clearly defined and stored/passed appropriately.
        2.  **Enhance Celery Task in `tasks.py` (e.g., `process_video_task`):**
            *   Ensure the task in `tasks.py` calls the core logic in `video_processing_service.py`.
            *   Implement retry mechanisms (e.g., `max_retries`, `default_retry_delay`) for transient issues.
            *   Add detailed logging for task status (started, progress, success, failure with reasons).
            *   Ensure the task updates the `Video` model status (e.g., `processing`, `processed`, `failed`).
        3.  **Triggering:** Confirm that `video_service.py` (after upload completion and `Video.status` is appropriate, e.g. `UPLOADED`) correctly enqueues this Celery task.
    *   **Impacted Services:** `video_processing_service.py`, `tasks.py`, `video_service.py`.
    *   **Validation:** Successful, logged, and retriable processing of various video formats; status updates in DB. ✅ (Integration tests for `test_video_tasks.py` passed)

**Step 1.1.2: Enhance `ai_service.py` for Pose Detection & Celery Integration**
    *   **Objective:** Integrate MediaPipe/MoveNet for 33+ keypoint detection as a Celery task.
    *   **Tasks:**
        1.  **Core Pose Detection Logic in `ai_service.py`: ✅ (Relevant unit tests pass, core logic for `detect_pose` and `process_frames_for_pose` confirmed. Overall `ai_service.py` coverage is 21% - further general testing deferred.)**
            *   Implement/verify method(s) using MediaPipe or MoveNet to process input frames (from Step 1.1.1 output) and extract 33+ keypoints per frame.
            *   Incorporate keypoint confidence threshold (0.70 from pipeline validation).
            *   Implement logic for pose consistency checks and frame interpolation for drops if feasible at this stage, or flag for later. (Smoothing/interpolation methods exist but are not yet called by `detect_pose_celery_task`)
            *   Define a clear output format for keypoints (e.g., structured list/dict per frame, including confidence).
        2.  **Celery Task in `tasks.py` (e.g., `detect_pose_task`): ✅ (`detect_pose_celery_task` in `ai_tasks.py` correctly calls `AIService.process_frames_for_pose` and handles necessary orchestration.)**
            *   This task should take processed video/frame data as input.
            *   Call the pose detection logic in `ai_service.py`.
            *   Implement retries and detailed logging.
            *   Store raw keypoint data (e.g., in a temporary location or dedicated DB table if voluminous, or associate with `FormAnalysis` / `FormCheck` record). Consider storage implications for raw keypoints.
            *   Update `Video` or `FormAnalysis` status.
        3.  **Triggering: ✅ (`process_video_celery_task` in `video_tasks.py` correctly enqueues `detect_pose_celery_task` on success.)** The `process_video_task` (on success, from Step 1.1.1) should enqueue `detect_pose_task`.
    *   **Impacted Services:** `ai_service.py`, `tasks.py`.
    *   **Validation:** Accurate keypoint extraction for various exercises; data stored correctly; Celery task reliable. ✅ (Integration tests for `test_ai_tasks.py` passed)

**Step 1.1.3: Initial Angle Calculation in `ai_service.py` or `biomechanics_service.py`** ✅ **Completed**
    *   **Objective:** Compute essential joint angles from detected keypoints.
    *   **Status & Validation Note:** Core logic for `ai_service.calculate_angles_for_pose_sequence` and `ai_service.smooth_angle_trajectories` implemented. `UNIVERSAL_ANGLE_DEFINITIONS` established in `constants/angles.py`. `calculate_angles_celery_task` in `ai_tasks.py` integrates these steps, stores results in `Video.calculated_angles`, and manages status transitions. Comprehensive unit tests for `AIService` methods and integration tests for `calculate_angles_celery_task` (including success, failure, and edge cases like empty `raw_pose_data` or internal errors) are in place and passing.
    *   **Tasks:**
        1.  **Angle Calculation Logic:**
            *   Within `ai_service.py` (if tightly coupled with pose detection output) or `biomechanics_service.py` (if more general biomechanical utils are centralized there):
                *   Implement methods using NumPy and custom geometry utils to calculate key joint angles (knee, hip, elbow, etc.) from the 33+ keypoints.
                *   Implement trajectory smoothing for angles.
        2.  **Integration:** This logic can be called by `detect_pose_task` after keypoint extraction or be a subsequent synchronous step within an overarching analysis flow.
        3.  **Output:** Store calculated angle trajectories alongside keypoints or as part of the `FormAnalysis` data.
    *   **Impacted Services:** `ai_service.py`, `biomechanics_service.py`.
    *   **Validation:** Correct angle calculations for known poses/movements. ✅ (Covered by the "Status & Validation Note" above - all tests passing)

### Phase 1.2: Implementing Core Analysis and Feedback Logic

**Goal:** Enable rule-based validation and prepare for advanced feedback.

**Step 1.2.1: Mature Rule-Based Validation (`dynamic_form_analysis_service.py`)**
    *   **Objective:** Ensure comprehensive rule-based form evaluation using `ExerciseConfiguration`.
    *   **Tasks:**
        1.  **Review/Enhance `dynamic_form_analysis_service.py`:**
            *   Confirm its "Custom Rules Engine" can effectively use `ExerciseConfiguration` data (from `exercise_config_service.py`).
            *   Ensure it covers checks: joint angle thresholds, range of motion, posture alignment, symmetry, rep detection (as per pipeline spec).
            *   Refine `get_exercise_config` to use the async `exercise_config_service.py`.
            *   Ensure all methods are async and use an `AsyncSession`.
        2.  **Review/Enhance `exercise_config_service.py`:**
            *   Ensure `ExerciseConfiguration` model and service methods can store and retrieve all necessary rule parameters (e.g., angle ranges, expected postures per phase).
        3.  **Integration with `form_check_service.py` or `ai_service.py`:**
            *   The main analysis orchestration (likely in `form_check_service.py` or `ai_service.py` as a Celery task) should call `dynamic_form_analysis_service.py` with keypoints and angle data.
            *   Output from this service (identified faults, scores) should be stored (e.g., in `FormCheck` or `FormAnalysis` records).
    *   **Impacted Services:** `dynamic_form_analysis_service.py`, `exercise_config_service.py`, `form_check_service.py`, `ai_service.py`.
    *   **Validation:** Correct identification of form faults based on defined rules for various exercises.

**Step 1.2.2: Database Schema Review and Enhancement for Analysis Results**
    *   **Objective:** Ensure DB schema robustly stores all analysis outputs.
    *   **Tasks:**
        1.  **Review `FormAnalysis`, `FormCheck`, `FeedbackItem` models (and potentially `Video`):**
            *   Ensure fields exist to store:
                *   Raw/processed keypoints (or reference to their storage).
                *   Joint angle trajectories.
                *   Detected exercise (user-provided or classified).
                *   Rule-based validation results (specific faults, scores per rep/segment).
                *   Confidence scores at various stages.
                *   Timestamps for events/faults.
            *   Verify use of `postgresql.UUID(as_uuid=True)` as per notes.
        2.  **Update Models & Migrations:** Make necessary changes and create Alembic migrations.
    *   **Impacted Services:** All services interacting with these models.
    *   **Validation:** DB schema can hold all data points generated by the pipeline up to this phase.

### Phase 1.3: Advanced AI Features - Classification and LLM Feedback

**Goal:** Implement exercise classification and Langflow-based feedback.

**Step 1.3.1: Implement Exercise Classification (`ai_service.py`)**
    *   **Objective:** Develop/Integrate a time-series model (LSTM+CNN or Transformer) for exercise classification.
    *   **Tasks (Significant ML Effort):**
        1.  **Model Development/Selection:**
            *   Choose architecture (LSTM+CNN, Transformer).
            *   Train model on sequence of keypoints (100+ frames/rep) for MVP exercises (squat, deadlift, etc.) to achieve 95% accuracy goal.
            *   Implement data augmentation (camera shift, time warping, occlusion).
        2.  **Integration into `ai_service.py`:**
            *   Add method(s) to load the trained model (PyTorch/TensorFlow).
            *   Add method(s) to preprocess keypoint sequences and run inference.
            *   This service should be callable if `Video.exercise_metadata` is missing.
        3.  **Celery Task (`classify_exercise_task` - Optional):**
            *   If inference is slow, this could be a separate Celery task. Otherwise, can be part of the main analysis task.
        4.  **Orchestration:** The main analysis flow (`form_check_service.py` or an overarching Celery task in `ai_service.py`) should call this if exercise type is not provided by the user.
        5.  **Result Storage:** Store the classified exercise with confidence.
    *   **Impacted Services:** `ai_service.py`, `tasks.py` (if Celery used).
    *   **Validation:** Accurate classification for top-N exercises when user metadata is missing.

**Step 1.3.2: Integrate Langflow/OpenAI for Feedback Generation**
    *   **Objective:** Generate natural language feedback using Langflow.
    *   **Tasks:**
        1.  **Identify/Create Langflow Service/Client:**
            *   This might be a new thin client service (`langflow_client_service.py`) or integrated within `personalized_feedback_service.py` or `ai_service.py`.
            *   This component will be responsible for making API calls to a deployed Langflow instance (or directly to OpenAI if Langflow is used as a templating/prompt management layer).
        2.  **Develop Langflow Prompts/Flows:**
            *   Design Langflow flows/prompts that take analysis results as input (user_exercise_type, joint_mistakes, temporal_faults, performance_summary).
            *   Ensure dynamic adjustment based on user-provided vs. predicted exercise.
            *   Implement feedback context safety (filters).
        3.  **Service Logic in `personalized_feedback_service.py` (or `ai_service.py`):**
            *   Method to gather context from `FormAnalysis`/`FormCheck` data.
            *   Call the Langflow service/client.
            *   Process and store the generated natural language feedback (e.g., in `FeedbackItem` or related table).
        4.  **Celery Task (`generate_feedback_task` - Optional):** If Langflow calls are slow.
    *   **Impacted Services:** `personalized_feedback_service.py` (preferred), `ai_service.py`, potentially a new `langflow_client_service.py`.
    *   **Validation:** Meaningful, contextually relevant feedback generated for various analysis outcomes.

### Phase 1.4: Enhancing User Experience and Delivery

**Goal:** Implement visual comparison aids and ensure robust delivery.

**Step 1.4.1: Backend Support for Visual Comparison**
    *   **Objective:** Provide data or processed images for frontend visual comparison.
    *   **Tasks:**
        1.  **Define Backend Role:** Decide if backend only provides:
            *   Raw keypoints + reference pose data for frontend to render.
            *   Annotated frames (backend image processing).
        2.  **If Backend Image Processing:**
            *   In `ai_service.py` or a new `visual_analysis_service.py`:
                *   Implement logic (e.g., using OpenCV, PIL) to take user pose frames, reference pose data, and identified faults.
                *   Generate images with overlays (e.g., skeleton lines, highlighted error joints, reference pose).
                *   Store these annotated frames or provide them on-demand.
        3.  **API Endpoints:** Ensure API endpoints can deliver this data/images to the frontend.
    *   **Impacted Services:** `ai_service.py`, potentially a new `visual_analysis_service.py`.
    *   **Validation:** Frontend can receive necessary data/images to display visual comparisons.

**Step 1.4.2: Robust Results Delivery (API & WebSockets)**
    *   **Objective:** Ensure results are delivered effectively.
    *   **Tasks:**
        1.  **Review API Endpoints:**
            *   Ensure all data points for "Side-by-Side Feedback Components" (timeline feedback, joint angle charts, visual overlay data, textual summary, trend comparison) can be queried via REST APIs.
        2.  **Enhance `feedback_service.py` (WebSockets):**
            *   If real-time updates on analysis progress or quick feedback snippets are desired via WebSockets, ensure this service can handle and push them.
            *   Consider if any Post-MVP real-time feedback via WebRTC/WebSocket starts here.
    *   **Impacted Services:** API endpoint files, `feedback_service.py`.
    *   **Validation:** All required feedback components are accessible to the frontend.

### Phase 1.5: General Backend Goals and Polish

**Goal:** Address overarching backend goals and refine the system.

**Step 1.5.1: Comprehensive Celery Retry and Error Handling**
    *   **Objective:** Ensure all pipeline Celery tasks have robust retry logic and failure management.
    *   **Tasks:**
        1.  **Review All Pipeline Celery Tasks (`tasks.py`):**
            *   Implement/verify `max_retries`, `default_retry_delay`, exponential backoff.
            *   Standardize error logging.
            *   Implement dead-letter queue or similar for persistent failures.
            *   Ensure tasks update relevant model statuses correctly on final failure (e.g., `Video.status = 'analysis_failed'`).
    *   **Impacted Services:** `tasks.py`, all services called by tasks.
    *   **Validation:** Pipeline is resilient to transient errors.

**Step 1.5.2: Validation and Data Integrity Checks**
    *   **Objective:** Implement pipeline validation points.
    *   **Tasks:**
        1.  **Keypoint Confidence (already in 1.1.2):** Ensure enforced.
        2.  **Outlier Detection:** In `ai_service.py` or `biomechanics_service.py`, implement outlier detection for keypoints/angles.
        3.  **Pose Consistency Check (already in 1.1.2):** Ensure enforced.
        4.  **Frame Interpolation for Drops (already in 1.1.2):** Ensure enforced.
        5.  **Validate all frame data before saving:** In `ai_service.py` or Celery task, discard noisy/low-confidence frames.
    *   **Impacted Services:** `ai_service.py`, `biomechanics_service.py`.
    *   **Validation:** Data quality improved through validation steps.

**Step 1.5.3: Configuration & Notes**
    *   **Ensure `postgresql.UUID(as_uuid=True)` is used.** (Covered in 1.2.2)
    *   **Ensure Langflow prompt template dynamically adjusts.** (Covered in 1.3.2)

**Ongoing Considerations (Throughout all Phases):**

*   **Testing:** Implement unit and integration tests for all new/modified logic. Test Celery tasks thoroughly.
*   **Documentation:** Update service docstrings, API documentation (OpenAPI). Document new ML models and their usage.
*   **Performance:** Monitor performance of Celery tasks and API endpoints. Optimize DB queries.
*   **Security:** Ensure new API endpoints are secured appropriately. Sanitize any inputs to ML models or external services (Langflow).
*   **Modularity:** Strive to keep services focused. If a service grows too large with new responsibilities (e.g., `ai_service.py`), consider refactoring parts into new, more specialized services.

This detailed plan provides a structured approach to fully integrate the AI pipeline. Each step should be treated as a mini-project with its own testing and validation, ensuring that changes are integrated smoothly without destabilizing the existing backend. 