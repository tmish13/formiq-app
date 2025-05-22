"""Enumeration types for the application models."""
from enum import Enum, auto
from typing import List, Dict, Any

class SubscriptionTier(str, Enum):
    """
    User subscription tiers.
    
    Attributes:
        FREE: Basic access with limited features
        BASIC: Standard access with core features
        PRO: Advanced access with additional features
        ENTERPRISE: Full access with all features
    """
    FREE = "free"
    BASIC = "basic"
    PRO = "pro"
    ENTERPRISE = "enterprise"
    PREMIUM = "premium"

    @classmethod
    def get_features(cls) -> Dict[str, List[str]]:
        """Get features available for each tier."""
        return {
            cls.FREE: ["form_check_basic", "view_history"],
            cls.BASIC: ["form_check_basic", "form_check_advanced", "view_history", "export_data"],
            cls.PRO: ["form_check_basic", "form_check_advanced", "view_history", "export_data", "priority_processing", "custom_exercises"],
            cls.ENTERPRISE: ["form_check_basic", "form_check_advanced", "view_history", "export_data", "priority_processing", "custom_exercises"]
        }

class FormCheckStatus(str, Enum):
    """
    Form check processing status.
    
    Attributes:
        PENDING: Awaiting processing
        PROCESSING: Currently being analyzed
        COMPLETED: Analysis finished successfully
        FAILED: Analysis failed
        CANCELLED: Processing cancelled by user
    """
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @classmethod
    def is_terminal_status(cls, status: str) -> bool:
        """Check if status is terminal (no further updates expected)."""
        return status in [cls.COMPLETED, cls.FAILED, cls.CANCELLED]

class VideoStatus(str, Enum):
    """
    Status of video processing and analysis.

    Attributes:
        PENDING_UPLOAD: Video record created, awaiting upload completion.
        UPLOADED: Video successfully uploaded, awaiting processing.
        PROCESSING: Video is currently being processed (frame extraction, etc.).
        PROCESSED: Initial video processing (frames) complete, pending further analysis.
        PROCESSING_FAILED: Video processing failed.
        PENDING_ANALYSIS: Video processed, awaiting form analysis (pose detection, etc.).
        ANALYZING: Form analysis is currently in progress.
        ANALYSIS_COMPLETE: Form analysis successfully completed.
        ANALYSIS_FAILED: Form analysis failed.
        PUBLISHED: Analysis results are published and available to the user.
        ARCHIVED: Video and/or analysis results are archived.
        ERROR: An unspecified error occurred.
        VIDEO_PROCESSING_FAILED: FFmpeg/Normalization failure
        POSE_DETECTION_PENDING: Task enqueued
        POSE_DETECTION_IN_PROGRESS: Task started
        POSE_DETECTED: Pose detection successful, landmarks stored
        POSE_DETECTION_FAILED: Pose detection failed
        ANGLE_CALCULATION_PENDING: Queued for angle calculation
        ANGLE_CALCULATION_IN_PROGRESS: Actively calculating angles
        ANGLES_CALCULATED: Angles successfully calculated and stored
        ANGLE_CALCULATION_FAILED: Angle calculation process failed
        FORM_ANALYSIS_PENDING: Queued for form analysis
        FORM_ANALYSIS_IN_PROGRESS: Actively analyzing form
        FORM_ANALYSIS_COMPLETE: Form analysis successful, feedback generated
        FORM_ANALYSIS_FAILED: Form analysis process failed
        FRAMES_EXTRACTED: Frames extracted successfully
        FRAMES_EXTRACTION_FAILED: Frames extraction failed
    """
    PENDING_UPLOAD = "pending_upload"
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PROCESSED = "processed"
    PROCESSING_FAILED = "processing_failed"
    PENDING_ANALYSIS = "pending_analysis"
    ANALYZING = "analyzing"
    ANALYSIS_COMPLETE = "analysis_complete"
    ANALYSIS_FAILED = "analysis_failed"
    PUBLISHED = "published"
    ARCHIVED = "archived"
    ERROR = "error"
    VIDEO_PROCESSING_FAILED = "VIDEO_PROCESSING_FAILED"
    POSE_DETECTION_PENDING = "POSE_DETECTION_PENDING"
    POSE_DETECTION_IN_PROGRESS = "POSE_DETECTION_IN_PROGRESS"
    POSE_DETECTED = "POSE_DETECTED"
    POSE_DETECTION_FAILED = "POSE_DETECTION_FAILED"
    ANGLE_CALCULATION_PENDING = "ANGLE_CALCULATION_PENDING"
    ANGLE_CALCULATION_IN_PROGRESS = "ANGLE_CALCULATION_IN_PROGRESS"
    ANGLES_CALCULATED = "ANGLES_CALCULATED"
    ANGLE_CALCULATION_FAILED = "ANGLE_CALCULATION_FAILED"
    FORM_ANALYSIS_PENDING = "FORM_ANALYSIS_PENDING"
    FORM_ANALYSIS_IN_PROGRESS = "FORM_ANALYSIS_IN_PROGRESS"
    FORM_ANALYSIS_COMPLETE = "FORM_ANALYSIS_COMPLETE"
    FORM_ANALYSIS_FAILED = "FORM_ANALYSIS_FAILED"
    FRAMES_EXTRACTED = "frames_extracted"
    FRAMES_EXTRACTION_FAILED = "frames_extraction_failed"

