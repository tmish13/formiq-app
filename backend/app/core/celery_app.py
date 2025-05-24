"""Celery configuration and initialization module."""
from celery import Celery
from app.core.config import settings

# Initialize Celery
# The first argument is the name of the current module, useful for automatic naming of tasks.
# The broker URL is taken from your application settings.
celery_app = Celery(
    __name__, # Or you can use a specific app name like 'formiq_tasks'
    broker=settings.CELERY_BROKER_URL, 
    # backend=settings.CELERY_RESULT_BACKEND, # Optional: if you need to store task results
    include=[
        'app.tasks.video_tasks',
        'app.tasks.ai_tasks', # Add the new AI tasks module
        'app.tasks.analysis_tasks', # ADD THIS LINE
        # 'app.tasks.pose_detection_tasks', # Example for future tasks
        # 'app.tasks.form_analysis_tasks',  # Example for future tasks
    ]
)

# Optional: Configure Celery further using settings from your config file
# celery_app.config_from_object('app.core.config.CeleryConfig') # If you have a CeleryConfig class in settings

# Example of further configuration (can also be in CeleryConfig class):
celery_app.conf.update(
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    timezone=settings.TIMEZONE if hasattr(settings, 'TIMEZONE') else 'UTC', # Use app timezone or default to UTC
    enable_utc=True,
    task_track_started=True, # If you want tasks to report 'started' state
    worker_prefetch_multiplier=1, # Can be useful for long-running I/O bound tasks
    # worker_concurrency=settings.CELERY_WORKER_CONCURRENCY if hasattr(settings, 'CELERY_WORKER_CONCURRENCY') else None, # Number of worker processes/threads
)

# Optional: If you want to use a custom Celery Task base class for all tasks
# (e.g., to automatically handle DB sessions or other common setup/teardown)
# class BaseTaskWithAppContext(celery_app.Task):
#     def __call__(self, *args, **kwargs):
#         # Example: You could manage app context or DB session here if needed globally
#         # with app.app_context(): # If using Flask-like app context
#         return super().__call__(*args, **kwargs)
# celery_app.Task = BaseTaskWithAppContext

# NOTE: If you use async def tasks, you must run Celery with an async worker pool (e.g., -P eventlet or -P gevent).\n# Example: celery -A app.core.celery_app.celery_app worker -l info

if __name__ == '__main__':
    # This is for running the worker directly from this module, e.g., for development:
    # celery -A app.core.celery_app.celery_app worker -l info
    celery_app.start()

# Celery beat schedule for periodic tasks (if needed)
celery_app.conf.beat_schedule = {
    # Example periodic task:
    # "cleanup-old-videos": {
    #     "task": "app.tasks.video_processing.cleanup_old_videos",
    #     "schedule": 86400.0,  # Once per day
    # },
} 