"""Celery tasks for AI processing."""

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional
import tempfile

from celery import Task, states
from celery.exceptions import Ignore, Reject, Retry

from app.core.celery_app import celery_app as app
from app.core.config import Settings
from app.core.db_deps import get_async_db as get_celery_db_session_context
from app.services.storage_service import StorageService
from app.services.video_service import VideoService
from app.services.ai_service import AIService # Assuming AIService will have the core logic
from app.models.enums import VideoStatus
from app.services.exercise_config_service import ExerciseConfigService
from app.services.dynamic_form_analysis_service import DynamicFormAnalysisService
from app.db.session import SessionLocal, get_settings_override
from app.services.form_check_service import FormCheckService

logger = logging.getLogger(__name__)

def get_app_settings() -> Settings:
    return Settings()

@app.task(bind=True, max_retries=3, default_retry_delay=120) # Increased retry delay
async def detect_pose_celery_task(self, video_id_str: str, frame_s3_keys: list[str]):
    """
    Celery task to detect poses from a list of S3 frame keys.
    Args:
        video_id_str (str): The UUID of the Video record, as a string.
        frame_s3_keys (list[str]): List of S3 object keys for the frames to process.
    """
    video_id = UUID(video_id_str)
    logger.info(f"Starting pose detection Celery task for video_id: {video_id}, with {len(frame_s3_keys)} frames.")

    settings_instance = get_app_settings()
    storage_service_instance = StorageService() # Uses global provider by default
    # AIService is likely stateless or gets its own resources, so direct instantiation might be fine.
    # If it needs settings or other deps, adjust instantiation.
    ai_service_instance = AIService(app_settings=settings_instance)

    async with get_celery_db_session_context() as db:
        video_service_instance = VideoService(
            db=db,
            storage_service=storage_service_instance, # VideoService might need this for other ops
            app_settings=settings_instance
        )

        try:
            await video_service_instance.set_video_status_from_task(video_id, new_status=VideoStatus.POSE_DETECTION_IN_PROGRESS)
            
            if not frame_s3_keys:
                logger.warning(f"No frame S3 keys provided for video {video_id}. Marking as POSE_DETECTION_FAILED.")
                await video_service_instance.set_video_status_from_task(
                    video_id,
                    VideoStatus.POSE_DETECTION_FAILED,
                    error_msg="No frame S3 keys"
                )
                return {"status": "failed", "video_id": str(video_id), "error": "No frame S3 keys"}

            # Download frames from S3 into memory (or temp files if very large/many)
            # For simplicity, let's process them one by one or batch them if AIService supports it.
            # AIService.process_frames_for_pose is expected to take a list of numpy arrays (frames).
            
            frames_data_np: list[np.ndarray] = []
            failed_downloads = 0
            for s3_key in frame_s3_keys:
                try:
                    frame_bytes = await storage_service_instance.download_file(s3_key)
                    # Convert bytes to NumPy array
                    frame_np = cv2.imdecode(np.frombuffer(frame_bytes, np.uint8), cv2.IMREAD_COLOR)
                    if frame_np is None:
                        logger.warning(f"Failed to decode frame from S3 key {s3_key} for video {video_id}. Skipping.")
                        # Potentially collect these and report, or fail if too many.
                        failed_downloads +=1
                        continue
                    frames_data_np.append(frame_np)
                except Exception as e_download:
                    logger.error(f"Failed to download/decode frame {s3_key} for video {video_id}: {e_download}", exc_info=True)
                    failed_downloads +=1
                    # Decide on failure strategy: e.g., fail if more than X% frames fail to download
                    if failed_downloads > len(frame_s3_keys) * 0.5: # Example: fail if > 50% fail
                         await video_service_instance.set_video_status_from_task(
                            video_id, VideoStatus.POSE_DETECTION_FAILED, error_msg=f"Failed to download sufficient frames from S3: {e_download}"
                        )
                         return {"status": "failed", "video_id": str(video_id), "error": f"S3 download failed for too many frames: {e_download}"}
                    continue # Skip this frame

            if not frames_data_np:
                logger.error(f"No frames could be successfully downloaded/decoded for video {video_id}.")
                await video_service_instance.set_video_status_from_task(
                    video_id, VideoStatus.POSE_DETECTION_FAILED, error_msg="Failed to download/decode any frames from S3."
                )
                return {"status": "failed", "video_id": str(video_id), "error": "No frames downloaded/decoded."}

            # Call AIService to process frames and detect poses
            # Assuming AIService.process_frames_for_pose returns a list of pose data per frame
            # (e.g., List[Optional[Dict[str, Any]]], where Dict contains keypoints)
            # This method in AIService needs to be async or run in a thread.
            
            logger.info(f"Calling AIService.process_frames_for_pose for video {video_id} with {len(frames_data_np)} frames.")
            
            # The AIService.process_frames_for_pose method itself might be a bottleneck.
            # It uses asyncio.to_thread internally for its CPU-bound MediaPipe calls per frame.
            pose_results_per_frame = await ai_service_instance.process_frames_for_pose(frames_data_np)
            
            # Store pose_results in the Video model (e.g., in a JSON field like `raw_pose_data`)
            # This method `update_video_pose_data_and_status` needs to be created in VideoService
            await video_service_instance.update_video_pose_data_and_status(
                video_id=video_id,
                pose_data=pose_results_per_frame,
                status=VideoStatus.POSE_DETECTED 
            )
            
            logger.info(f"Pose detection successful for video {video_id}. Stored {len(pose_results_per_frame)} pose results.")
            
            # Next step: Enqueue Angle Calculation Task
            # Update status to ANGLE_CALCULATION_PENDING before enqueuing
            await video_service_instance.set_video_status_from_task(video_id, new_status=VideoStatus.ANGLE_CALCULATION_PENDING)
            calculate_angles_celery_task.apply_async(args=[str(video_id)], countdown=10) # Add a small countdown if desired
            logger.info(f"Enqueued angle calculation task for video {video_id}.")

            return {"status": "success", "video_id": str(video_id), "pose_results_count": len(pose_results_per_frame)}

        except Exception as e:
            logger.error(f"Error during pose detection for video_id {video_id}: {e}", exc_info=True)
            try:
                await video_service_instance.set_video_status_from_task(
                    video_id, 
                    VideoStatus.POSE_DETECTION_FAILED, 
                    error_msg=str(e)
                )
            except Exception as e_db_update:
                logger.error(f"Failed to update video status to FAILED for {video_id} after error: {e_db_update}", exc_info=True)
            raise self.retry(exc=e) from e 

