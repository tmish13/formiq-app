"""Celery tasks for AI processing."""

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional
import tempfile
from uuid import UUID
import numpy as np
import cv2

from celery import Task, states
from celery.exceptions import Ignore, Reject, Retry

from app.core.celery_app import celery_app as app
from app.core.config import Settings
from app.core.db_deps import get_async_db as get_celery_db_session_context
from app.services.storage_service import StorageService
from app.services.video_service import VideoService
from app.services.ai_service import AIService
from app.models.enums import VideoStatus
from app.services.exercise_config_service import ExerciseConfigService
from app.services.dynamic_form_analysis_service import DynamicFormAnalysisService
from app.db.session import SessionLocal, get_settings_override
from app.services.form_check_service import FormCheckService
from app.tasks.analysis_tasks import process_form_check_task

logger = logging.getLogger(__name__)

def get_app_settings() -> Settings:
    return Settings()

@app.task(bind=True, max_retries=3, default_retry_delay=120)
async def detect_pose_celery_task(self, video_id_str: str, frame_s3_keys: list[str]):
    """
    Celery task to detect poses from a list of S3 frame keys.
    Args:
        video_id_str (str): The UUID of the Video record, as a string.
        frame_s3_keys (list[str]): List of S3 object keys for the frames to process.
    """
    video_id = UUID(video_id_str)
    logger.info(f"Starting pose detection Celery task for video_id: {video_id}, with {len(frame_s3_keys)} frames.")

    settings_instance = get_settings_override()
    storage_service_instance = StorageService(app_settings=settings_instance)
    ai_service_instance = AIService(app_settings=settings_instance)

    async with get_celery_db_session_context() as db:
        video_service_instance = VideoService(
            db=db,
            storage_service=storage_service_instance,
            app_settings=settings_instance
        )
        current_video = None
        try:
            current_video = await video_service_instance.get_async(id=video_id)
            if not current_video:
                logger.error(f"Video {video_id} not found. Aborting pose detection task.")
                self.update_state(state=states.FAILURE, meta={'exc_type': 'VideoNotFound', 'exc_message': f'Video {video_id} not found.'})
                raise Ignore()

            await video_service_instance.set_video_status_from_task(video_id, new_status=VideoStatus.POSE_DETECTION_IN_PROGRESS)
            
            if not frame_s3_keys:
                logger.warning(f"No frame S3 keys provided for video {video_id}. Marking as POSE_DETECTION_FAILED.")
                await video_service_instance.set_video_status_from_task(
                    video_id,
                    VideoStatus.POSE_DETECTION_FAILED,
                    error_msg="No frame S3 keys"
                )
                return {"status": "failed", "video_id": str(video_id), "error": "No frame S3 keys"}

            frames_data_np: list[np.ndarray] = []
            failed_downloads = 0
            for s3_key in frame_s3_keys:
                try:
                    frame_bytes = await storage_service_instance.download_file(s3_key)
                    if frame_bytes is None:
                        logger.warning(f"Downloaded None for frame {s3_key} for video {video_id}. Skipping.")
                        failed_downloads += 1
                        continue

                    frame_np = cv2.imdecode(np.frombuffer(frame_bytes, np.uint8), cv2.IMREAD_COLOR)
                    if frame_np is None:
                        logger.warning(f"Failed to decode frame from S3 key {s3_key} for video {video_id}. Skipping.")
                        failed_downloads += 1
                        continue
                    frames_data_np.append(frame_np)
                except Exception as e_download:
                    logger.error(f"Failed to download/decode frame {s3_key} for video {video_id}: {e_download}", exc_info=True)
                    failed_downloads += 1
                    if failed_downloads > len(frame_s3_keys) * 0.5:
                        await video_service_instance.set_video_status_from_task(
                            video_id, VideoStatus.POSE_DETECTION_FAILED, error_msg=f"Failed to download sufficient frames from S3: {e_download}"
                        )
                        return {"status": "failed", "video_id": str(video_id), "error": f"S3 download failed for too many frames: {e_download}"}
                    continue

            if not frames_data_np:
                logger.error(f"No frames could be successfully downloaded/decoded for video {video_id}.")
                await video_service_instance.set_video_status_from_task(
                    video_id, VideoStatus.POSE_DETECTION_FAILED, error_msg="Failed to download/decode any frames from S3."
                )
                return {"status": "failed", "video_id": str(video_id), "error": "No frames downloaded/decoded."}

            logger.info(f"Calling AIService.process_frames_for_pose for video {video_id} with {len(frames_data_np)} frames.")
            
            raw_pose_results_per_frame = await ai_service_instance.process_frames_for_pose(
                frames_data_np=frames_data_np,
                min_pose_confidence_threshold=settings_instance.AI_MIN_DETECTION_CONFIDENCE
            )

            # Check if all frames failed detection
            if not raw_pose_results_per_frame or all(result is None for result in raw_pose_results_per_frame):
                logger.error(f"All frames failed pose detection for video {video_id}.")
                error_msg_all_fail = "All frames failed pose detection after AI processing."
                await video_service_instance.update_video_raw_pose_data_and_status(
                    video_id=video_id,
                    raw_pose_data=None,
                    status=VideoStatus.POSE_DETECTION_FAILED,
                    error_message=json.dumps({"error_type": "PoseDetectionError", "details": error_msg_all_fail})
                )
                return {
                    "status": "failure", 
                    "video_id": str(video_id), 
                    "message": error_msg_all_fail,
                    "error": "All frames failed AI pose detection."
                }
            
            filtered_pose_results = [result for result in raw_pose_results_per_frame if result is not None]

            # Successfully processed, update video record with pose data and new status
            logger.info(f"Pose detection successful for video {video_id}. Stored {len(filtered_pose_results)} raw pose results.")
            await video_service_instance.update_video_raw_pose_data_and_status(
                video_id=current_video.id,
                raw_pose_data=filtered_pose_results,
                status=VideoStatus.POSE_DETECTED,
                error_message=None
            )
            
            await video_service_instance.set_video_status_from_task(video_id, new_status=VideoStatus.ANGLE_CALCULATION_PENDING)
            calculate_angles_celery_task.apply_async(args=[str(video_id)], countdown=10)
            logger.info(f"Enqueued angle calculation task for video {video_id}.")

            return {
                "status": "success", 
                "video_id": str(video_id), 
                "message": f"Pose detection successful. Stored raw pose data. Enqueued angle calculation.",
                "pose_results_count": len(filtered_pose_results) if filtered_pose_results else 0
            }

        except Retry as r_exc:
            logger.warning(f"Pose detection task for video {video_id} is being retried: {r_exc}")
            raise
        except Ignore as i_exc:
            logger.warning(f"Pose detection task for video {video_id} is being ignored: {i_exc}")
            raise
        except Exception as e:
            logger.error(f"Error during pose detection for video_id {video_id}: {e}", exc_info=True)
            error_details = {"error_type": e.__class__.__name__, "details": str(e)}
            if current_video:
                try:
                    await video_service_instance.update_video_raw_pose_data_and_status(
                        video_id=video_id,
                        raw_pose_data=None,
                        status=VideoStatus.POSE_DETECTION_FAILED, 
                        error_message=json.dumps(error_details)
                    )
                except Exception as e_db_update:
                    logger.error(f"Failed to update video status to FAILED for {video_id} after error: {e_db_update}", exc_info=True)
            raise self.retry(exc=e) from e

