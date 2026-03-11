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
from app.models.form_check import FormCheck
from app.models.exercise import ExerciseTemplate # MODIFIED
from app.models.exercise_config import ExerciseConfig
from app.models.video import Video as VideoModel # ADDED for type hint
from sqlalchemy import select, update as sa_update # ADDED for querying and updating
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
# Use as: async with get_async_session_for_celery() as session:
get_task_db_session = get_async_session_for_celery

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
        storage_service_instance = StorageService(app_settings=settings_obj)
    # Instantiate services that require DB session per task
    form_check_service = FormCheckService(
        db=db_session,
        settings=settings_obj,
        storage_service=storage_service_instance,
        ai_service=ai_service_instance, # This AIService might not be the one used for dynamic analysis
        cache_service=cache_service
    )
    exercise_config_service = ExerciseConfigService(db=db_session, settings=settings_obj)
    video_service = VideoService(db=db_session, app_settings=settings_obj, storage_service=storage_service_instance)
    
    dynamic_form_analysis_service = DynamicFormAnalysisService(
        db=db_session,
        settings=settings_obj,
        exercise_config_service=exercise_config_service,
        form_check_service=form_check_service,
        ai_service=ai_service_instance,
    )

    return (
        form_check_service, 
        storage_service_instance, 
        ai_service_instance, # Keep for potential other uses, or remove if DFAS fully replaces its role here
        exercise_config_service,
        video_service,
        dynamic_form_analysis_service
    )


# ---------------------------------------------------------------------------
# Phase 2 helpers: pose extraction inside the Celery task
# ---------------------------------------------------------------------------
async def _resolve_video_local_path(video_model, settings_obj) -> Optional[str]:
    """
    Convert the stored video URL / object_key back to a local filesystem path.
    LocalStorageProvider stores files under settings.UPLOAD_DIR keyed by the
    relative path that follows the base URL.
    """
    import os
    from app.core.storage import LocalStorageProvider
    try:
        provider = LocalStorageProvider()
        url = video_model.object_key or video_model.url or ""
        if not url:
            logger.warning(f"[PoseExtract] Video {video_model.id} has no url/object_key.")
            return None
        key = provider.get_key_from_url(url)
        local_path = os.path.join(provider.base_dir, key)
        if os.path.exists(local_path):
            logger.info(f"[PoseExtract] Resolved local path: {local_path}")
            return local_path
        # Fallback: maybe the URL itself is already a local path (e.g. stored as absolute)
        if os.path.exists(url):
            return url
        logger.warning(f"[PoseExtract] Local video file not found: {local_path} (key={key}, url={url})")
        return None
    except Exception as e:
        logger.error(f"[PoseExtract] Error resolving local path for Video {video_model.id}: {e}", exc_info=True)
        return None


async def _extract_pose_from_video(
    video_path: str,
    ai_service_instance,
    settings_obj,
) -> tuple:
    """
    Read all frames from video_path, run MediaPipe detect_pose on each,
    and return (pose_data_list, sequence_length, fps) where:
      - pose_data_list: List[Optional[List[Dict]]] — one entry per frame,
        None where no landmark was detected.
      - sequence_length: number of frames with valid landmark detection.
      - fps: frames-per-second reported by the video container (float).

    Runs synchronous OpenCV + MediaPipe in a thread pool via asyncio.to_thread.
    """
    import asyncio
    import cv2

    max_frames: int = getattr(settings_obj, "AI_MAX_FRAMES_PER_VIDEO_ANALYSIS", 300) or 300

    def _sync_extract(path: str, ai_svc) -> tuple:
        cap = cv2.VideoCapture(path)
        if not cap.isOpened():
            raise IOError(f"Cannot open video: {path}")
        video_fps: float = cap.get(cv2.CAP_PROP_FPS) or 30.0  # capture for duration gate
        pose_data: list = []
        valid_count = 0
        frame_idx = 0
        while cap.isOpened() and frame_idx < max_frames:
            ret, frame = cap.read()
            if not ret:
                break
            landmarks, confidence = ai_svc.detect_pose(frame)
            if landmarks:
                pose_data.append(landmarks)
                valid_count += 1
            else:
                pose_data.append(None)
            frame_idx += 1
        cap.release()
        logger.info(
            f"[PoseExtract] {path}: {frame_idx} frames read, "
            f"{valid_count} valid detections, fps={video_fps:.2f} "
            f"(complexity={ai_svc._pose_complexity_used}, fallback={ai_svc._pose_complexity_fallback})"
        )
        return pose_data, valid_count, video_fps

    pose_data, sequence_length, video_fps = await asyncio.to_thread(
        _sync_extract, video_path, ai_service_instance
    )
    return pose_data, sequence_length, video_fps


# Key body landmark indices for squat analysis (MediaPipe):
# shoulders (11,12), hips (23,24), knees (25,26), ankles (27,28)
_BODY_LANDMARK_INDICES_FOR_VIS_GATE = [11, 12, 23, 24, 25, 26, 27, 28]


def _check_body_landmark_visibility(
    pose_data: List[Optional[List[Optional[Dict[str, Any]]]]],
    min_body_vis: float = 0.3,
    min_visible_frame_ratio: float = 0.5,
) -> "tuple[bool, str]":
    """
    Visibility gate: verify key body landmarks have sufficient visibility.

    Returns (ok, reason). ok=True means body is sufficiently visible for squat analysis.

    This catches face-only videos where MediaPipe estimates body landmark positions
    with near-zero visibility scores (hips/knees/ankles not visible in frame).

    Args:
        pose_data: list of frames; each frame is list of landmark dicts {x,y,z,visibility}
        min_body_vis: minimum mean visibility required for a frame to count as "body visible"
        min_visible_frame_ratio: fraction of frames that must have sufficient body visibility
    """
    if not pose_data:
        return False, "no_pose_data"

    total_frames = 0
    visible_frames = 0

    for frame_landmarks in pose_data:
        if not frame_landmarks:
            continue
        total_frames += 1

        vis_scores = []
        for idx in _BODY_LANDMARK_INDICES_FOR_VIS_GATE:
            if idx < len(frame_landmarks) and isinstance(frame_landmarks[idx], dict):
                vis_scores.append(float(frame_landmarks[idx].get("visibility", 0.0)))

        if vis_scores and (sum(vis_scores) / len(vis_scores)) >= min_body_vis:
            visible_frames += 1

    if total_frames == 0:
        return False, "no_valid_frames"

    visible_ratio = visible_frames / total_frames
    if visible_ratio < min_visible_frame_ratio:
        return False, f"body_visibility_ratio_{visible_ratio:.2f}"

    return True, ""


