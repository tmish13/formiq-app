import logging
import os
from uuid import UUID
import shutil

from backend.app.core.celery_app import celery_app as app # Ensure this is the actual Celery app import

from backend.app.services.video_processing_service import VideoProcessingService
from backend.app.services.video_service import VideoService # For updating Video model
from backend.app.services.storage_service import StorageService # For S3 and VideoService constructor
from backend.app.models.enums import ExerciseType, VideoStatus, MimeType
from backend.app.core.config import Settings
from backend.app.core.db_deps import get_async_db as get_celery_db_session_context # MODIFIED IMPORT
from backend.app.tasks.ai_tasks import detect_pose_celery_task # Import the new AI task


def get_app_settings() -> Settings:
    return Settings()

logger = logging.getLogger(__name__)

@app.task(bind=True, max_retries=3, default_retry_delay=60) # Example retry configuration
async def process_video_celery_task(self, video_id_str: str, original_video_path: str, exercise_type_value: str):
    """
    Celery task to process a video: extract frames, preprocess, and save them.
    Args:
        video_id_str (str): The UUID of the Video record, as a string.
        original_video_path (str): Path to the original video file (e.g., S3 URL or local path accessible to worker).
        exercise_type_value (str): String value of the ExerciseType enum.
    """
    video_id = UUID(video_id_str)
    logger.info(f"Starting video processing Celery task for video_id: {video_id}")
    
    settings_instance = get_app_settings()
    storage_service_instance = StorageService(settings=settings_instance) 
    
    async with get_celery_db_session_context() as db:
        video_service_instance = VideoService(
            db=db, 
            storage_service=storage_service_instance, 
            app_settings=settings_instance
        )
        
        try:
            await video_service_instance.set_video_status_from_task(video_id, new_status=VideoStatus.PROCESSING)

            video_data: bytes
            if original_video_path.startswith("s3://"):
                video_data = await storage_service_instance.download_file_bytes(original_video_path)
            else: 
                if not os.path.exists(original_video_path):
                    logger.error(f"Original video path not found: {original_video_path}")
                    raise FileNotFoundError(f"Original video not found at {original_video_path}")
                with open(original_video_path, 'rb') as vf:
                    video_data = vf.read()
            
            exercise_type = ExerciseType(exercise_type_value)

            if not hasattr(settings_instance, 'CELERY_SHARED_DATA_PATH') or not settings_instance.CELERY_SHARED_DATA_PATH:
                 logger.error("CELERY_SHARED_DATA_PATH is not configured in settings.")
                 raise ValueError("CELERY_SHARED_DATA_PATH not configured.")

            processed_frames_output_dir = os.path.join(settings_instance.CELERY_SHARED_DATA_PATH, "processed_frames", str(video_id))
            if not os.path.exists(processed_frames_output_dir):
                os.makedirs(processed_frames_output_dir, exist_ok=True)
            
            video_processor = VideoProcessingService(app_settings=settings_instance)
            result = await video_processor.process_video(
                video_data=video_data,
                exercise_type=exercise_type,
                save_processed_frames=True,
                base_output_path=processed_frames_output_dir
            )

            local_frame_paths = result.get("frame_paths")
            temp_normalized_video_local_path = result.get("normalized_video_path")

            if not local_frame_paths or not temp_normalized_video_local_path:
                logger.error(f"Video processing for {video_id} completed but did not return frame_paths or normalized_video_path.")
                await video_service_instance.set_video_status_from_task(
                    video_id, 
                    VideoStatus.VIDEO_PROCESSING_FAILED, 
                    error_msg="Internal error: Missing frame paths or normalized video path after processing."
                )
                return {"status": "failed", "video_id": str(video_id), "error": "Missing frame_paths or normalized_video_path"}

            # 1. Upload normalized video to S3
            normalized_video_s3_key = f"processed_videos/{video_id}/normalized_{os.path.basename(temp_normalized_video_local_path)}"
            try:
                await storage_service_instance.upload_file_from_path(
                    local_file_path=temp_normalized_video_local_path, 
                    object_key=normalized_video_s3_key
                )
                logger.info(f"Uploaded normalized video for {video_id} to S3: {normalized_video_s3_key}")
            except Exception as e_upload_norm:
                logger.error(f"Failed to upload normalized video {temp_normalized_video_local_path} to S3 for {video_id}: {e_upload_norm}", exc_info=True)
                await video_service_instance.set_video_status_from_task(
                    video_id, VideoStatus.VIDEO_PROCESSING_FAILED, error_msg=f"Failed to upload normalized video to S3: {e_upload_norm}"
                )
                raise self.retry(exc=e_upload_norm) from e_upload_norm

            # 2. Upload processed frames to S3
            uploaded_frame_s3_keys = []
            for local_frame_path in local_frame_paths:
                frame_filename = os.path.basename(local_frame_path)
                frame_s3_key = f"processed_frames/{video_id}/{frame_filename}"
                try:
                    await storage_service_instance.upload_file_from_path(
                        local_file_path=local_frame_path, 
                        object_key=frame_s3_key
                    )
                    uploaded_frame_s3_keys.append(frame_s3_key)
                except Exception as e_upload_frame:
                    logger.error(f"Failed to upload frame {local_frame_path} to S3 for {video_id}: {e_upload_frame}", exc_info=True)
                    await video_service_instance.set_video_status_from_task(
                        video_id, VideoStatus.VIDEO_PROCESSING_FAILED, error_msg=f"Failed to upload frame {frame_filename} to S3: {e_upload_frame}"
                    )
                    raise self.retry(exc=e_upload_frame) from e_upload_frame
            logger.info(f"Uploaded {len(uploaded_frame_s3_keys)} processed frames to S3 for video {video_id}.")

            # 3. Video processing successful, update status and video metadata in DB
            video_metadata_from_processing = result.get("video_metadata")
            duration = video_metadata_from_processing.get("duration") if video_metadata_from_processing else None
            fps = video_metadata_from_processing.get("fps") if video_metadata_from_processing else None
            width = video_metadata_from_processing.get("width") if video_metadata_from_processing else None
            height = video_metadata_from_processing.get("height") if video_metadata_from_processing else None
            resolution_str = f"{width}x{height}" if width and height else None
            actual_frame_count = video_metadata_from_processing.get("actual_frame_count") if video_metadata_from_processing else None

            await video_service_instance.update_video_after_initial_processing(
                video_id=video_id,
                processed_object_key=normalized_video_s3_key, 
                frame_s3_keys=uploaded_frame_s3_keys,
                status=VideoStatus.POSE_DETECTION_PENDING,
                duration=duration,
                fps=fps,
                resolution=resolution_str,
                processed_frame_count=actual_frame_count
            )
            logger.info(f"Successfully processed video {video_id}. Normalized S3 key: {normalized_video_s3_key}. Frame S3 keys: {len(uploaded_frame_s3_keys)}.")

            # 4. Enqueue the pose detection task with S3 keys for frames
            detect_pose_celery_task.apply_async(
                args=[str(video_id), uploaded_frame_s3_keys], # Pass S3 keys
            )
            logger.info(f"Enqueued pose detection task for video {video_id} using S3 frame keys.")

            # Clean up local temp directory after upload
            try:
                shutil.rmtree(processed_frames_output_dir)
                logger.info(f"Cleaned up temp directory {processed_frames_output_dir} for video {video_id}.")
            except Exception as cleanup_err:
                logger.warning(f"Failed to clean up temp directory {processed_frames_output_dir} for video {video_id}: {cleanup_err}")

            return {"status": "success", "video_id": str(video_id), "processed_video_s3_key": normalized_video_s3_key, "processed_frames_s3_keys": uploaded_frame_s3_keys}

        except FileNotFoundError as fnf_error:
            logger.error(f"FileNotFoundError processing video_id {video_id}: {fnf_error}", exc_info=True)
            await video_service_instance.set_video_status_from_task(video_id, new_status=VideoStatus.PROCESSING_FAILED, error_msg=str(fnf_error))
            return {"status": "failed", "video_id": str(video_id), "error": str(fnf_error)}
        except ValueError as ve: # Handle configuration errors specifically to avoid retries
            logger.error(f"Configuration ValueError processing video_id {video_id}: {ve}", exc_info=True)
            await video_service_instance.set_video_status_from_task(video_id, new_status=VideoStatus.PROCESSING_FAILED, error_msg=f"Configuration error: {ve}")
            # Do not retry configuration errors
            return {"status": "failed", "video_id": str(video_id), "error": f"Configuration error: {ve}"}
        except Exception as e:
            logger.error(f"Error processing video_id {video_id}: {e}", exc_info=True)
            await video_service_instance.set_video_status_from_task(video_id, new_status=VideoStatus.PROCESSING_FAILED, error_msg=str(e))
            raise self.retry(exc=e) from e 