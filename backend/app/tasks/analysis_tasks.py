"""Celery tasks for analysis processing."""
import asyncio
import logging
import os
import threading
import time
from uuid import UUID
from tempfile import NamedTemporaryFile
from typing import Optional, Dict, Any, List

from celery.signals import worker_process_init
from app.core.celery_app import celery_app
from app.core.config import get_settings, Settings
from app.core.database import (  # Changed import path
    get_async_session_for_celery,
    get_celery_async_engine,
)

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
from app.services.decisions import COMBINER_VERSION, CheckerOutcome, combine
from app.services.decisions.adapters import (
    depth_outcome,
    keypoint_digest,
    knees_forward_outcome,
)
from app.services.decisions.recorder import (
    RUN_STATUS_COMPLETED,
    RUN_STATUS_FAILED,
    RUN_STATUS_RELEASED,
    close_run,
    open_run,
    record_decisions,
)

logger = logging.getLogger(__name__)

# ── Per-worker singleton cache ────────────────────────────────────────────────
# These are set lazily (on first task use) rather than eagerly at worker_process_init
# so that Celery worker startup is fast and Render deploy timeouts are avoided.
# MediaPipe + PyTorch + pandas/matplotlib are NOT imported until the first task runs.
_shared_ai_service: Optional[AIService] = None
_shared_storage_service: Optional[StorageService] = None
_shared_posture_v1_loader: Optional[Any] = None

_ai_service_lock = threading.Lock()
_posture_loader_lock = threading.Lock()
_storage_service_lock = threading.Lock()


# ── Temp-file registry ────────────────────────────────────────────────────────
# The S3 fallback in _resolve_video_local_path writes the video to a
# NamedTemporaryFile(delete=False).  The caller deletes it in its own `finally`,
# but that only fires if the caller actually received the path: if the task is
# cancelled at the await boundary (SoftTimeLimitExceeded lands as an exception
# in the coroutine) the file is already on disk and its path is lost.
#
# Registering the path at creation closes that window.  Under -P prefork each
# task owns its process and runs to completion before the next starts, so a
# module-level set is per-task in practice.
_TEMP_FILE_PREFIX = "formiq_pose_"
_task_temp_files: set = set()

# A hard kill (task_time_limit, OOM, docker kill) runs no `finally` at all, so
# files can still survive.  Sweep them at worker start instead — older than this
# many seconds, which must exceed task_time_limit so a sibling prefork child's
# in-flight download is never deleted.
_TEMP_FILE_STALE_SECONDS = 3600


def _register_temp_file(path: str) -> None:
    _task_temp_files.add(path)


def _release_temp_file(path: str) -> bool:
    """Delete one registered temp file. Returns True if a file was removed."""
    _task_temp_files.discard(path)
    try:
        os.unlink(path)
        return True
    except FileNotFoundError:
        return False
    except Exception as e:
        logger.warning("[TempSweep] Failed to delete temp file %s: %s", path, e)
        return False


def _sweep_task_temp_files() -> int:
    """Delete any temp file this task registered but never released."""
    leaked = list(_task_temp_files)
    removed = 0
    for path in leaked:
        if _release_temp_file(path):
            removed += 1
            logger.warning(
                "[TempSweep] Temp file %s outlived its cleanup block; removed by "
                "the task-level sweep.", path,
            )
    _task_temp_files.clear()
    return removed


def _sweep_stale_temp_files() -> int:
    """Delete orphaned temp videos left behind by a previously killed worker."""
    import tempfile
    import time

    tmp_dir = tempfile.gettempdir()
    cutoff = time.time() - _TEMP_FILE_STALE_SECONDS
    removed = 0
    try:
        names = os.listdir(tmp_dir)
    except OSError as e:
        logger.warning("[TempSweep] Cannot list %s: %s", tmp_dir, e)
        return 0
    for name in names:
        if not name.startswith(_TEMP_FILE_PREFIX):
            continue
        path = os.path.join(tmp_dir, name)
        try:
            if os.path.getmtime(path) < cutoff:
                os.unlink(path)
                removed += 1
        except FileNotFoundError:
            continue
        except Exception as e:
            logger.warning("[TempSweep] Failed to remove stale temp file %s: %s", path, e)
    if removed:
        logger.info("[TempSweep] Removed %d stale temp video(s) from %s", removed, tmp_dir)
    return removed


@worker_process_init.connect
def initialize_worker_services(**kwargs):
    """Initialize only lightweight services at worker startup.

    Heavy services (AIService, PostureV1) are deferred to first task use so that
    the worker process becomes ready quickly and Render deploy timeouts are avoided.
    MediaPipe / PyTorch / matplotlib-triggering imports are NOT executed here.
    """
    global _shared_storage_service
    logger.info("Celery worker process starting — lightweight services only...")
    # G-43: is this the image requirements.txt describes? Logs an ERROR naming each
    # pin that is missing or mismatched; never raises.
    from app.core.image_check import run_and_log as _image_check
    _image_check("worker")
    # A previously killed worker cannot have run its cleanup blocks; clear what it left.
    _sweep_stale_temp_files()
    # Build this child's own async engine here, after the fork, so no engine
    # object is ever shared between prefork children.
    get_celery_async_engine()
    try:
        settings_obj = get_settings()
        # StorageService is lightweight (no native libraries, no model files).
        # Initialize it eagerly so the first task doesn't pay the setup cost.
        with _storage_service_lock:
            if settings_obj.USE_S3_STORAGE:
                from app.core.storage.s3 import S3StorageProvider as _S3Provider
                _shared_storage_service = StorageService(provider=_S3Provider(), app_settings=settings_obj)
            else:
                _shared_storage_service = StorageService(app_settings=settings_obj)
        logger.info("Celery worker ready. AIService + PostureV1 will initialize on first task.")
    except Exception as e:
        logger.critical("Failed to initialize worker services: %s", e, exc_info=True)
        raise