class FeedbackType(str, Enum):
    """
    Type of feedback provided.
    
    Attributes:
        SUCCESS: Positive feedback on good form
        WARNING: Minor form issues identified
        ERROR: Major form issues identified
    """
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    FORM = "form"
    TECHNIQUE = "technique"
    POSTURE = "posture"
    RANGE = "range"
    SPEED = "speed"
    BALANCE = "balance"

    @classmethod
    def get_color(cls, feedback_type: str) -> str:
        """Get color code for feedback type."""
        return {
            cls.SUCCESS: "#4CAF50",  # Green
            cls.WARNING: "#FFC107",  # Amber
            cls.ERROR: "#F44336"     # Red
        }.get(feedback_type, "#000000")

class FeedbackSeverity(str, Enum):
    """
    Severity level of feedback.
    
    Attributes:
        LOW: Minor form adjustment needed
        MEDIUM: Notable form improvement required
        HIGH: Significant form correction needed
    """
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    @classmethod
    def get_priority(cls, severity: str) -> int:
        """Get numeric priority for severity level."""
        return {
            cls.LOW: 1,
            cls.MEDIUM: 2,
            cls.HIGH: 3
        }.get(severity, 0)

    @staticmethod
    def get_sort_order(severity: 'FeedbackSeverity') -> int:
        """Get a sortable order for severity (lower number is higher priority)."""
        order = {
            FeedbackSeverity.CRITICAL: 0,
            FeedbackSeverity.HIGH: 1,
            FeedbackSeverity.MEDIUM: 2,
            FeedbackSeverity.LOW: 3
        }
        return order.get(severity, 4) # Default for unknown severities

class ExerciseType(str, Enum):
    """
    Types of exercises supported.
    
    Attributes:
        SQUAT: Barbell or bodyweight squat
        DEADLIFT: Conventional or sumo deadlift
        BENCH_PRESS: Barbell bench press
        OVERHEAD_PRESS: Military or overhead press
        PULL_UP: Pull-up or chin-up variations
        PUSH_UP: Standard or modified push-ups
        LUNGE: Forward, reverse, or walking lunges
        PLANK: Front or side planks
        ROW: Rowing exercise
        OTHER: Other exercise types
    """
    SQUAT = "squat"
    DEADLIFT = "deadlift"
    BENCH_PRESS = "bench_press"
    OVERHEAD_PRESS = "overhead_press"
    PULL_UP = "pull_up"
    PUSH_UP = "push_up"
    LUNGE = "lunge"
    PLANK = "plank"
    ROW = "row"
    OTHER = "other"

    @classmethod
    def get_equipment(cls, exercise_type: str) -> List[str]:
        """Get required equipment for exercise type."""
        equipment_map = {
            cls.SQUAT: ["barbell", "rack"],
            cls.DEADLIFT: ["barbell", "plates"],
            cls.BENCH_PRESS: ["barbell", "bench", "rack"],
            cls.OVERHEAD_PRESS: ["barbell", "rack"],
            cls.PULL_UP: ["pull-up bar"],
            cls.PUSH_UP: [],
            cls.LUNGE: [],
            cls.PLANK: [],
            cls.ROW: [],
            cls.OTHER: []
        }
        return equipment_map.get(exercise_type, [])

class Difficulty(str, Enum):
    """Difficulty level enum."""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"