def _apply_duration_gate(
    pv1_decision: str,
    pv1_confidence: float,
    quality_flags: list,
    n_frames: int,
    fps: float,
    is_squat: bool,
    gate_sec: float = 6.5,
) -> tuple:
    """
    Apply slow-cadence duration gate to a PostureV1 result.

    If a single-rep squat video exceeds gate_sec in duration (n_frames / fps),
    the decision is overridden to "uncertain" and "duration_too_long_single_rep"
    is appended to quality_flags.  This handles out-of-distribution cadences
    (e.g. 9-second slow-motion reps vs 3-6s training distribution) that cause
    false faults via inflated phase-variance features.

    gate_sec is 6.5 (not 6.0) to give a small safety margin above the 6-second
    product max.  Frontend auto-stop produces ~6.05–6.15 s blobs due to
    setInterval drift; the 0.5 s headroom prevents valid clips from being gated.

    Args:
        pv1_decision:   Current decision string from PostureV1 inference.
        pv1_confidence: Current confidence from inference.
        quality_flags:  Existing quality flag list (copied; not mutated).
        n_frames:       Number of frames in the keypoint sequence.
        fps:            Video frame rate (from container metadata).
        is_squat:       Whether the exercise is squat-like.
        gate_sec:       Duration threshold in seconds (default 6.5).

    Returns:
        (decision, confidence, quality_flags, rep_duration_sec)
    """
    rep_duration_sec = n_frames / max(fps, 1.0)
    flags = list(quality_flags)  # copy; never mutate caller's list

    if is_squat and rep_duration_sec > gate_sec and pv1_decision != "uncertain":
        pv1_decision = "uncertain"
        pv1_confidence = 0.0
        flags.append("duration_too_long_single_rep")

    return pv1_decision, pv1_confidence, flags, rep_duration_sec


# Hip/knee landmark indices for motion gate
_HIP_INDICES = [23, 24]   # left_hip, right_hip (MediaPipe)
_KNEE_INDICES = [25, 26]  # left_knee, right_knee (MediaPipe)


def _check_minimum_motion(
    pose_data: List[Optional[List[Optional[Dict[str, Any]]]]],
    min_hip_y_range: float = 0.05,
    min_knee_y_range: float = 0.05,
) -> "tuple[bool, str]":
    """
    Motion gate: ensure meaningful hip/knee movement exists in the sequence.

    Uses landmark y-coordinate range as a proxy for joint excursion.
    MediaPipe y is normalised 0-1 (image fraction). A 90° squat depth
    produces ~0.10-0.25 y-range on a full-body frame; a static stance
    produces ~0.00-0.02. Threshold of 0.05 catches truly static clips.

    Returns (ok, reason). ok=True means meaningful movement was detected.
    """
    if not pose_data:
        return False, "no_pose_data"

    hip_y: List[float] = []
    knee_y: List[float] = []

    for frame_landmarks in pose_data:
        if not frame_landmarks:
            continue
        for idx in _HIP_INDICES:
            if idx < len(frame_landmarks) and isinstance(frame_landmarks[idx], dict):
                hip_y.append(float(frame_landmarks[idx].get("y", 0.0)))
        for idx in _KNEE_INDICES:
            if idx < len(frame_landmarks) and isinstance(frame_landmarks[idx], dict):
                knee_y.append(float(frame_landmarks[idx].get("y", 0.0)))

    if not hip_y or not knee_y:
        return False, "no_hip_knee_landmarks"

    hip_range = max(hip_y) - min(hip_y)
    knee_range = max(knee_y) - min(knee_y)

    if hip_range < min_hip_y_range and knee_range < min_knee_y_range:
        return (
            False,
            f"no_significant_movement_hip_{hip_range:.3f}_knee_{knee_range:.3f}",
        )

    return True, ""


# Explicitly name the task to ensure consistent registration
@celery_app.task(name="app.tasks.analysis_tasks.process_form_check", bind=True, max_retries=3, default_retry_delay=300)
def process_form_check_task(self, video_id_str: str, form_check_id_str: str):
    """Sync wrapper that runs the async task via asyncio.run()."""
    import asyncio
    return asyncio.run(_process_form_check_task_async(self, video_id_str, form_check_id_str))

