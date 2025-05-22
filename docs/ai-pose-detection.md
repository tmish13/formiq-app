# AI Pose Detection & Feedback Module

This document provides an overview of the AI Pose Detection & Feedback module implemented for FormIQ, which enables asynchronous processing of workout videos for form analysis.

## Overview

The AI Pose Detection & Feedback module allows users to upload workout videos that are automatically processed to:

1. Extract frames from the video at appropriate intervals
2. Detect human poses in each frame using MediaPipe
3. Calculate joint angles and movement metrics
4. Analyze form quality based on exercise-specific rules
5. Generate actionable feedback for the user

This processing is done asynchronously using background tasks to ensure good user experience.

## Architecture

The module consists of several components:

### 1. Backend Components

- **Video Model**: Stores video metadata, processing status, and analysis results
- **Celery Tasks**: Three main task types:
  - `video_processing`: Handles initial video processing (resizing, frame rate adjustment)
  - `pose_detection`: Extracts poses from video frames using MediaPipe
  - `form_analysis`: Analyzes detected poses to evaluate form and provide feedback
- **API Endpoints**: Routes for video upload, status checking, and results retrieval
- **Storage Service**: Handles S3 integration for efficient and scalable video storage

### 2. Processing Pipeline

The video processing pipeline follows these steps:

```
Upload → Video Processing → Pose Detection → Form Analysis → Results
```

Each step is performed asynchronously:

1. **Upload**: User uploads video directly to S3 via presigned URL
2. **Video Processing**: Video is downloaded, processed, and prepared for analysis
3. **Pose Detection**: Key frames are extracted and pose detection is performed
4. **Form Analysis**: Joint angles are calculated and form is evaluated
5. **Results**: Feedback and visualizations are generated and stored

### 3. Task Queue System

Tasks are managed by Celery with Redis as the message broker, providing:

- **Reliability**: Failed tasks can be retried automatically
- **Scalability**: Multiple workers can process videos in parallel
- **Monitoring**: Task status tracking via Flower dashboard
- **Resource Management**: Prevents server overload during intensive processing

## Configuration

The module is configured through environment variables:

```
# Video processing settings
VIDEO_FRAME_RATE=30
MAX_VIDEO_FRAMES=300
MAX_VIDEO_SIZE_MB=100
MAX_VIDEO_DURATION=60

# Pose detection settings
MIN_CONFIDENCE_THRESHOLD=0.7
POSE_DETECTION_MODEL=movenet  # movenet, mediapipe

# Redis settings
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_URL=redis://localhost:6379/0

# AWS S3 Settings
AWS_ACCESS_KEY_ID=xxx
AWS_SECRET_ACCESS_KEY=xxx
AWS_REGION=us-east-1
AWS_BUCKET_NAME=formiq-videos
USE_S3_STORAGE=true
```

## API Endpoints

### Video Uploads

```
POST /videos/upload/signed-url
```
Generates a presigned URL for direct S3 upload.

**Request Body:**
```json
{
  "filename": "workout.mp4",
  "content_type": "video/mp4",
  "metadata": {
    "exercise_type": "squat"
  }
}
```

**Response:**
```json
{
  "upload_url": "https://s3.amazonaws.com/...",
  "video_id": "123e4567-e89b-12d3-a456-426614174000",
  "object_key": "videos/user123/workout.mp4",
  "expires_in": 3600
}
```

### Confirm Upload

```
POST /videos/upload/confirm
```
Confirms successful upload and initiates processing.

**Request Body:**
```json
{
  "video_id": "123e4567-e89b-12d3-a456-426614174000",
  "object_key": "videos/user123/workout.mp4",
  "size": 15000000
}
```

### Get Video Details

```
GET /videos/{video_id}
```
Returns video details including processing status and analysis results.

### List Videos

```
GET /videos
```
Lists videos for the current user with pagination and filtering.

### Manually Trigger Processing

```
POST /videos/{video_id}/process
```
Manually triggers or retries video processing.

## Deployment

For production deployments, it's recommended to:

1. Use multiple Celery workers on separate machines for scalability
2. Configure appropriate timeouts for long-running tasks
3. Set up monitoring with Flower
4. Implement proper error handling and notification

To run Celery workers:

```
# Start worker for all queues
celery -A app.core.celery_app:celery_app worker --loglevel=info --queues=video_processing,pose_detection,form_analysis

# Start dedicated workers for specific queues
celery -A app.core.celery_app:celery_app worker --loglevel=info --queues=video_processing
celery -A app.core.celery_app:celery_app worker --loglevel=info --queues=pose_detection
celery -A app.core.celery_app:celery_app worker --loglevel=info --queues=form_analysis
```

## Exercise Configuration

Each exercise type can be configured with specific rules for form analysis:

```json
{
  "squat": {
    "key_points": ["hip", "knee", "ankle"],
    "target_angles": {"knee": 90, "hip": 90},
    "angle_tolerances": {"knee": 15, "hip": 15},
    "depth_threshold": 0.7
  },
  "pushup": {
    "key_points": ["shoulder", "elbow", "wrist"],
    "target_angles": {"elbow": 90},
    "angle_tolerances": {"elbow": 15},
    "body_alignment_threshold": 0.1
  }
}
```

## Future Enhancements

Planned enhancements for the module include:

1. Real-time feedback via WebSockets during processing
2. Support for more exercise types with specialized analysis
3. Machine learning model updates based on user corrections
4. Integration with exercise planning and progress tracking
5. Comparison with reference/exemplar performances 