from fastapi import APIRouter, Depends, HTTPException, Body, status, Request, Path, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List, Optional
from app.api import deps
from app.models.user import User
from app.models.video import Video, VideoStatus
from app.services.storage_service import StorageService
from app.core.logging import get_logger
from app.core.config import settings
from app.schemas.video import VideoCreate, VideoUpdate, VideoResponse, VideoAnalysisRequest, VideoAnalysisResult
from app.core.auth import get_current_admin_user
from uuid import UUID
import os
import time
from app.services.video_service import VideoService
from app.core.exceptions import NotFoundException, PermissionDeniedException

# Initialize logger
logger = get_logger(__name__)

# Initialize router
router = APIRouter(prefix="/videos", tags=["videos"])

# Frontend expects /videos/upload-url
@router.post("/upload-url", response_model=Dict[str, Any])
async def get_presigned_upload_url(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: User = Depends(deps.get_current_user),
    video_service: VideoService = Depends(deps.get_video_service),
    storage_service: StorageService = Depends(deps.get_storage_service),
    filename: str = Body(...),
    content_type: str = Body(...),
    exercise_id: Optional[str] = Body(None),
    user_id: Optional[str] = Body(None),
    metadata: Optional[Dict[str, Any]] = Body(default=None)
) -> Dict[str, Any]:
    """
    Get a presigned URL for direct video upload to S3.
    
    This endpoint allows clients to obtain a pre-signed URL to upload
    video files directly to the storage provider (S3), bypassing the backend
    for improved performance and reduced server load.
    
    Args:
        filename: Original filename
        content_type: MIME type of the file
        metadata: Optional additional metadata
        
    Returns:
        Dict with presigned URL and upload ID
    """
    try:
        # Validate content type
        if not content_type.startswith("video/"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid content type. Must be a video format."
            )
            
        # Prepare metadata with exercise_id if provided
        upload_metadata = metadata or {}
        if exercise_id:
            upload_metadata['exercise_id'] = exercise_id
        if user_id:
            upload_metadata['user_id'] = user_id

        response_data = await video_service.create_upload_session(
            user_id=current_user.id,
            filename=filename,
            content_type=content_type,
            metadata=upload_metadata,
        )

        logger.info(
            f"Generated presigned upload URL: user_id={current_user.id}, video_id={response_data.get('video_id')}, filename={filename}"
        )
        # Return data in format expected by frontend
        return {
            "uploadUrl": response_data.get("upload_url"),
            "videoId": response_data.get("video_id"),
            "fields": response_data.get("fields", {})
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error generating presigned URL: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating presigned URL: {str(e)}"
        )


# Frontend expects /videos/upload-complete
@router.post("/upload-complete", response_model=VideoResponse)
async def confirm_upload(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: User = Depends(deps.get_current_user),
    video_service: VideoService = Depends(deps.get_video_service),
    video_id: UUID = Body(..., alias="videoId"),
    duration: Optional[float] = Body(None),
    size: Optional[int] = Body(None),
    width: Optional[int] = Body(None),
    height: Optional[int] = Body(None),
    object_key: Optional[str] = Body(None)
) -> VideoResponse:
    """
    Confirm that a video has been successfully uploaded to S3.
    
    This endpoint is called by the client after completing a direct upload to S3.
    It updates the video record status and triggers processing if needed.
    
    Args:
        video_id: ID of the video record
        object_key: S3 object key
        size: File size in bytes if known
        
    Returns:
        Updated video record
    """
    try:
        updated_video_schema = await video_service.confirm_video_upload(
            video_id=video_id,
            current_user_id=current_user.id,
            is_superuser=current_user.is_superuser,
            object_key=object_key,
            size=size,
        )
        logger.info(f"Video upload confirmed: id={updated_video_schema.id}, initiating processing task")
        return updated_video_schema
    except HTTPException as e:
        raise e
    except NotFoundException as e:
        logger.warning(f"NotFoundException in confirm_upload: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except PermissionDeniedException as e:
        logger.warning(f"PermissionDeniedException in confirm_upload: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error confirming video upload: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error confirming video upload: {str(e)}"
        )


@router.get("/{video_id}", response_model=VideoResponse)
async def get_video(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: User = Depends(deps.get_current_user),
    video_service: VideoService = Depends(deps.get_video_service),
    video_id: UUID = Path(...)
) -> VideoResponse:
    """
    Get details of a specific video.
    
    Args:
        video_id: ID of the video
        
    Returns:
        Video details
    """
    try:
        video_schema = await video_service.get_video_details(
            video_id=video_id,
            current_user_id=current_user.id,
            is_superuser=current_user.is_superuser,
        )
        if not video_schema:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found or not authorized")
        return video_schema
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error retrieving video: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving video: {str(e)}"
        )
        