@app.task(bind=True, max_retries=3, default_retry_delay=180) # Longer delay for potentially sequential tasks
async def calculate_angles_celery_task(self, video_id_str: str):
    """
    Celery task to calculate joint angles from stored raw_pose_data for a video.
    Args:
        video_id_str (str): The UUID of the Video record, as a string.
    """
    video_id = UUID(video_id_str)
    logger.info(f"Starting angle calculation Celery task for video_id: {video_id}.")

    settings_instance = get_app_settings()
    storage_service_instance = StorageService() # May not be needed directly by VideoService for this op
    ai_service_instance = AIService(app_settings=settings_instance)

    async with get_celery_db_session_context() as db:
        video_service_instance = VideoService(
            db=db,
            storage_service=storage_service_instance, # Provide it just in case
            app_settings=settings_instance
        )

        try:
            video = await video_service_instance.get_video_by_id(video_id) # Using existing simple getter
            if not video:
                logger.error(f"Video {video_id} not found for angle calculation. Aborting task.")
                # No retry, as video not existing is a permanent issue for this task context
                return {"status": "failed", "video_id": str(video_id), "error": "Video not found"}
            
            if not video.raw_pose_data:
                logger.warning(f"Video {video_id} has no raw_pose_data. Marking as ANGLE_CALCULATION_FAILED.")
                await video_service_instance.set_video_status_from_task(
                    video_id,
                    VideoStatus.ANGLE_CALCULATION_FAILED,
                    error_msg="No raw_pose_data available for angle calculation."
                )
                return {"status": "failed", "video_id": str(video_id), "error": "No raw_pose_data"}

            # Update status to indicate angle calculation is in progress
            # We might need a new status like VideoStatus.ANGLE_CALCULATION_IN_PROGRESS
            # For now, let's assume it moves from POSE_DETECTED directly to ANGLES_CALCULATED or FAILED
            # Or, if VideoService.update_video_calculated_angles_and_status handles this, it's fine.

            logger.info(f"Calling AIService.calculate_angles_for_pose_sequence for video {video_id}.")
            calculated_angles_per_frame = await ai_service_instance.calculate_angles_for_pose_sequence(video.raw_pose_data)

            # Store calculated_angles in the Video model
            # This method `update_video_calculated_angles_and_status` needs to be created in VideoService
            await video_service_instance.update_video_calculated_angles_and_status(
                video_id=video_id,
                calculated_angles=calculated_angles_per_frame,
                status=VideoStatus.ANGLES_CALCULATED # New status needed
            )
            
            logger.info(f"Angle calculation successful for video {video_id}. Stored {len(calculated_angles_per_frame)} angle sets.")
            
            # Next step: Enqueue Form Analysis Task
            await video_service_instance.set_video_status_from_task(video_id, new_status=VideoStatus.FORM_ANALYSIS_PENDING)
            perform_form_analysis_celery_task.apply_async(args=[str(video_id)], countdown=10) # Add a small countdown
            logger.info(f"Enqueued form analysis task for video {video_id}.")

            return {"status": "success", "video_id": str(video_id), "angle_sets_count": len(calculated_angles_per_frame)}

        except Exception as e:
            logger.error(f"Error during angle calculation for video_id {video_id}: {e}", exc_info=True)
            try:
                await video_service_instance.set_video_status_from_task(
                    video_id, 
                    VideoStatus.ANGLE_CALCULATION_FAILED, # New status needed
                    error_msg=str(e)
                )
            except Exception as e_db_update:
                logger.error(f"Failed to update video status to ANGLE_CALCULATION_FAILED for {video_id} after error: {e_db_update}", exc_info=True)
            raise self.retry(exc=e) from e 