def _get_shared_ai_service() -> AIService:
    """Return the per-worker AIService singleton, creating it on first call.

    Thread-safe double-checked locking.  MediaPipe + PyTorch are imported
    here (not at module load time) so worker startup stays fast.
    """
    global _shared_ai_service
    if _shared_ai_service is None:
        with _ai_service_lock:
            if _shared_ai_service is None:
                logger.info("Initializing AIService for worker process (first task use)...")
                _shared_ai_service = AIService(app_settings=get_settings())
                logger.info("AIService initialized and cached for this worker.")
    return _shared_ai_service


def _get_shared_posture_loader() -> Any:
    """Return the per-worker PostureV1TorchLoader singleton, creating it on first call.

    PyTorch model loading (~1-3 s) happens here, not at worker startup.
    """
    global _shared_posture_v1_loader
    if _shared_posture_v1_loader is None:
        with _posture_loader_lock:
            if _shared_posture_v1_loader is None:
                settings_obj = get_settings()
                if getattr(settings_obj, "USE_POSTURE_V1", True):
                    logger.info("Loading PostureV1 model (first task use)...")
                    from app.ml.posture_v1.loader import PostureV1TorchLoader
                    _loader = PostureV1TorchLoader(settings_obj)
                    _loader._ensure_loaded()
                    _shared_posture_v1_loader = _loader
                    logger.info("PostureV1 model loaded and cached for this worker.")
    return _shared_posture_v1_loader

# Helper to get an async DB session for Celery tasks
# Use as: async with get_async_session_for_celery() as session:
get_task_db_session = get_async_session_for_celery

# Helper to instantiate services within a task context
async def get_services_for_task(db_session: AsyncSession, settings_obj: Settings):
    """Provides necessary services for the task."""
    # Use per-worker singletons (initialized lazily on first task use).
    ai_service_instance = _get_shared_ai_service()

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
async def _resolve_video_local_path(
    video_model,
    settings_obj,
    storage_service=None,
) -> "tuple[Optional[str], bool]":
    """
    Resolve the video to a local filesystem path the worker can open.

    For local-storage deployments: converts the stored URL/object_key to an
    absolute path on the current host.

    For S3-backed deployments (USE_S3_STORAGE=True): if the file is not on local
    disk (it won't be on Render/cloud workers), downloads the S3 object to a
    NamedTemporaryFile and returns that path.

    Returns:
        (local_path, is_temp) — local_path is None when the video cannot be
        located; is_temp is True only for S3-downloaded temp files (caller must
        delete the temp file after use).
    """
    import os
    import tempfile
    from app.core.storage import LocalStorageProvider
    try:
        provider = LocalStorageProvider()
        url = video_model.object_key or video_model.url or ""
        if not url:
            logger.warning(f"[PoseExtract] Video {video_model.id} has no url/object_key.")
            return None, False
        key = provider.get_key_from_url(url)
        local_path = os.path.join(provider.base_dir, key)
        if os.path.exists(local_path):
            logger.info(f"[PoseExtract] Resolved local path: {local_path}")
            return local_path, False
        # Fallback: maybe the URL itself is already a local path (e.g. stored as absolute)
        if os.path.exists(url):
            return url, False

        # --- S3 fallback: download to a temp file for processing ---
        # In cloud deployments (USE_S3_STORAGE=True) the video lives in S3, not
        # on the worker's disk.  Download it so ffmpeg/OpenCV can open it locally.
        use_s3 = getattr(settings_obj, 'USE_S3_STORAGE', False)
        if use_s3 and storage_service is not None:
            # Prefer the raw object_key; fall back to the key derived above
            s3_key = video_model.object_key or key
            logger.info(
                f"[PoseExtract] Local file not found for Video {video_model.id}; "
                f"downloading from S3 key: {s3_key}"
            )
            try:
                video_bytes = await storage_service.download_file(s3_key)
                suffix = os.path.splitext(s3_key)[-1] or ".mp4"
                tmp = tempfile.NamedTemporaryFile(
                    delete=False, suffix=suffix, prefix="formiq_pose_"
                )
                tmp.write(video_bytes)
                tmp.close()
                _register_temp_file(tmp.name)
                logger.info(
                    f"[PoseExtract] S3 download complete: {tmp.name} "
                    f"({len(video_bytes):,} bytes, key={s3_key})"
                )
                return tmp.name, True  # caller must delete after pose extraction
            except Exception as s3_err:
                logger.error(
                    f"[PoseExtract] S3 download failed for Video {video_model.id} "
                    f"(key={s3_key}): {s3_err}",
                    exc_info=True,
                )
                return None, False

        logger.warning(
            f"[PoseExtract] Local video file not found: {local_path} "
            f"(key={key}, url={url}, USE_S3_STORAGE={use_s3})"
        )
        return None, False
    except Exception as e:
        logger.error(f"[PoseExtract] Error resolving local path for Video {video_model.id}: {e}", exc_info=True)
        return None, False


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
        # AIService is a per-worker singleton and its MediaPipe Pose runs with
        # static_image_mode=False, so the tracker would otherwise carry the
        # previous video's landmarks into this one's first frames.  Reset it
        # per video: without this the same bytes score differently depending on
        # their predecessor (bench/results/2026-09-19-mediapipe-state-leak.md).
        ai_svc.reset_pose_tracker()
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


