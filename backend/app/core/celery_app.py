"""Celery configuration and initialization module."""
import os
from celery import Celery
from app.core.config import settings

# Setup OpenTelemetry tracing for Celery if available
def _setup_celery_tracing():
    """Setup OpenTelemetry tracing for Celery tasks."""
    try:
        from app.core.tracing import _safe_import
        celery_instrumentor = _safe_import('opentelemetry.instrumentation.celery')
        if celery_instrumentor:
            instrumentor = celery_instrumentor.CeleryInstrumentor()
            if not hasattr(instrumentor, '_is_instrumented') or not instrumentor._is_instrumented:
                instrumentor.instrument()
                print("Celery OpenTelemetry instrumentation configured")
    except Exception as e:
        print(f"Could not setup Celery tracing: {e}")

# Setup Celery tracing
_setup_celery_tracing()

# Initialize Celery
# The first argument is the name of the current module, useful for automatic naming of tasks.
# The broker URL is taken from your application settings.
celery_app = Celery(
    __name__, # Or you can use a specific app name like 'formiq_tasks'
    broker=settings.CELERY_BROKER_URL, 
    # backend=settings.CELERY_RESULT_BACKEND, # Optional: if you need to store task results
    include=[
        # app.tasks.video_tasks and app.tasks.ai_tasks are retired -- every task in
        # them was an async def under a plain @app.task, so Celery returned an
        # un-awaited coroutine and the bodies never ran. Their modules survive as
        # loud stubs; they are deliberately NOT registered with any worker.
        'app.tasks.analysis_tasks',
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
    # Ack only after the task finishes. With the default early ack the broker
    # forgets the message the moment it is delivered, so a worker that dies
    # mid-task loses the work silently -- which is how 17 of 20 form checks sat
    # at PENDING forever with nothing left to retry them.
    task_acks_late=True,
    # Late acks alone are not enough: a task whose worker vanishes would be
    # redelivered forever. This requeues it once and then rejects it, so a
    # poison message cannot pin a worker.
    task_reject_on_worker_lost=True,
    # The 20-video parity run measured 10-12 s/video, but complexity-2 pose on a
    # long clip is the tail. Soft limit raises SoftTimeLimitExceeded inside the
    # task so its cleanup blocks run; the hard limit is the backstop.
    task_soft_time_limit=300,  # Raise SoftTimeLimitExceeded after 5 minutes
    task_time_limit=360,       # Hard kill after 6 minutes
    # Concurrency capped well below DB pool_size (default 20) so analysis tasks
    # never exhaust PostgreSQL connections.  Override via CELERY_WORKER_CONCURRENCY
    # env var or --concurrency flag at worker startup.
    worker_concurrency=int(os.getenv("CELERY_WORKER_CONCURRENCY", "4")),
)

# Optional: If you want to use a custom Celery Task base class for all tasks
# (e.g., to automatically handle DB sessions or other common setup/teardown)
# class BaseTaskWithAppContext(celery_app.Task):
#     def __call__(self, *args, **kwargs):
#         # Example: You could manage app context or DB session here if needed globally
#         # with app.app_context(): # If using Flask-like app context
#         return super().__call__(*args, **kwargs)
# celery_app.Task = BaseTaskWithAppContext

# NOTE: run the worker with -P prefork (the default pool). Do NOT use -P gevent or
# -P eventlet here: the tasks in app.tasks.analysis_tasks are sync wrappers that
# call asyncio.run(), and under a green-thread pool every task shares one thread
# and one event loop, so the second concurrent task raises
#   RuntimeError: asyncio.run() cannot be called from a running event loop
# and dies. Prefork gives each task its own process and a fresh loop.
# Example: celery -A app.core.celery_app.celery_app worker -l info -P prefork --concurrency=4

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