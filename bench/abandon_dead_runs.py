"""One-off (Gate 1b, 2026-09-23 20:01 PDT): close the runs whose workers were SIGKILLed (their form checks are already
terminal). The scheduled reaper does exactly this once a run is 60 min old; this call
uses a 5-minute threshold so the Gate 1b trail can be reported closed now. Logged here."""
import asyncio
from datetime import timedelta
from app.core.database import get_async_session_for_celery
from app.tasks.maintenance_tasks import _abandon_unclosed_runs

async def main():
    async with get_async_session_for_celery() as session:
        n = await _abandon_unclosed_runs(session, timedelta(minutes=5))
        print("runs abandoned:", n)
asyncio.run(main())