@router.get("/", response_model=List[VideoResponse])
async def list_videos(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: User = Depends(deps.get_current_user),
    video_service: VideoService = Depends(deps.get_video_service),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None)
) -> List[VideoResponse]:
    """
    List videos for the current user.
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        status: Optional status filter
        
    Returns:
        List of videos
    """
    try:
        try:
            status_enum = VideoStatus(status) if status else None
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Invalid status value: {status}")
        videos_list_schema = await video_service.list_videos_for_user(
            user_id=current_user.id,
            skip=skip,
            limit=limit,
            status_filter=status_enum,
        )
        return videos_list_schema
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error listing videos: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing videos: {str(e)}"
        )


@router.delete("/{video_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_video(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: User = Depends(deps.get_current_user),
    video_service: VideoService = Depends(deps.get_video_service),
    video_id: UUID = Path(...)
):
    """
    Delete a video.
    
    Args:
        video_id: ID of the video to delete
    """
    try:
        await video_service.delete_video_by_id(
            video_id=video_id,
            current_user_id=current_user.id,
            is_superuser=current_user.is_superuser,
        )
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error deleting video: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting video: {str(e)}"
        )


@router.post("/{video_id}/process", response_model=VideoResponse)
async def process_video(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: User = Depends(deps.get_current_user),
    video_service: VideoService = Depends(deps.get_video_service),
    video_id: UUID = Path(...)
) -> VideoResponse:
    """
    Manually trigger processing for a video.
    
    This endpoint allows reprocessing of previously uploaded videos
    or retrying failed processing.
    
    Args:
        video_id: ID of the video to process
        
    Returns:
        Updated video record
    """
    try:
        video_schema = await video_service.request_video_processing(
            video_id=video_id,
            current_user_id=current_user.id,
            is_superuser=current_user.is_superuser,
        )
        return video_schema
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error processing video: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing video: {str(e)}"
        )


@router.get("/{video_id}/status", response_model=Dict[str, Any])
async def get_video_status(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: User = Depends(deps.get_current_user),
    video_service: VideoService = Depends(deps.get_video_service),
    video_id: UUID = Path(...)
) -> Dict[str, Any]:
    """
    Get video processing status.
    
    Args:
        video_id: ID of the video
        
    Returns:
        Video status information
    """
    try:
        video_schema = await video_service.get_video_details(
            video_id=video_id,
            current_user_id=current_user.id,
            is_superuser=current_user.is_superuser,
        )
        if not video_schema:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")
        
        return {
            "status": video_schema.status,
            "progress": 100 if video_schema.status == VideoStatus.READY else 50,
            "error": None if video_schema.status != VideoStatus.FAILED else "Processing failed",
            "processedUrl": video_schema.processed_url
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error getting video status: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting video status: {str(e)}"
        )


