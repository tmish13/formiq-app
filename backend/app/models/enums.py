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