class TransientTaskError(Exception):
    """Wraps an error the task should retry rather than record as FAILED.

    Raised out of the async body and converted into ``self.retry()`` by the sync
    wrapper. It exists so the classification decision is made in one place, next
    to the DB session that has to un-claim the row, rather than in the wrapper.
    """

    def __init__(self, original: BaseException):
        self.original = original
        super().__init__(f"{type(original).__name__}: {original}")


def _transient_exception_types() -> tuple:
    """Errors that mean "the infrastructure blinked", not "this video is bad".

    Deliberately narrow. Note what is NOT here:
      - OSError: IOError("Cannot open video") is an OSError, and a corrupt video
        is permanent. Only ConnectionError (an OSError subclass) counts.
      - SoftTimeLimitExceeded: a video that exceeded the soft limit will exceed
        it again on retry. Permanent, recorded as FAILED with the reason.
      - ValueError / NotFoundException: the task's own validation and gates.
    """
    from sqlalchemy import exc as sa_exc

    types = [
        sa_exc.OperationalError,   # server closed the connection, cannot connect
        sa_exc.InterfaceError,     # connection already closed / invalid
        sa_exc.DisconnectionError,
        ConnectionError,           # incl. ConnectionReset/Refused/Aborted
        TimeoutError,
        asyncio.TimeoutError,
    ]
    try:  # redis is the broker; its connection errors are transient too
        from redis import exceptions as redis_exc

        types += [redis_exc.ConnectionError, redis_exc.TimeoutError]
    except Exception:  # pragma: no cover - redis always present in practice
        pass
    return tuple(types)


def _is_transient(exc: BaseException, retries_so_far: int, max_retries: int) -> bool:
    """Transient AND we have retries left. Exhausted retries are permanent.

    Classifying an exhausted retry as transient would leave the row PENDING with
    nothing left to pick it up -- exactly the state this branch exists to remove.
    """
    if retries_so_far >= max_retries:
        return False
    return isinstance(exc, _transient_exception_types())


# Explicitly name the task to ensure consistent registration
@celery_app.task(name="app.tasks.analysis_tasks.process_form_check", bind=True, max_retries=3, default_retry_delay=300)
def process_form_check_task(self, video_id_str: str, form_check_id_str: str):
    """Sync wrapper that runs the async task via asyncio.run().

    Sync on purpose. An `async def` here would be handed to Celery unawaited and
    the body would never run -- see app/tasks/ai_tasks.py for four tasks that
    did exactly that.
    """
    import asyncio
    try:
        return asyncio.run(
            _process_form_check_task_async(self, video_id_str, form_check_id_str)
        )
    except TransientTaskError as wrapped:
        # max_retries=3 was declared on this task from the start but self.retry()
        # was never called, so it was dead configuration. The async body has
        # already put the row back to PENDING, so the retry can claim it.
        retries_so_far = getattr(self.request, "retries", 0) or 0
        countdown = min(2 ** retries_so_far, 300)
        logger.warning(
            "[CeleryTask] Transient failure for FormCheck %s (%s); retry %d/%d "
            "in %ds.",
            form_check_id_str, wrapped, retries_so_far + 1, self.max_retries,
            countdown,
        )
        raise self.retry(exc=wrapped.original, countdown=countdown)

