"""Retired: video-processing Celery tasks.

The implementation now lives in ``backend/archive/tasks_old/video_tasks.py``.

**These tasks never ran.** ``process_video_celery_task`` was declared
``async def`` under a plain ``@app.task`` decorator, and Celery has no await
step: it called the function, received a coroutine object, and returned that
object as the task's result. The body never executed, under any pool. Verified
by ``tests/unit/test_retired_tasks.py``.

That is the failure class this branch exists to remove -- work that is accepted,
reported as queued, and can never happen. So rather than delete the module (a
dozen test files patch these import paths) the names are kept and made loud:
dispatching raises instead of silently succeeding, and the API surface that
reached them returns 501.

The module is no longer in ``celery_app.conf.include``, so no worker registers
these names.
"""
from app.core.celery_app import celery_app

_RETIRED = (
    "{name} was retired on branch audit/phase1-worker-model. It was an async def "
    "under a plain @app.task, so Celery never awaited it and its body never ran. "
    "The implementation is preserved at backend/archive/tasks_old/video_tasks.py."
)


@celery_app.task(bind=True, name="app.tasks.video_tasks.process_video_celery_task")
def process_video_celery_task(self, *args, **kwargs):
    raise NotImplementedError(_RETIRED.format(name="process_video_celery_task"))

