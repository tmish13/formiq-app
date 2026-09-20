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
from app.models.enums import VideoStatus, CompressionMethod # ADDED: Import from central enums
from app.schemas.video import VideoResponse, VideoUploadResponse, VideoCreate, VideoUpdate, AngleDataItem
from app.services.storage_service import StorageService
from app.core.config import Settings # Renamed from settings for consistency
from uuid import uuid4
from app.services.base_service import BaseService
from app.core.exceptions import (
    NotFoundException,
    NotImplementedException,
    PermissionDeniedException,
    ServerErrorException,
)
from app.utils.compression import compress_pose_sequence, decompress_pose_sequence, CompressionMethod as CompMethod
from app.services.cache_service import CacheService, get_cache_service

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
        
        # Cache service for performance optimization
        self.cache_service: Optional[CacheService] = None
        self._cache_initialized = False
    
    async def _ensure_cache_service(self) -> Optional[CacheService]:
        """Lazily initialize cache service for performance optimization."""
        if not self._cache_initialized:
            try:
                self.cache_service = await get_cache_service(self.app_settings)
                if self.cache_service:
                    logger.info("Cache service initialized successfully for VideoService")
                else:
                    logger.warning("Cache service initialization failed, operating without cache")
            except Exception as e:
                logger.warning(f"Cache service initialization error: {e}")
                self.cache_service = None
            finally:
                self._cache_initialized = True
        
        return self.cache_service

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
            
        # No background processing is dispatched here any more.
        #
        # This used to call process_video_celery_task.delay() and then set the
        # video to PROCESSING. That task was an async def under a plain
        # @app.task, so Celery returned an un-awaited coroutine and the body
        # never executed -- every video confirmed through this path was marked
        # PROCESSING and stayed there forever, with a celery_task_id that
        # pointed at nothing.
        #
        # Confirming an upload is this method's job; dispatching was a side
        # effect. So the upload is confirmed and the video is left UPLOADED,
        # which is what it actually is. Pose extraction happens inline in
        # app.tasks.analysis_tasks when a form check is submitted for it.
        logger.info(
            "Video upload confirmed: id=%s, status=UPLOADED. No pre-processing "
            "task dispatched (process_video_celery_task is retired).",
            updated_video.id,
        )
        return self.response_schema.from_orm(updated_video)

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
        celery_task_id: Optional[str] = None, # ADDED
        processed_frame_count: Optional[int] = None, # ADDED
    ):
        video = await self.get_async(id=video_id)
        if not video:
            logger.error(f"Video not found with ID {video_id} in update_video_metadata_and_status.")
            # raise ValueError(f"Video not found with ID {video_id} for update.") # CHANGED
            raise NotFoundException(f"Video with id {video_id} not found for update (prior to super().update_async).") # TO NotFoundException and updated message to match test

        update_data = {key: value for key, value in {
            "metadata": metadata,
            "status": status.value if status else None, # Ensure status is passed as its value if enum
            "error_message": error_message,
            "celery_task_id": celery_task_id, # ADDED
            "processed_frame_count": processed_frame_count, # ADDED
        }.items() if value is not None}

        if not update_data:
            logger.info(f"No actual update parameters provided for video {video_id}. Returning current state.")
            return self.response_schema.from_orm(video)

        # Construct VideoUpdate schema for the update
        try:
            video_update_schema = VideoUpdate(**update_data)
        except Exception as e: # Catch potential Pydantic validation errors early
            logger.error(f"Pydantic validation error creating VideoUpdate schema for video {video_id}: {e}. Data: {update_data}", exc_info=True)
            raise ServerErrorException(f"Invalid data provided for video update: {e}")

        updated_video = await super().update_async(db_obj=video, obj_in=video_update_schema) # Pass schema instance
        
        if not updated_video:
            # This case might be redundant if get_async already confirmed video existence
            # and super().update_async raises its own errors for update failures.
            # However, keeping it for robustness in case update_async returns None on failure.
            logger.error(f"Failed to update video {video_id} using super().update_async.")
            raise ServerErrorException(f"Failed to update video {video_id}.")

        logger.info(f"Video {video_id} updated: status={status}, celery_id={celery_task_id}, error='{error_message if error_message else ''}'")
        return self.response_schema.from_orm(updated_video)

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

        # Same retirement as the confirm-upload path above: the task this retried
        # into never executed, so "retry processing" could only ever re-park the
        # video in PROCESSING.
        raise NotImplementedException(
            message=(
                "Retrying video processing is retired. process_video_celery_task "
                "was an async def under @app.task and never executed. Submit a new "
                "form check for this video instead."
            ),
            details={"video_id": str(video.id)},
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
        use_compression: bool = True,
        compression_method: Optional[CompressionMethod] = None
    ):
        """
        Updates the raw pose data, status, and error message for a video with optional compression.
        
        Args:
            video_id: Video ID to update
            raw_pose_data: Pose sequence data to store
            status: Video processing status
            error_message: Error message if any
            use_compression: Whether to compress pose data (default: True)
            compression_method: Compression method to use (default: auto-select based on data size)
        """
        video = await self.get_async(id=video_id) 
        if not video:
            logger.error(f"Video not found with ID {video_id} in update_video_raw_pose_data_and_status.")
            raise ValueError(f"Video not found with ID {video_id} for update.") 

        update_data = {}
        
        if raw_pose_data is not None:
            if use_compression:
                # Use compressed storage for better performance
                success = await self._store_compressed_pose_data(
                    video, raw_pose_data, compression_method
                )
                if success:
                    logger.info(f"Successfully compressed and stored pose data for video {video_id}")
                    # Keep raw_pose_data as None since we're using compressed storage
                    update_data["raw_pose_data"] = None
                else:
                    logger.warning(f"Compression failed for video {video_id}, falling back to uncompressed storage")
                    update_data["raw_pose_data"] = raw_pose_data
            else:
                # Use legacy uncompressed storage
                update_data["raw_pose_data"] = raw_pose_data
                
        elif raw_pose_data is None and hasattr(video, 'raw_pose_data'):
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

        video_update_schema = VideoUpdate(**update_data) # Convert to schema
        video = await self.update_async(db_obj=video, obj_in=video_update_schema) # CORRECTED CALL
        # No explicit commit here, BaseService.update_async handles it.
        await self.db.refresh(video) # Refresh to get the latest state after update
        
        # Invalidate cache for this video when pose data is updated
        if raw_pose_data is not None:
            cache_service = await self._ensure_cache_service()
            if cache_service:
                try:
                    invalidated_count = await cache_service.invalidate_video_cache(video_id)
                    if invalidated_count > 0:
                        logger.info(f"Invalidated {invalidated_count} cache entries for video {video_id}")
                except Exception as e:
                    logger.warning(f"Cache invalidation failed for video {video_id}: {e}")
        
        logger.info(f"Updated video {video_id} with pose data (compressed: {use_compression}), status to {status}. Error: {error_message}.")
        return video
        
    async def _store_compressed_pose_data(
        self,
        video: Video,
        pose_sequence: list,
        compression_method: Optional[CompressionMethod] = None
    ) -> bool:
        """
        Store pose sequence data using compression.
        
        Args:
            video: Video model instance
            pose_sequence: Pose sequence to compress and store
            compression_method: Compression method to use
            
        Returns:
            True if compression and storage succeeded, False otherwise
        """
        try:
            # Auto-select compression method based on data size if not specified
            if compression_method is None:
                import json
                estimated_size_kb = len(json.dumps(pose_sequence).encode('utf-8')) / 1024
                compression_method = CompressionMethod.get_recommended_method(int(estimated_size_kb))
                logger.debug(f"Auto-selected compression method {compression_method.value} for {estimated_size_kb:.1f}KB pose data")
            
            # Use the Video model's compression helper method
            success = video.set_compressed_pose_data(pose_sequence, compression_method)
            
            if success:
                logger.info(f"Compressed pose data for video {video.id}: "
                          f"{video.original_pose_size:,} → {video.compressed_pose_size:,} bytes "
                          f"({video.compression_ratio:.3f} ratio) using {compression_method.value}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to compress pose data for video {video.id}: {e}", exc_info=True)
            return False
    
    async def get_video_pose_data(self, video_id: UUID) -> Optional[list]:
        """
        Retrieve pose data for a video with cache optimization.
        
        Args:
            video_id: Video ID to retrieve pose data for
            
        Returns:
            Pose sequence data or None if not found
        """
        try:
            # Check cache first
            cache_service = await self._ensure_cache_service()
            cached_pose_data = None
            
            if cache_service:
                # Generate cache key for video pose data
                video_cache_key = cache_service.key_manager.generate_video_metadata_key(video_id)
                try:
                    # For pose sequences, we cache by video_id but need the actual data to generate the pose key
                    # So we'll cache at the video metadata level for now
                    pass  # We'll implement video-level caching after getting the data
                except Exception as e:
                    logger.debug(f"Cache lookup failed for video {video_id}: {e}")
            
            video = await self.get_async(id=video_id)
            if not video:
                logger.error(f"Video not found with ID {video_id}")
                return None
            
            pose_data = None
            
            # Try compressed data first (preferred)
            if video.compressed_pose_data and video.pose_compression_method:
                pose_data = video.get_pose_data_decompressed()
                if pose_data is not None:
                    logger.debug(f"Retrieved compressed pose data for video {video_id} "
                               f"(method: {video.pose_compression_method.value}, "
                               f"ratio: {video.compression_ratio:.3f})")
                else:
                    logger.warning(f"Failed to decompress pose data for video {video_id}, trying fallback")
            
            # Fallback to uncompressed data
            if pose_data is None:
                if video.raw_pose_data:
                    logger.debug(f"Retrieved uncompressed pose data for video {video_id}")
                    pose_data = video.raw_pose_data
                elif video.pose_data:
                    logger.debug(f"Retrieved legacy pose data for video {video_id}")
                    pose_data = video.pose_data
            
            # Cache the pose data if available and cache service is ready
            if pose_data and cache_service:
                try:
                    await cache_service.set_pose_sequence(
                        pose_data, 
                        ttl=cache_service.pose_ttl,
                        compression_method=CompMethod.LZ4  # Fast compression for retrieval caching
                    )
                    logger.debug(f"Cached pose data for video {video_id}")
                except Exception as e:
                    logger.debug(f"Failed to cache pose data for video {video_id}: {e}")
            
            if pose_data is None:
                logger.info(f"No pose data found for video {video_id}")
            
            return pose_data
            
        except Exception as e:
            logger.error(f"Failed to retrieve pose data for video {video_id}: {e}", exc_info=True)
            return None
    
    async def store_extracted_features(
        self, 
        video_id: UUID, 
        features: Dict[str, float],
        use_compression: bool = True,
        compression_method: Optional[CompressionMethod] = None
    ) -> bool:
        """
        Store extracted features for a video with optional compression.
        
        Args:
            video_id: Video ID to update
            features: Extracted biomechanical features
            use_compression: Whether to compress features (default: True)
            compression_method: Compression method to use
            
        Returns:
            True if storage succeeded, False otherwise
        """
        try:
            video = await self.get_async(id=video_id)
            if not video:
                logger.error(f"Video not found with ID {video_id}")
                return False
            
            # Cache features for fast ML model access
            cache_service = await self._ensure_cache_service()
            
            if use_compression:
                # Auto-select compression method for features (smaller data)
                if compression_method is None:
                    compression_method = CompressionMethod.GZIP  # Best for small feature data
                
                success = video.set_compressed_features(features, compression_method)
                if success:
                    logger.info(f"Compressed and stored features for video {video_id} "
                              f"using {compression_method.value}")
                    
                    # Update the video in database
                    await self.db.commit()
                    await self.db.refresh(video)
                    
                    # Cache features for ML model access
                    if cache_service:
                        try:
                            await cache_service.set_features(
                                features, 
                                ttl=cache_service.features_ttl,
                                use_compression=True
                            )
                            logger.debug(f"Cached features for video {video_id}")
                        except Exception as e:
                            logger.debug(f"Failed to cache features for video {video_id}: {e}")
                    
                    return True
                else:
                    logger.warning(f"Feature compression failed for video {video_id}")
                    return False
            else:
                # Store features in analysis_results field (legacy approach)
                update_data = {"analysis_results": {"features": features}}
                video_update_schema = VideoUpdate(**update_data)
                await self.update_async(db_obj=video, obj_in=video_update_schema)
                logger.info(f"Stored uncompressed features for video {video_id}")
                
                # Cache features even if stored uncompressed
                if cache_service:
                    try:
                        await cache_service.set_features(
                            features, 
                            ttl=cache_service.features_ttl,
                            use_compression=False
                        )
                        logger.debug(f"Cached uncompressed features for video {video_id}")
                    except Exception as e:
                        logger.debug(f"Failed to cache features for video {video_id}: {e}")
                
                return True
                
        except Exception as e:
            logger.error(f"Failed to store features for video {video_id}: {e}", exc_info=True)
            return False

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
        
        video_update_schema = VideoUpdate(pose_data=smoothed_pose_data) # Create schema instance
        video = await self.update_async(db_obj=video, obj_in=video_update_schema) # CORRECTED CALL
        # BaseService.update_async handles commit.
        # No explicit refresh needed here unless the updated object is immediately used in a way that requires it.
        logger.info(f"Updated video {video_id} with smoothed pose data.")
        return video # Return updated video object