async def _reclaim_after_worker_lost(db_session, form_check_id, task_id: str) -> bool:
    """G-46: take back a row whose worker died, the moment its message comes round again.

    A child killed mid-task (SIGKILL, OOM) runs no `finally`: its row stays PROCESSING
    and its run stays open. Celery requeues the message (`task_reject_on_worker_lost`)
    and marks the redelivery. When that redelivery loses the claim and finds a PROCESSING
    row whose OPEN run carries this very task id, nobody else owns the row -- the only
    other party that could is the reaper, and it waits 30 minutes. So: close the dead run
    as abandoned/worker_lost (the reason the trail was missing, G-46) and re-take the row
    now. Returns True iff this task owns the row afterwards.

    Measured before this existed: 7 kills in 900 videos, each a 30-minute wait.
    """
    from sqlalchemy import select as _select
    from app.models.audit import AnalysisRun, RUN_STATUS_ABANDONED, RUN_STATUS_RUNNING
    from app.services.decisions.recorder import close_run

    dead_run_id = (await db_session.execute(
        _select(AnalysisRun.id)
        .where(AnalysisRun.form_check_id == form_check_id)
        .where(AnalysisRun.celery_task_id == task_id)
        .where(AnalysisRun.status == RUN_STATUS_RUNNING)
        .where(AnalysisRun.finished_at.is_(None))
        .limit(1)
    )).scalar_one_or_none()
    if dead_run_id is None:
        return False
    await close_run(
        db_session, run_id=dead_run_id, status=RUN_STATUS_ABANDONED, error_type="worker_lost",
        error_message="worker child died mid-task (SIGKILL/OOM); message redelivered and the row reclaimed",
    )
    reclaim = await db_session.execute(
        sa_update(FormCheck)
        .where(FormCheck.id == form_check_id)
        .where(FormCheck.status == FormCheckStatus.PROCESSING)
        .values(status=FormCheckStatus.PROCESSING)      # a no-op write: asserts the state, bumps updated_at
    )
    await db_session.commit()
    return reclaim.rowcount == 1


