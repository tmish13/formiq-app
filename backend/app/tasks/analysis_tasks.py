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
from app.services.exercise_config_service import ExerciseConfigService # ADDED
from app.services.video_service import VideoService # ADDED
from app.core.cache import cache_service # Global instance, already initialized
from app.models.enums import FormCheckStatus, ExerciseType
from app.models.exercise import ExerciseTemplate
from app.models.video import Video as VideoModel # ADDED for type hint
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import NotFoundException
from app.services.dynamic_form_analysis_service import DynamicFormAnalysisService
from app.services.video_service import VideoService

logger = logging.getLogger(__name__)

# Global instances for services initialized once per worker process
_shared_ai_service: Optional[AIService] = None
_shared_storage_service: Optional[StorageService] = None
_shared_exercise_config_service: Optional[ExerciseConfigService] = None # ADDED
_shared_video_service: Optional[VideoService] = None # ADDED

@worker_process_init.connect
def initialize_worker_services(**kwargs):
    """Initialize shared services once per Celery worker process."""
    global _shared_ai_service, _shared_storage_service, _shared_exercise_config_service, _shared_video_service # MODIFIED
    logger.info("Celery worker process initializing shared services...")
    try:
        settings_obj = get_settings() # Services might need settings
        _shared_ai_service = AIService(app_settings=settings_obj) # Pass settings
        _shared_storage_service = StorageService(settings=settings_obj) # Pass settings
        # Initialize ExerciseConfigService and VideoService with db access needs to be handled carefully
        # For services requiring DB session for __init__, this pattern might not be ideal,
        # or they should be designed to be initializable without a session, deferring DB ops to methods.
        # Assuming ExerciseConfigService and VideoService can be initialized without a db session, or get it later.
        # If they strictly need a DB session at init, they should be created inside the task context.
        # For now, let's assume they can be initialized here or their __init__ is adapted.
        # A safer pattern for DB-bound services is to instantiate them per task, or use a factory that gets a session.
        # However, ExerciseConfigService and VideoService in this project are typically instantiated with a db session.
        # This highlights a potential design consideration for shared Celery services.
        # For this refactor, we'll assume they are instantiated in get_services_for_task for safety if they need DB at init.
        # So, we will NOT initialize them globally here to avoid issues with DB session state across tasks.
        # They will be created in get_services_for_task.
        _shared_exercise_config_service = None # Will be created in task
        _shared_video_service = None       # Will be created in task
        logger.info("Shared services (AIService, StorageService) initialized successfully for Celery worker. Other services (ExerciseConfig, Video) will be task-scoped.")
    except Exception as e:
        logger.critical(f"CRITICAL: Failed to initialize shared services in Celery worker: {e}", exc_info=True)
        raise

# Helper to get an async DB session for Celery tasks
async def get_task_db_session() -> AsyncSession:
    async for session in get_async_session_for_celery():
        yield session

# Helper to instantiate services within a task context
async def get_services_for_task(db_session: AsyncSession, settings_obj: Settings):
    """Provides necessary services for the task."""
    # Use globally initialized AI and Storage if available, otherwise fallback (with warning)
    ai_service_instance = _shared_ai_service
    if ai_service_instance is None:
        logger.warning("Shared AIService not initialized, creating a new instance for this task.")
        ai_service_instance = AIService(app_settings=settings_obj)

        storage_service_instance = _shared_storage_service
    if storage_service_instance is None:
        logger.warning("Shared StorageService not initialized, creating a new instance for this task.")
        storage_service_instance = StorageService(settings=settings_obj)
    # Instantiate services that require DB session per task
    form_check_service = FormCheckService(
        db=db_session,
        settings=settings_obj,
        storage_service=storage_service_instance,
        ai_service=ai_service_instance, # This AIService might not be the one used for dynamic analysis
        cache_service=cache_service
    )
    exercise_config_service = ExerciseConfigService(db=db_session, settings=settings_obj)
    video_service = VideoService(db=db_session, settings=settings_obj, storage_service=storage_service_instance)
    
    dynamic_form_analysis_service = DynamicFormAnalysisService(
        db=db_session,
        settings=settings_obj,
        exercise_config_service=exercise_config_service,
        form_check_service=form_check_service # DFAS might use this for creating/updating FormCheck
    )

    return (
        form_check_service, 
        storage_service_instance, 
        ai_service_instance, # Keep for potential other uses, or remove if DFAS fully replaces its role here
        exercise_config_service,
        video_service,
        dynamic_form_analysis_service
    )


