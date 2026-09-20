from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import logging
from uuid import UUID

from app.api import deps
from app.services.video_service import VideoService

# perform_form_analysis_celery_task is retired: it was an async def under
# @app.task, so Celery returned an un-awaited coroutine and the body never ran.
# This endpoint used to answer 202 Accepted and enqueue it, i.e. it promised work
# that could not happen. It now says so.
_RETIRED_DETAIL = (
    "Form analysis is not available through this endpoint. The task it dispatched "
    "(ai.perform_form_analysis) was an async def under a plain @app.task, so its "
    "body never executed -- this endpoint returned 202 Accepted for work that "
    "never ran. Submit a form check instead: POST /api/v1/form-checks/."
)


router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/analyze-form/{video_id}", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def trigger_form_analysis(
    video_id: UUID,
    video_service: VideoService = Depends(deps.get_video_service),
):
    """Retired. Always 501.

    Kept as a route so callers get a clear answer rather than a 404 that looks
    like a typo. The live path is the form-check pipeline.
    """
    logger.warning(
        "Retired endpoint POST /analysis/analyze-form/%s called; returning 501.",
        video_id,
    )
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=_RETIRED_DETAIL
    )


# Add this router to the main FastAPI app in app/main.py
# from app.api.v1.endpoints import analysis as analysis_router
# app.include_router(analysis_router.router, prefix="/api/v1/analysis", tags=["Analysis"])
# Note: The above line for main.py is a comment and should be manually added by the user. 