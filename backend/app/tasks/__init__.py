"""Background tasks package for Celery.

The only live task module is ``analysis_tasks``. ``video_tasks`` and ``ai_tasks``
are retired stubs kept so existing import paths still resolve -- see their
docstrings.
"""

from .analysis_tasks import process_form_check_task

__all__ = ["process_form_check_task"]
