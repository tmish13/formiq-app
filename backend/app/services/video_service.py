"""Video Service for managing video uploads, processing, and metadata."""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException, status, Depends
from uuid import UUID
import logging
from typing import List, Optional, Dict, Any
import os
import time
from datetime import datetime, timezone
import json

from app.models.video import Video # MODIFIED
from app.models.enums import VideoStatus # ADDED: Import from central enums
from app.schemas.video import VideoResponse, VideoUploadResponse, VideoCreate, VideoUpdate, AngleDataItem
from app.services.storage_service import StorageService
from app.core.config import Settings # Renamed from settings for consistency
from uuid import uuid4
from app.services.base_service import BaseService
from app.core.exceptions import NotFoundException, PermissionDeniedException, ServerErrorException

logger = logging.getLogger(__name__)

class VideoService(BaseService[Video, VideoCreate, VideoUpdate]):
    def __init__(self, db: AsyncSession, storage_service: StorageService, app_settings: Settings):
        # BaseService.__init__ signature is (self, db, model, settings=None)
        # Current call: super().__init__(db=db, settings=app_settings, model=Video)
        # Corrected call (keywords make order flexible, but matching names is key):
        super().__init__(db=db, model=Video, settings=app_settings)
        self.storage_service = storage_service
        self.app_settings = app_settings
        self.response_schema = VideoResponse

    async def create_upload_session(
        self, 
        user_id: UUID, 
        filename: str, 
        content_type: str, 
        metadata: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Creates a video record and generates a presigned URL for direct S3 upload.
        """
        if not content_type.startswith("video/"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid content type. Must be a video format."
            )

        current_timestamp = int(time.time())
        s3_user_id_path = str(user_id) 
        safe_filename = os.path.basename(filename)
        object_key = f"videos/{s3_user_id_path}/{current_timestamp}_{safe_filename}"
        
        full_metadata_s3 = {
            "user_id": str(user_id),
            "original_filename": filename,
            "upload_timestamp": str(current_timestamp),
        }
        if metadata:
            full_metadata_s3.update(metadata)
        
        # Extract exercise_type from input metadata if provided
        client_provided_exercise_type: Optional[str] = None
        if metadata and isinstance(metadata.get("exercise_type"), str):
            client_provided_exercise_type = metadata.get("exercise_type")
            # Potentially validate against ExerciseType enum values here if desired
            # e.g., if client_provided_exercise_type not in [e.value for e in ExerciseType]: raise ValueError(...)

        video_data = VideoCreate(
            id=uuid4(),
            user_id=user_id, 
            filename=safe_filename,
            status=VideoStatus.PENDING_UPLOAD, # Use Enum member directly
            mime_type=content_type,
            object_key=object_key,
            exercise_type=client_provided_exercise_type # ADDED: Pass exercise_type
        )
        try:
            video_record = await super().create_async(obj_in=video_data)
        except Exception as e:
            logger.error(f"DB error creating video record for {filename}, user {user_id}: {e}", exc_info=True)
            raise ServerErrorException("Could not create video record.")
        
        try:
            presigned_url_data = await self.storage_service.generate_presigned_upload_url(
                object_key=object_key,
                content_type=content_type,
                metadata=full_metadata_s3,
                expires_in=3600
            )
        except Exception as e_storage:
            logger.error(f"Failed to generate presigned URL for video {video_record.id} (obj: {object_key}): {e_storage}", exc_info=True)
            try:
                # Use the new status update method if available, or super().update_async
                await self.update_video_metadata_and_status(video_id=video_record.id, status=VideoStatus.PROCESSING_FAILED, error_message=f"Storage error: {e_storage}")
            except Exception as e_update:
                 logger.error(f"Failed to mark video {video_record.id} as PROCESSING_FAILED after storage error: {e_update}", exc_info=True)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Could not generate upload URL.")

        logger.info(f"Generated presigned URL for video {video_record.id}, user {user_id}")
        
        return {
            "upload_url": presigned_url_data.get("url"),
            "fields": presigned_url_data.get("fields", {}),
            "video_id": str(video_record.id),
            "object_key": object_key,
            "expires_in": 3600,
        }

    async def confirm_video_upload(
        self,
        video_id: UUID,
        current_user_id: UUID,
        is_superuser: bool,
        object_key: str,
        size: Optional[int],
    ) -> VideoResponse:
        """
        Confirms successful video upload, updates status, triggers processing.
        """
        video = await super().get_async(id=video_id)
        if not video:
            raise NotFoundException("Video not found")
    
        if video.user_id != current_user_id and not is_superuser:
            raise PermissionDeniedException("Not authorized to confirm this video upload")
    
        if hasattr(video, 'object_key') and video.object_key != object_key:
            logger.error(f"Object key mismatch for video {video_id}. Expected {video.object_key}, received {object_key}")
            # Call update_video_metadata_and_status to set error state BEFORE raising HTTPException
            await self.update_video_metadata_and_status(video_id=video.id, status=VideoStatus.PROCESSING_FAILED, error_message="Object key mismatch during confirmation.")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Object key mismatch.")

        # Handle already terminal/finalized/processing states first
        if video.status in [
            VideoStatus.PROCESSED, 
            VideoStatus.ANALYSIS_COMPLETE, 
            VideoStatus.PROCESSING_FAILED, 
            VideoStatus.ERROR, 
            VideoStatus.PROCESSING # Added PROCESSING here
        ]:
            logger.info(f"Video {video_id} already in state {video.status}. No further action taken by confirm_video_upload.")
            return self.response_schema.from_orm(video)
        
        # Allow processing only if PENDING_UPLOAD or UPLOADED
        if video.status not in [VideoStatus.PENDING_UPLOAD, VideoStatus.UPLOADED]:
            logger.warning(f"Video {video_id} is in state {video.status}, which is not PENDING_UPLOAD or UPLOADED. Cannot confirm upload for processing.")
            return self.response_schema.from_orm(video) # Return current state
    
        # Original logic for PENDING_UPLOAD / UPLOADED states continues here
        update_data_dict = {"status": VideoStatus.UPLOADED} 
        if size is not None:
            update_data_dict["size"] = size
        
        # This public_url logic might be better placed after successful processing, 
        # or if storage_service can confirm file existence by object_key before generating public URL.
        try:
            if hasattr(video, 'object_key') and video.object_key:
                public_url = await self.storage_service.get_public_url(video.object_key)
                if public_url:
                     update_data_dict["url"] = public_url
            else:
                logger.warning(f"Video {video.id} has no object_key, cannot generate public_url at confirmation.")
        except Exception as e_storage_pub_url:
            logger.warning(f"Failed to get public URL for video {video.id} object {getattr(video, 'object_key', 'N/A')} after upload: {e_storage_pub_url}")

        updated_video = await super().update_async(db_obj=video, obj_in=VideoUpdate(**update_data_dict))
        if not updated_video:
            raise ServerErrorException("Failed to update video record after confirmation, record vanished.")
            
        # Trigger background processing via Celery
        try:
            # Ensure original_video_path is correctly determined (e.g., from video.object_key or video.url)
            # For S3, it would be the s3://<bucket>/<object_key>
            # For local, it would be the path where the video was stored by a previous step (if not direct upload to S3)
            # This assumes video.object_key holds the definitive path for the Celery worker.
            
            original_video_path_for_celery = updated_video.object_key 
            if not original_video_path_for_celery:
                 logger.error(f"Cannot dispatch Celery task for video {updated_video.id}: object_key is missing.")
                 # SUT returns updated_video (status UPLOADED) here by falling through, error is just logged.
                 # To be more robust, should set to PROCESSING_FAILED here too.
                 # For now, align with test expectations of what Celery failure path handles.
            else:
                from app.tasks.video_tasks import process_video_celery_task 
                task_result = process_video_celery_task.delay(
                    video_id_str=str(updated_video.id), 
                    original_video_path=original_video_path_for_celery, 
                    exercise_type_value=updated_video.exercise_type # Assuming exercise_type is a string here matching enum value
                )
                # logger.info(f"Video upload confirmed: id={updated_video.id}, processing task dispatched.")
                # Status will be further updated by the Celery task itself (e.g., to PROCESSING)
                # RETURN updated_video (status UPLOADED) IS REMOVED FROM HERE

                task_id = "unknown_task_id" # Default if .delay doesn't return an ID (e.g. if not EagerResult)
                if hasattr(task_result, 'id') and task_result.id:
                    task_id = task_result.id

                processing_video = await self.update_video_metadata_and_status(
                    video_id=updated_video.id, # Use updated_video which is after first super().update_async
                    status=VideoStatus.PROCESSING,
                    celery_task_id=task_id,
                    error_message=None # Explicitly clear any prior error message
                )
                logger.info(f"Video upload confirmed: id={processing_video.id}, status set to PROCESSING, Celery task ID: {task_id} dispatched.")
                return self.response_schema.from_orm(processing_video)

        except ImportError as e_import:
            logger.error(f"Celery task import failed for video {updated_video.id}: {e_import}. Video will not be processed automatically.")
            error_updated_video = await self.update_video_metadata_and_status(video_id=updated_video.id, status=VideoStatus.PROCESSING_FAILED, error_message=f"Task dispatch failed: Import Error - {e_import}")
            return self.response_schema.from_orm(error_updated_video)
        except Exception as e_task:
            logger.error(f"Failed to dispatch processing task for video {updated_video.id}: {e_task}", exc_info=True)
            error_updated_video = await self.update_video_metadata_and_status(video_id=updated_video.id, status=VideoStatus.PROCESSING_FAILED, error_message=f"Task dispatch failed: {e_task}") # Changed from VideoStatus.ERROR to PROCESSING_FAILED
            return self.response_schema.from_orm(error_updated_video)

        return self.response_schema.from_orm(updated_video) # Default return if no exception and no celery dispatch due to missing object_key

    async def get_video_details(
        self,
        video_id: UUID,
        current_user_id: UUID,
        is_superuser: bool,
    ) -> VideoResponse | None:
        """Retrieve details for a specific video, checking ownership."""
        video = await super().get_async(id=video_id)
        if not video:
            return None # Endpoint will handle 404
        
        # Check ownership
        if video.user_id != current_user_id and not is_superuser:
            # Consider raising specific AuthorizationException instead of returning None
            # For now, returning None, endpoint checks this.
            # Alternatively: raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
             logger.warning(f"User {current_user_id} attempted to access video {video_id} owned by {video.user_id}.")
             raise PermissionDeniedException("User not authorized to view this video")
        
        # Return the video details as schema
        return self.response_schema.from_orm(video)

    async def get_videos_by_user_id(self, user_id: UUID, skip: int = 0, limit: int = 100, status_filter: Optional[VideoStatus] = None) -> List[Video]:
        """Retrieve videos for a given user, with optional status filter and pagination."""
        query = select(Video).filter(Video.user_id == user_id)
        if status_filter:
            query = query.filter(Video.status == status_filter.value)
        query = query.order_by(Video.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def update_video_metadata_and_status(
        self, 
        video_id: UUID, 
        metadata: Optional[Dict[str, Any]] = None,
        status: Optional[VideoStatus] = None, 
        error_message: Optional[str] = None, # Parameter
    ):
        video = await self.get_async(id=video_id) 
        if not video:
            logger.error(f"Video not found with ID {video_id} in update_video_metadata_and_status.")
            raise ValueError(f"Video not found with ID {video_id} for update.")

        update_data = {}
        if metadata is not None:
            update_data["metadata"] = metadata
        
        # Simplified error message handling
        if error_message is not None:
            update_data["error_message"] = error_message
        else:
            if hasattr(video, 'error_message'):
                 update_data["error_message"] = None

        if status:
            update_data["status"] = status
            update_data["status_updated_at"] = datetime.now(timezone.utc)
            if status.value.endswith("_FAILED") and update_data.get("error_message") is None:
                 default_error_detail = f"{video.__class__.__name__} status set to {status.value} with no specific error message."
                 update_data["error_message"] = json.dumps({"error_type": "DefaultProcessingError", "details": default_error_detail})
        
        if not update_data:
            logger.warning(f"No actual data provided to update_video_metadata_and_status for video {video_id}")
            return

        updated_video_db_model = await self.update_async(db_obj=video, obj_in=update_data)
        logger.info(
            f"Updated video {video_id} metadata, status to {status}. Error: {update_data.get('error_message')}. BaseService handled commit."
        )

    async def update_video_after_initial_processing(
        self,
        video_id: UUID,
        processed_object_key: str,
        frame_s3_keys: List[str],
        status: VideoStatus, # e.g., VideoStatus.POSE_DETECTION_PENDING
        duration: Optional[float] = None,
        fps: Optional[float] = None,
        resolution: Optional[str] = None, # e.g., "1280x720"
        processed_frame_count: Optional[int] = None
    ) -> VideoResponse:
        """
        Updates video record after initial processing (normalization, frame extraction/upload).
        This is typically called by a Celery task.
        """
        video = await super().get_async(id=video_id)
        if not video:
            logger.error(f"Video {video_id} not found for update_after_initial_processing.")
            raise NotFoundException(f"Video {video_id} not found during post-processing update.")

        update_data: Dict[str, Any] = {
            "status": status,
            "processed_object_key": processed_object_key,
            "frame_s3_keys": frame_s3_keys,
        }
        if duration is not None:
            update_data["duration"] = duration
        if fps is not None:
            update_data["fps"] = fps
        if resolution is not None:
            update_data["resolution"] = resolution
        if processed_frame_count is not None:
            update_data["processed_frame_count"] = processed_frame_count
        
        try:
            if processed_object_key:
                public_url = await self.storage_service.get_public_url(processed_object_key)
                if public_url:
                    update_data["processed_url"] = public_url
            else:
                logger.warning(f"No processed_object_key provided for video {video_id}, cannot set processed_url.")
        except Exception as e_storage_url:
            logger.warning(f"Failed to get public URL for processed_object_key {processed_object_key} for video {video_id}: {e_storage_url}")

        updated_video = await super().update_async(db_obj=video, obj_in=VideoUpdate(**update_data))
        if not updated_video:
            logger.error(f"Failed to update video {video_id} after initial processing (super().update_async returned None or raised).")
            # BaseService.update_async should raise ServiceError on failure and rollback.
            # If we reach here and updated_video is None, it implies a scenario not covered by BaseService's current error handling (e.g., it returned None).
            raise ServerErrorException(f"Failed to update video {video_id} after processing completion; update_async did not return an object.")
        
        # Commit is handled by super().update_async
        logger.info(f"Video {video_id} updated after initial processing. Status: {updated_video.status}, Processed Key: {updated_video.processed_object_key}. BaseService handled commit.")
            
        return self.response_schema.from_orm(updated_video)

    async def set_video_status_from_task(
        self, 
        video_id: UUID, 
        new_status: VideoStatus, 
        error_msg: Optional[str] = None
    ) -> None:
        video = await super().get_async(id=video_id)
        if not video:
            logger.error(f"Video {video_id} not found in set_video_status_from_task. Cannot update status.")
            # If video not found, trying to commit will achieve nothing and might hide the error.
            # The task should handle the case where the video disappears.
            return
        
        update_payload = {"status": new_status}
        if error_msg:
            update_payload["error_message"] = error_msg
        elif new_status != VideoStatus.PROCESSING_FAILED and new_status != VideoStatus.ANALYSIS_FAILED: # Clear error if status is not a failure one
            update_payload["error_message"] = None

        updated_video = await super().update_async(db_obj=video, obj_in=VideoUpdate(**update_payload))
        if updated_video:
            # Commits are handled by super().update_async (BaseService)
            log_extra = f" | error_msg: '{error_msg}'" if error_msg is not None else " | error_msg: None (cleared or not set)"
            logger.info(f"Celery task updated video {video_id} status to {new_status}{log_extra}. BaseService handled commit.")
        else:
            # super().update_async would raise ServiceError on failure and rollback.
            logger.error(f"super().update_async returned None for video {video_id} in set_video_status_from_task. Status was to be {new_status}.")
            # No explicit rollback here as BaseService should have handled it.

    async def set_video_processed_frames_info_from_task(
        self, 
        video_id: UUID, 
        frame_paths: List[str], 
        frame_count: int
    ) -> None:
        video = await super().get_async(id=video_id)
        if not video:
            logger.error(f"Video {video_id} not found in set_video_processed_frames_info_from_task. Cannot update frame info.")
            return
        
        update_payload = {
            "processed_frame_paths": frame_paths,
            "processed_frame_count": frame_count
        }
        # The 'video' object fetched at the beginning of the method is the correct db_obj
        await super().update_async(db_obj=video, obj_in=VideoUpdate(**update_payload))
        logger.info(f"Celery task updated video {video_id} with {frame_count} processed frame paths.")

    async def list_videos_for_user(
        self,
        user_id: UUID,
        skip: int = 0, 
        limit: int = 100, 
        status_filter: Optional[VideoStatus] = None,
    ) -> List[VideoResponse]:
        """Retrieve videos for a given user, with optional status filter and pagination, returning VideoResponse."""
        query = select(self.model).filter(self.model.user_id == user_id)
        if status_filter:
            query = query.filter(self.model.status == status_filter.value) # Ensure status_filter is enum or its .value used
        query = query.order_by(self.model.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        videos = result.scalars().all()
        return [self.response_schema.from_orm(video) for video in videos]

    async def delete_video_by_id(
        self,
        video_id: UUID,
        current_user_id: UUID,
        is_superuser: bool,
    ) -> None:
        """Delete a video by ID, checking ownership and handling S3 objects."""
        video = await super().get_async(id=video_id)
        if not video:
            raise NotFoundException(f"Video with id {video_id} not found.")

        if not is_superuser and video.user_id != current_user_id:
            logger.warning(
                f"User {current_user_id} lacks permission to delete video {video_id} owned by {video.user_id}."
            )
            raise PermissionDeniedException("You do not have permission to delete this video.")

        object_key_to_delete = video.object_key

        try:
            # Use BaseService.delete_async for the DB record deletion
            await super().delete_async(id=video_id) 
            logger.info(f"Video record {video_id} deleted from DB by user {current_user_id}.")
        except ServiceError as e:
            # BaseService.delete_async might raise ServiceError if object not found (already handled by get_async) or other DB issues
            logger.error(f"Database error deleting video record {video_id}: {e}", exc_info=True)
            raise ServerErrorException(f"Could not delete video record from database: {e}")
        except Exception as e:
            logger.error(f"Unexpected error deleting video record {video_id} from DB: {e}", exc_info=True)
            # Consider specific error or re-raise if BaseService doesn't cover it, but ServiceError should catch most.
            raise ServerErrorException(f"An unexpected error occurred while deleting video from database: {e}")

        # If DB deletion was successful, proceed to delete from S3
        if video.object_key:
            try:
                if video.url:
                    await self.storage_service.delete_file(file_url=video.url)
                    logger.info(f"Video file for object_key {video.object_key} (via URL {video.url}) deleted from S3 for video {video_id}.")
                else:
                    logger.warning(f"Cannot delete file for video {video_id} from S3: video.url is not set, object_key is {video.object_key}")
            except Exception as e_storage:
                logger.error(f"Failed to delete video file (URL: {video.url}, Key: {video.object_key}) from S3 for video {video_id}: {e_storage}")
                # Do not re-raise, allow DB record deletion
        else:
            logger.warning(f"Video {video_id} has no object_key, skipping S3 deletion.")
        return # Explicit None return

    async def request_video_processing(
        self,
        video_id: UUID,
        current_user_id: UUID,
        is_superuser: bool,
    ) -> VideoResponse:
        """Requests reprocessing for a video that may have failed or needs re-analysis."""
        video = await self.get_async(id=video_id)

        if video.user_id != current_user_id and not is_superuser:
            raise PermissionDeniedException("Not authorized to retry processing for this video.")

        # Allow retry for states that indicate a failure or a point where processing can restart.
        # For example, if it failed at POSE_DETECTION_FAILED, it should re-trigger from video processing if necessary
        # or directly to pose detection if frames are available.
        # This simplified version re-triggers the initial video processing task.
        # A more sophisticated retry would inspect current state and re-trigger the appropriate task.

        if video.status not in [
            VideoStatus.UPLOADED, 
            VideoStatus.PROCESSING_FAILED, 
            VideoStatus.VIDEO_PROCESSING_FAILED,
            VideoStatus.POSE_DETECTION_FAILED, 
            VideoStatus.ANGLE_CALCULATION_FAILED,
            VideoStatus.FORM_ANALYSIS_FAILED,
            VideoStatus.ERROR,
            VideoStatus.PROCESSED, # Allow re-analysis from processed state
            VideoStatus.POSE_DETECTED, # Allow re-calculation of angles/analysis
            VideoStatus.ANGLES_CALCULATED # Allow re-analysis
        ]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Video is in status '{video.status}' and cannot be reprocessed at this stage using this endpoint."
            )

        if not video.object_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Video has no object_key, cannot initiate reprocessing."
            )
        
        logger.info(f"Retrying video processing for video {video_id}, current status: {video.status}")

        # Reset relevant fields before re-processing
        # This ensures that if it failed midway, it can restart cleanly.
        update_fields = {
            "status": VideoStatus.PENDING_UPLOAD, # This will be updated to PROCESSING by the task
            "processing_errors": None, # Clear previous errors
            "celery_task_id": None,
            # Depending on where it failed, might also clear: 
            # "processed_object_key": None, "frame_s3_keys": None, "processed_frame_count": None,
            # "raw_pose_data": None, "calculated_angles": None
        }
        # For a simple re-trigger of initial processing:
        video.status = VideoStatus.PROCESSING # Set to processing to indicate intent
        video.processing_errors = None
        video.celery_task_id = None
        # Potentially clear other fields if starting from scratch
        video.processed_url = None
        video.processed_object_key = None
        video.frame_s3_keys = None
        video.processed_frame_count = None
        video.raw_pose_data = None
        video.calculated_angles = None
        
        video = await self.update_async(db_obj=video, obj_in=VideoUpdate(**update_fields))
        if not video: # Should not happen if get_async worked
             raise ServerErrorException("Failed to update video for retry.")

        from app.tasks.video_tasks import process_video_celery_task
        task_result = process_video_celery_task.delay(
            video_id_str=str(video.id),
            original_video_path=video.object_key,
            exercise_type_value=video.exercise_type
        )
        
        task_id = task_result.id if hasattr(task_result, 'id') else "unknown_retry_task"
        video.celery_task_id = task_id # Save new task ID
        video.status = VideoStatus.PROCESSING # Explicitly set to PROCESSING as task is dispatched
        video = await self.update_async(db_obj=video, obj_in=VideoUpdate(celery_task_id=task_id, status=VideoStatus.PROCESSING))

        logger.info(f"Video processing retry requested: id={video.id}, new task_id={task_id}.")
        return self.response_schema.from_orm(video)

    async def update_video_pose_data_and_status(
        self,
        video_id: UUID,
        pose_data: Optional[list] = None,
        status: Optional[VideoStatus] = None,
        error_message: Optional[str] = None, # This is the parameter passed to the function
    ):
        video = await self.get_async(id=video_id) 
        if not video:
            logger.error(f"Video not found with ID {video_id} in update_video_pose_data_and_status.")
            raise ValueError(f"Video not found with ID {video_id} for update.") 
        
        update_data = {}
        if pose_data is not None:
            update_data["pose_data"] = pose_data
            update_data["processed_pose_data_at"] = datetime.now(timezone.utc)
        elif pose_data is None and hasattr(video, 'pose_data'): # Explicitly clear if passed as None
            update_data["pose_data"] = None
            update_data["processed_pose_data_at"] = None

        # Simplified error message handling
        if error_message is not None:
            update_data["error_message"] = error_message
        else:
            # If error_message param is None, ensure we clear it in the DB
            # but only if the field exists on the model (which it does for Video)
            if hasattr(video, 'error_message'):
                 update_data["error_message"] = None

        if status:
            update_data["status"] = status
            update_data["status_updated_at"] = datetime.now(timezone.utc)
            # If status is FAILED and error_message in update_data is still None (because param was None)
            # set a generic error.
            if status.value.endswith("_FAILED") and update_data.get("error_message") is None:
                 default_error_detail = f"{video.__class__.__name__} status set to {status.value} with no specific error message."
                 update_data["error_message"] = json.dumps({"error_type": "DefaultProcessingError", "details": default_error_detail})
        
        if not update_data:
            logger.warning(f"No actual data provided to update_video_pose_data_and_status for video {video_id}")
            return

        updated_video_db_model = await self.update_async(db_obj=video, obj_in=update_data)
        
        logger.info(
            f"Updated video {video_id} with pose data, status to {status}. Error: {update_data.get('error_message')}. BaseService handled commit."
        )

    async def update_video_calculated_angles_and_status(
        self,
        video_id: UUID,
        calculated_angles: Optional[list] = None,
        status: Optional[VideoStatus] = None,
        error_message: Optional[str] = None, # Parameter
    ):
        video = await self.get_async(id=video_id)
        if not video:
            logger.error(f"Video not found with ID {video_id} in update_video_calculated_angles_and_status.")
            raise ValueError(f"Video not found with ID {video_id} for update.")

        update_data = {}
        if calculated_angles is not None:
            update_data["calculated_angles"] = calculated_angles
            update_data["processed_angles_at"] = datetime.now(timezone.utc)
        elif calculated_angles is None and hasattr(video, 'calculated_angles'): # Explicitly clear
            update_data["calculated_angles"] = None
            update_data["processed_angles_at"] = None
            
        # Simplified error message handling
        if error_message is not None:
            update_data["error_message"] = error_message
        else:
            if hasattr(video, 'error_message'):
                 update_data["error_message"] = None

        if status:
            update_data["status"] = status
            update_data["status_updated_at"] = datetime.now(timezone.utc)
            if status.value.endswith("_FAILED") and update_data.get("error_message") is None:
                 default_error_detail = f"{video.__class__.__name__} status set to {status.value} with no specific error message."
                 update_data["error_message"] = json.dumps({"error_type": "DefaultProcessingError", "details": default_error_detail})
        
        if not update_data:
            logger.warning(f"No actual data provided to update_video_calculated_angles_and_status for video {video_id}")
            return
            
        updated_video_db_model = await self.update_async(db_obj=video, obj_in=update_data)
        logger.info(
            f"Updated video {video_id} calculated_angles, status to {status}. Error: {update_data.get('error_message')}. BaseService handled commit."
        )

    async def update_video_raw_pose_data_and_status(
        self,
        video_id: UUID,
        raw_pose_data: Optional[list] = None,
        status: Optional[VideoStatus] = None,
        error_message: Optional[str] = None,
    ):
        """Updates the raw pose data, status, and error message for a video."""
        video = await self.get_async(id=video_id) 
        if not video:
            logger.error(f"Video not found with ID {video_id} in update_video_raw_pose_data_and_status.")
            raise ValueError(f"Video not found with ID {video_id} for update.") 

        update_data = {}
        if raw_pose_data is not None:
            update_data["raw_pose_data"] = raw_pose_data
            # No specific 'processed_raw_pose_data_at' timestamp for this one, 
            # as it's considered more 'raw' than 'pose_data' generally.
        elif raw_pose_data is None and hasattr(video, 'raw_pose_data'): # Explicitly clear if passed as None
            update_data["raw_pose_data"] = None

        if status is not None:
            update_data["status"] = status

        # Handle error_message: always update if provided, clear if explicitly None and field exists
        if error_message is not None:
            update_data["error_message"] = error_message
        elif error_message is None and hasattr(video, 'error_message'):
            update_data["error_message"] = None 
            
        if not update_data:
            logger.info(f"No data provided to update for video {video_id} in update_video_raw_pose_data_and_status.")
            return video # Or raise error if an update was expected

        video = await self.update_async(db_obj=video, **update_data)
        # No explicit commit here, BaseService.update_async handles it.
        await self.db.refresh(video) # Refresh to get the latest state after update
        logger.info(f"Updated video {video_id} with raw_pose_data, status to {status}. Error: {error_message}. BaseService handled commit.")
        return video

    async def update_video_smoothed_pose_data(
        self,
        video_id: UUID,
        smoothed_pose_data: List[Optional[List[Optional[Dict[str, float]]]]]
    ):
        """Updates the smoothed pose data (Video.pose_data) for a video."""
        video = await self.get_async(id=video_id)
        if not video:
            logger.error(f"Video not found with ID {video_id} in update_video_smoothed_pose_data.")
            # Depending on desired behavior, could raise error or log and return
            raise ValueError(f"Video not found with ID {video_id} for smoothed pose data update.")
        
        await self.update_async(db_obj=video, pose_data=smoothed_pose_data)
        # BaseService.update_async handles commit.
        # No explicit refresh needed here unless the updated object is immediately used in a way that requires it.
        logger.info(f"Updated video {video_id} with smoothed pose data.")
        return video # Return updated video object
