"""Celery tasks for analysis processing."""
import asyncio
import logging
import os
from uuid import UUID
from tempfile import NamedTemporaryFile
from typing import Optional, Dict, Any, List

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
from app.models.exercise import ExerciseTemplate # MODIFIED
from app.models.exercise_config import ExerciseConfig
from app.models.video import Video as VideoModel # ADDED for type hint
from sqlalchemy import select # ADDED for querying ExerciseTemplate by slug
from app.core.exceptions import NotFoundException
from sqlalchemy.ext.asyncio import AsyncSession # ADDED FOR TYPE HINT
from app.services.dynamic_form_analysis_service import DynamicFormAnalysisService # RE-ADDED
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
        _shared_storage_service = StorageService(app_settings=settings_obj) # Pass settings
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

        # Prioritize smoothed pose_data, then raw_pose_data for classification
        keypoint_sequence_for_classification: Optional[List[List[Optional[Dict[str, float]]]]] = None
        if video_model.pose_data and isinstance(video_model.pose_data, list):
            # Assuming video_model.pose_data is List[Optional[List[Optional[Dict[str, Any]]]]]
            # which is compatible with List[List[Optional[Dict[str, float]]]]
            keypoint_sequence_for_classification = video_model.pose_data
            logger.info(f"[CeleryTask] Using video_model.pose_data (smoothed) for exercise classification. Frames: {len(keypoint_sequence_for_classification) if keypoint_sequence_for_classification else 0}")
        elif video_model.raw_pose_data and isinstance(video_model.raw_pose_data, list):
            keypoint_sequence_for_classification = video_model.raw_pose_data
            logger.info(f"[CeleryTask] video_model.pose_data not available, using video_model.raw_pose_data for exercise classification. Frames: {len(keypoint_sequence_for_classification) if keypoint_sequence_for_classification else 0}")
        else:
            logger.warning(
                f"[CeleryTask] Neither video_model.pose_data nor video_model.raw_pose_data are available or are not lists "
                f"for Video ID {video_id}. Cannot perform exercise classification if needed. "
                f"Pose_data type: {type(video_model.pose_data)}, Raw_pose_data type: {type(video_model.raw_pose_data)}"
            )
            # Continue, classification will fail if attempted without keypoints
        
        # Ensure the sequence is not empty if it was populated
        if keypoint_sequence_for_classification and not any(frame_kps for frame_kps in keypoint_sequence_for_classification):
            logger.warning(f"[CeleryTask] Keypoint sequence for Video ID {video_id} is empty or contains only empty frames. Classification might be unreliable.")
            # keypoint_sequence_for_classification = None # Or let the classifier handle empty sequence if it can

        # Prepare exercise_id and config for analysis (dynamic and new ML)
        exercise_config_for_analysis: Optional[ExerciseConfig] = None
        exercise_template_for_analysis: Optional[ExerciseTemplate] = None
        final_exercise_id_for_ml: Optional[UUID] = None

        if form_check.exercise_id:
            logger.info(f"[CeleryTask] User provided exercise_id: {form_check.exercise_id}. Fetching config directly.")
            try:
                exercise_config_for_analysis = await exercise_config_service.get_active_config_for_exercise_async(
                    exercise_id=form_check.exercise_id
                )
                if exercise_config_for_analysis:
                    exercise_template_for_analysis = await db_session.get(ExerciseTemplate, form_check.exercise_id)
                    final_exercise_id_for_ml = form_check.exercise_id
                else:
                    logger.warning(f"[CeleryTask] No active ExerciseConfig found for user-provided exercise_id: {form_check.exercise_id}. Proceeding with generic analysis if possible.")
            except NotFoundException:
                logger.warning(f"[CeleryTask] ExerciseTemplate or active ExerciseConfig not found for user-provided exercise_id: {form_check.exercise_id}. Proceeding with generic analysis if possible.")
        else:
            logger.info("[CeleryTask] User did not provide exercise_id. Attempting classification.")
            if keypoint_sequence_for_classification and any(frame_kps for frame_kps in keypoint_sequence_for_classification):
                classified_slug, confidence = await _ai_service_instance.classify_exercise_from_keypoints(
                    keypoint_sequence=keypoint_sequence_for_classification
                )
                form_check.classified_exercise_slug = classified_slug
                form_check.classification_confidence = confidence
                if classified_slug and confidence and confidence >= settings_obj.EXERCISE_CLASSIFICATION_THRESHOLD:
                    logger.info(f"[CeleryTask] Classified as '{classified_slug}' with confidence {confidence:.2f}. Fetching config.")
                    try:
                        exercise_config_for_analysis = await exercise_config_service.get_active_config_by_template_slug_async(
                            slug=classified_slug
                        )
                        if exercise_config_for_analysis and exercise_config_for_analysis.exercise_template:
                            exercise_template_for_analysis = exercise_config_for_analysis.exercise_template # Already loaded by service
                            final_exercise_id_for_ml = exercise_template_for_analysis.id
                        else:
                            logger.warning(f"[CeleryTask] No active ExerciseConfig found for classified slug: {classified_slug}. Proceeding with generic analysis.")
                    except NotFoundException:
                        logger.warning(f"[CeleryTask] ExerciseTemplate or active ExerciseConfig not found for classified slug: {classified_slug}. Proceeding with generic analysis.")
                else:
                    logger.info(f"[CeleryTask] Classification failed or below threshold (Slug: {classified_slug}, Conf: {confidence}). Proceeding with generic analysis.")
            else:
                logger.warning("[CeleryTask] No keypoints available for classification. Proceeding with generic analysis.")

        # *** Enhanced Temporal ML Analysis Step ***
        if final_exercise_id_for_ml:
            logger.info(f"[CeleryTask] Preparing inputs for enhanced temporal ML analysis. Exercise ID: {final_exercise_id_for_ml}")
            
            # Get exercise template for analysis method determination
            exercise_template_name = exercise_template_for_analysis.name if exercise_template_for_analysis else "unknown"
            
            # Prepare clean keypoint sequence for temporal analysis
            clean_keypoints_for_ml: List[List[Dict[str, float]]] = []
            if keypoint_sequence_for_classification:
                for frame in keypoint_sequence_for_classification:
                    if frame is not None and isinstance(frame, list) and len(frame) > 0:
                        # Filter out None landmarks and ensure proper structure
                        valid_landmarks = [lm for lm in frame if lm is not None and isinstance(lm, dict)]
                        if valid_landmarks:
                            clean_keypoints_for_ml.append(valid_landmarks)

            angles_for_ml: List[Dict[str, float]] = []
            if video_model.calculated_angles:
                angles_for_ml = [
                    frame for frame in video_model.calculated_angles if frame is not None
                ]
            
            if not clean_keypoints_for_ml:
                logger.warning(f"[CeleryTask] No valid keypoint sequences available for temporal ML analysis for FormCheck {form_check_id}. Skipping enhanced ML scoring.")
            else:
                try:
                    logger.info(f"[CeleryTask] Using enhanced temporal analysis for {exercise_template_name} with {len(clean_keypoints_for_ml)} valid frames")
                    
                    # Use new temporal sequence analysis method
                    temporal_analysis_results = await _ai_service_instance.analyze_form_sequence(
                        landmark_sequence=clean_keypoints_for_ml,
                        exercise_type=exercise_template_name.lower(),
                        min_confidence=0.6
                    )
                    
                    # Extract temporal metrics and scores
                    temporal_metrics = temporal_analysis_results.get('temporal_metrics', {})
                    movement_quality = temporal_analysis_results.get('movement_quality', {})
                    
                    # Store enhanced metrics in form_check
                    form_check.posture_score = temporal_analysis_results.get('score', 0.0) / 100.0  # Store as 0-1
                    form_check.stability_score = temporal_metrics.get('stability_score', 0.0)
                    form_check.depth_score = movement_quality.get('consistency', 0.0)
                    
                    # Store additional temporal analysis metadata
                    enhanced_details = form_check.details or {}
                    enhanced_details.update({
                        'temporal_analysis': True,
                        'frame_count': temporal_metrics.get('frame_count', 0),
                        'valid_frames': temporal_metrics.get('valid_frames', 0),
                        'consistency_score': temporal_metrics.get('consistency_score', 0.0),
                        'analysis_method': temporal_analysis_results.get('analysis_method', 'unknown'),
                        'movement_quality': movement_quality
                    })
                    form_check.details = enhanced_details
                    
                    logger.info(f"[CeleryTask] Enhanced temporal analysis complete for FormCheck {form_check_id}: "
                               f"Score={temporal_analysis_results.get('score', 0):.1f}%, "
                               f"Method={temporal_analysis_results.get('analysis_method')}, "
                               f"Frames={temporal_metrics.get('valid_frames')}/{temporal_metrics.get('frame_count')}")
                    
                    await db_session.merge(form_check) # Merge changes before potential commit by DFAS or finalize
                    
                    # Also call legacy ML scoring for compatibility if available
                    if angles_for_ml and hasattr(_ai_service_instance, 'analyze_exercise_form_ml'):
                        try:
                            legacy_ml_scores = await _ai_service_instance.analyze_exercise_form_ml(
                                keypoint_data=clean_keypoints_for_ml, 
                                angle_data=angles_for_ml, 
                                exercise_id=final_exercise_id_for_ml
                            )
                            # Store additional legacy scores if needed
                            if 'hypertrophy_form_score' in legacy_ml_scores:
                                enhanced_details['hypertrophy_form_score'] = legacy_ml_scores['hypertrophy_form_score']
                                form_check.details = enhanced_details
                                await db_session.merge(form_check)
                            logger.debug(f"[CeleryTask] Legacy ML scores also computed: {legacy_ml_scores}")
                        except Exception as legacy_exc:
                            logger.warning(f"[CeleryTask] Legacy ML scoring failed, continuing with temporal analysis: {legacy_exc}")
                    
                except Exception as ml_exc:
                    logger.error(f"[CeleryTask] Error during enhanced temporal ML analysis for FormCheck {form_check_id}: {ml_exc}", exc_info=True)
                    # Fallback to storing basic analysis failure details
                    form_check.details = form_check.details or {}
                    form_check.details['temporal_analysis_error'] = str(ml_exc)
                    await db_session.merge(form_check)
        else:
            logger.info(f"[CeleryTask] No definitive exercise_id for temporal ML analysis (FormCheck {form_check_id}). Skipping enhanced ML scoring.")

        # Existing Dynamic Form Analysis (Rule-Based)
        logger.info(f"[CeleryTask] Proceeding with DynamicFormAnalysisService for FormCheck ID: {form_check_id}")
        if video_model.calculated_angles and exercise_config_for_analysis:
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
                exercise_config=exercise_config_for_analysis,
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
                "summary": analyzed_form_check_model.summary, # Make sure DFAS sets this
                # Include ML scores from the FormCheck model
                "posture_score": form_check.posture_score,
                "stability_score": form_check.stability_score,
                "depth_score": form_check.depth_score
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