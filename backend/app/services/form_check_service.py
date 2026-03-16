"""Form check service module."""
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
import logging
import os
import hashlib
import cv2
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete as sqlalchemy_delete, func, or_
from fastapi import UploadFile, HTTPException, status, Depends
from enum import Enum
from datetime import datetime, timedelta
import asyncio
from sqlalchemy.orm import selectinload
from sqlalchemy import and_

from app.models.form_check import FormCheck, FeedbackItem
from app.models.enums import (
    FormCheckStatus,
    ExerciseType,
    FeedbackType,
    FeedbackSeverity
)
from app.core.storage import upload_video as core_upload_video, delete_video as core_delete_video
from app.schemas.form_check import (
    FormCheckCreate,
    FormCheckUpdate,
    FormCheckResponse,
    FeedbackItemCreate,
    FeedbackItemUpdate,
    FeedbackItemResponse
)
from app.services.base_service import BaseService
from app.services.storage_service import StorageService
from app.services.ai_service import AIService
from app.core.config import Settings
from app.core.exceptions import (
    ValidationError,
    NotFoundException,
    ServerErrorException,
    PermissionDeniedException
)
from app.models.exercise import ExerciseTemplate
from app.core.cache import CacheService, cache_service
# from app.core.deps import get_async_db, get_settings # REMOVED

logger = logging.getLogger(__name__)

async def enqueue_form_check_analysis(form_check_id: UUID) -> None:
    logger.info(f"Would enqueue form check {form_check_id} for analysis (stub)")
    pass