@app.task(name="ai.perform_form_analysis", bind=True,
                autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={'max_retries': 3})
async def perform_form_analysis_celery_task(self, video_id_str: str):
    """
    Celery task to perform dynamic form analysis on a video.
    """
    logger.info(f"Celery task started: Perform dynamic form analysis for video ID: {video_id_str}")
    video_id = UUID(video_id_str)
    db_session = None
    try:
        # Create a new database session for the task
        db_session = SessionLocal()
        settings = get_settings_override() # Get settings for the task environment

        video_service = VideoService(db_session=db_session)
        exercise_config_service = ExerciseConfigService(db_session=db_session, settings=settings)
        form_check_service = FormCheckService(db_session=db_session)

        dynamic_analysis_service = DynamicFormAnalysisService(
            db_session=db_session, 
            settings=settings, 
            exercise_config_service=exercise_config_service,
            form_check_service=form_check_service
        )

        video = await video_service.get_video_by_id_async(video_id)
        if not video:
            logger.error(f"Video with ID {video_id} not found. Cannot perform analysis.")
            # Optionally update FormCheck status to failed if one was created prematurely
            return f"Video {video_id} not found."

        # TODO: Consider updating Video/FormCheck status to 'ANALYZING' here

        logger.info(f"Calling DynamicFormAnalysisService for video {video_id}")
        form_check_result = await dynamic_analysis_service.analyze_form_dynamically(video)
        
        logger.info(f"Dynamic form analysis completed for video ID: {video_id}. FormCheck ID: {form_check_result.id}, Status: {form_check_result.status}")
        # TODO: Consider updating Video/FormCheck status to 'ANALYSIS_COMPLETE' or 'ANALYSIS_FAILED' based on form_check_result.status
        
        return f"Analysis complete for video {video_id}. FormCheck ID: {form_check_result.id}, Score: {form_check_result.overall_score}"

    except Exception as e:
        logger.error(f"Error during dynamic form analysis for video {video_id}: {e}", exc_info=True)
        # TODO: Update FormCheck status to 'ANALYSIS_FAILED'
        # Example: 
        # if db_session and video_id: # Ensure db_session and video_id are available
        #     fc_service = FormCheckService(db_session)
        #     fc, _ = await fc_service.get_or_create_form_check_for_video(video_id=video_id)
        #     if fc:
        #         fc.status = "analysis_failed"
        #         fc.overall_feedback = f"Celery task failed: {str(e)[:2000]}"
        #         await db_session.merge(fc)
        #         await db_session.commit()
        raise # Re-raise for Celery to handle retry/failure
    finally:
        if db_session:
            await db_session.close()
            logger.info(f"Closed database session for video ID: {video_id_str}")