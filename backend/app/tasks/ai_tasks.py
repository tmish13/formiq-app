"""Retired: pose-detection / angle / form-analysis Celery tasks.

The implementation now lives in ``backend/archive/tasks_old/ai_tasks.py``.

**These tasks never ran.** All three were declared ``async def`` under
``@app.task``, so Celery called them, got a coroutine object back, and returned
it as the result without ever awaiting it. ``perform_form_analysis_celery_task``
additionally carried ``autoretry_for=(Exception,)``, which wraps the function but
does not await it either -- calling it still yields a coroutine. Verified by
``tests/unit/test_retired_tasks.py``.

See ``app/tasks/video_tasks.py`` for why the names are kept rather than deleted.
The live analysis path is ``app.tasks.analysis_tasks.process_form_check_task``,
which is a sync wrapper around ``asyncio.run()`` and does execute.
"""
from app.core.celery_app import celery_app

_RETIRED = (
    "{name} was retired on branch audit/phase1-worker-model. It was an async def "
    "under a plain @app.task, so Celery never awaited it and its body never ran. "
    "The implementation is preserved at backend/archive/tasks_old/ai_tasks.py. "
    "The live analysis path is app.tasks.analysis_tasks.process_form_check_task."
)


@celery_app.task(bind=True, name="app.tasks.ai_tasks.detect_pose_celery_task")
def detect_pose_celery_task(self, *args, **kwargs):
    raise NotImplementedError(_RETIRED.format(name="detect_pose_celery_task"))


@celery_app.task(bind=True, name="app.tasks.ai_tasks.calculate_angles_celery_task")
def calculate_angles_celery_task(self, *args, **kwargs):
    raise NotImplementedError(_RETIRED.format(name="calculate_angles_celery_task"))


@celery_app.task(bind=True, name="ai.perform_form_analysis")
def perform_form_analysis_celery_task(self, *args, **kwargs):
    raise NotImplementedError(_RETIRED.format(name="perform_form_analysis_celery_task"))
