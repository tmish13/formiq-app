"""Celery tasks for analysis processing."""
import asyncio
import logging
import os
from uuid import UUID
from tempfile import NamedTemporaryFile
from typing import Optional, Dict, Any

from celery.signals import worker_process_init
from app.core.celery_app import celery_app
from app.core.config import get_settings, Settings
from app.core.database import get_async_session_for_celery # Changed import path

# Import services
from app.services.form_check_service import FormCheckService
from app.services.storage_service import StorageService
from app.services.ai_service import AIService
from app.core.cache import cache_service # Global instance, already initialized
from app.models.enums import FormCheckStatus, ExerciseType
from app.models.exercise import ExerciseTemplate
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import NotFoundException
from app.services.dynamic_form_analysis_service import DynamicFormAnalysisService

logger = logging.getLogger(__name__)

# Global instances for services initialized once per worker process
_shared_ai_service: Optional[AIService] = None
_shared_storage_service: Optional[StorageService] = None

@worker_process_init.connect
def initialize_worker_services(**kwargs):
    """Initialize shared services once per Celery worker process."""
    global _shared_ai_service, _shared_storage_service
    logger.info("Celery worker process initializing shared services...")
    try:
        # settings_obj = get_settings() # If services need settings for their __init__
        _shared_ai_service = AIService() # Pass settings_obj if needed
        _shared_storage_service = StorageService() # Pass settings_obj if needed
        logger.info("Shared services (AIService, StorageService) initialized successfully for Celery worker.")
    except Exception as e:
        logger.critical(f"CRITICAL: Failed to initialize shared services in Celery worker: {e}", exc_info=True)
        # Depending on the service, you might want to raise the exception
        # to prevent the worker from starting if these services are absolutely critical.
        raise

# Helper to get an async DB session for Celery tasks
async def get_task_db_session() -> AsyncSession:
    async with get_async_session_for_celery() as session:
        yield session

# Helper to instantiate services within a task context
async def get_services_for_task(db_session: AsyncSession, settings_obj: Settings):
    """Provides FormCheckService and access to shared AI and Storage services."""
    if _shared_ai_service is None or _shared_storage_service is None:
        logger.error(
            "Shared services (_shared_ai_service or _shared_storage_service) are not initialized! "
            "This indicates an issue with Celery worker_process_init. "
            "Attempting to initialize them now as a fallback, but this should be investigated."
        )
        # Fallback: This is not ideal and should be alerted on if it happens frequently.
        try:
            ai_service_instance = AIService() # Pass settings_obj if needed
            storage_service_instance = StorageService() # Pass settings_obj if needed
        except Exception as e_fallback_init:
            logger.critical(f"CRITICAL: Fallback initialization of AI/Storage service failed: {e_fallback_init}", exc_info=True)
            raise
        logger.warning("Fallback initialization of AI/Storage services completed.")
    else:
        ai_service_instance = _shared_ai_service
        storage_service_instance = _shared_storage_service

    form_check_service = FormCheckService(
        db=db_session,
        settings=settings_obj,
        storage_service=storage_service_instance, # Use shared or fallback instance
        ai_service=ai_service_instance,          # Use shared or fallback instance
        cache_service=cache_service # global instance
    )
    return form_check_service, storage_service_instance, ai_service_instance