class MuscleGroup(str, Enum):
    """
    Primary muscle groups targeted by exercises.
    
    Attributes:
        CHEST: Pectoralis major and minor
        BACK: Latissimus dorsi, rhomboids, trapezius
        SHOULDERS: Deltoids (anterior, lateral, posterior)
        LEGS: Quadriceps, hamstrings, calves
        ARMS: Biceps, triceps, forearms
        CORE: Abdominals, obliques, lower back
        FULL_BODY: Multiple major muscle groups
    """
    CHEST = "chest"
    BACK = "back"
    SHOULDERS = "shoulders"
    LEGS = "legs"
    ARMS = "arms"
    CORE = "core"
    FULL_BODY = "full_body"

    @classmethod
    def get_related_exercises(cls, muscle_group: str) -> List[str]:
        """Get common exercises for a muscle group."""
        exercise_map = {
            cls.CHEST: ["bench_press", "push_up", "dips"],
            cls.BACK: ["pull_up", "row", "deadlift"],
            cls.SHOULDERS: ["overhead_press", "lateral_raise"],
            cls.LEGS: ["squat", "lunge", "deadlift"],
            cls.ARMS: ["curl", "tricep_extension"],
            cls.CORE: ["plank", "crunch", "russian_twist"],
            cls.FULL_BODY: ["burpee", "clean_and_jerk", "snatch"]
        }
        return exercise_map.get(muscle_group, [])

class MimeType(str, Enum):
    """
    Common MIME types, focusing on video for now.

    Attributes:
        VIDEO_MP4: MP4 video
        VIDEO_QUICKTIME: QuickTime video (MOV)
        VIDEO_WEBM: WebM video
        VIDEO_AVI: AVI video
        VIDEO_MPEG: MPEG video
        IMAGE_JPEG: JPEG image
        IMAGE_PNG: PNG image
        APPLICATION_JSON: JSON data
    """
    # Video types
    VIDEO_MP4 = "video/mp4"
    VIDEO_QUICKTIME = "video/quicktime"
    VIDEO_WEBM = "video/webm"
    VIDEO_AVI = "video/avi"
    VIDEO_X_MSVIDEO = "video/x-msvideo" # Another common one for AVI
    VIDEO_MPEG = "video/mpeg"
    # Other common types for completeness, though not strictly needed by video tasks yet
    IMAGE_JPEG = "image/jpeg"
    IMAGE_PNG = "image/png"
    APPLICATION_JSON = "application/json"
    TEXT_PLAIN = "text/plain"
    # Add other common types as needed...

class PoseDetectionModel(str, Enum):
    """
    Models available for pose detection.

    Attributes:
        BLAZEPOSE_LITE: MediaPipe BlazePose Lite model
        BLAZEPOSE_FULL: MediaPipe BlazePose Full model
        BLAZEPOSE_HEAVY: MediaPipe BlazePose Heavy model
        MOVENET_SINGLEPOSE_LIGHTNING: MoveNet SinglePose Lightning model
        MOVENET_SINGLEPOSE_THUNDER: MoveNet SinglePose Thunder model
        MOVENET_MULTIPOSE_LIGHTNING: MoveNet MultiPose Lightning model
        YOLOV7_POSE: YOLOv7-Pose model
        YOLOV8_POSE: YOLOv8-Pose model
        DEFAULT: Default model to use if not specified
    """
    BLAZEPOSE_LITE = "blazepose_lite"
    BLAZEPOSE_FULL = "blazepose_full"
    BLAZEPOSE_HEAVY = "blazepose_heavy"
    MOVENET_SINGLEPOSE_LIGHTNING = "movenet_singlepose_lightning"
    MOVENET_SINGLEPOSE_THUNDER = "movenet_singlepose_thunder"
    MOVENET_MULTIPOSE_LIGHTNING = "movenet_multipose_lightning"
    YOLOV7_POSE = "yolov7_pose"
    YOLOV8_POSE = "yolov8_pose"
    DEFAULT = BLAZEPOSE_LITE # Default model

class PoseEstimationFramework(str, Enum):
    """
    Frameworks used for pose estimation.

    Attributes:
        MEDIAPIPE: MediaPipe framework
        TENSORFLOW_LITE: TensorFlow Lite framework
        TENSORFLOW: TensorFlow framework
        PYTORCH: PyTorch framework
        ONNX: ONNX framework
        DEFAULT: Default framework to use if not specified
    """
    MEDIAPIPE = "mediapipe"
    TENSORFLOW_LITE = "tensorflow_lite"
    TENSORFLOW = "tensorflow"
    PYTORCH = "pytorch"
    ONNX = "onnx"
    DEFAULT = MEDIAPIPE # Default framework

# Example of a more complex enum if needed in the future
# class DetailedEnum(Enum): 