class FormCheckService(BaseService[FormCheck, FormCheckCreate, FormCheckUpdate]):
    def __init__(self, db: AsyncSession, settings: Settings, storage_service: StorageService, ai_service: AIService, cache_service: Optional[CacheService] = None):
        super().__init__(db=db, model=FormCheck, settings=settings)
        self.storage_service = storage_service
        self.ai_service = ai_service
        self.cache_service = cache_service
        self.response_schema = FormCheckResponse

    async def _process_video_frames_cv2(self, video_path: str) -> List[Dict[str, Any]]:
        """Synchronous helper function to process video frames using OpenCV."""
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise IOError(f"Could not open video file: {video_path}")

        frame_results = []
        processed_frames = 0
        max_frames_to_process = 300

        while cap.isOpened() and processed_frames < max_frames_to_process:
            ret, frame = cap.read()
            if not ret:
                break
            landmarks, confidence = self.ai_service.detect_pose(frame)
            
            if landmarks:
                frame_results.append({"landmarks": landmarks, "confidence": confidence})
            processed_frames += 1

        cap.release()
        if processed_frames >= max_frames_to_process:
            logger.warning(f"Video {video_path} exceeded max frames ({max_frames_to_process}), processing truncated.")
        return frame_results

    async def analyze_video_via_ai_service(self, video_path: str, exercise_type: ExerciseType) -> Dict[str, Any]:
        try:
            frame_results = await asyncio.to_thread(self._process_video_frames_cv2, video_path)

            if not frame_results:
                logger.info(f"No poses detected in video: {video_path}")
                return {"score": 0.0, "feedback": ["No poses detected in the video."], "risk_level": "low", "feedback_structured": []}

            best_frame_data = max(frame_results, key=lambda x: x["confidence"])
            
            analysis_results = await self.ai_service.analyze_form(
                best_frame_data["landmarks"],
                exercise_type.value
            )
            return analysis_results

        except IOError as ioe:
            logger.error(f"Video IO error during analysis ({video_path}): {ioe}")
            raise ServerErrorException(f"Error accessing video file for analysis: {ioe}")
        except Exception as e:
            logger.error(f"Unexpected error in analyze_video_via_ai_service for {video_path}: {e}", exc_info=True)
            raise ServerErrorException("Video analysis failed due to an unexpected error.")

    async def submit_form_check(
        self,
        user_id: UUID,
        video_file: UploadFile,
        exercise_type_enum: ExerciseType,
        notes: Optional[str] = None,
        threshold_mode: Optional[str] = None,
        posture_v1_mode: Optional[str] = None,
        weight_kg: Optional[float] = None,
        reps: Optional[int] = None,
        **kwargs,
    ) -> FormCheckResponse:
        logger.info(f"Submitting form check for user {user_id}, exercise: {exercise_type_enum.value}, video: {video_file.filename}")
        file_key: Optional[str] = None  # S3 object key
        video_cloud_url: Optional[str] = None  # presigned URL for initial use

        try:
            # 1. Upload video using StorageService to cloud storage; capture the S3 key
            logger.info(f"Uploading video '{video_file.filename}' to cloud storage.")
            folder = f"form_check_videos/{user_id}"

            file_key = await self.storage_service.upload_file_and_get_key(
                file=video_file,
                folder=folder,
                user_id=str(user_id)
            )
            video_cloud_url = self.storage_service.get_file_url(file_key, expires_in=3600)
            logger.info(f"Video uploaded. Key: {file_key}")

            # 2. Get Exercise ID from ExerciseType enum.
            # Case-insensitive match: DB may store "Squat" while the enum value is "squat".
            _exercise_name_lower = exercise_type_enum.value.lower()
            exercise_template_stmt = select(ExerciseTemplate).where(
                func.lower(ExerciseTemplate.name) == _exercise_name_lower
            )
            exercise_template_result = await self.db.execute(exercise_template_stmt)
            exercise_template = exercise_template_result.scalars().first()

            if not exercise_template:
                logger.error(
                    "ExerciseTemplate lookup failed: no row with LOWER(name) = '%s' in "
                    "exercise_templates. Expected identifier: 'Squat' (case-insensitive). "
                    "The table is likely unseeded — run: alembic upgrade head",
                    _exercise_name_lower,
                )
                if video_cloud_url:
                    try:
                        logger.info("Cleaning up orphaned upload after template miss: %s", file_key)
                        await self.storage_service.delete_file(video_cloud_url)
                    except Exception as e_del:
                        logger.error(
                            "Failed to delete orphaned upload %s after template miss: %s",
                            file_key, e_del,
                        )
                raise NotFoundException(
                    f"Exercise template not found for type '{exercise_type_enum.value}'. "
                    "The database may be missing seed data — contact support."
                )
            actual_exercise_id: UUID = exercise_template.id

            # 3. Create Video record.
            # exercise_type is stored on Video so that the Celery task can
            # route to PostureV1 even when the ExerciseTemplate lookup inside
            # the task returns None (e.g. race between template deletion and task).
            import uuid as _uuid
            from app.models.video import Video
            video_record = Video(
                id=_uuid.uuid4(),
                user_id=user_id,
                filename=video_file.filename or "unknown.mp4",
                url=video_cloud_url,
                object_key=file_key,  # store the actual S3 key, not the presigned URL
                mime_type=video_file.content_type or "video/mp4",
                status="UPLOADED",
                exercise_type=exercise_type_enum.value,  # fallback for _is_squat routing
            )
            self.db.add(video_record)
            await self.db.flush()
            logger.info(f"Created Video record ID {video_record.id}")

            # 4. Create initial FormCheck record with PENDING status
            # Store s3:// URI as video_url — permanent reference; fresh presigned URLs
            # are generated on-demand from video_key (avoids 1-hr expiry problem).
            from app.core.config import settings as _settings
            s3_video_uri = f"s3://{_settings.S3_BUCKET_NAME}/{file_key}"
            form_check_create_schema = FormCheckCreate(
                user_id=user_id,
                exercise_id=actual_exercise_id,
                video_url=s3_video_uri,
                notes=notes,
                status=FormCheckStatus.PENDING,
                video_key=file_key,
                weight_kg=weight_kg,
                reps=reps,
            )
            db_form_check = await super().create_async(obj_in=form_check_create_schema)
            db_form_check.video_id = video_record.id
            db_form_check.exercise_type = exercise_type_enum.value
            await self.db.flush()
            await self.db.commit()  # Persist video_id linkage (create_async committed without it)
            logger.info(f"Created FormCheck record ID {db_form_check.id} with PENDING status, video_id={video_record.id}")

            # Store threshold_mode and posture_v1_mode in details JSON if provided
            if threshold_mode or posture_v1_mode:
                existing_details = db_form_check.details or {}
                if threshold_mode:
                    existing_details["threshold_mode"] = threshold_mode
                if posture_v1_mode:
                    existing_details["posture_v1_mode"] = posture_v1_mode
                db_form_check.details = existing_details
                await self.db.flush()

            # 4. Dispatch background task for analysis
            try:
                from app.tasks.analysis_tasks import process_form_check_task
                process_form_check_task.delay(
                    video_id_str=str(video_record.id),
                    form_check_id_str=str(db_form_check.id),
                )
                logger.info(f"Successfully dispatched analysis task for FormCheck ID {db_form_check.id}.")
            except Exception as e_task_dispatch:
                logger.error(f"Failed to dispatch Celery task for FormCheck ID {db_form_check.id}: {e_task_dispatch}", exc_info=True)
                # Critical error: FormCheck created but analysis not started. Update status to ERROR.
                # This requires db_form_check to be an actual ORM object that can be updated.
                if db_form_check: # Ensure db_form_check is not None
                    error_update_payload = {"status": FormCheckStatus.FAILED, "error_details": f"Failed to dispatch analysis task: {str(e_task_dispatch)}"}
                    await super().update_async(db_obj=db_form_check, obj_in=error_update_payload) # Use db_obj if get_async was called prior, or id if not
                    await self.db.commit() # Ensure error status is saved
                # Re-raise or raise a specific HTTPException to inform the client of the dispatch failure.
                # This depends on how much detail the client needs.
                raise ServerErrorException(f"Form check submitted (ID: {db_form_check.id}) but failed to start analysis processing. Please contact support.")

            return self.response_schema.from_orm(db_form_check)

        except NotFoundException as nfe:
            logger.warning(f"Error submitting form check: {nfe}")
            # video_cloud_url might exist if error happened after upload but before this catch
            # However, NotFoundException for ExerciseTemplate already handles deletion.
            raise 
        except ValidationError as ve: 
            logger.warning(f"Validation error submitting form check: {ve}")
            if video_cloud_url: # If video was uploaded before validation error
                try:
                    logger.info(f"Attempting to delete video {video_cloud_url} due to validation error.")
                    await self.storage_service.delete_file(video_cloud_url)
                except Exception as e_clean:
                    logger.error(f"Failed to cleanup video {video_cloud_url} after validation error: {e_clean}")
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(ve))
        except Exception as e:
            logger.error(f"General error submitting form check: {e}", exc_info=True)
            if video_cloud_url: # If video was uploaded before a general error
                try:
                    logger.info(f"Attempting to delete video {video_cloud_url} due to general error.")
                    await self.storage_service.delete_file(video_cloud_url)
                except Exception as e_clean:
                    logger.error(f"Failed to cleanup video {video_cloud_url} after general error: {e_clean}")
            raise ServerErrorException("An unexpected error occurred while submitting the form check.")
        # The 'finally' block for local temp file cleanup is removed as we are using StorageService
        # which should manage its own temporary file handling if any during cloud upload.

    async def finalize_form_check_analysis_async(
        self,
        form_check_id: UUID,
        analysis_results: Dict[str, Any],
        status: FormCheckStatus = FormCheckStatus.COMPLETED # Can be ERROR too
    ) -> FormCheckResponse:
        logger.info(f"Finalizing analysis for FormCheck ID {form_check_id} with status {status.value}")
        
        form_check = await super().get_async(id=form_check_id)
        if not form_check:
            # This should ideally not happen if the task was dispatched for a valid ID
            logger.error(f"FormCheck ID {form_check_id} not found during finalization.")
            # Depending on policy, could raise, or just log and exit.
            # If we can't find it, can't update it.
            raise NotFoundException(f"FormCheck ID {form_check_id} not found during finalization.")

        update_payload = {
            "status": status,
            "score": analysis_results.get("score"),
            "summary": "\n".join(analysis_results.get("feedback", [])), # Or a more structured summary
            "details": { # Storing raw/additional details from AI service
                "risk_level": analysis_results.get("risk_level"),
                "raw_feedback_strings": analysis_results.get("feedback", []),
                "model_version": analysis_results.get("model_version", "unknown") # Example additional detail
            },
            "analysis_completed_at": datetime.utcnow(),
            # Add ML scores from analysis results
            "posture_score": analysis_results.get("posture_score"),
            "stability_score": analysis_results.get("stability_score"),
            "depth_score": analysis_results.get("depth_score")
        }
        
        if status == FormCheckStatus.FAILED:
            update_payload["error_details"] = analysis_results.get("error_message", "Analysis failed due to an unknown error.")

        updated_form_check = await super().update_async(db_obj=form_check, obj_in=update_payload)

        # Delete old FeedbackItems and create new ones
        logger.info(f"Deleting existing feedback items for FormCheck ID {form_check_id}")
        await self.db.execute(sqlalchemy_delete(FeedbackItem).where(FeedbackItem.form_check_id == form_check_id))
        # The commit for this deletion will happen after adding new items or at end of service method call if using session context manager

        created_feedback_items_count = 0
        if status == FormCheckStatus.COMPLETED and "feedback_structured" in analysis_results:
            structured_feedback_list = analysis_results.get("feedback_structured", [])
            logger.info(f"Creating {len(structured_feedback_list)} new feedback items for FormCheck ID {form_check_id}")
            for item_data in structured_feedback_list:
                try:
                    feedback_item_create_schema = FeedbackItemCreate(
                        form_check_id=updated_form_check.id,
                        is_ai_generated=True, # Assuming these are from AI
                        **item_data # type, message, timestamp, severity, suggestions, joint_angles etc.
                    )
                    fb_item_model = FeedbackItem(**feedback_item_create_schema.model_dump())
                    self.db.add(fb_item_model)
                    created_feedback_items_count += 1
                except Exception as e_fb_create:
                    logger.error(f"Error creating structured FeedbackItem for FC {updated_form_check.id}: {e_fb_create}. Data: {item_data}", exc_info=True)
        
        await self.db.commit() # Commit FormCheck update and new/deleted FeedbackItems
        logger.info(f"Successfully finalized analysis for FormCheck ID {form_check_id}. Created {created_feedback_items_count} feedback items.")

        # Refresh to load relationships if needed by the response schema
        await self.db.refresh(updated_form_check, attribute_names=['feedback_items'])
        
        # Handle caching if applicable (example from existing FCS code)
        if self.cache_service and status == FormCheckStatus.COMPLETED:
            # Assuming video_hash can be derived or is part of analysis_results or form_check
            # For example, if AIService adds a video_hash to its results:
            video_hash = analysis_results.get("video_hash") 
            if not video_hash and updated_form_check.details and isinstance(updated_form_check.details, dict):
                 video_hash = updated_form_check.details.get("video_file_hash") # Or however it's stored

            if video_hash:
                # Prepare data for caching, might be the analysis_results itself or a specific format
                cacheable_results = {
                    "score": updated_form_check.score,
                    "summary": updated_form_check.summary,
                    "details": updated_form_check.details,
                    "feedback_items": [FeedbackItemResponse.from_orm(fi).model_dump() for fi in updated_form_check.feedback_items]
                }
                await self.cache_analysis_results(video_hash, cacheable_results)
            else:
                logger.warning(f"Video hash not available for FormCheck ID {form_check_id}, skipping caching.")

        return self.response_schema.from_orm(updated_form_check)

    async def get_form_check_details(self, form_check_id: UUID, user_id: UUID, is_superuser: bool) -> Optional[FormCheckResponse]:
        form_check = await super().get_async(id=form_check_id)
        if not form_check:
            return None
        
        if form_check.user_id != user_id and not is_superuser:
            raise PermissionDeniedException("Not authorized to view this form check.")
        return self.response_schema.from_orm(form_check)

    async def list_user_form_checks(
        self,
        user_id: UUID,
        status_filter: Optional[FormCheckStatus] = None,
        exercise_id_filter: Optional[UUID] = None,
        skip: int = 0,
        limit: int = 10
    ) -> List[FormCheckResponse]:
        # Build filter conditions
        conditions = [FormCheck.user_id == user_id]
        if status_filter:
            conditions.append(FormCheck.status == status_filter)
        if exercise_id_filter:
            conditions.append(FormCheck.exercise_id == exercise_id_filter)

        # Use a direct query with selectinload so related objects (exercise,
        # feedback_items) are fetched in 2 extra queries instead of N queries.
        stmt = (
            select(FormCheck)
            .where(and_(*conditions))
            .options(
                selectinload(FormCheck.exercise),
                selectinload(FormCheck.feedback_items),
            )
            .order_by(FormCheck.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        form_checks_db = result.scalars().all()
        return [self.response_schema.from_orm(fc) for fc in form_checks_db]

    async def create_form_check_with_url(
        self,
        user_id: UUID,
        video_url: str,
        exercise_id: UUID,
        notes: Optional[str] = None,
        status: FormCheckStatus = FormCheckStatus.PENDING
    ) -> FormCheckResponse:
        create_schema = FormCheckCreate(
            user_id=user_id,
            video_url=video_url,
            exercise_id=exercise_id,
            notes=notes,
            status=status 
        )
        new_form_check_db = await super().create_async(obj_in=create_schema)
        return self.response_schema.from_orm(new_form_check_db)

    async def delete_form_check_record(
        self,
        form_check_id: UUID,
        user_id: UUID,
        is_superuser: bool,
        delete_associated_file: bool = True # Default to true for file deletion
    ) -> None:
        form_check = await super().get_async(id=form_check_id)
        if not form_check:
            raise NotFoundException("FormCheck not found.")

        if form_check.user_id != user_id and not is_superuser:
            raise PermissionDeniedException("Not authorized to delete this form check.")

        video_url_to_delete = form_check.video_url
        
        # Delete related FeedbackItems first
        stmt_delete_feedback = sqlalchemy_delete(FeedbackItem).where(FeedbackItem.form_check_id == form_check_id)
        await self.db.execute(stmt_delete_feedback)
        # No separate commit here, will be part of the transaction with FormCheck deletion or committed after.

        deleted_fc_db_obj = await super().remove_async(id=form_check_id) # remove_async should handle its own commit for FormCheck.
        
        if not deleted_fc_db_obj: # Check if remove_async was successful
            # This case implies that the FormCheck was found by get_async but remove_async failed to delete it
            # or returned None indicating it couldn't find it (which would be strange here).
            # Consider rolling back feedback deletion if formcheck deletion fails and not cascaded by DB.
            # However, BaseService.remove_async should raise an error if deletion fails after finding.
            # If it returns None because it re-fetched and couldn't find, that's an edge case.
            logger.error(f"FormCheck {form_check_id} was found but remove_async failed or returned None.")
            # Attempt to commit feedback deletion if super().remove_async doesn't commit or failed before commit.
            # This part is a bit tricky depending on BaseService's transaction handling.
            # For now, assume remove_async either succeeds and commits, or raises an error.
            # If it returns None on failure to find (after initial find), then feedback items might be deleted without formcheck.
            # To be safe, commit feedback deletion explicitly if formcheck deletion is confirmed OR handle transactions more globally.
            # For now, we commit everything at the end if file deletion is also attempted.
            pass # Let errors from remove_async propagate if it raises them.

        if delete_associated_file and video_url_to_delete:
            try:
                await core_delete_video(video_url_to_delete) 
                logger.info(f"Deleted video file {video_url_to_delete} for form check {form_check_id}")
            except Exception as e_storage:
                logger.error(f"Failed to delete video file {video_url_to_delete} for form check {form_check_id}: {e_storage}. DB record was deleted.")
                # Consider if this should re-raise or just log, as DB part is done.

        # Commit FeedbackItem deletions if not handled by remove_async transaction scope
        # BaseService.remove_async likely commits for its own model.
        # We need to ensure FeedbackItem deletions are committed.
        await self.db.commit() # Commit FeedbackItem deletions and potentially FormCheck if super().remove_async doesn't

    async def complete_form_check_analysis_manually(
        self,
        form_check_id: UUID,
        user_id: UUID,
        is_superuser: bool,
        summary: str,
        overall_score: float,
        status_val: FormCheckStatus = FormCheckStatus.COMPLETED
    ) -> FormCheckResponse:
        form_check = await super().get_async(id=form_check_id)
        if not form_check:
            raise NotFoundException("FormCheck not found.")
        if form_check.user_id != user_id and not is_superuser:
            raise PermissionDeniedException("Not authorized to complete this form check analysis.")

        # FormCheckUpdate schema from file: video_url, exercise_id, status, overall_feedback, score
        update_payload = FormCheckUpdate(
            status=status_val,
            overall_feedback=summary,
            score=overall_score
        )
        updated_fc = await super().update_async(id=form_check_id, obj_in=update_payload)
        if not updated_fc: 
            raise ServerErrorException("Failed to update FormCheck for manual completion.")
        
        return self.response_schema.from_orm(updated_fc)

    async def add_feedback_item_to_form_check(self, form_check_id: UUID, feedback_data: FeedbackItemCreate) -> FeedbackItemResponse:
        # Ensure the FormCheck record exists to associate with
        form_check = await super().get_async(id=form_check_id)
        if not form_check:
            raise NotFoundException(f"FormCheck with ID {form_check_id} not found. Cannot add feedback item.")
        
        # Validate payload form_check_id if it exists in FeedbackItemCreate, though it's often path-derived
        # For now, assuming FeedbackItemCreate does not enforce form_check_id from payload if derived from path.
        # Or, we ensure feedback_data (schema) is created with the correct form_check_id.
        # The schema FeedbackItemCreate has form_check_id: UUID
        if feedback_data.form_check_id != form_check_id:
            raise ValidationError("Path form_check_id does not match form_check_id in payload")

        new_item_model = FeedbackItem(**feedback_data.model_dump())
        self.db.add(new_item_model)
        await self.db.commit() # Commit this new item
        await self.db.refresh(new_item_model) # Refresh to get DB-generated fields like ID
        return FeedbackItemResponse.from_orm(new_item_model)

    async def get_feedback_items_for_form_check(self, form_check_id: UUID) -> List[FeedbackItemResponse]:
        stmt = select(FeedbackItem).filter(FeedbackItem.form_check_id == form_check_id).order_by(FeedbackItem.timestamp)
        result = await self.db.execute(stmt)
        items_db = result.scalars().all()
        if not items_db:
            return []
        return [FeedbackItemResponse.from_orm(item) for item in items_db]

    async def get_single_feedback_item(self, feedback_item_id: int) -> Optional[FeedbackItemResponse]: 
        # FeedbackItem.id is an Integer in the model snippet
        item_db = await self.db.get(FeedbackItem, feedback_item_id) # Use self.db.get for PK lookup
        if not item_db:
            return None
        return FeedbackItemResponse.from_orm(item_db)

    async def update_feedback_item(self, feedback_item_id: int, update_data: FeedbackItemUpdate) -> Optional[FeedbackItemResponse]:
        item_db = await self.db.get(FeedbackItem, feedback_item_id)
        if not item_db:
            # Or raise NotFoundException(f"FeedbackItem with ID {feedback_item_id} not found.")
            return None 

        update_dict = update_data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(item_db, key, value)
        
        self.db.add(item_db) # Add to session before commit
        await self.db.commit()
        await self.db.refresh(item_db)
        return FeedbackItemResponse.from_orm(item_db)

    async def delete_feedback_item(self, feedback_item_id: int) -> bool:
        item_db = await self.db.get(FeedbackItem, feedback_item_id)
        if not item_db:
            return False # Or raise NotFoundException
        
        await self.db.delete(item_db)
        await self.db.commit()
        return True

    async def get_cached_analysis(self, video_hash: str) -> Optional[Dict[str, Any]]:
        if not self.cache_service or not await self.cache_service.is_available(): # Make is_available async if it involves IO
            logger.debug("Cache service not available or not configured.")
            return None
        
        cache_key = f"form_check_analysis:{video_hash}"
        try:
            cached_data = await self.cache_service.get(cache_key)
            if cached_data:
                logger.info(f"Retrieved cached analysis for video hash: {video_hash}")
                return cached_data # Assuming it's stored as a dict
            return None
        except Exception as e:
            logger.error(f"Error retrieving from cache for key {cache_key}: {e}", exc_info=True)
            return None # Treat cache errors as a cache miss
        
    async def cache_analysis_results(self, video_hash: str, analysis_results: Dict[str, Any], ttl: int = 86400 * 7) -> None: # Cache for 7 days
        if not self.cache_service or not await self.cache_service.is_available():
            logger.debug("Cache service not available, skipping caching analysis results.")
            return
            
        cache_key = f"form_check_analysis:{video_hash}"
        try:
            await self.cache_service.set(cache_key, analysis_results, expire=ttl)
            logger.info(f"Cached analysis results for video hash: {video_hash}")
        except Exception as e:
            logger.error(f"Error caching analysis results for key {cache_key}: {e}", exc_info=True)

    async def get_user_form_checks(
        self,
        user_id: UUID,
        status: Optional[FormCheckStatus] = None,
        exercise_type: Optional[ExerciseType] = None,
        page: int = 1,
        per_page: int = 10
    ) -> List[FormCheckResponse]:
        """Get form checks for a user with optional filtering.

        Args:
            user_id: ID of the user
            status: Optional filter by status
            exercise_type: Optional filter by exercise type
            page: Page number
            per_page: Items per page

        Returns:
            List of form checks
        """
        skip = (page - 1) * per_page
        limit = per_page
        
        # Apply filters
        filters = {"user_id": user_id}
        if status:
            filters["status"] = status
        if exercise_type:
            filters["exercise_type"] = exercise_type
            
        return self.form_check_repository.get_multi_filtered(
            filters=filters,
            skip=skip,
            limit=limit
        )

    async def get(self, id: UUID) -> FormCheckResponse:
        """Get a specific form check by ID.

        Args:
            id: Form check ID

        Returns:
            Form check data
            
        Raises:
            ValueError: If form check not found
        """
        form_check = self.form_check_repository.get(id=id)
        if not form_check:
            raise ValueError("Form check not found")
        return form_check

    async def get_feedback(self, feedback_id: int) -> FeedbackItemResponse:
        """Get a specific feedback item by ID.
        
        Args:
            feedback_id: ID of the feedback item
            
        Returns:
            Feedback item data
            
        Raises:
            ValueError: If feedback item not found
        """
        feedback_item = self.feedback_repository.get(id=feedback_id)
        if not feedback_item:
            raise ValueError("Feedback item not found")
        return feedback_item

    async def add_feedback(
        self,
        form_check_id: UUID,
        feedback_type: FeedbackType,
        severity: FeedbackSeverity,
        timestamp: float,
        description: str,
        suggestions: Optional[List[str]] = None,
        joint_angles: Optional[Dict[str, float]] = None,
        is_ai_generated: bool = False
    ) -> FeedbackItemResponse:
        """Add feedback to a form check.

        Args:
            form_check_id: ID of the form check
            feedback_type: Type of feedback
            severity: Severity level
            timestamp: Video timestamp in seconds
            description: Detailed feedback
            suggestions: Optional improvement suggestions
            joint_angles: Optional joint angle measurements
            is_ai_generated: Whether this feedback was generated by AI

        Returns:
            Created feedback item
            
        Raises:
            ValidationError: If validation fails
            ValueError: If form check not found
        """
        # Validate form check exists
        form_check = self.form_check_repository.get(id=form_check_id)
        if not form_check:
            raise ValueError("Form check not found")
        
        # Validate feedback data
        validate_feedback(
            feedback_type=feedback_type,
            severity=severity,
            timestamp=timestamp,
            description=description,
            suggestions=suggestions
        )
        
        # Create feedback item
        feedback_data = {
            "form_check_id": form_check_id,
            "type": feedback_type,
            "message": description,
            "timestamp": timestamp,
            "severity": severity,
            "suggestions": suggestions,
            "joint_angles": joint_angles,
            "is_ai_generated": is_ai_generated
        }
        
        feedback_item = self.feedback_repository.create(feedback_data)
        return feedback_item

    async def get_feedback_items(self, form_check_id: UUID) -> List[FeedbackItemResponse]:
        """Get all feedback items for a form check.

        Args:
            form_check_id: ID of the form check

        Returns:
            List of feedback items
            
        Raises:
            ValueError: If form check not found
        """
        # Validate form check exists
        form_check = self.form_check_repository.get(id=form_check_id)
        if not form_check:
            raise ValueError("Form check not found")
            
        return self.feedback_repository.get_by_form_check(form_check_id=form_check_id)

    async def update_feedback(
        self,
        feedback_id: int,
        update_data: Dict[str, Any]
    ) -> FeedbackItemResponse:
        """Update a feedback item.

        Args:
            feedback_id: ID of the feedback item
            update_data: Data to update

        Returns:
            Updated feedback item
            
        Raises:
            ValueError: If feedback item not found
        """
        # Get existing feedback item
        feedback_item = self.feedback_repository.get(id=feedback_id)
        if not feedback_item:
            raise ValueError("Feedback item not found")
            
        # Update feedback item
        updated_item = self.feedback_repository.update(
            db_obj=feedback_item,
            obj_in=update_data
        )
        return updated_item

    async def delete_feedback(self, feedback_id: int) -> None:
        """Delete a feedback item.

        Args:
            feedback_id: ID of the feedback item
            
        Raises:
            ValueError: If feedback item not found
        """
        # Get existing feedback item
        feedback_item = self.feedback_repository.get(id=feedback_id)
        if not feedback_item:
            raise ValueError("Feedback item not found")
            
        # Delete feedback item
        self.feedback_repository.delete(id=feedback_id)

    async def complete_analysis(
        self,
        form_check_id: UUID,
        summary: str,
        overall_score: float
    ) -> FormCheckResponse:
        """Complete form check analysis.

        Args:
            form_check_id: ID of the form check
            summary: Overall feedback summary
            overall_score: Score from 0-10

        Returns:
            Updated form check
            
        Raises:
            ValidationError: If validation fails
            ValueError: If form check not found
        """
        # Validate form check exists
        form_check = self.form_check_repository.get(id=form_check_id)
        if not form_check:
            raise ValueError("Form check not found")
        
        # Validate summary data
        validate_form_check_summary(summary=summary, overall_score=overall_score)
        
        # Update form check
        update_data = {
            "status": FormCheckStatus.COMPLETED,
            "overall_feedback": summary,
            "score": overall_score * 10  # Convert to 0-100 scale
        }
        
        updated_form_check = self.form_check_repository.update(
            db_obj=form_check,
            obj_in=update_data
        )
        
        # Cache analysis results for future use
        try:
            # Get full form check with feedback items
            form_check_with_feedback = self.form_check_repository.get(id=form_check_id)
            feedback_items = self.feedback_repository.get_by_form_check(form_check_id=form_check_id)
            
            # Create cache entry
            cache_data = {
                "overall_feedback": updated_form_check.overall_feedback,
                "score": updated_form_check.score,
                "confidence_score": updated_form_check.confidence_score,
                "form_metadata": updated_form_check.form_metadata,
                "results": updated_form_check.results,
                "feedback_items": [
                    {
                        "type": item.type,
                        "message": item.message,
                        "timestamp": item.timestamp,
                        "severity": item.severity,
                        "joint_angles": item.joint_angles,
                        "suggestions": item.suggestions
                    }
                    for item in feedback_items
                ]
            }
            
            # Get video hash from metadata if available
            video_hash = None
            if updated_form_check.form_metadata and "video_hash" in updated_form_check.form_metadata:
                video_hash = updated_form_check.form_metadata["video_hash"]
            elif updated_form_check.video_url:
                # If no hash stored, try to get it from the URL
                try:
                    storage = StorageService()
                    file_info = await storage.get_file_info(updated_form_check.video_url)
                    if file_info and file_info.get("Metadata", {}).get("video_hash"):
                        video_hash = file_info["Metadata"]["video_hash"]
                except:
                    pass
            
            # Cache if we have a video hash
            if video_hash:
                await self.cache_analysis_results(video_hash, cache_data)
                logger.info(f"Cached analysis results for video {video_hash}")
        except Exception as e:
            logger.error(f"Failed to cache analysis results: {str(e)}", exc_info=True)
        
        return updated_form_check

    async def delete_form_check(self, form_check_id: UUID, user_id: UUID) -> None:
        """Delete a form check.

        Args:
            form_check_id: ID of the form check
            user_id: ID of the user
            
        Raises:
            ValueError: If form check not found or not owned by user
        """
        # Get form check
        form_check = self.form_check_repository.get(id=form_check_id)
        if not form_check:
            raise ValueError("Form check not found")
        
        # Verify ownership
        if form_check.user_id != user_id:
            raise ValueError("You do not have permission to delete this form check")
        
        # Delete video from storage
        if form_check.video_url:
            await delete_video(form_check.video_url)
            
        # Delete analysis video if exists
        if form_check.analysis_url:
            await delete_video(form_check.analysis_url)
        
        # Delete form check from database
        self.form_check_repository.delete(id=form_check_id)

    async def create_with_url(
        self,
        user_id: str,
        video_url: str,
        exercise_type: str,
        notes: Optional[str] = None
    ) -> FormCheck:
        """Create a form check with an already uploaded video URL."""
        try:
            # Get storage service to validate URL
            storage = StorageService()
            
            # Validate that the URL belongs to our S3 bucket
            try:
                file_info = await storage.get_file_info(video_url)
                logger.info(f"Valid video URL: {video_url}, size: {file_info.get('ContentLength', 0)}")
            except Exception as e:
                logger.error(f"Error validating video URL: {str(e)}")
                raise ValidationException(f"Invalid video URL: {str(e)}")
            
            # Generate a unique ID for the form check
            form_check_id = str(uuid.uuid4())
            
            # Create the form check model
            form_check = FormCheck(
                id=form_check_id,
                user_id=user_id,
                exercise_type=exercise_type,
                video_url=video_url,
                status=FormCheckStatus.pending,
                notes=notes,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            # Save to database
            self.db.add(form_check)
            await self.db.commit()
            await self.db.refresh(form_check)
            logger.info(f"Created form check with URL: {form_check_id}")
            
            # Start async analysis if enabled
            if settings.AUTO_ANALYZE_FORM_CHECKS:
                # Import here to avoid circular imports
                await enqueue_form_check_analysis(form_check_id)
                
                # Update status to analyzing
                form_check.status = FormCheckStatus.analyzing
                await self.db.commit()
                logger.info(f"Queued form check for analysis: {form_check_id}")
            
            return form_check
        except ValidationException as e:
            logger.warning(f"Validation error creating form check with URL: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error creating form check with URL: {str(e)}", exc_info=True)
            await self.db.rollback()
            raise Exception(f"Failed to create form check: {str(e)}")

    async def list_user_form_checks_detailed(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 100,
        exercise_id_filter: Optional[UUID] = None,
        exercise_type_filter: Optional[ExerciseType] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        status_filter: Optional[FormCheckStatus] = None # API sends string, convert before calling
    ) -> List[FormCheck]: # Returns ORM models for API to convert to FormCheckDetailedResponse
        """
        Retrieves a list of form checks for a user with detailed information (exercise, feedback items)
        eagerly loaded. Suitable for FormCheckDetailedResponse.
        """
        logger.info(
            f"Listing detailed form checks for user {user_id} with filters: "
            f"exercise_id={exercise_id_filter}, exercise_type={exercise_type_filter}, "
            f"start_date={start_date}, end_date={end_date}, status={status_filter}, "
            f"skip={skip}, limit={limit}"
        )
        
        filter_conditions: List[ColumnElement] = []
        if user_id:
            filter_conditions.append(self.model.user_id == user_id)
        if exercise_id_filter:
            filter_conditions.append(self.model.exercise_id == exercise_id_filter)
        
        if start_date:
            filter_conditions.append(self.model.created_at >= start_date)
        if end_date:
            # Make end_date inclusive for the whole day
            inclusive_end_date = end_date + timedelta(days=1)
            filter_conditions.append(self.model.created_at < inclusive_end_date)

        if status_filter:
            # Ensure status_filter is an enum instance; if it's a string, convert it.
            # This should ideally be handled at the API layer or Pydantic model.
            # For robustness here, let's assume it's already a FormCheckStatus enum instance.
            status_condition = self.model.status == str(status_filter.value) # Explicit str cast
            logger.info(f"FormCheckService: Adding status_condition: {str(status_condition)}")
            logger.info(f"FormCheckService: status_filter.value type: {type(status_filter.value)}, value: {status_filter.value}")
            logger.info(f"FormCheckService: self.model.status type: {type(self.model.status)}")
            try:
                compiled_status_condition = status_condition.compile(compile_kwargs={"literal_binds": True})
                logger.info(f"FormCheckService: Compiled status_condition: {str(compiled_status_condition)}")
            except Exception as e:
                logger.error(f"FormCheckService: FAILED to compile status_condition: {e}")

            filter_conditions.append(status_condition)

        # Handling ExerciseType filter requires a join or subquery.
        # For simplicity with BaseService.get_multi_async, if exercise_type_filter is present,
        # we first fetch matching ExerciseTemplate IDs.
        exercise_ids_for_type: Optional[List[UUID]] = None
        if exercise_type_filter:
            stmt_exercise_tpl = select(ExerciseTemplate.id).where(ExerciseTemplate.type == exercise_type_filter)
            result_exercise_tpl = await self.db.execute(stmt_exercise_tpl)
            exercise_ids_for_type = result_exercise_tpl.scalars().all()
            if not exercise_ids_for_type:
                logger.info(f"No ExerciseTemplates found for type {exercise_type_filter}, returning empty list for user {user_id}")
                return [] # No exercises of this type, so no form checks
            filter_conditions.append(self.model.exercise_id.in_(exercise_ids_for_type))

        eager_loading_options = [
            selectinload(self.model.exercise),      # Eager load ExerciseTemplate
            selectinload(self.model.feedback_items) # Eager load FeedbackItems
        ]

        query = (
            select(self.model)
            .where(and_(*filter_conditions))
            .options(*eager_loading_options)
            .order_by(self.model.created_at.desc())
            .offset(skip)
            .limit(limit)
        )

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_or_create_form_check_for_video(
        self, 
        video_id: UUID, 
        user_id: UUID, 
        exercise_id: UUID # This should be the ExerciseTemplate.id
    ) -> Optional[FormCheck]:
        """
        Retrieves an existing FormCheck for a given video_id, or creates a new one.
        Ensures that a FormCheck is linked to the video for storing analysis results.
        Args:
            video_id: The ID of the video being analyzed.
            user_id: The ID of the user who owns the video.
            exercise_id: The ID of the exercise (ExerciseTemplate) associated with the video.
        Returns:
            The existing or newly created FormCheck ORM instance, or None if creation fails.
        """
        # Check if a FormCheck already exists for this video_id
        stmt = select(self.model).where(self.model.video_id == video_id)
        result = await self.db.execute(stmt)
        existing_form_check = result.scalars().first()

        if existing_form_check:
            logger.info(f"Found existing FormCheck {existing_form_check.id} for video {video_id}.")
            return existing_form_check
        
        # If not, create a new one
        logger.info(f"No existing FormCheck for video {video_id}. Creating a new one.")
        try:
            form_check_create_data = FormCheckCreate(
                user_id=user_id,
                exercise_id=exercise_id, # This is ExerciseTemplate.id
                video_id=video_id,
                # video_url might be populated from video.url if needed, or left for FormCheckService to manage
                status=FormCheckStatus.PENDING, # Initial status before analysis task runs its course
                # Other fields like notes, score will be updated by the analysis task
            )
            new_form_check = await super().create_async(obj_in=form_check_create_data)
            logger.info(f"Successfully created new FormCheck {new_form_check.id} for video {video_id}.")
            return new_form_check
        except Exception as e:
            logger.error(f"Failed to create FormCheck for video {video_id}: {e}", exc_info=True)
            return None
    
    async def get_form_check_details_with_reference(
        self, 
        form_check_id: UUID, 
        user_id: UUID,
        include_reference_pose: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Get detailed form check information including reference pose data for visual overlays.
        
        Args:
            form_check_id: ID of the form check
            user_id: ID of the requesting user
            include_reference_pose: Whether to include reference pose data
            
        Returns:
            Dictionary with form check details and optional reference pose data
        """
        try:
            # Get the form check with eager loading
            stmt = select(FormCheck).options(
                selectinload(FormCheck.feedback_items),
                selectinload(FormCheck.exercise)
            ).where(FormCheck.id == form_check_id)
            
            result = await self.db.execute(stmt)
            form_check = result.scalar_one_or_none()
            
            if not form_check:
                logger.warning(f"FormCheck {form_check_id} not found")
                return None
            
            # Check permissions
            if form_check.user_id != user_id:
                raise PermissionDeniedException("Not authorized to view this form check.")
            
            # Generate a fresh presigned URL if a video_key is stored.
            # Fallback to the stored video_url for legacy rows that only have
            # a presigned https:// URL (may be expired).
            if getattr(form_check, 'video_key', None):
                fresh_video_url = self.storage_service.get_file_url(form_check.video_key, expires_in=3600)
            else:
                fresh_video_url = form_check.video_url

            # Convert to dict for easier manipulation
            form_check_dict = {
                "id": str(form_check.id),
                "user_id": str(form_check.user_id),
                "exercise_id": str(form_check.exercise_id),
                "video_url": fresh_video_url,
                "status": form_check.status.value if hasattr(form_check.status, 'value') else str(form_check.status),
                "score": form_check.score,
                "overall_feedback": form_check.overall_feedback,
                "created_at": form_check.created_at,
                "exercise_name": form_check.exercise.name if form_check.exercise else None,
                "configuration_id": str(form_check.configuration_id) if form_check.configuration_id else None,
                "classified_exercise_slug": form_check.classified_exercise_slug,
                "classification_confidence": form_check.classification_confidence,
                "exercise_type": form_check.exercise_type,
                "form_metadata": form_check.form_metadata,
                # Add ML scores from XGBoost model
                "posture_score": form_check.posture_score,
                "stability_score": form_check.stability_score,
                "depth_score": form_check.depth_score,
                "feedback_items": [
                    {
                        "id": item.id,
                        "form_check_id": str(item.form_check_id),
                        "type": item.type.value if hasattr(item.type, 'value') else str(item.type),
                        "severity": item.severity.value if hasattr(item.severity, 'value') else str(item.severity),
                        "message": item.message,
                        "timestamp": item.timestamp,
                        "suggestions": item.suggestions,
                        "created_at": item.created_at
                    }
                    for item in form_check.feedback_items
                ] if form_check.feedback_items else []
            }
            
            # Add reference pose data and visual overlay data if requested
            if include_reference_pose and form_check.exercise_id:
                try:
                    # Import here to avoid circular imports
                    from app.services.exercise_config_service import ExerciseConfigService
                    from app.services.pose_comparison_service import PoseComparisonService
                    from app.services.reference_pose_service import ReferencePoseService
                    
                    # Create service instances
                    exercise_config_service = ExerciseConfigService(
                        db=self.db,
                        settings=self.settings
                    )
                    pose_comparison_service = PoseComparisonService(self.settings)
                    reference_pose_service = ReferencePoseService(self.settings)
                    
                    # Get or generate reference pose data
                    reference_data = await exercise_config_service.get_reference_pose_by_exercise_id(
                        exercise_id=form_check.exercise_id
                    )
                    
                    # If no reference pose exists, generate it
                    if not reference_data and form_check.exercise:
                        exercise_name = form_check.exercise.name.lower()
                        if 'squat' in exercise_name:
                            reference_data = reference_pose_service.generate_reference_pose('squat')
                            # Optionally save this for future use
                            await exercise_config_service.generate_and_populate_reference_pose(
                                exercise_id=form_check.exercise_id,
                                exercise_type='squat'
                            )
                    
                    form_check_dict["reference_pose_data"] = reference_data
                    
                    # Generate visual overlay comparison data if we have user pose data
                    overlay_data = None
                    if reference_data and form_check.keypoints:
                        try:
                            # Extract user pose data from keypoints
                            user_pose_data = form_check.keypoints
                            
                            # For now, use the setup pose for comparison
                            # In a full implementation, you'd match the user's video phase
                            if 'key_poses' in reference_data and 'setup' in reference_data['key_poses']:
                                setup_pose = reference_data['key_poses']['setup']
                                
                                # Generate comparison data
                                from app.services.pose_comparison_service import PoseAlignmentService
                                alignment_service = PoseAlignmentService(self.settings)
                                
                                overlay_data = alignment_service.generate_overlay_alignment_data(
                                    user_pose=user_pose_data,
                                    reference_pose=setup_pose,
                                    highlight_deviations=True
                                )
                                
                        except Exception as overlay_error:
                            logger.warning(f"Error generating overlay data: {overlay_error}")
                            overlay_data = None
                    
                    form_check_dict["visual_overlay_data"] = overlay_data
                    
                    logger.info(f"Added reference pose data and visual overlay to form check {form_check_id}")
                    
                except Exception as e:
                    logger.error(f"Error getting reference pose data for form check {form_check_id}: {e}")
                    form_check_dict["reference_pose_data"] = None
                    form_check_dict["visual_overlay_data"] = None
            else:
                form_check_dict["reference_pose_data"] = None
                form_check_dict["visual_overlay_data"] = None
            
            return form_check_dict
            
        except Exception as e:
            logger.error(f"Error getting form check details with reference: {e}", exc_info=True)
            return None

    async def get_previous_completed_form_check(
        self,
        user_id: UUID,
        exercise_slug: str,
        exclude_form_check_id: UUID,
        db: AsyncSession,
    ) -> Optional[FormCheck]:
        """Return the most recent completed FormCheck before exclude_form_check_id."""
        query = (
            select(FormCheck)
            .where(
                FormCheck.user_id == user_id,
                FormCheck.status == FormCheckStatus.COMPLETED,
                FormCheck.id != exclude_form_check_id,
                or_(
                    FormCheck.exercise_type == exercise_slug,
                    FormCheck.classified_exercise_slug == exercise_slug,
                ),
            )
            .order_by(FormCheck.created_at.desc())
            .limit(1)
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_user_best_score(
        self,
        user_id: UUID,
        exercise_slug: str,
        exclude_form_check_id: UUID,
        db: AsyncSession,
    ) -> Optional[float]:
        """Return highest posture_score across all previous completed sessions."""
        query = (
            select(func.max(FormCheck.posture_score))
            .where(
                FormCheck.user_id == user_id,
                FormCheck.status == FormCheckStatus.COMPLETED,
                FormCheck.id != exclude_form_check_id,
                FormCheck.posture_score.isnot(None),
                or_(
                    FormCheck.exercise_type == exercise_slug,
                    FormCheck.classified_exercise_slug == exercise_slug,
                ),
            )
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()


async def get_async_form_check_service(
    # db: AsyncSession = Depends(get_async_db), # MODIFIED: Removed Depends from signature
    # settings: Settings = Depends(get_settings), # MODIFIED: Removed Depends from signature
    storage_service: StorageService = Depends(StorageService),
    ai_service: AIService = Depends(AIService),
    cache_service_instance: CacheService = Depends(lambda: cache_service) # MODIFIED: use imported cache_service
) -> FormCheckService:
    from app.core.deps import get_async_db, get_settings # Local import
    from fastapi import Depends # Ensure Depends is available

    # Obtain db and settings using Depends with the locally imported functions
    db: AsyncSession = Depends(get_async_db)
    settings: Settings = Depends(get_settings)

    return FormCheckService(
        db=db, 
        settings=settings, 
        storage_service=storage_service, 
        ai_service=ai_service,
        cache_service=cache_service_instance
    )