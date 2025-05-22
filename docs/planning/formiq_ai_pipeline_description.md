# FormIQ AI Pose Detection & Feedback System

**Task:** Implement AI Pose Detection & Feedback System for FORMIQ

**Description:**
This task defines the full end-to-end machine learning pipeline that powers FormIQ's core feature: AI-based workout form analysis.
It integrates pose detection, form scoring, exercise classification, personalized feedback generation (via Langflow), and frontend delivery.

**Pipeline:**
  - **Name:** `FORMIQ_ML_Pipeline`
  - **Steps:**
    - **1. Video Upload (`video_upload`)**
      - **Description:** User uploads a workout video via presigned S3 URL with optional exercise metadata.
      - **Tools:** FastAPI, AWS S3
    - **2. Video Processing (`video_processing`)**
      - **Description:** Extract frames at 30fps, normalize, compress for processing.
      - **Tools:** ffmpeg, OpenCV
    - **3. Pose Detection (`pose_detection`)**
      - **Description:** Detect 33+ keypoints per frame using real-time models.
      - **Tools:** MediaPipe, MoveNet
    - **4. Angle Calculation (`angle_calculation`)**
      - **Description:** Compute joint angles (e.g., knee, hip, elbow) and smooth trajectories.
      - **Tools:** NumPy, Custom Geometry Utils
    - **5. Exercise Classification (`exercise_classification`)**
      - **Description:** Predict the exercise if user metadata is missing using time-series classification.
      - **Tools:** PyTorch, TensorFlow
      - **Strategy:**
        - **Model:** LSTM + CNN or Transformer
        - **Input:** "Sequence of keypoints (100+ frames per rep)"
        - **Labels:** ["squat", "deadlift", "pushup", "lunge", ...]
        - **Augmentation:** [camera_shift, time_warping, occlusion]
        - **Accuracy Goal:** "95% for top-5 MVP exercises"
    - **6. Rule-Based Validation (`rule_based_validation`)**
      - **Description:** Evaluate form using hard-coded biomechanical rules per exercise.
      - **Tools:** Custom Rules Engine
      - **Checks:** [joint_angle_thresholds, range_of_motion, posture_alignment, symmetry, rep_detection]
    - **7. Feedback Generation (`feedback_generation`)**
      - **Description:** Generate natural language feedback from analysis results.
      - **Tools:** Langflow, OpenAI
      - **Context:**
        - user_exercise_type
        - joint_mistakes
        - temporal_faults
        - performance_summary
    - **8. Visual Comparison (`visual_comparison`)**
      - **Description:** Overlay user pose frames vs. reference pose data and annotate rep-specific faults.
      - **Tools:** Backend Image Processing, Frontend Overlay Logic
    - **9. Results Storage (`results_storage`)**
      - **Description:** Store processed results in Postgres (joint angles, score, feedback).
      - **Tools:** SQLAlchemy, PostgreSQL
    - **10. Results Delivery (`results_delivery`)**
      - **Description:** Deliver results via REST API or WebSocket to frontend clients.
      - **Tools:** FastAPI, WebSocket

**Validation:**
  - Redundant Scoring: [rule_based_validation, ML_prediction]
  - Keypoint Confidence Threshold: 0.70
  - Outlier Detection Enabled: true
  - Pose Consistency Check: true
  - Frame Interpolation for Drops: true
  - Feedback Context Safety: Langflow filters based on exercise-type

**Side-by-Side Feedback Components:**
  - Timeline Feedback: "Timestamped rep feedback with frame tags (e.g., 'back rounding @ 00:13')"
  - Joint Angle Charts: "Time-series visualization for key joints"
  - Visual Overlay: "Pose comparison (user vs. ideal reference)"
  - Textual Summary: "AI-generated tips and mistakes from Langflow"
  - Trend Comparison: "Compare with previous sessions"

**Backend Goals:**
  - Integrate Celery for asynchronous task handling (video_processing, pose_detection, form_analysis)
  - Add robust database schema for video, pose, feedback metadata
  - Integrate Langflow agent for feedback generation
  - Provide fallback classification if user input is missing
  - Add retry logic for failed analysis
  - Ensure support for both desktop and mobile uploads

**Post-MVP:**
  - Add user correction loop to fine-tune model with user flags
  - Integrate real-time form feedback via WebRTC/WebSocket
  - Auto-tag sets, rest periods, and fatigue from motion patterns

**Notes:**
  - Remove SQLiteUUID if used in model classes; use `postgresql.UUID(as_uuid=True)` for compatibility.
  - Validate all frame data before saving; discard noisy or low-confidence frames.
  - Ensure the Langflow prompt template dynamically adjusts based on user-provided vs. predicted exercise. 