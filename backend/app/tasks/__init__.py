"""Background tasks package for Celery."""

from .analysis_tasks import process_form_check_task
# Import other tasks here as they are created
# e.g.:
from .video_tasks import process_video_celery_task
from .ai_tasks import detect_pose_celery_task

__all__ = (
    "process_form_check_task",
    "process_video_celery_task",
    "detect_pose_celery_task"
) 