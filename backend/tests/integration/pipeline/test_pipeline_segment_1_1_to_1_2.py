import pytest
pytestmark = pytest.mark.integration

from unittest.mock import MagicMock, patch, AsyncMock
from uuid6 import uuid7
import os

from app.models.video import Video
from app.models.enums import VideoStatus, ExerciseType
from app.tasks.video_tasks import process_video_celery_task
from app.tasks.ai_tasks import detect_pose_celery_task
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import Settings # For mocking settings



# Assume task_always_eager=True is set for Celery in the test environment.

@pytest.fixture
async def pipeline_test_video(db_session: AsyncSession) -> Video:
    """Creates a sample video object in the database for pipeline testing."""
    video = Video(
        id=uuid7(),
        user_id=uuid7(),
        filename="pipeline_video.mp4",
        object_key="test_pipeline_videos/pipeline_video.mp4", # s3_key
        s3_bucket="test-bucket", # Added for completeness for original_s3_path construction
        status=VideoStatus.UPLOADED,
        exercise_type=ExerciseType.SQUAT,
        mime_type="video/mp4"
    )
    db_session.add(video)
    await db_session.commit()
    await db_session.refresh(video)
    return video

@pytest.mark.asyncio
@pytest.mark.pipeline # Custom marker for pipeline tests
@patch('app.tasks.video_tasks.get_app_settings') # For process_video_celery_task
@patch('app.tasks.ai_tasks.settings')      # For detect_pose_celery_task (assuming it uses global settings)
@patch('app.tasks.video_tasks.StorageService')
@patch('app.tasks.video_tasks.VideoProcessingService')
@patch('app.tasks.ai_tasks.AIService') # Patch AIService for detect_pose_celery_task
@patch('app.tasks.video_tasks.os.path.exists') 
@patch('app.tasks.video_tasks.os.makedirs')
# We are NOT patching 'detect_pose_celery_task.apply_async' because with task_always_eager=True,
# it should execute the task directly.
async def test_pipeline_segment_video_processing_to_pose_detection(
    mock_video_task_os_makedirs: MagicMock,
    mock_video_task_os_path_exists: MagicMock,
    MockAIService: MagicMock, # For detect_pose_celery_task
    MockVideoProcessingService: MagicMock, # For process_video_celery_task
    MockStorageService: MagicMock,         # For process_video_celery_task
    mock_ai_task_global_settings: MagicMock, # For detect_pose_celery_task
    mock_video_task_get_app_settings: MagicMock, # For process_video_celery_task
    db_session: AsyncSession,
    pipeline_test_video: Video,
    mock_celery_task_self: MagicMock # Generic mock for 'self' arg of tasks
):
    """
    Test the pipeline segment from process_video_celery_task to detect_pose_celery_task.
    Assumes Celery's task_always_eager=True is active.
    """
    video_id = pipeline_test_video.id
    original_s3_path = f"s3://{pipeline_test_video.s3_bucket}/{pipeline_test_video.object_key}"

    # ARRANGE
    # 1. Configure settings mocks for both tasks
    mock_shared_celery_path = "/tmp/pipeline_shared_test"
    mock_video_task_settings = Settings(CELERY_SHARED_DATA_PATH=mock_shared_celery_path)
    mock_video_task_get_app_settings.return_value = mock_video_task_settings

    # Settings for AI task (can be different attributes if needed)
    mock_ai_task_global_settings.AI_POSE_CONFIDENCE_THRESHOLD = 0.5
    mock_ai_task_global_settings.AI_SMOOTHING_WINDOW_SIZE = 5
    mock_ai_task_global_settings.AI_MAX_INTERPOLATION_GAP = 3
    
    # 2. Mock os.path.exists and os.makedirs for process_video_celery_task
    mock_video_task_os_path_exists.return_value = True # Assume dir exists
    mock_video_task_os_makedirs.return_value = None

    # 3. Mock StorageService for process_video_celery_task
    mock_storage_service_instance = MockStorageService.return_value
    mock_storage_service_instance.download_file_bytes = AsyncMock(return_value=b"pipeline video content")

    # 4. Mock VideoProcessingService for process_video_celery_task to "succeed"
    mock_vps_instance = MockVideoProcessingService.return_value
    mock_processed_frame_s3_keys = [f"processed_frames/pipeline/{video_id}/f{i}.jpg" for i in range(3)]
    mock_normalized_video_s3_key = f"normalized_videos/pipeline/{video_id}/norm.mp4"
    vps_result = {
        "frame_paths": mock_processed_frame_s3_keys,
        "normalized_video_path": mock_normalized_video_s3_key,
        "raw_video_path": "/tmp/pipeline_shared_test/raw_pipeline.mp4",
        "processed_frame_count": len(mock_processed_frame_s3_keys),
        "video_duration": 10.0, "fps": 30.0, "video_dimensions": (1280, 720), "errors": None
    }
    mock_vps_instance.process_video = AsyncMock(return_value=vps_result)

    # 5. Mock AIService for detect_pose_celery_task to "succeed"
    mock_ai_service_instance = MockAIService.return_value
    mock_raw_landmarks = [[{'name': 'nose', 'x': 0.1 * i}] for i in range(len(mock_processed_frame_s3_keys))]
    mock_final_pose_data = [[{'name': 'nose', 'x': 0.1 * i, 'smooth': True}] for i in range(len(mock_processed_frame_s3_keys))]
    mock_ai_service_instance.process_frames_for_pose = AsyncMock(return_value=mock_raw_landmarks)
    mock_ai_service_instance.smooth_and_interpolate_poses = AsyncMock(return_value=mock_final_pose_data)

    # ACT
    # Directly call the first task. If task_always_eager=True, this should trigger the second task.
    # We pass the generic mock_celery_task_self for the 'self' argument of bound tasks.
    await process_video_celery_task(
        mock_celery_task_self, # self for process_video_celery_task
        video_id_str=str(video_id),
        original_video_path=original_s3_path,
        exercise_type_value=pipeline_test_video.exercise_type.value
    )
    # No need to explicitly call detect_pose_celery_task if task_always_eager is True.
    # The 'mock_celery_task_self' will also be implicitly used by detect_pose_celery_task if it's bound.

    # ASSERT
    # Check VideoProcessingService calls (for the first task)
    expected_output_dir = os.path.join(mock_shared_celery_path, "processed_frames", str(video_id))
    mock_vps_instance.process_video.assert_called_once_with(
        video_data=b"pipeline video content",
        exercise_type=pipeline_test_video.exercise_type,
        save_processed_frames=True,
        base_output_path=expected_output_dir
    )

    # Check AIService calls (for the second task)
    MockAIService.assert_called_once_with() # Instantiated
    mock_ai_service_instance.process_frames_for_pose.assert_called_once_with(
        frame_paths=mock_processed_frame_s3_keys,
        min_pose_confidence_threshold=mock_ai_task_global_settings.AI_POSE_CONFIDENCE_THRESHOLD
    )
    mock_ai_service_instance.smooth_and_interpolate_poses.assert_called_once_with(
        pose_sequence=mock_raw_landmarks,
        smoothing_window_size=mock_ai_task_global_settings.AI_SMOOTHING_WINDOW_SIZE,
        max_interpolation_gap=mock_ai_task_global_settings.AI_MAX_INTERPOLATION_GAP
    )

    # Assert final state of the Video record in the database
    await db_session.refresh(pipeline_test_video)
    assert pipeline_test_video.status == VideoStatus.POSE_DETECTED
    assert pipeline_test_video.processed_url == mock_normalized_video_s3_key
    assert pipeline_test_video.processed_frame_paths == mock_processed_frame_s3_keys
    assert pipeline_test_video.processed_frame_count == len(mock_processed_frame_s3_keys)
    assert pipeline_test_video.raw_pose_data == mock_final_pose_data
    assert pipeline_test_video.processing_errors is None

# (Remove the old TestPipelineSegment11To12 class if it was just a placeholder)
# For this edit, we are defining the class and its test method directly.
# The original placeholder class from the setup phase can be considered replaced by this. 