# Explicitly name the task to ensure consistent registration
@celery_app.task(name="app.tasks.analysis_tasks.process_form_check", bind=True, max_retries=3, default_retry_delay=300)
async def process_form_check_task(self, video_id_str: str, form_check_id_str: str):
    """
    Celery task to process a form check analysis for a given video and form_check ID.
    Uses DynamicFormAnalysisService for rule-based evaluation.
    """
    form_check_id = UUID(form_check_id_str)
    video_id = UUID(video_id_str) # Convert video_id_str to UUID
    logger.info(f"[CeleryTask] Starting analysis for FormCheck ID: {form_check_id}, Video ID: {video_id}")

    settings_obj = get_settings()
    db_session: Optional[AsyncSession] = None
    form_check_service: Optional[FormCheckService] = None
    
    analysis_output_for_finalize: Dict[str, Any] = {} # Renamed to avoid confusion with model
    final_status: FormCheckStatus = FormCheckStatus.ERROR
    analyzed_form_check_model: Optional[FormCheck] = None # To store the result from DFAS

    try:
        async for session in get_task_db_session():
            db_session = session
            break 
        if not db_session:
            logger.critical("[CeleryTask] Failed to acquire DB session. Aborting task.")
            raise Exception("Failed to acquire DB session for Celery task.")

        (
            form_check_service, 
            storage_service, # Not used directly in this refactored analysis path, but available
            _ai_service_instance, # Keep variable name to avoid breaking other parts if used, though DFAS is primary
            exercise_config_service,
            video_service,
            dynamic_form_analysis_service
        ) = await get_services_for_task(db_session, settings_obj)

        try:
            form_check = await form_check_service.get_async(id=form_check_id)
            if not form_check: # Double check after get_async
                raise NotFoundException(f"FormCheck ID {form_check_id} not found after get_async.")
        except NotFoundException:
            logger.error(f"[CeleryTask] FormCheck ID {form_check_id} not found. Aborting task.")
            return {"status": "error", "message": "FormCheck not found"}

        if form_check.status != FormCheckStatus.PENDING:
            logger.warning(f"[CeleryTask] FormCheck ID {form_check_id} not PENDING (status: {form_check.status.value}). Skipping.")
            return {"status": "skipped", "message": f"Not in PENDING state, was {form_check.status.value}"}

        await form_check_service.update_async(db_obj=form_check, obj_in={"status": FormCheckStatus.PROCESSING})
        await db_session.commit()
        logger.info(f"[CeleryTask] FormCheck ID {form_check_id} status updated to PROCESSING.")

        # Fetch the Video object which should have angle_data
        video_model = await video_service.get_video_by_id_async(video_id=video_id)
        if not video_model:
            logger.error(f"[CeleryTask] Video ID {video_id} not found for FormCheck {form_check_id}")
            analysis_output_for_finalize = {"error_message": "Associated Video not found for analysis."}
            raise ValueError("Video not found for analysis.")

        if not video_model.angle_data: # Or calculated_angles_url if angles are stored separately
            logger.error(f"[CeleryTask] Angle data not found for Video ID {video_id} (FormCheck {form_check_id})")
            analysis_output_for_finalize = {"error_message": "Angle data missing for Video. Ensure prior pipeline steps completed."}
            raise ValueError("Angle data missing in Video model.")

        # Fetch the ExerciseConfig
        exercise_config = await exercise_config_service.get_active_config_for_exercise_async(exercise_id=form_check.exercise_id)
        if not exercise_config:
            logger.error(f"[CeleryTask] Active ExerciseConfig not found for exercise ID {form_check.exercise_id} (FormCheck {form_check_id})")
            analysis_output_for_finalize = {"error_message": "Active ExerciseConfiguration not found."}
            raise ValueError("ExerciseConfiguration not found.")

        logger.info(f"[CeleryTask] Performing dynamic form analysis for FormCheck {form_check_id} using DynamicFormAnalysisService.")
        
        # DynamicFormAnalysisService.analyze_form_dynamically is expected to return an updated FormCheck model
        # It now also takes the initial form_check object to update.
        # Let's assume analyze_form_dynamically can take the form_check_id or the object
        # and updates it or returns a new one. For this refactor, assume it returns an updated FormCheck.
        # The service method `analyze_form_dynamically` in `dynamic_form_analysis_service.py` needs to be
        # adjusted if it's currently creating a NEW form_check rather than updating an existing one based on ID.
        # For now, let's assume it's: analyze_form_dynamically(self, video: Video, exercise_config: ExerciseConfig, existing_form_check_id: UUID) -> FormCheck
        # Or, if it creates a new one, we'd use its data.
        # The current signature is: analyze_form_dynamically(self, video: Video) -> FormCheck
        # This needs adjustment in DynamicFormAnalysisService to accept exercise_config and form_check_id/object.
        # Let's proceed with the assumption that DynamicFormAnalysisService will be adapted or can work with this.
        # A practical implementation might involve DFAS loading the FormCheck internally if given an ID,
        # or taking a FormCheck object to update.
        # For now, we will call it and then adapt its output.
        # Let's assume the service is adapted to:
        # async def analyze_form_dynamically(self, video: VideoModel, exercise_config: ExerciseConfig, base_form_check: FormCheck) -> FormCheck:
        # This would be a change in dynamic_form_analysis_service.py

        # --- SIMPLIFIED APPROACH FOR NOW: Assume DFAS returns a FormCheck like object or dict ---
        # This part requires careful thought on how DFAS integrates.
        # If DFAS fully populates a FormCheck object including feedback items:
        analyzed_form_check_model = await dynamic_form_analysis_service.analyze_form_dynamically(
            video=video_model, 
            exercise_config=exercise_config,
            initial_form_check=form_check # Pass the existing form_check to be updated
        )
        # The above line assumes dynamic_form_analysis_service.analyze_form_dynamically is refactored
        # to accept `initial_form_check` and update it or return an updated version.

        if not analyzed_form_check_model:
            logger.error(f"[CeleryTask] DynamicFormAnalysisService returned no result for FormCheck {form_check_id}.")
            analysis_output_for_finalize = {"error_message": "Dynamic analysis yielded no results."}
            raise ValueError("Dynamic analysis failed or returned no results.")

        final_status = analyzed_form_check_model.status
        # Prepare analysis_results for finalize_form_check_analysis_async
        # This assumes analyzed_form_check_model is an ORM object with eager loaded/set feedback_items
        
        feedback_messages_list = []
        feedback_structured_list = []
        if analyzed_form_check_model.feedback_items: # Ensure feedback_items is loaded
            for item in analyzed_form_check_model.feedback_items:
                feedback_messages_list.append(item.message if item.message else "N/A")
                feedback_structured_list.append({
                    "type": item.type.value if item.type else FeedbackType.GENERAL.value, # Use .value for enums
                    "message": item.message if item.message else "N/A",
                    "timestamp": item.timestamp if item.timestamp is not None else 0.0,
                    "severity": item.severity.value if item.severity else FeedbackSeverity.INFO.value, # Use .value for enums
                    "suggestions": item.suggestions if item.suggestions else [],
                    "details": item.details if item.details else {} 
                })
        
        analysis_output_for_finalize = {
            "score": analyzed_form_check_model.score if analyzed_form_check_model.score is not None else 0.0,
            "feedback": feedback_messages_list,
            "risk_level": analyzed_form_check_model.details.get("risk_level", "low") if analyzed_form_check_model.details else "low",
            "feedback_structured": feedback_structured_list,
            "error_message": analyzed_form_check_model.error_details,
            "summary": analyzed_form_check_model.summary # Make sure DFAS sets this
        }
        
        if final_status != FormCheckStatus.COMPLETED: # If DFAS set it to ERROR
             if not analysis_output_for_finalize.get("error_message") and analyzed_form_check_model.error_details:
                 analysis_output_for_finalize["error_message"] = analyzed_form_check_model.error_details
             elif not analysis_output_for_finalize.get("error_message"):
                 analysis_output_for_finalize["error_message"] = "Analysis by DynamicFormAnalysisService resulted in non-COMPLETED status."

        logger.info(f"[CeleryTask] Dynamic form analysis successful for FormCheck ID {form_check_id}.")

    except ValueError as ve: # Catch specific value errors from our checks
        logger.error(f"[CeleryTask] ValueError during FormCheck {form_check_id} analysis: {ve}", exc_info=True)
        final_status = FormCheckStatus.ERROR
        if "error_message" not in analysis_output_for_finalize or not analysis_output_for_finalize["error_message"]:
            analysis_output_for_finalize["error_message"] = str(ve)
    except Exception as e:
        logger.error(f"[CeleryTask] General error during FormCheck {form_check_id} analysis: {type(e).__name__}: {e}", exc_info=True)
        final_status = FormCheckStatus.ERROR
        if "error_message" not in analysis_output_for_finalize or not analysis_output_for_finalize["error_message"]:
            analysis_output_for_finalize["error_message"] = f"{type(e).__name__}: {str(e)}"
    finally:
        if form_check_service and form_check_id: # Ensure form_check_id is available
            try:
                logger.info(f"[CeleryTask] Finalizing FormCheck {form_check_id} with status {final_status.value}")
                # Ensure all necessary fields for finalize are in analysis_output_for_finalize
                if "score" not in analysis_output_for_finalize: analysis_output_for_finalize["score"] = 0.0
                if "feedback" not in analysis_output_for_finalize: analysis_output_for_finalize["feedback"] = []
                if "risk_level" not in analysis_output_for_finalize: analysis_output_for_finalize["risk_level"] = "high"
                if "feedback_structured" not in analysis_output_for_finalize: analysis_output_for_finalize["feedback_structured"] = []
                
                await form_check_service.finalize_form_check_analysis_async(
                    form_check_id=form_check_id,
                    analysis_results=analysis_output_for_finalize,
                    status=final_status
                )
                logger.info(f"[CeleryTask] FormCheck {form_check_id} finalized.")
            except Exception as e_finalize:
                logger.critical(f"[CeleryTask] CRITICAL: Failed to finalize FormCheck {form_check_id} in DB: {e_finalize}", exc_info=True)
        else:
            logger.error(f"[CeleryTask] form_check_service not initialized or form_check_id missing. Cannot finalize FormCheck.")
        
        # Local video file cleanup was removed in original task, assuming cloud URLs are used.
        # If DynamicFormAnalysisService downloads files, it should clean them up.
        # The original task downloaded video_url to video_file_path_local, this is removed now
        # as DFAS takes Video object which should have data/urls.
        # If DFAS needs local file, it has to handle its download/cleanup or this task gives it a path.
        # For now, assume DFAS works with Video object and its angle_data.
        
        if db_session:
            await db_session.close()
            logger.info(f"[CeleryTask] DB session closed for FormCheck ID: {form_check_id}")

    logger.info(f"[CeleryTask] Finished processing FormCheck ID: {form_check_id} with status: {final_status.value}")
    return {"status": final_status.value, "form_check_id": str(form_check_id), "final_score": analysis_output_for_finalize.get("score")}

# To make this task discoverable, ensure __init__.py in the tasks folder (and its parent app folder)
# imports this module or the celery_app directly.
# e.g. in app/tasks/__init__.py:
# from .analysis_tasks import process_form_check_task 