@celery_app.task(name="tasks.process_form_check_task", bind=True, max_retries=3, default_retry_delay=60)
async def process_form_check_task(self, form_check_id_str: str):
    form_check_id = UUID(form_check_id_str)
    logger.info(f"[CeleryTask] Starting analysis for FormCheck ID: {form_check_id}")

    settings_obj = get_settings()
    db_session: Optional[AsyncSession] = None
    form_check_service: Optional[FormCheckService] = None
    # storage_service and ai_service will be the shared (or fallback) instances provided by get_services_for_task
    # No need to declare them as Optional[StorageService] here if get_services_for_task guarantees their return
    
    video_file_path_local: Optional[str] = None
    analysis_results: Dict[str, Any] = {}
    final_status: FormCheckStatus = FormCheckStatus.ERROR

    try:
        async for session in get_task_db_session():
            db_session = session
            break # We only need one session
        if not db_session:
            # This should not happen if AsyncSessionLocal is configured correctly.
            logger.critical("[CeleryTask] Failed to acquire DB session. Aborting task.")
            raise Exception("Failed to acquire DB session for Celery task.")

        # Get services - this now uses shared instances for AI and Storage
        _form_check_service, _storage_service, _ai_service = await get_services_for_task(db_session, settings_obj)
        # Assign to task-local variables for clarity if preferred, or use directly
        form_check_service = _form_check_service
        storage_service = _storage_service
        ai_service = _ai_service

        try:
            form_check = await form_check_service.get_async(id=form_check_id)
        except NotFoundException:
            logger.error(f"[CeleryTask] FormCheck ID {form_check_id} not found. Aborting task.")
            return {"status": "error", "message": "FormCheck not found"}

        if form_check.status != FormCheckStatus.PENDING:
            logger.warning(f"[CeleryTask] FormCheck ID {form_check_id} not PENDING (status: {form_check.status.value}). Skipping.")
            return {"status": "skipped", "message": f"Not in PENDING state, was {form_check.status.value}"}

        await form_check_service.update_async(db_obj=form_check, obj_in={"status": FormCheckStatus.PROCESSING})
        await db_session.commit()
        logger.info(f"[CeleryTask] FormCheck ID {form_check_id} status updated to PROCESSING.")

        video_url = form_check.video_url
        exercise_id = form_check.exercise_id

        # Ensure ExerciseTemplate is imported and used correctly
        exercise_template = await db_session.get(ExerciseTemplate, exercise_id)
        if not exercise_template:
            logger.error(f"[CeleryTask] ExerciseTemplate ID {exercise_id} not found for FormCheck {form_check_id}")
            analysis_results = {"error_message": "Associated ExerciseTemplate not found."}
            raise ValueError("ExerciseTemplate not found for analysis.")

        try:
            current_exercise_type = ExerciseType(exercise_template.name) # Use name from ExerciseTemplate
        except ValueError:
            logger.error(f"[CeleryTask] Invalid exercise type string '{exercise_template.name}' from DB for FormCheck {form_check_id}.")
            analysis_results = {"error_message": f"Invalid exercise type '{exercise_template.name}' configured."}
            raise ValueError(f"Invalid exercise type '{exercise_template.name}' for analysis.")

        logger.info(f"[CeleryTask] Downloading video {video_url} for FormCheck ID {form_check_id}")
        video_content = await storage_service.download_file(video_url)
        
        with NamedTemporaryFile(delete=False, suffix=".mp4") as tmpfile:
            tmpfile.write(video_content)
            video_file_path_local = tmpfile.name
        logger.info(f"[CeleryTask] Video for FormCheck {form_check_id} downloaded to: {video_file_path_local}")

        logger.info(f"[CeleryTask] Performing AI analysis for FormCheck {form_check_id}, exercise: {current_exercise_type.value}")
        
        analysis_results = await ai_service.analyze_video_file_for_form_check(video_file_path_local, current_exercise_type)

        if not analysis_results or analysis_results.get("error_message") or analysis_results.get("score") is None:
             logger.error(f"[CeleryTask] AI analysis failed or returned invalid/error results for FormCheck {form_check_id}. Results: {analysis_results}")
             if "error_message" not in analysis_results:
                # Ensure a generic error message if AI service doesn't provide one specifically
                error_msg_detail = analysis_results.get("feedback")
                if isinstance(error_msg_detail, list) and error_msg_detail:
                    analysis_results["error_message"] = error_msg_detail[0]
                else:
                    analysis_results["error_message"] = "AI analysis yielded no valid results or an unspecified error."
             raise ValueError(f"AI Analysis returned invalid results or error: {analysis_results.get('error_message')}")

        final_status = FormCheckStatus.COMPLETED
        logger.info(f"[CeleryTask] AI analysis successful for FormCheck ID {form_check_id}.")

    except Exception as e:
        logger.error(f"[CeleryTask] Error during FormCheck {form_check_id} analysis: {type(e).__name__}: {e}", exc_info=True)
        final_status = FormCheckStatus.ERROR
        if "error_message" not in analysis_results:
            analysis_results["error_message"] = f"{type(e).__name__}: {str(e)}" # Provide more specific error from exception
        # Consider Celery retry for specific exceptions:
        # if isinstance(e, SomeRetriableInfrastructureError):
        #     self.retry(exc=e)

    finally:
        if form_check_service: 
            try:
                logger.info(f"[CeleryTask] Finalizing FormCheck {form_check_id} with status {final_status.value}")
                await form_check_service.finalize_form_check_analysis_async(
                    form_check_id=form_check_id,
                    analysis_results=analysis_results,
                    status=final_status
                )
            except Exception as e_finalize:
                logger.critical(f"[CeleryTask] CRITICAL: Failed to finalize FormCheck {form_check_id} in DB: {e_finalize}", exc_info=True)
        else:
            logger.error(f"[CeleryTask] form_check_service was not initialized. Cannot finalize FormCheck {form_check_id}.")

        if video_file_path_local and os.path.exists(video_file_path_local):
            try:
                os.remove(video_file_path_local)
                logger.info(f"[CeleryTask] Cleaned up temp video file {video_file_path_local} for FormCheck {form_check_id}")
            except Exception as e_clean:
                logger.error(f"[CeleryTask] Failed to clean up temp video file {video_file_path_local}: {e_clean}", exc_info=True)
        
        if db_session:
            await db_session.close()
            logger.info(f"[CeleryTask] DB session closed for FormCheck ID: {form_check_id}")

    logger.info(f"[CeleryTask] Finished processing FormCheck ID: {form_check_id} with status: {final_status.value}")
    return {"status": final_status.value, "form_check_id": str(form_check_id)}

# To make this task discoverable, ensure __init__.py in the tasks folder (and its parent app folder)
# imports this module or the celery_app directly.
# e.g. in app/tasks/__init__.py:
# from .analysis_tasks import process_form_check_task 