async def _process_form_check_task_async(self, video_id_str: str, form_check_id_str: str):
    """
    Celery task to process a form check analysis for a given video and form_check ID.
    Uses DynamicFormAnalysisService for rule-based evaluation.
    """
    form_check_id = UUID(form_check_id_str)
    video_id = UUID(video_id_str) # Convert video_id_str to UUID
    logger.info(f"[CeleryTask] Starting analysis for FormCheck ID: {form_check_id}, Video ID: {video_id}")

    # get_async_session_for_celery() uses a NullPool engine — no connection is ever
    # held across asyncio.run() boundaries, so no manual dispose() is needed here.
    settings_obj = get_settings()
    db_session: Optional[AsyncSession] = None
    form_check_service: Optional[FormCheckService] = None
    
    analysis_output_for_finalize: Dict[str, Any] = {} # Renamed to avoid confusion with model
    final_status: FormCheckStatus = FormCheckStatus.FAILED
    # Set only when the failure is worth retrying; see _is_transient().
    transient_exc: Optional[TransientTaskError] = None
    analyzed_form_check_model: Optional[FormCheck] = None # To store the result from DFAS
    # Bound here rather than only inside the try, so the `finally` can read it
    # on the paths that failed before it was fetched.
    form_check: Optional[FormCheck] = None
    # Decision trail (Stage A). Best-effort throughout: a missing audit row is
    # a missing explanation, never a failed analysis.
    run_id = None
    _checker_outcomes: List[CheckerOutcome] = []
    _run_started_monotonic = time.monotonic()
    # G-48: True only once the conditional claim below has moved the row from
    # PENDING to PROCESSING. Until then the row belongs to someone else -- a
    # worker that already finished it, or nobody -- and the `finally` must not
    # write to it. Without this, a duplicate dispatch that lost the claim still
    # finalized the row with `final_status` (FAILED by default): 520 completed
    # form checks were flipped to FAILED an hour after they completed.
    claimed = False

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

        # Claim the row atomically.
        #
        # This used to read the status, compare it, and then write PROCESSING in
        # a separate statement -- a read-then-write race. Two workers handed the
        # same message (which late acks and the reaper's re-dispatch both make
        # more likely, not less) could each read PENDING and both proceed,
        # running the model twice and finalizing over each other.
        #
        # A conditional UPDATE, not SELECT ... FOR UPDATE. FOR UPDATE would hold
        # a row lock for the entire analysis -- minutes of pose extraction and
        # inference -- against a NullPool connection, so a worker killed
        # mid-task would strand the lock until its connection timed out, and the
        # reaper would then block behind it. A single UPDATE ... WHERE
        # status='pending' is atomic in one statement, takes no lock past
        # commit, and rowcount says exactly whether we won.
        claim = await db_session.execute(
            sa_update(FormCheck)
            .where(FormCheck.id == form_check_id)
            .where(FormCheck.status == FormCheckStatus.PENDING)
            .values(status=FormCheckStatus.PROCESSING)
        )
        await db_session.commit()

        if claim.rowcount == 0:
            # Someone else claimed it, or it is already terminal. Either way it
            # is not ours; return without touching the row -- with one exception:
            # a REDELIVERED message for a PROCESSING row whose open run bears this
            # task id is our own dead predecessor (G-46). Reclaim it now.
            await db_session.refresh(form_check)
            observed = getattr(form_check.status, "value", form_check.status)
            _req = getattr(self, "request", None)
            _delivery = getattr(_req, "delivery_info", None)
            _delivery = _delivery if isinstance(_delivery, dict) else {}
            _task_id = getattr(_req, "id", None)
            reclaimed = False
            if (str(observed) == FormCheckStatus.PROCESSING.value and _delivery.get("redelivered")
                    and isinstance(_task_id, str)):
                reclaimed = await _reclaim_after_worker_lost(db_session, form_check_id, _task_id)
            if not reclaimed:
                logger.warning(
                    "[CeleryTask] FormCheck ID %s could not be claimed (status: %s). "
                    "Skipping -- another worker has it or it is already finished.",
                    form_check_id, observed,
                )
                return {"status": "skipped", "message": f"Not in PENDING state, was {observed}"}
            logger.warning(
                "[CeleryTask] FormCheck %s reclaimed after worker loss (message redelivered); "
                "dead run closed as worker_lost, continuing.", form_check_id,
            )

        claimed = True
        # The raw UPDATE bypassed the identity map, so refresh before anything
        # downstream reads form_check.status.
        await db_session.refresh(form_check)
        logger.info(f"[CeleryTask] FormCheck ID {form_check_id} claimed; status updated to PROCESSING.")

        # ---- Open the decision trail (Stage A) ----------------------------
        # Immediately after the claim, with its own commit, so a worker killed
        # one instruction later still leaves `running` + finished_at NULL --
        # which is exactly what the reaper sweeps. Opened inside the task's main
        # transaction it would vanish on rollback, and the run most worth
        # explaining (the one that died) would be the one with no record.
        #
        # pose_pass_id is not known yet: MediaPipe's effective complexity is only
        # settled once the AIService has built its tracker, and a run stamped
        # with the CONFIGURED complexity would silently misattribute every
        # verdict from a worker that fell back to complexity 1. It is written on
        # close instead. See app/core/pose_pass.py and G-39.
        _rules_spec_hash = None
        try:
            from app.rules import load_params, rules_spec_hash as _rsh
            _rules_spec_hash = _rsh(load_params())
        except Exception:
            pass   # the rules layer is advisory; its absence must not matter here
        run_id = await open_run(
            db_session,
            form_check_id=form_check_id,
            video_id=video_id,
            user_id=getattr(form_check, "user_id", None),
            celery_task_id=getattr(getattr(self, "request", None), "id", None),
            attempt=getattr(getattr(self, "request", None), "retries", 0) or 0,
            content_hash=getattr(form_check, "content_hash", None),
            model_version=getattr(form_check, "model_version", None),
            spec_hash=getattr(form_check, "spec_hash", None),
            rules_spec_hash=_rules_spec_hash,
            combiner_version=COMBINER_VERSION,
        )

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
            _video_is_temp = False  # track whether we downloaded a temp file from S3
            video_local_path = None
            try:
                video_local_path, _video_is_temp = await _resolve_video_local_path(
                    video_model, settings_obj, storage_service
                )
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
                    logger.warning(f"[CeleryTask] Could not resolve video path for Video {video_id} — skipping pose extraction.")
            except Exception as pose_exc:
                logger.error(f"[CeleryTask] Pose extraction failed for Video {video_id}: {pose_exc}", exc_info=True)
                # Non-fatal: PostureV1 quality gate will set decision=uncertain if frames insufficient.
            finally:
                # Always clean up S3-downloaded temp files
                if _video_is_temp and video_local_path:
                    if _release_temp_file(video_local_path):
                        logger.info(f"[PoseExtract] Cleaned up temp video file: {video_local_path}")

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
                    # `depth_score` used to receive movement_quality['consistency'].
                    # Consistency is how steady the movement was; it is not depth,
                    # nothing depth-related feeds it, and the word "femur" appears
                    # nowhere in this repo. A column named depth_score carrying a
                    # consistency metric is a claim the system cannot support, and
                    # it is worse than NULL because it reads as an answer.
                    #
                    # It stays NULL until a FITTED depth checker exists. The
                    # definitional parallel rule shipped in Stage A is unfitted and
                    # advisory (see the rules block below); the value it computes
                    # is recorded in results["rules_shadow"], which is labelled.
                    _mq = form_check.results or {}
                    _mq.setdefault("movement_quality", {})["consistency"] = \
                        movement_quality.get('consistency')
                    form_check.results = _mq

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

                # Use the process-scoped shared loader (lazy-initialized on first use)
                # so model + scaler are loaded ONCE per worker process, not once per task.
                posture_v1_loader = _get_shared_posture_loader()
                if posture_v1_loader is None:
                    # USE_POSTURE_V1 is False — fall back to per-task instance.
                    posture_v1_loader = PostureV1TorchLoader(settings_obj)
                    logger.debug(
                        "[CeleryTask] PostureV1 disabled or unavailable — "
                        "created per-task instance (FormCheck %s)",
                        form_check_id,
                    )
                else:
                    logger.debug(
                        "[CeleryTask] Reusing cached PostureV1 artifacts (FormCheck %s)",
                        form_check_id,
                    )

                # Apply named threshold mode if set in form_check details.
                # Save the current threshold and restore it after inference so the
                # shared loader is not left with a per-task override for the next task.
                _threshold_mode = (form_check.details or {}).get("threshold_mode")
                _saved_pv1_threshold = posture_v1_loader._fault_threshold
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
                # Gated on COACHING_FEEDBACK_ENABLED (default False) so workers
                # without langchain_openai never attempt the import and never emit
                # "No module named 'langchain_openai'" warnings.
                if not _is_shadow and pv1_decision != "uncertain" and getattr(settings_obj, 'COACHING_FEEDBACK_ENABLED', False):
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

                # ---- Decision trail (Stage A) -----------------------------
                # Dual-written beside the legacy telemetry row, which is kept
                # rather than migrated: its 103 existing rows have no run_id to
                # invent. Removing it is a separate branch.
                #
                # PostureV1 is the one FITTED checker, so it is the only one
                # allowed to be authoritative. `advisory` tracks shadow mode:
                # in shadow it answers for the record and changes nothing.
                try:
                    _checker_outcomes.append(CheckerOutcome(
                        checker_name="posture_v1",
                        checker_kind="model",
                        checker_version=posture_v1_result.get("model_version"),
                        target="posture",
                        decision=str(pv1_decision).upper(),
                        fitted=True,
                        advisory=bool(_is_shadow),
                        abstained=(pv1_decision == "uncertain"),
                        abstain_reason=("model_uncertain"
                                        if pv1_decision == "uncertain" else None),
                        prob=pv1_prob,
                        confidence=pv1_confidence,
                        threshold=posture_v1_result.get("threshold"),
                        indicators=scoring.get("top_signals"),
                        quality={
                            "quality_flags": posture_v1_result.get("quality_flags"),
                            "quality_ok": posture_v1_result.get("quality_ok"),
                            "angle_validity": posture_v1_result.get("angle_validity"),
                            "threshold_mode": _threshold_mode,
                            "posture_v1_mode": _posture_v1_mode,
                        },
                        latency_ms=posture_v1_result.get("latency_ms"),
                    ))
                except Exception as audit_exc:
                    logger.warning("[Audit] could not build the PostureV1 outcome: %s",
                                   audit_exc)

                # Restore threshold on shared loader so the next task is not
                # affected by this task's per-form-check threshold override.
                posture_v1_loader._fault_threshold = _saved_pv1_threshold

            except Exception as pv1_exc:
                # Restore threshold even on failure path.
                try:
                    posture_v1_loader._fault_threshold = _saved_pv1_threshold
                except Exception:
                    pass
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

                # An errored checker is still a checker that ran. Recording it
                # is what distinguishes "PostureV1 threw" from "PostureV1 never
                # executed", which the legacy table could not tell apart either.
                try:
                    _checker_outcomes.append(CheckerOutcome(
                        checker_name="posture_v1",
                        checker_kind="model",
                        target="posture",
                        decision="ERROR",
                        fitted=True,
                        advisory=True,
                        error=str(pv1_exc)[:2000],
                    ))
                except Exception:
                    pass

        elif _run_posture_v1 and not _is_squat and keypoint_sequence_for_classification:
            logger.info(f"[CeleryTask] Exercise '{_exercise_slug}' is not squat — skipping PostureV1 (FormCheck {form_check_id})")
            existing_results = form_check.results or {}
            existing_results["posture_v1"] = {"status": "not_supported", "exercise_type": _exercise_slug, "reason": "posture_v1 only supports squat"}
            form_check.results = existing_results
            await db_session.merge(form_check)
        elif not _run_posture_v1:
            logger.debug("[CeleryTask] PostureV1 disabled via USE_POSTURE_V1=false")

        # ---- Unfitted rule checkers (Stage A) -----------------------------
        # Two hand-set rules, both `fitted: false`, both ADVISORY. They exist to
        # carry the two-checker path end to end and to record evidence; the
        # combiner will not let either set a verdict or move a score, and
        # `depth_score` stays NULL.
        #
        # Not because of caution in the abstract. All three fault rules were
        # measured and refuted at the video level on train:
        #   depth          -- best AUROC 0.578 of ten axes tried
        #   knee valgus    -- real signal, ~5% front view, 4 positive examples
        #   knees forward  -- 80.2% within-video, 0.572 between, floor F1 0.812
        # See bench/results/2026-09-23-corpus-level-negative.md.
        #
        # Its own try/except and its own guard: a rules failure must not touch a
        # PostureV1 result that already succeeded.
        if _is_squat and keypoint_sequence_for_classification:
            try:
                from app.rules import (
                    evaluate_depth,
                    evaluate_knees_forward,
                    load_knees_forward_params,
                    load_params,
                )
                _rules_t0 = time.monotonic()
                _depth_params = load_params()
                _kf_params = load_knees_forward_params()
                # From video_model, not from _fps_used: that name is bound
                # inside the PostureV1 block, so reading it here would make the
                # rules layer silently never run whenever PostureV1 is disabled
                # or failed early. Same source as analysis_tasks.py:1103.
                _rule_fps = float(video_model.fps or 0.0) or _kf_params["fallback_fps"]

                _dv = evaluate_depth(keypoint_sequence_for_classification,
                                     _rule_fps, _depth_params)
                _kv = evaluate_knees_forward(keypoint_sequence_for_classification,
                                             _rule_fps, _kf_params)
                _rules_ms = (time.monotonic() - _rules_t0) * 1000.0

                # Mapping lives in app/services/decisions/adapters.py, not
                # inline here: when it was inline, depth's `score` was left out
                # and every stored depth decision had a NULL score while the
                # identical offline computation produced a real one. Nothing
                # raised -- the field existed on all three sides and simply was
                # not connected. A unit test now asserts the mapping is total.
                # One digest of the exact array both checkers saw, so two
                # stored decisions can be compared without re-running anything.
                _kp_digest = keypoint_digest(keypoint_sequence_for_classification)
                _checker_outcomes.extend([
                    depth_outcome(_dv, _depth_params, round(_rules_ms, 3),
                                  inputs_digest=_kp_digest),
                    knees_forward_outcome(_kv, round(_rules_ms, 3),
                                          inputs_digest=_kp_digest),
                ])
                # Recorded under its own key, never in depth_score. Writing an
                # unfitted verdict into a user-visible column is the exact
                # mistake analysis_tasks.py already made once, when movement
                # consistency was written into depth_score.
                _existing = form_check.results or {}
                _existing["rules_shadow"] = {
                    "depth": _dv.as_dict(),
                    "knees_forward": _kv.as_dict(),
                    "fitted": False,
                    "advisory": True,
                    "note": ("unfitted hand-set rules, recorded as evidence only; "
                             "no user-visible field is derived from them"),
                }
                form_check.results = _existing
                await db_session.merge(form_check)
                logger.info(
                    "[Rules] FormCheck %s depth=%s(%s) knees_forward=%s(%s) in %.1fms",
                    form_check_id, _dv.verdict, _dv.abstain_reason,
                    _kv.decision, _kv.abstain_reason, _rules_ms,
                )
            except Exception as rules_exc:
                logger.warning("[Rules] rules layer failed for FormCheck %s: %s",
                               form_check_id, rules_exc, exc_info=True)
                try:
                    _checker_outcomes.append(CheckerOutcome(
                        checker_name="rules_layer", checker_kind="rule",
                        target="rules", decision="ERROR", fitted=False,
                        advisory=True, error=str(rules_exc)[:2000],
                    ))
                except Exception:
                    pass

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
                # Explicit None, not omission. Under the presence-based writes
                # in finalize (form_check_service.py), omitting a key means
                # "leave the column alone" -- which would START shipping the
                # legacy temporal heuristic's stability_score, a user-visible
                # number nothing validates. Until it is measured it declines,
                # the same call made for depth_score.
                #
                # This preserves today's observable behaviour exactly. What
                # changes is that it is now a decision in the code rather than
                # a side effect of finalize blanking every score it had no
                # opinion about.
                "stability_score": None,
                "depth_score": None,
            }
        elif not analysis_output_for_finalize:
            # Nothing produced a result: DFAS was skipped AND PostureV1 has no
            # output. No exception was raised, so none of the handlers below run
            # and final_status keeps its initial value of FAILED -- which is
            # right, but it was being written with an empty payload. The user
            # was told "failed" and given nothing to act on.
            #
            # Measured: a corrupt upload finalized in 0.17s as FAILED with
            # details={"risk_level": "high", "raw_feedback_strings": [],
            # "model_version": "unknown"} and no error_message at all.
            frames = keypoint_sequence_for_classification or []
            usable = sum(1 for f in frames if f)
            final_status = FormCheckStatus.FAILED
            analysis_output_for_finalize = {
                "score": None,
                "feedback": [],
                "risk_level": "high",
                "feedback_structured": [],
                "error_message": (
                    "No analysis could be produced from this video: pose "
                    f"extraction returned {usable} usable frame(s) out of "
                    f"{len(frames)}. The file may be unreadable, may not show a "
                    "person clearly enough, or may be too short to analyse."
                ),
            }
            logger.warning(
                "[CeleryTask] FormCheck %s produced no analysis at all "
                "(%d/%d usable frames); failing with an explicit reason.",
                form_check_id, usable, len(frames),
            )

    except ValueError as ve: # Catch specific value errors from our checks
        logger.error(f"[CeleryTask] ValueError during FormCheck {form_check_id} analysis: {ve}", exc_info=True)
        final_status = FormCheckStatus.FAILED
        if "error_message" not in analysis_output_for_finalize or not analysis_output_for_finalize["error_message"]:
            analysis_output_for_finalize["error_message"] = str(ve)
    except Exception as e:
        retries_so_far = getattr(getattr(self, "request", None), "retries", 0) or 0
        max_retries = getattr(self, "max_retries", 3) or 0
        if _is_transient(e, retries_so_far, max_retries):
            # Infrastructure blinked. Do NOT finalize as FAILED -- that would burn
            # the form check on a problem that has nothing to do with the video.
            logger.warning(
                "[CeleryTask] Transient error during FormCheck %s analysis "
                "(attempt %d/%d): %s: %s",
                form_check_id, retries_so_far + 1, max_retries,
                type(e).__name__, e,
            )
            transient_exc = TransientTaskError(e)
        else:
            logger.error(f"[CeleryTask] General error during FormCheck {form_check_id} analysis: {type(e).__name__}: {e}", exc_info=True)
            final_status = FormCheckStatus.FAILED
            if "error_message" not in analysis_output_for_finalize or not analysis_output_for_finalize["error_message"]:
                reason = f"{type(e).__name__}: {str(e)}"
                if retries_so_far >= max_retries:
                    reason = f"{reason} (gave up after {retries_so_far} retries)"
                analysis_output_for_finalize["error_message"] = reason
    finally:
        # ---- Close the decision trail (Stage A) ---------------------------
        # At the TOP of the finally, before the transient/finalize branching, so
        # every exit path closes its run: a retried task closes as `released`
        # rather than being left open and swept as abandoned by the reaper.
        #
        # Two statements, deliberately. The decision rows go first in their own
        # transaction; close_run then rolls back and issues a bare UPDATE,
        # because by this point the ORM session may be poisoned by whatever put
        # us here. Both are best-effort: an audit write must never be the reason
        # an analysis fails.
        if run_id is not None and db_session is not None:
            try:
                _combined = combine(_checker_outcomes)
                _written = await record_decisions(
                    db_session, run_id=run_id, outcomes=_checker_outcomes,
                    form_check_id=form_check_id,
                    content_hash=getattr(form_check, "content_hash", None),
                )
                await db_session.commit()
                logger.info(
                    "[Audit] run %s: %d checker decision(s), %d contributor(s), "
                    "%d advisory, score=%s",
                    run_id, _written, len(_combined.contributors),
                    len(_combined.advisory), _combined.score,
                )
            except Exception as audit_exc:
                logger.warning("[Audit] could not write decisions for run %s: %s",
                               run_id, audit_exc)
                _combined = None
                try:
                    await db_session.rollback()
                except Exception:
                    pass

            if transient_exc is not None:
                _run_status, _err_type = RUN_STATUS_RELEASED, type(
                    transient_exc.original).__name__
            elif final_status == FormCheckStatus.COMPLETED:
                _run_status, _err_type = RUN_STATUS_COMPLETED, None
            else:
                _run_status, _err_type = RUN_STATUS_FAILED, None

            _pose_pass = None
            try:
                # Resolved HERE, not at open: the effective MediaPipe complexity
                # is only settled once the tracker is built, and a worker that
                # fell back to complexity 1 produced different keypoints (G-39).
                from app.core.pose_pass import extraction_contract, pose_pass_id
                _pose_pass = pose_pass_id(extraction_contract(
                    ai_service=_ai_service_instance, settings=settings_obj))
            except Exception:
                pass

            await close_run(
                db_session,
                run_id=run_id,
                status=_run_status,
                outcome_status=getattr(final_status, "value", None),
                final_decision=((_combined.verdicts or {}).get("posture")
                                if _combined else None),
                final_score=(_combined.score if _combined else None),
                error_type=_err_type,
                error_message=(analysis_output_for_finalize or {}).get("error_message"),
                latency_ms=round((time.monotonic() - _run_started_monotonic) * 1000.0, 3),
                pose_pass_id=_pose_pass,
                n_frames=(len(keypoint_sequence_for_classification)
                          if "keypoint_sequence_for_classification" in dir()
                          and keypoint_sequence_for_classification else None),
            )

        if transient_exc is not None and form_check_id and db_session:
            # Put the row back to PENDING so the retry's guard lets it through.
            # Without this the row stays PROCESSING and the retry skips it,
            # leaving a form check that is neither running nor finished.
            try:
                await db_session.rollback()
                await db_session.execute(
                    sa_update(FormCheck)
                    .where(FormCheck.id == form_check_id)
                    .where(FormCheck.status == FormCheckStatus.PROCESSING)
                    .values(status=FormCheckStatus.PENDING)
                )
                await db_session.commit()
                logger.info(
                    "[CeleryTask] FormCheck %s released back to PENDING for retry.",
                    form_check_id,
                )
            except Exception as e_release:
                # The DB is very likely what just failed, so this can fail too.
                # The stuck-row reaper is the backstop for exactly this case.
                logger.error(
                    "[CeleryTask] Could not release FormCheck %s back to PENDING: "
                    "%s. The reaper will pick it up.", form_check_id, e_release,
                )
        elif not claimed and form_check_service is not None:
            # The services came up but this task never won the row: the claim
            # found it already PROCESSING/terminal, or get_async found nothing.
            # Either way it is not ours to finalize. The raw fallback below stays
            # reachable for the case where the services never initialised, and
            # it is guarded on PENDING, so it cannot rewrite a finished row.
            logger.info(
                "[CeleryTask] FormCheck %s was never claimed by this task; row left untouched (G-48).",
                form_check_id,
            )
        elif form_check_service and form_check_id: # Ensure form_check_id is available
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

        # Catch any temp file registered but not released -- e.g. the task was
        # cancelled between NamedTemporaryFile creation and the caller binding
        # the returned path, so the inner `finally` had nothing to delete.
        _swept = _sweep_task_temp_files()
        if _swept:
            logger.warning(
                f"[CeleryTask] Task-level sweep removed {_swept} leaked temp file(s) "
                f"for FormCheck {form_check_id}."
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

    if transient_exc is not None:
        # Raised here, after the finally block, so the DB session is closed and
        # the row is back at PENDING before Celery is told to retry.
        raise transient_exc

    logger.info(f"[CeleryTask] Finished processing FormCheck ID: {form_check_id} with status: {final_status.value}")
    return {"status": final_status.value, "form_check_id": str(form_check_id), "final_score": analysis_output_for_finalize.get("score")}

# To make this task discoverable, ensure __init__.py in the tasks folder (and its parent app folder)
# imports this module or the celery_app directly.
# e.g. in app/tasks/__init__.py:
# from .analysis_tasks import process_form_check_task 