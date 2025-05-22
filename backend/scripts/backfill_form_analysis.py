import asyncio
import logging
from uuid import UUID

from sqlalchemy import select, or_, and_
from sqlalchemy.orm import joinedload, selectinload

from app.db.session import SessionLocal, get_settings_override
from app.models.video import Video
from app.models.form_check import FormCheck
from app.core.config import Settings
# Import the Celery task
try:
    from app.tasks.ai_tasks import perform_form_analysis_celery_task
except ImportError:
    perform_form_analysis_celery_task = None
    logging.error("Celery task perform_form_analysis_celery_task not found. Backfill script will not function.")

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def backfill_video_analysis():
    """
    Fetches videos that need analysis and enqueues Celery tasks for them.
    Videos needing analysis are those with angle_data and either:
    1. No associated FormCheck record.
    2. An associated FormCheck record that has no overall_score.
    """
    if perform_form_analysis_celery_task is None:
        logger.error("perform_form_analysis_celery_task is not configured. Aborting backfill.")
        return

    logger.info("Starting backfill for video form analysis...")
    db_session = SessionLocal()
    videos_to_analyze_count = 0
    tasks_enqueued_count = 0

    try:
        # Query for videos that have angle_data
        # And either no FormCheck OR FormCheck with overall_score IS NULL
        stmt = (
            select(Video)
            .outerjoin(FormCheck, Video.id == FormCheck.video_id)
            .options(selectinload(Video.form_checks)) # Eager load form_checks to inspect them
            .where(
                Video.angle_data.isnot(None),
                or_(
                    Video.form_checks == None,  # No FormCheck at all
                    FormCheck.overall_score.is_(None) # FormCheck exists but no score
                )
            )
        )
        
        result = await db_session.execute(stmt)
        videos = result.scalars().unique().all()
        
        videos_to_analyze_count = len(videos)
        logger.info(f"Found {videos_to_analyze_count} videos requiring form analysis.")

        for video in videos:
            logger.info(f"Processing video ID: {video.id} (Duration: {video.duration_seconds}s, Angle data present: {bool(video.angle_data)})")
            
            # Additional check just to be sure, though query should handle it
            needs_analysis = True
            if video.form_checks:
                # If multiple form checks, check if ANY have a score. If so, maybe skip.
                # For simplicity, if there's any form_check without a score, we re-queue.
                # A more sophisticated approach might look at the latest form_check.
                scored_form_check_exists = any(fc.overall_score is not None for fc in video.form_checks)
                if scored_form_check_exists:
                    logger.info(f"Video {video.id} already has a FormCheck with a score. Skipping.")
                    needs_analysis = False
            
            if needs_analysis:
                try:
                    task = perform_form_analysis_celery_task.delay(str(video.id))
                    logger.info(f"Enqueued analysis task for video ID: {video.id}. Task ID: {task.id}")
                    tasks_enqueued_count += 1
                    # Optional: Add a small delay to avoid overwhelming Celery broker/workers if many tasks
                    # await asyncio.sleep(0.1)
                except Exception as e:
                    logger.error(f"Failed to enqueue task for video ID {video.id}: {e}", exc_info=True)
            else:
                 logger.info(f"Skipping video {video.id} as it does not meet analysis criteria based on form_checks.")

        logger.info(f"Backfill process completed. Total videos checked: {videos_to_analyze_count}. Tasks enqueued: {tasks_enqueued_count}.")

    except Exception as e:
        logger.error(f"An error occurred during the backfill process: {e}", exc_info=True)
    finally:
        await db_session.close()

if __name__ == "__main__":
    # This script should be run in an environment where Celery and DB settings are available.
    # Ensure your PYTHONPATH is set correctly to find `app` module.
    # Example: PYTHONPATH=$PYTHONPATH:./backend python backend/scripts/backfill_form_analysis.py
    
    # Load settings explicitly if needed for Celery task discovery or db connection outside app context
    # settings = get_settings_override()
    
    logger.info("Running video analysis backfill script...")
    asyncio.run(backfill_video_analysis()) 