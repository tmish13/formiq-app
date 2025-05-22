from fastapi import APIRouter, Depends, HTTPException, Body, UploadFile, File, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict, Any, List
import json

# Potential: from app.api import deps # If get_api_key and get_db are moved to deps
from app.core import deps # Add
from app.core.auth import get_api_key # Assuming this is still valid or placeholder
from app.core.database import AsyncSessionLocal # Add, or the correct path to it
from app.services.video_processing_service import VideoProcessingService, get_async_video_processing_service # Import service and its provider
from app.models.enums import ExerciseType
from app.schemas.training_data import TrainingDataSubmission, TrainingDataResponse
from app.services.ai_service import AIService
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/training", tags=["training"])
# video_processing = VideoProcessingService() # Removed module-level instance
ml_service = AIService()

@router.post("/submit", response_model=TrainingDataResponse)
async def submit_training_data(
    background_tasks: BackgroundTasks,
    submission: TrainingDataSubmission = Body(...),
):
    """
    Endpoint for Zapier to submit training data.
    
    This allows external tools to feed the system with new labeled data
    for improving the form analysis models.
    """
    api_key: str = Depends(get_api_key) # Re-declare to ensure it's part of the signature for FastAPI

    try:
        # Log the submission
        logger.info(f"Received training data submission for exercise: {submission.exercise_type}")
        
        # Store the training data in the database
        # In a real implementation, you would save this to your database
        # and queue it for model training
        
        # Add to background task queue for processing
        background_tasks.add_task(
            process_training_data,
            submission,
        )
        
        return TrainingDataResponse(
            success=True,
            message="Training data accepted for processing",
            submission_id="12345"  # In real implementation, return actual ID
        )
        
    except Exception as e:
        logger.error(f"Error processing training data: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing training data: {str(e)}"
        )

@router.post("/submit_video")
async def submit_training_video(
    background_tasks: BackgroundTasks,
    video: UploadFile = File(...),
    metadata: str = Body(...),
    video_processing_service: VideoProcessingService = Depends(get_async_video_processing_service)
):
    """
    Submit a video file with training metadata.
    
    This endpoint allows uploading video recordings with associated
    training metadata like expert scores and corrections.
    """
    api_key: str = Depends(get_api_key) # Re-declare for FastAPI

    try:
        # Parse metadata
        metadata_dict = json.loads(metadata)
        exercise_type = metadata_dict.get("exercise_type")
        
        if not exercise_type:
            raise HTTPException(
                status_code=400,
                detail="Exercise type is required in metadata"
            )
        
        # Read video content
        video_content = await video.read()
        
        # Process video in background
        background_tasks.add_task(
            process_training_video,
            video_content,
            metadata_dict,
            video_processing_service
        )
        
        return {
            "success": True,
            "message": "Video accepted for processing"
        }
        
    except Exception as e:
        logger.error(f"Error processing training video: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error processing training video: {str(e)}"
        )

async def process_training_data(
    submission: TrainingDataSubmission,
):
    """Background task to process submitted training data."""
    async with AsyncSessionLocal() as db:
        try:
            logger.info(f"Processing training data for {submission.exercise_type} using async session")
            
            # Example DB operation (replace with actual logic):
            # from app.models.training_log import TrainingLog # Example model
            # new_log = TrainingLog(exercise_type=submission.exercise_type.value, data=submission.dict())
            # db.add(new_log)
            # await db.commit()
            
        except Exception as e:
            logger.error(f"Error in background training data processing: {str(e)}")
            # Consider await db.rollback() here if operations were attempted

async def process_training_video(
    video_content: bytes,
    metadata: Dict[str, Any],
    video_processing_service: VideoProcessingService
):
    """Process training video in the background."""
    async with AsyncSessionLocal() as db: # Add async session context manager
        try:
            exercise_type_str = metadata.get("exercise_type")
            if not exercise_type_str:
                logger.error("Exercise type missing in metadata for training video.")
                return

            logger.info(f"Processing training video for {exercise_type_str} using async session")
            
            # Process video frames
            # VideoProcessingService.process_video might need db session if it interacts with DB
            # Assuming VideoProcessingService handles its own DB needs or is DB-agnostic here
            video_data = await video_processing_service.process_video(
                video_data=video_content,
                exercise_type=ExerciseType(exercise_type_str) # Ensure ExerciseType enum is used
            )
            
            # Example DB operation (replace with actual logic):
            # from app.models.video_training_data import VideoTrainingData # Example model
            # new_video_data = VideoTrainingData(
            #     exercise_type=exercise_type_str,
            #     metadata=metadata,
            #     processed_video_path=video_data.get("path") # Assuming video_data returns path
            # )
            # db.add(new_video_data)
            # await db.commit()
            
            logger.info(f"Processed training video for {exercise_type_str}")
            
        except Exception as e:
            logger.error(f"Error processing training video in background: {str(e)}")
            # Consider await db.rollback() here

# video_processing = VideoProcessingService() # Removed module-level instance
# ml_service = AIService()
# video_processing = VideoProcessingService() # Removed module-level instance
# ml_service = AIService() 