async def _process_form_check_task_async(self, video_id_str: str, form_check_id_str: str):
    """
    Celery task to process a form check analysis for a given video and form_check ID.
    Uses DynamicFormAnalysisService for rule-based evaluation.
    """
    form_check_id = UUID(form_check_id_str)
    video_id = UUID(video_id_str) # Convert video_id_str to UUID
    logger.info(f"[CeleryTask] Starting analysis for FormCheck ID: {form_check_id}, Video ID: {video_id}")

    # Dispose the async engine connection pool before acquiring a session.
    # Each asyncio.run() call creates a new event loop; connections held in the
    # QueuePool from the previous (now-closed) loop are stale for asyncpg.
    # Disposing forces fresh connections in the current event loop.
    from app.core.database import async_engine as _async_engine
    try:
        await _async_engine.dispose()
    except Exception as _dispose_exc:
        logger.warning(f"[CeleryTask] async_engine.dispose() warning (non-fatal): {_dispose_exc}")

    settings_obj = get_settings()
    db_session: Optional[AsyncSession] = None
    form_check_service: Optional[FormCheckService] = None
    
    analysis_output_for_finalize: Dict[str, Any] = {} # Renamed to avoid confusion with model
    final_status: FormCheckStatus = FormCheckStatus.FAILED
    analyzed_form_check_model: Optional[FormCheck] = None # To store the result from DFAS

    try:
        _session_cm = get_task_db_session()
        db_session = await _session_cm.__aenter__()
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

        # Fetch the Video object (Phase 3 fix: use base get_async, not missing method)
        video_model = await video_service.get_async(id=video_id)
        if not video_model:
            logger.error(f"[CeleryTask] Video ID {video_id} not found for FormCheck {form_check_id}")
            analysis_output_for_finalize = {"error_message": "Associated Video not found for analysis."}
            raise ValueError("Video not found for analysis.")

        # *** Phase 2: Pose Extraction ***
        # Generate pose_data if not already present (freshly uploaded videos have no pose_data yet).
        # This is the core pipeline gap fix: the task itself runs MediaPipe on the stored video file.
        if not (video_model.pose_data and isinstance(video_model.pose_data, list)):
            logger.info(f"[CeleryTask] pose_data missing for Video {video_id} — running pose extraction now.")
            try:
                video_local_path = await _resolve_video_local_path(video_model, settings_obj)
                if video_local_path:
                    raw_pose, sequence_length, video_fps = await _extract_pose_from_video(
                        video_local_path, _ai_service_instance, settings_obj
                    )
                    if raw_pose:
                        video_model.raw_pose_data = raw_pose
                        video_model.pose_data = raw_pose  # smoothed == raw for now
                        # Store fps for duration gate (only set if not already populated)
                        if video_fps and not video_model.fps:
                            video_model.fps = round(float(video_fps), 3)
                        await db_session.merge(video_model)
                        await db_session.commit()
                        logger.info(
                            f"[CeleryTask] Pose extraction complete for Video {video_id}: "
                            f"{sequence_length} real frames, {len(raw_pose)} total slots, fps={video_fps:.2f}."
                        )
                    else:
                        logger.warning(f"[CeleryTask] Pose extraction yielded no landmarks for Video {video_id}.")
                else:
                    logger.warning(f"[CeleryTask] Could not resolve local path for Video {video_id} — skipping pose extraction.")
            except Exception as pose_exc:
                logger.error(f"[CeleryTask] Pose extraction failed for Video {video_id}: {pose_exc}", exc_info=True)
                # Non-fatal: PostureV1 quality gate will set decision=uncertain if frames insufficient.

        # Prioritize pose_data (smoothed), fall back to raw_pose_data
        keypoint_sequence_for_classification: Optional[List[List[Optional[Dict[str, float]]]]] = None
        if video_model.pose_data and isinstance(video_model.pose_data, list):
            keypoint_sequence_for_classification = video_model.pose_data
            logger.info(f"[CeleryTask] Using video_model.pose_data for classification. Frames: {len(keypoint_sequence_for_classification)}")
        elif video_model.raw_pose_data and isinstance(video_model.raw_pose_data, list):
            keypoint_sequence_for_classification = video_model.raw_pose_data
            logger.info(f"[CeleryTask] Using video_model.raw_pose_data for classification. Frames: {len(keypoint_sequence_for_classification)}")
        else:
            logger.warning(
                f"[CeleryTask] No pose_data available for Video {video_id} after extraction attempt. "
                f"PostureV1 will mark as uncertain."
            )
        
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
                # Always load the ExerciseTemplate so exercise type is known for routing (e.g., _is_squat)
                # even when no active ExerciseConfig exists.
                exercise_template_for_analysis = await db_session.get(ExerciseTemplate, form_check.exercise_id)
                if exercise_config_for_analysis and exercise_template_for_analysis:
                    final_exercise_id_for_ml = form_check.exercise_id
                elif exercise_template_for_analysis:
                    logger.info(
                        f"[CeleryTask] No active ExerciseConfig for exercise '{exercise_template_for_analysis.name}' "
                        f"— exercise type known, using for PostureV1 routing only."
                    )
                else:
                    logger.warning(f"[CeleryTask] No ExerciseTemplate found for exercise_id: {form_check.exercise_id}. Proceeding with generic analysis.")
            except NotFoundException:
                logger.warning(f"[CeleryTask] ExerciseTemplate or active ExerciseConfig not found for user-provided exercise_id: {form_check.exercise_id}. Proceeding with generic analysis if possible.")
        else:
            # All submissions are squats (enforced at the endpoint).
            # exercise_id should always be present — log a warning if not.
            logger.warning(
                "[CeleryTask] No exercise_id on FormCheck %s — exercise type from video metadata: %r",
                form_check_id, getattr(video_model, 'exercise_type', None),
            )

        # Determine exercise type from available sources — used by the legacy
        # temporal ML guard below AND by the PostureV1 routing block.
        # Priority: ExerciseTemplate name → AI classified slug → video metadata.
        _exercise_slug = (
            (exercise_template_for_analysis.name.lower() if exercise_template_for_analysis else None)
            or (form_check.classified_exercise_slug or "").lower()
            or (video_model.exercise_type or "").lower()
        ).strip()
        _is_squat = "squat" in _exercise_slug if _exercise_slug else False
        logger.info(
            "[CeleryTask] Exercise routing for FormCheck %s: slug=%r is_squat=%s",
            form_check_id, _exercise_slug, _is_squat,
        )

        # *** Legacy temporal ML — experimental, non-squat path only ***
        # PostureV1 is the PRIMARY and AUTHORITATIVE model for squats.
        # This block MUST NOT write to form_check.posture_score when _is_squat
        # is True, because PostureV1 will set it (or keep it NULL for uncertain).
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
                    
                    # analyze_form_sequence returns score on a 0–100 scale.
                    _temporal_score = temporal_analysis_results.get('score', 0.0)

                    # For squats PostureV1 is the SOLE writer of posture_score.
                    # Storing temporal score in results["temporal_ml"] instead of
                    # form_check.posture_score prevents a stale fractional value
                    # from leaking when PostureV1 returns decision="uncertain".
                    if _is_squat:
                        _t_results = form_check.results or {}
                        _t_results["temporal_ml"] = {
                            "score": _temporal_score,
                            "analysis_method": temporal_analysis_results.get("analysis_method", "unknown"),
                        }
                        form_check.results = _t_results
                        logger.info(
                            "[CeleryTask] Squat: temporal score=%.1f stored in results.temporal_ml "
                            "(posture_score left for PostureV1) — FormCheck %s",
                            _temporal_score, form_check_id,
                        )
                    else:
                        # Non-squat: legacy model drives posture_score.  Score is 0–100.
                        form_check.posture_score = _temporal_score

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

        # *** Non-squat bypass guard (belt-and-suspenders) ***
        # All submissions should be squats (enforced at the endpoint), but if
        # somehow a non-squat reaches here, mark it uncertain and skip inference.
        if not _is_squat:
            logger.error(
                "[CeleryTask] Non-squat type %r in analysis task for FormCheck %s. "
                "Setting decision=uncertain and skipping inference.",
                _exercise_slug, form_check_id,
            )
            analysis_output_for_finalize["score"] = None
            analysis_output_for_finalize["decision"] = "uncertain"

        # *** PostureV1 CNN-LSTM Inference Step (squat only) ***
        # _is_squat / _exercise_slug already computed above (before legacy temporal block).
        # PostureV1 is the SOLE writer of form_check.posture_score for squats.
        _run_posture_v1 = getattr(settings_obj, 'USE_POSTURE_V1', True)

        if _run_posture_v1 and _is_squat and keypoint_sequence_for_classification:
            try:
                from app.ml.posture_v1.loader import PostureV1TorchLoader
                from app.ml.posture_v1.scoring import compute_full_scores
                posture_v1_loader = PostureV1TorchLoader(settings_obj)

                # Apply named threshold mode if set in form_check details
                _threshold_mode = (form_check.details or {}).get("threshold_mode")
                if _threshold_mode:
                    posture_v1_loader.set_threshold_mode(_threshold_mode)

                # Determine shadow vs active mode
                _posture_v1_mode = (form_check.details or {}).get("posture_v1_mode", "active")
                _is_shadow = _posture_v1_mode == "shadow"
                if _is_shadow:
                    logger.info(f"[CeleryTask] PostureV1 running in SHADOW mode — scores not applied (FormCheck {form_check_id})")

                # --- Body visibility gate ---
                # Rejects face-only videos where body landmarks are hallucinated
                # by MediaPipe with near-zero visibility scores.
                _vis_ok, _vis_reason = _check_body_landmark_visibility(
                    keypoint_sequence_for_classification
                )
                if not _vis_ok:
                    logger.warning(
                        "[CeleryTask] Body visibility gate FAILED for FormCheck %s (%s) "
                        "— skipping PostureV1 inference, marking as uncertain.",
                        form_check_id, _vis_reason,
                    )
                    posture_v1_result = {
                        "decision": "uncertain",
                        "prob_fault": 0.5,
                        "confidence": 0.0,
                        "threshold": getattr(posture_v1_loader, "_fault_threshold", 0.525),
                        "quality_flags": [f"body_landmark_{_vis_reason}"],
                        "quality_ok": False,
                        "preprocessing": {
                            "original_frames": len(keypoint_sequence_for_classification),
                            "valid_frames": 0,
                            "sequence_length": 0,
                        },
                        "reason": "body_landmarks_not_visible",
                        "_raw_features_151d": None,
                    }
                else:
                    # --- Motion gate: ensure meaningful hip/knee movement ---
                    _motion_ok, _motion_reason = _check_minimum_motion(
                        keypoint_sequence_for_classification
                    )
                    if not _motion_ok:
                        logger.warning(
                            "[CeleryTask] Motion gate FAILED for FormCheck %s (%s) "
                            "— skipping inference, marking as uncertain.",
                            form_check_id, _motion_reason,
                        )
                        posture_v1_result = {
                            "decision": "uncertain",
                            "prob_fault": 0.5,
                            "confidence": 0.0,
                            "threshold": getattr(posture_v1_loader, "_fault_threshold", 0.525),
                            "quality_flags": [f"motion_{_motion_reason}"],
                            "quality_ok": False,
                            "preprocessing": {
                                "original_frames": len(keypoint_sequence_for_classification),
                                "valid_frames": 0,
                                "sequence_length": 0,
                            },
                            "reason": "no_significant_movement",
                            "_raw_features_151d": None,
                        }
                    else:
                        posture_v1_result = posture_v1_loader.predict_posture(
                            keypoint_sequence_for_classification
                        )

                logger.info(
                    "[CeleryTask] PostureV1 result for FormCheck %s: "
                    "decision=%s prob_fault=%.4f confidence=%.3f quality_ok=%s latency=%.1fms mode=%s",
                    form_check_id,
                    posture_v1_result.get("decision"),
                    posture_v1_result.get("prob_fault", 0.0),
                    posture_v1_result.get("confidence", 0.0),
                    posture_v1_result.get("quality_ok"),
                    posture_v1_result.get("latency_ms", 0.0),
                    _posture_v1_mode,
                )

                pv1_prob = posture_v1_result.get("prob_fault", 0.5)
                pv1_confidence = posture_v1_result.get("confidence", 0.0)
                pv1_decision = posture_v1_result.get("decision", "uncertain")

                # ── Duration gate: slow-cadence single-rep detection ──────────────────
                # Reps > 6s inflate phase-variance features, causing false faults.
                # Apply before score write so uncertain videos don't overwrite DB scores.
                _fps_used = video_model.fps or 30.0
                _gate_sec = getattr(settings_obj, "POSTURE_V1_MAX_REP_DURATION_SEC", 6.5)
                pv1_decision, pv1_confidence, _gated_flags, _rep_duration_sec = _apply_duration_gate(
                    pv1_decision=pv1_decision,
                    pv1_confidence=pv1_confidence,
                    quality_flags=posture_v1_result.get("quality_flags") or [],
                    n_frames=len(keypoint_sequence_for_classification),
                    fps=_fps_used,
                    is_squat=_is_squat,
                    gate_sec=_gate_sec,
                )
                if _gated_flags != (posture_v1_result.get("quality_flags") or []):
                    logger.info(
                        "[PostureV1] Duration gate triggered for FormCheck %s: "
                        "%.1fs > %.1fs (fps=%.1f) — decision overridden to uncertain",
                        form_check_id, _rep_duration_sec, _gate_sec, _fps_used,
                    )
                posture_v1_result["quality_flags"] = _gated_flags

                # Compute full scoring with component scores from real features
                raw_features = posture_v1_result.pop("_raw_features_151d", None)
                _component_visibility = posture_v1_result.pop("_component_visibility", None)
                scaler_mean, scaler_std = posture_v1_loader.get_scaler_params()
                scoring = compute_full_scores(
                    prob_fault=pv1_prob,
                    features_151d=raw_features,
                    scaler_mean=scaler_mean,
                    scaler_std=scaler_std,
                    threshold=posture_v1_result.get("threshold", 0.525),
                    model_version=posture_v1_result.get("model_version", "posture_v1"),
                    component_visibility=_component_visibility,
                )

                # Only write posture_score/confidence_score in active mode
                if not _is_shadow and pv1_decision != "uncertain":
                    form_check.posture_score = scoring["posture_score"]
                    form_check.confidence_score = round(pv1_confidence, 4)

                # Build result payload
                _pv1_result_payload = {
                    "model": {
                        "name": "posture_v1",
                        "version": posture_v1_result.get("model_version"),
                        "threshold": posture_v1_result.get("threshold"),
                    },
                    "exercise_type": "squat",
                    "prob_fault": pv1_prob,
                    "decision": pv1_decision,
                    "confidence": pv1_confidence,
                    "posture_score": scoring["posture_score"],
                    "score_band": scoring.get("score_band"),
                    "component_scores": scoring.get("component_scores", {}),
                    "named_scores": scoring.get("named_scores", {}),
                    "top_signals": scoring.get("top_signals", []),
                    # Weighted-average scoring metadata (Score Integrity Fix)
                    "score_exclusions": scoring.get("score_exclusions", []),
                    "weights_used": scoring.get("weights_used", {}),
                    "valid_component_count": scoring.get("valid_component_count", 0),
                    # Canonical pipeline fields (mirrors pipeline.py output)
                    "feature_insights": [
                        s["name"] for s in scoring.get("top_signals", [])
                    ],
                    "components": {
                        "torso_stability": (scoring.get("named_scores") or {}).get("torso_stability_score"),
                        "knee_symmetry": (scoring.get("named_scores") or {}).get("knee_symmetry_score"),
                        "bottom_control": (scoring.get("named_scores") or {}).get("bottom_control_score"),
                        "forward_lean": (scoring.get("named_scores") or {}).get("forward_lean_score"),
                    },
                    "quality": {
                        "quality_flags": posture_v1_result.get("quality_flags", []),
                        "quality_ok": posture_v1_result.get("quality_ok"),
                    },
                    "component_visibility": _component_visibility,
                    "preprocessing": {
                        **posture_v1_result.get("preprocessing", {}),
                        "model_complexity": _ai_service_instance._pose_complexity_used,
                        "pose_complexity_fallback": _ai_service_instance._pose_complexity_fallback,
                        "duration_sec": round(_rep_duration_sec, 2),
                        "fps": round(_fps_used, 2),
                    },
                    "feature_version": posture_v1_result.get("feature_version"),
                    "latency_ms": posture_v1_result.get("latency_ms"),
                }

                # SCORE_AUDIT_LOG: set SCORE_AUDIT_LOG=true in .env to enable.
                # Remove this block before GA.
                import os as _os
                if _os.environ.get("SCORE_AUDIT_LOG") == "true":
                    logger.info(
                        "[SCORE_AUDIT] form_check_id=%s model_score=%s named_scores=%s "
                        "posture_score=%s weights_used=%s exclusions=%s",
                        form_check_id,
                        scoring.get("model_score"),
                        scoring.get("named_scores"),
                        scoring.get("posture_score"),
                        scoring.get("weights_used"),
                        scoring.get("score_exclusions"),
                    )

                # --- Highlight frame injection (best-effort, never fails the task) ---
                try:
                    from app.ml.posture_v1.highlight import select_highlight_frame
                    _highlight = select_highlight_frame(
                        keypoint_sequence_for_classification,
                        fps=_fps_used,
                    )
                    if _highlight is not None:
                        _pv1_result_payload["highlight_frame"] = {
                            "frame_index": _highlight.frame_index,
                            "timestamp_sec": _highlight.timestamp_sec,
                            "knee_angle_left": _highlight.knee_angle_left,
                            "knee_angle_right": _highlight.knee_angle_right,
                            "hip_angle": _highlight.hip_angle,
                            "depth_proxy": _highlight.depth_proxy,
                        }
                except Exception as _hf_err:
                    logger.warning("[CeleryTask] highlight_frame extraction failed: %s", _hf_err)

                # --- Calibrated confidence (best-effort) ---
                try:
                    from app.ml.posture_v1.scoring import compute_calibrated_confidence
                    import numpy as _np_cc
                    _vis_ratio = float(_np_cc.mean(list(_component_visibility.values()))) \
                        if _component_visibility else 1.0
                    _outlier_z3 = posture_v1_result.get("outlier_counts", {}).get("count_z3", 0)
                    _seq_len = posture_v1_result.get("preprocessing", {}).get("sequence_length", 1) or 1
                    _temporal = float(_np_cc.clip(1.0 - _outlier_z3 / _seq_len, 0.0, 1.0))
                    _cal_conf = compute_calibrated_confidence(pv1_prob, _vis_ratio, _temporal)
                    _pv1_result_payload["calibrated_confidence"] = _cal_conf
                except Exception as _cc_err:
                    logger.warning("[CeleryTask] calibrated_confidence failed: %s", _cc_err)

                # --- Delta engine (best-effort) ---
                try:
                    _fcs = FormCheckService(
                        db=db_session,
                        settings=settings_obj,
                        storage_service=_shared_storage_service,
                        ai_service=_ai_service_instance,
                    )
                    _delta_slug = _exercise_slug or form_check.exercise_type or ""
                    _cur_score = scoring["posture_score"]

                    _prev = await _fcs.get_previous_completed_form_check(
                        form_check.user_id, _delta_slug, form_check_id, db_session
                    )
                    _best_prev = await _fcs.get_user_best_score(
                        form_check.user_id, _delta_slug, form_check_id, db_session
                    )

                    if _prev is None:
                        _pv1_result_payload["delta"] = {"baseline_session": True}
                    else:
                        _prev_pv1 = (_prev.results or {}).get("posture_v1", {})
                        _prev_score = _prev.posture_score
                        _prev_named = _prev_pv1.get("named_scores", {})
                        _cur_named = _pv1_result_payload.get("named_scores", {})

                        def _named_delta(key):
                            c, p = _cur_named.get(key), _prev_named.get(key)
                            return round(c - p, 1) if c is not None and p is not None else None

                        _pv1_result_payload["delta"] = {
                            "baseline_session": False,
                            "overall_score_delta": round(_cur_score - _prev_score, 1) if _prev_score is not None and _cur_score is not None else None,
                            "posture_delta": round(_cur_score - _prev_score, 1) if _prev_score is not None and _cur_score is not None else None,
                            "torso_stability_delta": _named_delta("torso_stability_score"),
                            "knee_symmetry_delta": _named_delta("knee_symmetry_score"),
                            "bottom_control_delta": _named_delta("bottom_control_score"),
                            "forward_lean_delta": _named_delta("forward_lean_score"),
                            "personal_best": bool(
                                _cur_score is not None and (_best_prev is None or _cur_score > _best_prev)
                            ),
                        }
                except Exception as _delta_err:
                    logger.warning("[CeleryTask] delta engine failed: %s", _delta_err)

                # --- Level system (best-effort) ---
                try:
                    from app.ml.posture_v1.scoring import compute_level
                    _pv1_result_payload["level"] = compute_level(scoring["posture_score"])
                except Exception as _lvl_err:
                    logger.warning("[CeleryTask] level computation failed: %s", _lvl_err)

                # --- Primary limiter tracking (best-effort) ---
                try:
                    _named_scores = _pv1_result_payload.get("named_scores", {})
                    _valid_scores = {k: v for k, v in _named_scores.items() if v is not None}
                    if _valid_scores:
                        _primary_limiter_key = min(_valid_scores, key=_valid_scores.get)
                        # Query last 2 prior completed sessions for same exercise
                        _limiter_query = (
                            select(FormCheck)
                            .where(
                                FormCheck.user_id == form_check.user_id,
                                FormCheck.status == FormCheckStatus.COMPLETED,
                                FormCheck.id != form_check_id,
                                (FormCheck.exercise_type == (_exercise_slug or "")) |
                                (FormCheck.classified_exercise_slug == (_exercise_slug or "")),
                            )
                            .order_by(FormCheck.created_at.desc())
                            .limit(2)
                        )
                        _prev_checks = (await db_session.execute(_limiter_query)).scalars().all()
                        _consecutive = 0
                        for _pc in _prev_checks:
                            _pc_named = (_pc.results or {}).get("posture_v1", {}).get("named_scores", {})
                            _pc_valid = {k: v for k, v in _pc_named.items() if v is not None}
                            if _pc_valid and min(_pc_valid, key=_pc_valid.get) == _primary_limiter_key:
                                _consecutive += 1
                        _pv1_result_payload["primary_limiter"] = {
                            "key": _primary_limiter_key,
                            "persistent_limiter": _consecutive >= 2,
                        }
                except Exception as _lim_err:
                    logger.warning("[CeleryTask] limiter tracking failed: %s", _lim_err)

                # --- Coaching feedback generation (best-effort, active mode only) ---
                if not _is_shadow and pv1_decision != "uncertain":
                    try:
                        from app.services.rag_feedback_service import rag_feedback_service as _rag_svc, FeedbackContext
                        if _rag_svc.is_available():
                            _fb_exercise_name = (
                                exercise_template_for_analysis.name
                                if exercise_template_for_analysis
                                else (_exercise_slug or "squat").replace("_", " ").title()
                            )
                            _named_sc = scoring.get("named_scores", {}) or {}
                            _fb_form_scores = {"posture_score": scoring["posture_score"]}
                            _fb_form_scores.update({k: v for k, v in _named_sc.items() if v is not None})
                            _fb_faults = [k for k, v in _named_sc.items() if v is not None and v < 70]
                            if pv1_decision == "fault":
                                _fb_faults.append("posture_fault")
                            _level_to_ul = {
                                "Beginner": "beginner", "Developing": "beginner",
                                "Solid": "intermediate", "Advanced": "intermediate", "Elite": "advanced",
                            }
                            _fb_user_level = _level_to_ul.get(_pv1_result_payload.get("level", "Developing"), "intermediate")
                            _fb_ctx = FeedbackContext(
                                exercise_name=_fb_exercise_name,
                                exercise_type="squat",
                                form_scores=_fb_form_scores,
                                identified_faults=_fb_faults,
                                user_level=_fb_user_level,
                            )
                            _feedback_text = await _rag_svc.generate_feedback(_fb_ctx)
                            if _feedback_text:
                                _pv1_result_payload["feedback_text"] = _feedback_text
                            logger.info("[CeleryTask] Coaching feedback generated for FormCheck %s", form_check_id)
                        else:
                            logger.debug("[CeleryTask] RAG service unavailable — skipping coaching feedback")
                    except Exception as _fb_exc:
                        logger.warning("[CeleryTask] Coaching feedback generation failed (non-fatal): %s", _fb_exc)

                # Store under different key for shadow mode
                existing_results = form_check.results or {}
                _results_key = "posture_v1_shadow" if _is_shadow else "posture_v1"
                existing_results[_results_key] = _pv1_result_payload
                form_check.results = existing_results

                await db_session.merge(form_check)
                logger.info(f"[CeleryTask] PostureV1 scores stored for FormCheck {form_check_id} (key={_results_key})")
                # Mark success so finalize sets COMPLETED even if DFAS is skipped
                if not _is_shadow and pv1_decision != "uncertain":
                    final_status = FormCheckStatus.COMPLETED

                # --- Telemetry write (best-effort) ---
                try:
                    from app.models.telemetry import PostureV1InferenceLog
                    _preprocessing = posture_v1_result.get("preprocessing", {})
                    _orig_frames = _preprocessing.get("original_frames", 0)
                    _valid_frames = _preprocessing.get("valid_frame_count", _preprocessing.get("sequence_length", 0))
                    _missing_ratio = round(1.0 - (_valid_frames / _orig_frames), 4) if _orig_frames > 0 else None
                    _outlier_counts = posture_v1_result.get("outlier_counts", {})

                    telemetry_row = PostureV1InferenceLog(
                        form_check_id=form_check_id,
                        video_id=video_id,
                        decision=pv1_decision,
                        prob_fault=pv1_prob,
                        confidence=pv1_confidence,
                        threshold=posture_v1_result.get("threshold"),
                        threshold_mode=_threshold_mode,
                        posture_v1_mode=_posture_v1_mode,
                        sequence_length=_preprocessing.get("sequence_length"),
                        missing_ratio=_missing_ratio,
                        outlier_z_gt3=_outlier_counts.get("count_z3"),
                        outlier_z_gt6=_outlier_counts.get("count_z6"),
                        angle_validity=posture_v1_result.get("angle_validity"),
                        gate_flags=posture_v1_result.get("quality_flags"),
                        top_signals=scoring.get("top_signals"),
                        named_scores=scoring.get("named_scores"),
                        model_version=posture_v1_result.get("model_version"),
                        latency_ms=posture_v1_result.get("latency_ms"),
                    )
                    db_session.add(telemetry_row)
                    logger.info(
                        "[PostureV1 Telemetry] form_check_id=%s decision=%s prob_fault=%.4f "
                        "confidence=%.3f threshold=%s latency_ms=%.1f gate_flags=%s mode=%s",
                        form_check_id, pv1_decision, pv1_prob, pv1_confidence,
                        posture_v1_result.get("threshold"), posture_v1_result.get("latency_ms", 0.0),
                        posture_v1_result.get("quality_flags"), _posture_v1_mode,
                    )
                except Exception as telem_exc:
                    logger.warning(f"[PostureV1 Telemetry] Failed to write telemetry row: {telem_exc}")

            except Exception as pv1_exc:
                logger.error(
                    f"[CeleryTask] PostureV1 inference failed for FormCheck {form_check_id}: {pv1_exc}",
                    exc_info=True,
                )
                existing_results = form_check.results or {}
                existing_results["posture_v1_error"] = str(pv1_exc)
                form_check.results = existing_results
                await db_session.merge(form_check)

                # Error telemetry (best-effort)
                try:
                    from app.models.telemetry import PostureV1InferenceLog
                    error_row = PostureV1InferenceLog(
                        form_check_id=form_check_id,
                        video_id=video_id,
                        decision="error",
                        error=str(pv1_exc),
                        posture_v1_mode=(form_check.details or {}).get("posture_v1_mode", "active"),
                    )
                    db_session.add(error_row)
                except Exception as telem_exc:
                    logger.warning(f"[PostureV1 Telemetry] Failed to write error telemetry: {telem_exc}")

        elif _run_posture_v1 and not _is_squat and keypoint_sequence_for_classification:
            logger.info(f"[CeleryTask] Exercise '{_exercise_slug}' is not squat — skipping PostureV1 (FormCheck {form_check_id})")
            existing_results = form_check.results or {}
            existing_results["posture_v1"] = {"status": "not_supported", "exercise_type": _exercise_slug, "reason": "posture_v1 only supports squat"}
            form_check.results = existing_results
            await db_session.merge(form_check)
        elif not _run_posture_v1:
            logger.debug("[CeleryTask] PostureV1 disabled via USE_POSTURE_V1=false")

        # Phase 4 (Option A): DFAS requires calculated_angles — skip gracefully when absent.
        # PostureV1 results are already written to form_check.results above; they are not lost.
        # DFAS signature is analyze_form_dynamically(self, video: Video) and does NOT accept
        # exercise_config or initial_form_check kwargs, so we call it only if angles exist.
        if video_model.calculated_angles and exercise_config_for_analysis:
            logger.info(f"[CeleryTask] Running DynamicFormAnalysisService for FormCheck {form_check_id}")
            try:
                analyzed_form_check_model = await dynamic_form_analysis_service.analyze_form_dynamically(
                    video=video_model
                )
                if analyzed_form_check_model:
                    final_status = analyzed_form_check_model.status
                    feedback_messages_list = []
                    feedback_structured_list = []
                    if getattr(analyzed_form_check_model, "feedback_items", None):
                        for item in analyzed_form_check_model.feedback_items:
                            feedback_messages_list.append(item.message or "N/A")
                            feedback_structured_list.append({
                                "type": item.type.value if item.type else FeedbackType.GENERAL.value,
                                "message": item.message or "N/A",
                                "timestamp": item.timestamp if item.timestamp is not None else 0.0,
                                "severity": item.severity.value if item.severity else FeedbackSeverity.INFO.value,
                                "suggestions": item.suggestions or [],
                                "details": item.details or {},
                            })
                    analysis_output_for_finalize = {
                        "score": analyzed_form_check_model.score or 0.0,
                        "feedback": feedback_messages_list,
                        "risk_level": (analyzed_form_check_model.details or {}).get("risk_level", "low"),
                        "feedback_structured": feedback_structured_list,
                        "error_message": getattr(analyzed_form_check_model, "error_details", None),
                        "summary": getattr(analyzed_form_check_model, "summary", None),
                        "posture_score": form_check.posture_score,
                        "stability_score": form_check.stability_score,
                        "depth_score": form_check.depth_score,
                    }
                    logger.info(f"[CeleryTask] DFAS complete for FormCheck {form_check_id}.")
                else:
                    logger.warning(f"[CeleryTask] DFAS returned None for FormCheck {form_check_id} — using PostureV1 results only.")
            except Exception as dfas_exc:
                logger.error(f"[CeleryTask] DFAS failed for FormCheck {form_check_id}: {dfas_exc}", exc_info=True)
        else:
            logger.info(
                f"[CeleryTask] Skipping DFAS for FormCheck {form_check_id}: "
                f"calculated_angles={bool(video_model.calculated_angles)}, "
                f"exercise_config={bool(exercise_config_for_analysis)}. "
                f"PostureV1 results already stored."
            )

        # If we reach here without analysis_output_for_finalize populated by DFAS,
        # build a minimal payload from PostureV1 data so finalize can mark COMPLETED.
        if not analysis_output_for_finalize and (form_check.results or form_check.posture_score is not None):
            pv1_data = (form_check.results or {}).get("posture_v1", {})
            final_status = FormCheckStatus.COMPLETED
            analysis_output_for_finalize = {
                "score": form_check.posture_score,  # None for uncertain results → stored as NULL, frontend shows "—"
                "feedback": [],
                "risk_level": "low",
                "feedback_structured": [],
                "posture_score": form_check.posture_score,
                "confidence_score": form_check.confidence_score,
                "posture_v1_decision": pv1_data.get("decision"),
            }

    except ValueError as ve: # Catch specific value errors from our checks
        logger.error(f"[CeleryTask] ValueError during FormCheck {form_check_id} analysis: {ve}", exc_info=True)
        final_status = FormCheckStatus.FAILED
        if "error_message" not in analysis_output_for_finalize or not analysis_output_for_finalize["error_message"]:
            analysis_output_for_finalize["error_message"] = str(ve)
    except Exception as e:
        logger.error(f"[CeleryTask] General error during FormCheck {form_check_id} analysis: {type(e).__name__}: {e}", exc_info=True)
        final_status = FormCheckStatus.FAILED
        if "error_message" not in analysis_output_for_finalize or not analysis_output_for_finalize["error_message"]:
            analysis_output_for_finalize["error_message"] = f"{type(e).__name__}: {str(e)}"
    finally:
        if form_check_service and form_check_id: # Ensure form_check_id is available
            try:
                logger.info(f"[CeleryTask] Finalizing FormCheck {form_check_id} with status {final_status.value}")
                # Ensure all necessary fields for finalize are in analysis_output_for_finalize
                if "score" not in analysis_output_for_finalize: analysis_output_for_finalize["score"] = None
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
            # Raw DB fallback: if form_check_service failed to initialize but we still have a
            # db_session and form_check_id, use a direct UPDATE so the form check doesn't stay
            # stuck at PENDING forever (which would block the user with no error message).
            if form_check_id and db_session:
                try:
                    err_msg = analysis_output_for_finalize.get("error_message", "Service initialization failed")
                    await db_session.execute(
                        sa_update(FormCheck)
                        .where(FormCheck.id == form_check_id)
                        .where(FormCheck.status == FormCheckStatus.PENDING)
                        .values(
                            status=FormCheckStatus.FAILED,
                            details={"error_message": (err_msg or "Task init failed")[:500]},
                        )
                    )
                    await db_session.commit()
                    logger.error(f"[CeleryTask] Raw fallback: marked FormCheck {form_check_id} as FAILED.")
                except Exception as _e_raw:
                    logger.critical(
                        f"[CeleryTask] Raw fallback also failed for FormCheck {form_check_id}: {_e_raw}"
                    )

        # Local video file cleanup was removed in original task, assuming cloud URLs are used.
        # If DynamicFormAnalysisService downloads files, it should clean them up.
        # The original task downloaded video_url to video_file_path_local, this is removed now
        # as DFAS takes Video object which should have data/urls.
        # If DFAS needs local file, it has to handle its download/cleanup or this task gives it a path.
        # For now, assume DFAS works with Video object and its angle_data.
        
        # Always exit the context manager so the session is properly returned to the pool
        try:
            await _session_cm.__aexit__(None, None, None)
        except Exception as e_exit:
            logger.warning(f"[CeleryTask] Error closing DB session context manager: {e_exit}")
        logger.info(f"[CeleryTask] DB session closed for FormCheck ID: {form_check_id}")

    logger.info(f"[CeleryTask] Finished processing FormCheck ID: {form_check_id} with status: {final_status.value}")
    return {"status": final_status.value, "form_check_id": str(form_check_id), "final_score": analysis_output_for_finalize.get("score")}

# To make this task discoverable, ensure __init__.py in the tasks folder (and its parent app folder)
# imports this module or the celery_app directly.
# e.g. in app/tasks/__init__.py:
# from .analysis_tasks import process_form_check_task 