from enum import Enum

class SubscriptionTier(str, Enum):
    FREE = "free"
    BASIC = "basic"
    PREMIUM = "premium"

class FormCheckStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class FeedbackType(str, Enum):
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"

class FeedbackSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class ExerciseType(str, Enum):
    SQUAT = "squat"
    DEADLIFT = "deadlift"
    BENCH_PRESS = "bench_press"
    OVERHEAD_PRESS = "overhead_press"
    PULL_UP = "pull_up"
    PUSH_UP = "push_up"
    LUNGE = "lunge"
    PLANK = "plank"
    OTHER = "other" 