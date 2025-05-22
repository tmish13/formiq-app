from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import logging
from uuid import UUID

from app.db.session import get_db
from app.services.video_service import VideoService
# Import the Celery task
try:
    from app.tasks.ai_tasks import perform_form_analysis_celery_task
except ImportError:
    # This is a placeholder. If ai_tasks.py or the task doesn't exist,
    # this will allow the API to start, but calls will fail.
    # The task creation is handled in a subsequent step.
    perform_form_analysis_celery_task = None 
    logging.warning("Celery task perform_form_analysis_celery_task not found. Analysis endpoint will not function correctly.")


router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/analyze-form/{video_id}", status_code=status.HTTP_202_ACCEPTED)
async def trigger_form_analysis(
    video_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Triggers dynamic form analysis for a given video ID.

    The analysis is performed asynchronously. This endpoint will return
    a 202 Accepted response immediately after queueing the analysis task.
    """
    video_service = VideoService(db_session=db)
    video = await video_service.get_video_by_id_async(video_id)
    if not video:
        logger.warning(f"Trigger analysis: Video with ID {video_id} not found.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")

    if not video.angle_data:
        logger.warning(f"Trigger analysis: Video {video_id} has no angle data. Analysis cannot proceed.")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Video has no angle data to analyze.")

    if perform_form_analysis_celery_task is None:
        logger.error("perform_form_analysis_celery_task is not available. Cannot queue analysis.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Analysis task handler is not configured.")

    try:
        # Update video status to indicate analysis is pending/queued
        # Example: video.status = VideoStatus.FORM_ANALYSIS_PENDING (ensure VideoStatus enum is updated)
        # await video_service.update_video_async(video_id, {"status": "FORM_ANALYSIS_PENDING"})

        task = perform_form_analysis_celery_task.delay(str(video_id))
        logger.info(f"Enqueued dynamic form analysis for video ID: {video_id}. Task ID: {task.id}")
        
        return {"message": "Form analysis accepted and queued.", "video_id": video_id, "task_id": task.id}

    except Exception as e:
        logger.error(f"Failed to enqueue form analysis task for video ID {video_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to queue analysis task.")

# Add this router to the main FastAPI app in app/main.py
# from app.api.v1.endpoints import analysis as analysis_router
# app.include_router(analysis_router.router, prefix="/api/v1/analysis", tags=["Analysis"])
# Note: The above line for main.py is a comment and should be manually added by the user. 