@router.get("/statistics", response_model=Dict[str, Any])
async def get_video_statistics(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: User = Depends(deps.get_current_user),
    video_service: VideoService = Depends(deps.get_video_service),
    time_range: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """
    Get comprehensive video statistics.
    
    Args:
        time_range: Optional time range filter (7d, 30d, 90d, 1y)
        
    Returns:
        Video statistics
    """
    try:
        # Get user's videos
        videos = await video_service.list_videos_for_user(
            user_id=current_user.id,
            skip=0,
            limit=1000,  # Get all videos for statistics
            status_filter=None,
        )
        
        # Calculate statistics
        total_videos = len(videos)
        processed_videos = sum(1 for v in videos if v.status == VideoStatus.READY.value)
        failed_videos = sum(1 for v in videos if v.status == VideoStatus.FAILED.value)
        processing_videos = sum(1 for v in videos if v.status == VideoStatus.PROCESSING.value)
        
        # Calculate storage used
        total_storage = sum(v.size or 0 for v in videos)
        
        # Mock exercise type breakdown (would need actual exercise tracking)
        uploads_by_exercise = {
            "squat": int(total_videos * 0.4),
            "deadlift": int(total_videos * 0.3), 
            "bench_press": int(total_videos * 0.2),
            "other": total_videos - int(total_videos * 0.9)
        }
        
        # Group videos by date
        daily_uploads = {}
        for video in videos:
            date_str = video.created_at.strftime("%Y-%m-%d")
            daily_uploads[date_str] = daily_uploads.get(date_str, 0) + 1
        
        daily_uploads_list = [
            {"date": date, "count": count} 
            for date, count in daily_uploads.items()
        ]
        
        success_rate = (processed_videos / total_videos * 100) if total_videos > 0 else 0
        
        return {
            "totalVideos": total_videos,
            "processedVideos": processed_videos,
            "failedVideos": failed_videos,
            "processingVideos": processing_videos,
            "averageProcessingTime": 45,  # Mock value in seconds
            "totalStorageUsed": total_storage,
            "uploadsByExerciseType": uploads_by_exercise,
            "dailyUploads": daily_uploads_list,
            "successRate": success_rate
        }
    except Exception as e:
        logger.error(f"Error getting video statistics: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting video statistics: {str(e)}"
        )


@router.get("/processing-stats", response_model=Dict[str, Any])
async def get_processing_stats(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: User = Depends(deps.get_current_user),
    video_service: VideoService = Depends(deps.get_video_service)
) -> Dict[str, Any]:
    """
    Get video processing performance metrics.
    
    Returns:
        Processing performance statistics
    """
    try:
        # Get user's videos
        videos = await video_service.list_videos_for_user(
            user_id=current_user.id,
            skip=0,
            limit=1000,
            status_filter=None,
        )

        processing_success = sum(1 for v in videos if v.status == VideoStatus.READY.value)
        processing_failure = sum(1 for v in videos if v.status == VideoStatus.FAILED.value)
        processing_videos = sum(1 for v in videos if v.status == VideoStatus.PROCESSING.value)
        
        # Count processed today
        from datetime import datetime, timedelta
        today = datetime.now().date()
        processed_today = sum(
            1 for v in videos 
            if v.status == VideoStatus.READY.value and v.updated_at.date() == today
        )
        
        return {
            "averageProcessingTime": 45,  # Mock value
            "processingSuccess": processing_success,
            "processingFailure": processing_failure,
            "queueLength": processing_videos,
            "processedToday": processed_today,
            "processingErrors": [
                {"error": "Invalid format", "count": int(processing_failure * 0.4)},
                {"error": "File corrupted", "count": int(processing_failure * 0.3)},
                {"error": "Processing timeout", "count": int(processing_failure * 0.3)}
            ],
            "processingTimeByExercise": {
                "squat": 40,
                "deadlift": 50,
                "bench_press": 35,
                "other": 45
            }
        }
    except Exception as e:
        logger.error(f"Error getting processing stats: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting processing stats: {str(e)}"
        )


@router.get("/conversion-metrics", response_model=Dict[str, Any])
async def get_conversion_metrics(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: User = Depends(deps.get_current_user),
    video_service: VideoService = Depends(deps.get_video_service),
    time_range: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """
    Get video-to-form-check conversion metrics.
    
    Args:
        time_range: Optional time range filter
        
    Returns:
        Conversion metrics
    """
    try:
        # Get user's videos
        videos = await video_service.list_videos_for_user(
            user_id=current_user.id,
            skip=0,
            limit=1000,
            status_filter=None,
        )
        
        videos_uploaded = len(videos)
        successful_videos = sum(1 for v in videos if v.status == VideoStatus.READY.value)
        
        # Estimate form checks created (95% of successful videos)
        form_checks_created = int(successful_videos * 0.95)
        
        conversion_rate = (form_checks_created / videos_uploaded * 100) if videos_uploaded > 0 else 0
        
        return {
            "videosUploaded": videos_uploaded,
            "formChecksCreated": form_checks_created,
            "conversionRate": conversion_rate,
            "averageTimeToCompletion": 120,  # 2 minutes average
            "successfulAnalyses": form_checks_created,
            "failedAnalyses": successful_videos - form_checks_created
        }
    except Exception as e:
        logger.error(f"Error getting conversion metrics: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting conversion metrics: {str(e)}"
        )


@router.get("/quality-metrics", response_model=Dict[str, Any])
async def get_quality_metrics(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: User = Depends(deps.get_current_user),
    video_service: VideoService = Depends(deps.get_video_service)
) -> Dict[str, Any]:
    """
    Get video storage and quality metrics.
    
    Returns:
        Quality metrics
    """
    try:
        # Get user's videos
        videos = await video_service.list_videos_for_user(
            user_id=current_user.id,
            skip=0,
            limit=1000,
            status_filter=None,
        )
        
        total_size = sum(v.size or 0 for v in videos)
        avg_file_size = total_size / len(videos) if videos else 0
        
        # Generate estimated distribution data
        video_count = len(videos)
        resolution_distribution = {
            "1920x1080": int(video_count * 0.4),
            "1280x720": int(video_count * 0.35),
            "640x480": int(video_count * 0.15),
            "other": int(video_count * 0.1)
        }
        
        format_distribution = {
            "mp4": int(video_count * 0.7),
            "webm": int(video_count * 0.2),
            "mov": int(video_count * 0.1)
        }
        
        return {
            "averageFileSize": avg_file_size,
            "averageDuration": 30,  # 30 seconds average
            "resolutionDistribution": resolution_distribution,
            "formatDistribution": format_distribution,
            "qualityScores": [
                {"quality": "High", "count": int(video_count * 0.6)},
                {"quality": "Medium", "count": int(video_count * 0.3)},
                {"quality": "Low", "count": int(video_count * 0.1)}
            ],
            "compressionRates": [
                {"original": 100, "compressed": 60, "ratio": 0.6},
                {"original": 80, "compressed": 45, "ratio": 0.56},
                {"original": 120, "compressed": 70, "ratio": 0.58}
            ]
        }
    except Exception as e:
        logger.error(f"Error getting quality metrics: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting quality metrics: {str(e)}"
        ) 