@app.task(bind=True, max_retries=3, default_retry_delay=180)
async def calculate_angles_celery_task(self, video_id_str: str):
    """
    Celery task to calculate joint angles from stored raw_pose_data for a video.
    Args:
        video_id_str (str): The UUID of the Video record, as a string.
    """
    video_id = UUID(video_id_str)
    logger.info(f"Starting angle calculation Celery task for video_id: {video_id}.")

    settings_instance = get_settings_override()
    storage_service_instance = StorageService()
    ai_service_instance = AIService(app_settings=settings_instance)

    async with get_celery_db_session_context() as db:
        video_service_instance = VideoService(
            db=db,
            storage_service=storage_service_instance,
            app_settings=settings_instance
        )
        current_video = None
        try:
            current_video = await video_service_instance.get_async(id=video_id)
            if not current_video:
                logger.error(f"Video {video_id} not found for angle calculation. Aborting task.")
                self.update_state(state=states.FAILURE, meta={'exc_type': 'VideoNotFound', 'exc_message': f'Video {video_id} not found.'})
                raise Ignore()

            if current_video.raw_pose_data is None:
                logger.warning(f"Video {video_id} has no raw_pose_data. Marking as ANGLE_CALCULATION_FAILED.")
                await video_service_instance.update_video_calculated_angles_and_status(
                    video_id,
                    calculated_angles=None,
                    status=VideoStatus.ANGLE_CALCULATION_FAILED,
                    error_message="No raw_pose_data available for angle calculation."
                )
                return {"status": "failed", "video_id": str(video_id), "error": "No raw_pose_data"}

            await video_service_instance.set_video_status_from_task(video_id, new_status=VideoStatus.ANGLE_CALCULATION_IN_PROGRESS)

            # --- BEGIN SMOOTHING STEP ---
            logger.info(f"Calling AIService.smooth_and_interpolate_poses for video {video_id}.")
            smoothed_pose_sequence = await ai_service_instance.smooth_and_interpolate_poses(
                pose_sequence=current_video.raw_pose_data,
                # num_expected_landmarks can be taken from AIService or settings if configurable
                # smoothing_window_size and max_interpolation_gap can also be from settings
            )
            if not smoothed_pose_sequence:
                logger.warning(f"Smoothing/interpolation resulted in empty pose sequence for video {video_id}. Using raw_pose_data for angles.")
                # Fallback to raw_pose_data if smoothing fails to produce anything, or handle as error
                pose_data_for_angles = current_video.raw_pose_data 
            else:
                logger.info(f"Successfully smoothed/interpolated pose data for video {video_id}. Storing in Video.pose_data.")
                # Update the video record with the smoothed pose data
                current_video = await video_service_instance.update_video_smoothed_pose_data(
                    video_id=video_id,
                    smoothed_pose_data=smoothed_pose_sequence
                )
                # Refresh is important if current_video object is used later and needs to reflect this change
                await db.refresh(current_video) 
                pose_data_for_angles = current_video.pose_data
            
            if pose_data_for_angles is None:
                 logger.error(f"No pose data available (raw or smoothed) for angle calculation for video {video_id}. Marking as FAILED.")
                 await video_service_instance.update_video_calculated_angles_and_status(
                    video_id,
                    calculated_angles=None,
                    status=VideoStatus.ANGLE_CALCULATION_FAILED,
                    error_message="No pose data available (raw or smoothed) for angle calculation."
                )
                 return {"status": "failed", "video_id": str(video_id), "error": "No pose data available for angle calculation"}
            # --- END SMOOTHING STEP ---

            logger.info(f"Calling AIService.calculate_angles_for_pose_sequence for video {video_id}.")
            # The pose_data_for_angles is List[Optional[List[Optional[Dict[str, Any]]]]]
            # calculate_angles_for_pose_sequence expects this type.
            raw_angles_per_frame = await ai_service_instance.calculate_angles_for_pose_sequence(
                pose_sequence=pose_data_for_angles
            )

            if raw_angles_per_frame is None or (raw_angles_per_frame and all(frame_angles is None for frame_angles in raw_angles_per_frame)):
                logger.error(f"Angle calculation resulted in no angles for video {video_id}. Marking as ANGLE_CALCULATION_FAILED.")
                await video_service_instance.update_video_calculated_angles_and_status(
                    video_id,
                    calculated_angles=None,
                    status=VideoStatus.ANGLE_CALCULATION_FAILED,
                    error_message="Angle calculation resulted in no angles or all frames failed."
                )
                return {"status": "failed", "video_id": str(video_id), "error": "No angles calculated"}

            logger.info(f"Successfully calculated raw angles for {len(raw_angles_per_frame)} frames for video {video_id}. Now smoothing angles.")

            # --- BEGIN ANGLE SMOOTHING STEP ---
            # raw_angles_per_frame is List[Optional[Dict[str, float]]]
            # smooth_angle_trajectories expects this type.
            smoothed_angles_per_frame = ai_service_instance.smooth_angle_trajectories(
                raw_angles_per_frame=raw_angles_per_frame,
                # smoothing_window and max_gap_to_interpolate can be from settings if needed
            )
            # --- END ANGLE SMOOTHING STEP ---

            if not smoothed_angles_per_frame or all(frame_angles is None for frame_angles in smoothed_angles_per_frame):
                logger.warning(f"Angle smoothing resulted in no angles for video {video_id}. Using raw angles if available, or marking as FAILED.")
                final_angles_to_store = raw_angles_per_frame # Fallback to raw if smoothing failed
                
                # Check if the fallback (raw angles) is also unusable
                if final_angles_to_store is None or (final_angles_to_store and all(fa is None for fa in final_angles_to_store)):
                    logger.error(f"Both raw and smoothed angles are empty or invalid for video {video_id}. Marking as ANGLE_CALCULATION_FAILED.")
                    await video_service_instance.update_video_calculated_angles_and_status(
                        video_id,
                        calculated_angles=None,
                        status=VideoStatus.ANGLE_CALCULATION_FAILED,
                        error_message="Angle calculation and smoothing resulted in no valid angle data."
                    )
                    return {"status": "failed", "video_id": str(video_id), "error": "No angles after calculation and smoothing"}
                # If raw angles are valid (even if empty list), we use them.
            else:
                final_angles_to_store = smoothed_angles_per_frame

            # At this point, final_angles_to_store is determined. It can be an empty list [],
            # a list of angle dicts, or a list with some None frames. All these are considered success for storage.
            # The previous duplicated check for `final_angles_to_store is None or (final_angles_to_store and all(fa is None for fa in final_angles_to_store))`
            # which led to failure for an empty list should be removed if it was added again by mistake.
            # The critical part is that an empty list `[]` for `final_angles_to_store` IS a success scenario.

            logger.info(f"Angle calculation and smoothing successful for video {video_id}. Storing {len(final_angles_to_store)} sets of frame angles.")
            await video_service_instance.update_video_calculated_angles_and_status(
                video_id=video_id,
                calculated_angles=final_angles_to_store, # Store the smoothed (or fallback raw) angles
                status=VideoStatus.ANGLES_CALCULATED,
                error_message=None
            )
            
            # TODO: Trigger next step in pipeline, e.g., form analysis task
            # Example: process_form_check_task.apply_async(args=[str(video_id)], countdown=5)
            logger.info(f"Angle calculation complete for video {video_id}. Next step (e.g. form analysis) should be triggered.")

            return {
                "status": "success", 
                "video_id": str(video_id), 
                "message": "Angle calculation and smoothing successful. Stored calculated angles.",
                "num_angle_frames": len(final_angles_to_store)
            }

        except Retry as r_exc:
            logger.warning(f"Angle calculation task for video {video_id} is being retried: {r_exc}")
            raise
        except Ignore as i_exc:
            logger.warning(f"Angle calculation task for video {video_id} is being ignored: {i_exc}")
            raise
        except Exception as e:
            logger.error(f"Error during angle calculation for video_id {video_id}: {e}", exc_info=True)
            error_details = {"error_type": e.__class__.__name__, "details": str(e)}
            if current_video:
                try:
                    await video_service_instance.update_video_calculated_angles_and_status(
                        video_id, 
                        calculated_angles=None,
                        status=VideoStatus.ANGLE_CALCULATION_FAILED, 
                        error_message=json.dumps(error_details)
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
    db_session_local_instance = None
    settings = get_settings_override()
    current_video_obj = None
    try:
        db_session_local_instance = SessionLocal()

        async with get_celery_db_session_context() as db_async_session:
            video_service = VideoService(db_async_session, storage_service=StorageService(), app_settings=settings)
            exercise_config_service = ExerciseConfigService(db_session=db_async_session, settings=settings)
            form_check_service = FormCheckService(db_session=db_async_session, settings=settings)

            dynamic_analysis_service = DynamicFormAnalysisService(
                db_session=db_async_session, 
                settings=settings, 
                exercise_config_service=exercise_config_service,
                form_check_service=form_check_service,
                ai_service=AIService(app_settings=settings)
            )

            current_video_obj = await video_service.get_async(id=video_id)
            if not current_video_obj:
                logger.error(f"Video with ID {video_id} not found. Cannot perform analysis.")
                self.update_state(state=states.FAILURE, meta={'exc_type': 'VideoNotFound', 'exc_message': f'Video {video_id} not found.'})
                raise Ignore()
            
            if not current_video_obj.calculated_angles:
                logger.warning(f"Video {video_id} has no calculated_angles. Marking as FORM_ANALYSIS_FAILED.")
                await video_service.set_video_status_from_task(
                    video_id, 
                    VideoStatus.FORM_ANALYSIS_FAILED, 
                    error_msg="No calculated_angles available for form analysis."
                )
                return {"status": "failed", "video_id": str(video_id), "error": "No calculated_angles"}

            await video_service.set_video_status_from_task(video_id, new_status=VideoStatus.FORM_ANALYSIS_IN_PROGRESS)
            logger.info(f"Calling DynamicFormAnalysisService for video {video_id}")
            
            form_check_result_model = await dynamic_analysis_service.analyze_form_dynamically(current_video_obj)
            
            logger.info(f"Dynamic form analysis completed for video ID: {video_id}. FormCheck ID: {form_check_result_model.id}, Status: {form_check_result_model.status}")
            
            if form_check_result_model.status == "completed":
                await video_service.set_video_status_from_task(video_id, VideoStatus.ANALYSIS_COMPLETE)
            else:
                await video_service.set_video_status_from_task(video_id, VideoStatus.FORM_ANALYSIS_FAILED, error_msg=f"FormCheck status: {form_check_result_model.status}")

            return f"Analysis complete for video {video_id}. FormCheck ID: {form_check_result_model.id}, Score: {form_check_result_model.overall_score}"

    except Retry as r_exc:
        logger.warning(f"Form analysis task for video {video_id} is being retried: {r_exc}")
        raise
    except Ignore as i_exc:
        logger.warning(f"Form analysis task for video {video_id} is being ignored: {i_exc}")
        raise
    except Exception as e:
        logger.error(f"Error during dynamic form analysis for video {video_id}: {e}", exc_info=True)
        error_details = {"error_type": e.__class__.__name__, "details": str(e)}
        if current_video_obj:
            try:
                async with get_celery_db_session_context() as db_async_session_on_error:
                    video_service_on_error = VideoService(db_async_session_on_error, storage_service=StorageService(), app_settings=settings)
                    await video_service_on_error.set_video_status_from_task(
                        video_id, 
                        VideoStatus.FORM_ANALYSIS_FAILED, 
                        error_msg=json.dumps(error_details)
                    )
            except Exception as e_db_update:
                logger.error(f"Failed to update video status to FORM_ANALYSIS_FAILED for {video_id} after error: {e_db_update}", exc_info=True)
        raise self.retry(exc=e) from e