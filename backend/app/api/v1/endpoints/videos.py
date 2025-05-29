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
from app.tasks.video_processing import process_uploaded_video
from app.services.video_service import VideoService
from app.core.exceptions import NotFoundException, PermissionDeniedException

# Initialize logger
logger = get_logger(__name__)

# Initialize router
router = APIRouter(prefix="/videos", tags=["videos"])

@router.post("/upload/signed-url", response_model=Dict[str, Any])
async def get_presigned_upload_url(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: User = Depends(deps.get_current_user),
    video_service: VideoService = Depends(deps.get_video_service),
    storage_service: StorageService = Depends(deps.get_storage_service),
    filename: str = Body(...),
    content_type: str = Body(...),
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
            
        response_data = await video_service.create_upload_session(
            user_id=current_user.id,
            filename=filename,
            content_type=content_type,
            metadata=metadata,
            db_session=db
        )
        
        logger.info(
            f"Generated presigned upload URL: user_id={current_user.id}, video_id={response_data.get('video_id')}, filename={filename}"
        )
        return response_data
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error generating presigned URL: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating presigned URL: {str(e)}"
        )


@router.post("/upload/confirm", response_model=VideoResponse)
async def confirm_upload(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: User = Depends(deps.get_current_user),
    video_service: VideoService = Depends(deps.get_video_service),
    video_id: UUID = Body(...),
    object_key: str = Body(...),
    size: Optional[int] = Body(None)
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
            db_session=db
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
            db_session=db
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
        videos_list_schema = await video_service.list_videos_for_user(
            user_id=current_user.id, 
            skip=skip, 
            limit=limit, 
            status_filter_str=status,
            db_session=db
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
            db_session=db
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
            db_session=db
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