import pytest
from unittest.mock import patch, MagicMock, AsyncMock, ANY, PropertyMock
from uuid6 import uuid7
from uuid import UUID
from datetime import datetime, timezone
import logging # ADDED for retry test warnings
import numpy as np # ADDED
import cv2 # ADDED
import json

from app.models.video import Video
from app.models.enums import VideoStatus, ExerciseType
from app.tasks.ai_tasks import detect_pose_celery_task, calculate_angles_celery_task
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker # Added async_sessionmaker
from app.core.config import Settings # For mocking settings
from celery.exceptions import Ignore, Retry as CeleryTaskRetryException # Added Ignore

# Shared attempt_tracker for the retry test to ensure statefulness across calls
# This is a module-level variable to ensure it's the same instance.
retry_test_attempt_tracker = {'count': 0}

@pytest.fixture
async def video_for_pose_detection(db_session: AsyncSession) -> Video:
    """Creates a sample video object in the database, prepared for pose detection."""
    video_id_for_frames = uuid7() # Use a consistent ID for frame paths if needed for realism
    current_time = datetime.now(timezone.utc)
    unique_object_key = f"test_raw_videos/sample_video_for_pose_{video_id_for_frames}.mp4"
    video = Video(
        id=video_id_for_frames,
        user_id=uuid7(),
        filename="sample_video_for_pose.mp4",
        object_key=unique_object_key,
        processed_url=f"normalized_videos/{video_id_for_frames}/normalized.mp4",
        frame_s3_keys=[
            f"processed_frames/{video_id_for_frames}/frame_001.jpg",
            f"processed_frames/{video_id_for_frames}/frame_002.jpg",
            f"processed_frames/{video_id_for_frames}/frame_003.jpg"
        ],
        processed_frame_count=3,
        duration=5.0,
        fps=30.0,
        resolution="1920x1080",
        status=VideoStatus.POSE_DETECTION_PENDING, 
        exercise_type=ExerciseType.SQUAT,
        mime_type="video/mp4",
        created_at=current_time,
        updated_at=current_time
    )
    db_session.add(video)
    await db_session.commit()
    await db_session.refresh(video)
    return video

@pytest.fixture
async def video_for_angle_calculation(db_session: AsyncSession) -> Video:
    """Creates a sample video object in the database, prepared for angle calculation."""
    video_id = uuid7()
    current_time = datetime.now(timezone.utc)
    # Mock raw_pose_data: 3 frames, 33 landmarks per frame. Some landmarks can be None.
    # Frame 0: All landmarks present
    # Frame 1: All landmarks None (simulating a bad frame from pose detection)
    # Frame 2: Some landmarks present, some None
    mock_landmark = lambda i: {'x': 0.5 + i*0.01, 'y': 0.5 - i*0.01, 'z': 0.1, 'visibility': 0.9}
    
    frame_0_landmarks = [mock_landmark(i) for i in range(33)]
    frame_1_landmarks = None # Simulate a frame where pose detection failed entirely
    frame_2_landmarks = [mock_landmark(i) if i % 2 == 0 else None for i in range(33)] # Some landmarks missing

    raw_pose_data = [
        frame_0_landmarks,
        frame_1_landmarks,
        frame_2_landmarks
    ]

    video = Video(
        id=video_id,
        user_id=uuid7(),
        filename="sample_video_for_angles.mp4",
        object_key=f"test_raw_videos/sample_video_for_angles_{video_id}.mp4",
        status=VideoStatus.ANGLE_CALCULATION_PENDING,
        exercise_type="squat", # Example exercise type
        mime_type="video/mp4",
        raw_pose_data=raw_pose_data, # Key data for this test
        created_at=current_time,
        updated_at=current_time
    )
    db_session.add(video)
    await db_session.commit()
    await db_session.refresh(video)
    return video

@pytest.mark.asyncio
@patch('app.tasks.ai_tasks.get_settings_override')
# @patch('app.tasks.ai_tasks.StorageService') # REMOVED
# @patch('app.tasks.ai_tasks.AIService') # REMOVED
# @patch('app.tasks.ai_tasks.VideoService') # REMOVED
@patch('app.services.storage_service.StorageService.download_file', new_callable=AsyncMock) # ADDED
@patch('app.services.ai_service.AIService.process_frames_for_pose', new_callable=AsyncMock) # ADDED
@patch('app.tasks.ai_tasks.calculate_angles_celery_task')
@patch('cv2.imdecode') # RESTORED - Called in this path
async def test_detect_pose_celery_task_process_frames_failure(
    mock_cv2_imdecode: MagicMock, # RESTORED
    mock_calculate_angles_task: MagicMock,
    mock_ai_process_frames: AsyncMock, # UPDATED
    mock_storage_download_file: AsyncMock, # UPDATED
    mock_get_settings_override: MagicMock,
    video_for_pose_detection: Video,
    test_async_session_factory: async_sessionmaker[AsyncSession]
    # mock_video_service_class: MagicMock, # REMOVED
):
    video_id = video_for_pose_detection.id
    s3_keys = video_for_pose_detection.frame_s3_keys
    simulated_error_message = "Simulated AI error during process_frames_for_pose"
    simulated_error_type = "RuntimeError"

    # ARRANGE
    settings_return_value = mock_get_settings_override.return_value
    settings_return_value.AI_MIN_DETECTION_CONFIDENCE = 0.5

    dummy_np_frame = np.array([[[1, 2, 3]]], dtype=np.uint8)
    mock_cv2_imdecode.return_value = dummy_np_frame # RESTORED

    mock_storage_download_file.return_value = b"dummy_frame_content" # Setup on the patched method

    mock_ai_process_frames.side_effect = RuntimeError(simulated_error_message) # Setup on the patched method

    # VideoService will be real. We expect it to try and update the DB.
    # We don't need to mock its instantiation or methods like get_video_by_id for this test path
    # as the error occurs before those would be problematic if not mocked.

    # ACT
    with pytest.raises(RuntimeError, match=simulated_error_message):
        # The task itself will raise the error from ai_service.process_frames_for_pose
        # and then this will be caught by self.retry(exc=e) if bind=True
        # For this test, we are checking if the original error propagates
        await detect_pose_celery_task.__wrapped__(
            str(video_id),
            s3_keys
        )

    # ASSERT MOCK CALLS
    mock_get_settings_override.assert_called() # Settings are always fetched
    
    # Assert that our patched methods were called
    mock_storage_download_file.assert_called() 
    mock_ai_process_frames.assert_called_once_with(
        frames_data_np=ANY, # We can be more specific if needed by capturing frames
        min_pose_confidence_threshold=settings_return_value.AI_MIN_DETECTION_CONFIDENCE
    )
    
    mock_calculate_angles_task.apply_async.assert_not_called()

    # ASSERT DATABASE STATE 
    # The task's error handling should update the video status to FAILED
    # and record the error message. The commit in BaseService seems to persist
    # despite the subsequent self.retry() call and session rollback in get_celery_db_session_context.
    session_maker = test_async_session_factory
    async with session_maker() as new_db_session:
        new_db_session.expire_all() # Ensure no cached state
        refreshed_video = await new_db_session.get(Video, video_id)
        assert refreshed_video is not None
        
        assert refreshed_video.status == VideoStatus.POSE_DETECTION_FAILED
        expected_error_details_json_str = json.dumps({"error_type": simulated_error_type, "details": simulated_error_message})
        assert refreshed_video.error_message == expected_error_details_json_str

@pytest.mark.asyncio
@patch('app.tasks.ai_tasks.get_settings_override')
# @patch('app.tasks.ai_tasks.StorageService') # REMOVED
# @patch('app.tasks.ai_tasks.AIService') # REMOVED
# @patch('app.tasks.ai_tasks.VideoService') # REMOVED
@patch('app.tasks.ai_tasks.calculate_angles_celery_task')
# @patch('cv2.imdecode') # CORRECT - Stays commented, not called in this path
async def test_detect_pose_celery_task_video_not_found(
    # mock_cv2_imdecode: MagicMock, # CORRECT - Stays commented
    mock_calculate_angles_task: MagicMock,
    mock_get_settings_override: MagicMock,
    # db_session: AsyncSession, # Not directly used for assertion if task raises Ignore
    # mock_video_service_class: MagicMock, # REMOVED
    # mock_ai_service_class: MagicMock, # REMOVED
    # mock_storage_service_class: MagicMock, # REMOVED
):
    non_existent_video_id_str = str(uuid7())
    dummy_frame_s3_keys = ["frame1.jpg", "frame2.jpg"]

    # ARRANGE
    # settings_return_value = mock_get_settings_override.return_value # Not strictly needed for asserts if services are real

    # VideoService will be real. Its get_async method will return None.
    # StorageService and AIService will be real but not used significantly in this path.

    # ACT & ASSERT
    with pytest.raises(Ignore):
        await detect_pose_celery_task.__wrapped__(
            str(non_existent_video_id_str),
            dummy_frame_s3_keys
        )
    
    # ASSERT MOCK CALLS
    mock_get_settings_override.assert_called_once() 
    # We can't easily assert on real service instantiations without more complex patching or DI.
    # The core check is that Ignore is raised and other mocks aren't called.
    
    mock_calculate_angles_task.apply_async.assert_not_called()
    # mock_cv2_imdecode.assert_not_called() # CORRECT - Stays commented

    # Further assertions on real service method calls (e.g. VideoService.get_async) would require
    # patching those specific methods if we wanted to verify they were called with specific args
    # before the Ignore. For this test, verifying Ignore is raised is the main goal.


@pytest.mark.asyncio
@patch('app.tasks.ai_tasks.get_settings_override')
# @patch('app.tasks.ai_tasks.StorageService') # REMOVED
# @patch('app.tasks.ai_tasks.AIService') # REMOVED
# @patch('app.tasks.ai_tasks.VideoService') # REMOVED
@patch('app.services.storage_service.StorageService.download_file', new_callable=AsyncMock) # ADDED
@patch('app.services.ai_service.AIService.process_frames_for_pose', new_callable=AsyncMock) # ADDED
@patch('app.tasks.ai_tasks.calculate_angles_celery_task')
@patch('cv2.imdecode') # RESTORED - Called in this path
async def test_detect_pose_celery_task_retry_and_succeed(
    mock_cv2_imdecode: MagicMock, # RESTORED
    mock_calculate_angles_task: MagicMock,
    mock_ai_process_frames: AsyncMock, # UPDATED
    mock_storage_download_file: AsyncMock, # UPDATED
    mock_get_settings_override: MagicMock,
    video_for_pose_detection: Video,
    test_async_session_factory: async_sessionmaker[AsyncSession]
    # mock_video_service_class: MagicMock, # REMOVED
    # mock_ai_service_class: MagicMock, # REMOVED
    # mock_storage_service_class: MagicMock, # REMOVED
):
    video_id = video_for_pose_detection.id
    s3_keys = video_for_pose_detection.frame_s3_keys
    transient_error_message = "Simulated transient AI error in process_frames"
    simulated_error_type = "RuntimeError"
    num_frames = len(s3_keys)

    # ARRANGE
    settings_return_value = mock_get_settings_override.return_value
    settings_return_value.AI_MIN_DETECTION_CONFIDENCE = 0.55
    settings_return_value.CELERY_TASK_MAX_RETRIES = 3
    settings_return_value.CELERY_TASK_DEFAULT_RETRY_DELAY = 1

    dummy_np_frame = np.array([[[1, 2, 3]]], dtype=np.uint8)
    mock_cv2_imdecode.return_value = dummy_np_frame # RESTORED

    mock_storage_download_file.return_value = b"dummy_frame_content"

    mock_landmark_data_retry = {'x': 0.6, 'y': 0.15, 'z': 0.25, 'visibility': 0.97}
    mock_raw_landmarks_retry_success = [[mock_landmark_data_retry] * 33] * num_frames
    
    retry_test_attempt_tracker['count'] = 0 

    async def mock_process_frames_side_effect_for_retry(*args, **kwargs):
        retry_test_attempt_tracker['count'] += 1
        if retry_test_attempt_tracker['count'] == 1:
            raise RuntimeError(transient_error_message)
        return mock_raw_landmarks_retry_success
    
    mock_ai_process_frames.side_effect = mock_process_frames_side_effect_for_retry

    # VideoService will be real.
    celery_retry_call_tracker = {'count': 0} 
    mock_request_context_obj = MagicMock()
    # Initialize retries to 0 for the first "actual" run before Celery's retry mechanism kicks in.
    # The task's `self.request.retries` will be 0 on the first execution.
    mock_request_context_obj.retries = 0

    def custom_mock_celery_retry_method(exc=None, countdown=None, **kwargs):
        nonlocal celery_retry_call_tracker 
        celery_retry_call_tracker['count'] += 1
        # Simulate Celery updating the retries count on the request object for the *next* attempt
        # This mock doesn't perfectly replicate Celery's internal request object lifecycle across
        # actual retries, but helps track that retry() was called.
        # The task itself reads self.request.retries to know current attempt number.
        # For the *first* call that leads to self.retry(), self.request.retries is 0.
        # Celery would handle incrementing it for subsequent actual worker executions.
        raise CeleryTaskRetryException(exc=exc)

    # ACT & ASSERT - First call (should raise CeleryTaskRetryException due to task calling self.retry)
    # Patch self.retry and self.request for the task instance
    # Patching Task.request globally for this specific call context.
    with patch('celery.app.task.Task.request', new_callable=PropertyMock, return_value=mock_request_context_obj) as mock_global_task_request_prop, \
         patch('app.tasks.ai_tasks.detect_pose_celery_task.retry', side_effect=custom_mock_celery_retry_method) as mock_task_retry_method:
        
        # Ensure the global mock is active when the task runs
        assert detect_pose_celery_task.request == mock_request_context_obj

        with pytest.raises(CeleryTaskRetryException) as exc_info:
            await detect_pose_celery_task.__wrapped__(str(video_id), s3_keys)
        
        assert celery_retry_call_tracker['count'] == 1
        assert isinstance(exc_info.value.exc, RuntimeError) 
        assert str(exc_info.value.exc) == transient_error_message

        # DB assertions after first (failed) attempt - commit in error handler persists
        async with test_async_session_factory() as new_db_session:
            new_db_session.expire_all()
            video_after_fail_attempt = await new_db_session.get(Video, video_id)
            assert video_after_fail_attempt is not None
            assert video_after_fail_attempt.status == VideoStatus.POSE_DETECTION_FAILED
            expected_error_details_json_str = json.dumps({"error_type": simulated_error_type, "details": transient_error_message})
            assert video_after_fail_attempt.error_message == expected_error_details_json_str
        
        mock_calculate_angles_task.apply_async.assert_not_called()

    # ARRANGE for the second call (simulating Celery retry, should succeed)
    # Reset side effect for AI service mock to ensure it succeeds now
    mock_ai_process_frames.reset_mock() # Reset call count and side_effect
    mock_ai_process_frames.side_effect = mock_process_frames_side_effect_for_retry # Re-assign side_effect
    
    # Reset other relevant mocks
    mock_storage_download_file.reset_mock()
    mock_storage_download_file.return_value = b"dummy_frame_content" # Re-assign after reset
    mock_calculate_angles_task.reset_mock()
    
    # Simulate Celery's behavior for a retry: self.request.retries would be 1
    # Need a new mock_request_context_obj or update the existing one for the "next" call.
    # Let's assume for the direct __wrapped__ call, we are simulating the *code path* of a retry,
    # so the internal logic of `detect_pose_celery_task` will run again.
    # The retry_test_attempt_tracker['count'] ensures `process_frames_for_pose` succeeds.
    # `self.request.retries` would be 1 if Celery was actually re-executing the task.
    # Our patching of `self.retry` doesn't make the task re-execute via Celery's loop.
    # We call __wrapped__ again. The crucial part is `retry_test_attempt_tracker`.
    
    # ACT - Second call (simulating Celery retry by direct invocation, should succeed)
    # No need to patch self.retry or self.request again, as it shouldn't call retry this time.
    await detect_pose_celery_task.__wrapped__(str(video_id), s3_keys)

    assert retry_test_attempt_tracker['count'] == 2 
    assert mock_storage_download_file.call_count == num_frames 
    assert mock_ai_process_frames.call_count == 1 # Called once in this successful attempt

    mock_calculate_angles_task.apply_async.assert_called_once()

    # DB assertions after successful "retry"
    async with test_async_session_factory() as new_db_session:
        new_db_session.expire_all()
        refreshed_video_after_retry = await new_db_session.get(Video, video_id)
        assert refreshed_video_after_retry is not None
        assert refreshed_video_after_retry.status == VideoStatus.ANGLE_CALCULATION_PENDING
        assert refreshed_video_after_retry.error_message is None # Error cleared on success path
        assert refreshed_video_after_retry.raw_pose_data == mock_raw_landmarks_retry_success # CORRECTED ASSERTION

@pytest.mark.asyncio
@patch('app.tasks.ai_tasks.get_settings_override')
# @patch('app.tasks.ai_tasks.StorageService') # REMOVED
# @patch('app.tasks.ai_tasks.AIService') # REMOVED
# @patch('app.tasks.ai_tasks.VideoService') # REMOVED
@patch('app.services.storage_service.StorageService.download_file', new_callable=AsyncMock) # ADDED
@patch('app.tasks.ai_tasks.calculate_angles_celery_task')
# @patch('cv2.imdecode') # CORRECT - Stays commented, cv2.imdecode won't be called if download fails
async def test_detect_pose_celery_task_storage_service_failure(
    # mock_cv2_imdecode: MagicMock, # CORRECT - Stays commented
    mock_calculate_angles_task: MagicMock,
    mock_storage_download_file: AsyncMock, # UPDATED
    mock_get_settings_override: MagicMock,
    video_for_pose_detection: Video,
    test_async_session_factory: async_sessionmaker[AsyncSession]
    # mock_video_service_class: MagicMock, # REMOVED
    # mock_ai_service_class: MagicMock, # REMOVED
    # mock_storage_service_class: MagicMock, # REMOVED
):
    video_id = video_for_pose_detection.id
    s3_keys = video_for_pose_detection.frame_s3_keys
    simulated_exception_message = "Simulated S3 download error"
    # The type of exception raised by the mock download_file (not directly used in DB error msg for this path)
    # simulated_exception_type_name = "Exception" 

    # ARRANGE
    settings_return_value = mock_get_settings_override.return_value
    settings_return_value.MAX_FRAME_DOWNLOAD_FAILURE_RATIO = 0.5 # Default, but explicit

    mock_storage_download_file.side_effect = Exception(simulated_exception_message)

    # ACT
    await detect_pose_celery_task.__wrapped__(str(video_id), s3_keys)

    # ASSERT DATABASE STATE
    async with test_async_session_factory() as new_db_session:
        new_db_session.expire_all()
        refreshed_video = await new_db_session.get(Video, video_id)
        assert refreshed_video is not None
        assert refreshed_video.status == VideoStatus.POSE_DETECTION_FAILED
        
        # The error message set by ai_tasks.py in this specific path is a direct string:
        # error_msg = f"Failed to download sufficient frames from S3: {e_download_decode}"
        expected_error_message_in_db = f"Failed to download sufficient frames from S3: {simulated_exception_message}"
        assert refreshed_video.error_message == expected_error_message_in_db

    # ASSERT MOCK CALLS
    mock_get_settings_override.assert_called_once()
    assert mock_storage_download_file.call_count == 2 
    mock_calculate_angles_task.apply_async.assert_not_called()

@pytest.mark.asyncio
@patch('app.tasks.ai_tasks.get_settings_override')
# @patch('app.tasks.ai_tasks.StorageService') # REMOVED
# @patch('app.tasks.ai_tasks.AIService') # REMOVED - AIService is not directly called if no frames
# @patch('app.tasks.ai_tasks.VideoService') # REMOVED
@patch('app.services.storage_service.StorageService.download_file', new_callable=AsyncMock) # CORRECT
@patch('app.tasks.ai_tasks.calculate_angles_celery_task')
# @patch('cv2.imdecode') # CORRECT - Stays commented, not called in this path
async def test_detect_pose_celery_task_no_frames_downloaded(
    # mock_cv2_imdecode_unused: MagicMock, # CORRECT - Stays commented/removed
    mock_calculate_angles_task: MagicMock,
    mock_storage_download_file: AsyncMock, # CORRECT
    mock_get_settings_override: MagicMock,
    video_for_pose_detection: Video,
    test_async_session_factory: async_sessionmaker[AsyncSession]
    # mock_video_service_class: MagicMock, # REMOVED
    # mock_ai_service_class: MagicMock, # REMOVED - No direct AI service call
):
    video_id = video_for_pose_detection.id
    s3_keys = video_for_pose_detection.frame_s3_keys # These will be passed to the task

    # ARRANGE
    settings_return_value = mock_get_settings_override.return_value
    # No AI_MIN_DETECTION_CONFIDENCE needed as AI service won't be called

    mock_storage_download_file.return_value = None # Simulate download failure for all frames

    # Real VideoService, StorageService (with download_file patched), and AIService (not called) will be used by the task.

    # ACT
    task_result = await detect_pose_celery_task.__wrapped__(str(video_id), s3_keys)

    # ASSERT MOCK CALLS
    mock_get_settings_override.assert_called_once()
    assert mock_storage_download_file.call_count == len(s3_keys)
    # mock_ai_service.process_frames_for_pose should not be called if no frames are downloaded
    # To assert this, we would need to patch 'app.services.ai_service.AIService.process_frames_for_pose'
    # For now, covered by DB state and task result. If direct assertion is desired, add the patch.
    mock_calculate_angles_task.apply_async.assert_not_called()
    
    # ASSERT TASK RESULT
    expected_task_return_error = "No frames downloaded/decoded."
    assert task_result is not None
    assert task_result["status"] == "failed"
    assert task_result["video_id"] == str(video_id)
    assert task_result["error"] == expected_task_return_error

    # ASSERT DATABASE STATE
    expected_db_error_message = "Failed to download/decode any frames from S3."
    session_maker = test_async_session_factory
    async with session_maker() as new_db_session:
        new_db_session.expire_all()
        refreshed_video = await new_db_session.get(Video, video_id)
        assert refreshed_video is not None
        assert refreshed_video.status == VideoStatus.POSE_DETECTION_FAILED
        assert refreshed_video.pose_data is None
        assert refreshed_video.error_message == expected_db_error_message

@pytest.mark.asyncio
@patch('app.tasks.ai_tasks.get_settings_override')
# @patch('app.tasks.ai_tasks.StorageService') # REMOVED
# @patch('app.tasks.ai_tasks.AIService') # REMOVED
# @patch('app.tasks.ai_tasks.VideoService') # REMOVED
@patch('app.services.storage_service.StorageService.download_file', new_callable=AsyncMock) # ADDED
@patch('app.services.ai_service.AIService.process_frames_for_pose', new_callable=AsyncMock) # ADDED
@patch('app.tasks.ai_tasks.calculate_angles_celery_task')
@patch('cv2.imdecode') # RESTORED - Called in this path
async def test_detect_pose_celery_task_all_frames_fail_detection(
    mock_cv2_imdecode: MagicMock, # RESTORED
    mock_calculate_angles_task: MagicMock,
    mock_ai_process_frames: AsyncMock, # UPDATED
    mock_storage_download_file: AsyncMock, # UPDATED
    mock_get_settings_override: MagicMock,
    video_for_pose_detection: Video,
    test_async_session_factory: async_sessionmaker[AsyncSession]
    # mock_video_service_class: MagicMock, # REMOVED
    # mock_storage_service_class: MagicMock, # REMOVED
    # mock_ai_service_class: MagicMock, # REMOVED
):
    video_id = video_for_pose_detection.id
    s3_keys = video_for_pose_detection.frame_s3_keys
    
    error_detail_str = "All frames failed pose detection after AI processing."
    expected_error_json_in_db = json.dumps({"error_type": "PoseDetectionError", "details": error_detail_str})

    # ARRANGE
    settings_return_value = mock_get_settings_override.return_value
    settings_return_value.AI_MIN_DETECTION_CONFIDENCE = 0.5 # Example value

    dummy_np_frame = np.array([[[1, 2, 3]]], dtype=np.uint8)
    mock_cv2_imdecode.return_value = dummy_np_frame # RESTORED

    mock_storage_download_file.return_value = b"dummy_frame_content" # Setup on the patched method

    # Simulate AIService.process_frames_for_pose returning None for all frames
    mock_ai_process_frames.return_value = [None] * len(s3_keys) # Setup on the patched method

    # Real VideoService will be used.

    # ACT
    task_result = await detect_pose_celery_task.__wrapped__(str(video_id), s3_keys)

    # ASSERT MOCK CALLS
    mock_get_settings_override.assert_called_once()
    mock_storage_download_file.assert_called()
    mock_ai_process_frames.assert_called_once() # Ensure it was called
    mock_calculate_angles_task.apply_async.assert_not_called()

    # ASSERT TASK RESULT
    assert task_result is not None
    assert task_result["status"] == "failure"
    assert task_result["video_id"] == str(video_id)
    assert task_result["message"] == error_detail_str
    assert task_result["error"] == "All frames failed AI pose detection."

    # ASSERT DATABASE STATE
    session_maker = test_async_session_factory
    async with session_maker() as new_db_session:
        new_db_session.expire_all()
        refreshed_video = await new_db_session.get(Video, video_id)
        assert refreshed_video is not None
        assert refreshed_video.status == VideoStatus.POSE_DETECTION_FAILED
        assert refreshed_video.pose_data is None
        assert refreshed_video.error_message == expected_error_json_in_db

@pytest.mark.asyncio
@patch('app.tasks.ai_tasks.get_settings_override')
# @patch('app.tasks.ai_tasks.StorageService') # Ensure this is commented or removed
# @patch('app.tasks.ai_tasks.AIService')    # Ensure this is commented or removed
# @patch('app.tasks.ai_tasks.VideoService')  # Ensure this is commented or removed
@patch('app.tasks.ai_tasks.calculate_angles_celery_task')
# @patch('cv2.imdecode') # CORRECT - Stays commented, not called in this path
async def test_detect_pose_celery_task_no_frame_paths_in_video(
    # mock_cv2_imdecode_unused: MagicMock, # CORRECT - Stays commented
    mock_calculate_angles_task: MagicMock,
    mock_get_settings_override: MagicMock,
    video_for_pose_detection: Video,
    test_async_session_factory: async_sessionmaker[AsyncSession]
):
    video_id = video_for_pose_detection.id
    # ARRANGE
    s3_keys_for_task = [] 
    
    expected_db_error_message = "No frame S3 keys"
    expected_task_return_error = "No frame S3 keys"

    # Real services will be instantiated by the task using settings_instance from get_settings_override()

    # ACT
    task_result = await detect_pose_celery_task.__wrapped__(str(video_id), s3_keys_for_task)

    # ASSERT MOCK CALLS
    mock_calculate_angles_task.apply_async.assert_not_called()
    # mock_cv2_imdecode_unused.assert_not_called() # CORRECT - Stays commented

    # ASSERT TASK RESULT
    assert task_result is not None
    assert task_result["status"] == "failed"
    assert task_result["video_id"] == str(video_id)
    assert task_result["error"] == expected_task_return_error

    # ASSERT DATABASE STATE
    session_maker = test_async_session_factory
    async with session_maker() as new_db_session:
        new_db_session.expire_all() 
        refreshed_video = await new_db_session.get(Video, video_id)
        assert refreshed_video is not None
        assert refreshed_video.status == VideoStatus.POSE_DETECTION_FAILED
        assert refreshed_video.pose_data is None
        assert refreshed_video.error_message == expected_db_error_message
        assert len(refreshed_video.frame_s3_keys) == 3 # Original from fixture

@pytest.mark.asyncio
@patch('app.tasks.ai_tasks.get_settings_override')
# @patch('app.tasks.ai_tasks.StorageService') # REMOVED
# @patch('app.tasks.ai_tasks.AIService') # REMOVED
# @patch('app.tasks.ai_tasks.VideoService') # REMOVED
@patch('app.services.storage_service.StorageService.download_file', new_callable=AsyncMock) # ADDED
@patch('app.services.ai_service.AIService.process_frames_for_pose', new_callable=AsyncMock) # ADDED
@patch('app.tasks.ai_tasks.calculate_angles_celery_task')
@patch('cv2.imdecode') # RESTORED - Called in this path
async def test_detect_pose_celery_task_successful_flow(
    mock_cv2_imdecode: MagicMock, # RESTORED
    mock_calculate_angles_task: MagicMock,
    mock_ai_process_frames: AsyncMock, # UPDATED from mock_ai_service_class
    mock_storage_download_file: AsyncMock, # UPDATED from mock_storage_service_class
    mock_get_settings_override: MagicMock,
    video_for_pose_detection: Video,
    test_async_session_factory: async_sessionmaker[AsyncSession]
    # mock_video_service_class: MagicMock, # REMOVED
):
    video_id = video_for_pose_detection.id
    s3_keys = video_for_pose_detection.frame_s3_keys
    num_frames = len(s3_keys)

    # ARRANGE
    settings_return_value = mock_get_settings_override.return_value
    settings_return_value.AI_MIN_DETECTION_CONFIDENCE = 0.6

    dummy_np_frame = np.array([[[1, 2, 3]]], dtype=np.uint8)
    mock_cv2_imdecode.return_value = dummy_np_frame # RESTORED

    mock_storage_download_file.return_value = b"dummy_frame_content" # Setup on the patched method

    mock_landmark_data = {'x': 0.5, 'y': 0.5, 'z': 0.1, 'visibility': 0.9}
    mock_raw_pose_results_per_frame_from_ai_service = [
        [mock_landmark_data] * 33, 
        None, # Simulate one frame failing detection within AI service
        [mock_landmark_data] * 33  
    ]
    # After filtering None, this is what should be saved
    expected_saved_pose_data = [
        [mock_landmark_data] * 33,
        [mock_landmark_data] * 33
    ]
    mock_ai_process_frames.return_value = mock_raw_pose_results_per_frame_from_ai_service # Setup on the patched method

    # VideoService will be real. We expect it to:
    # 1. Fetch the video using get_async (implicitly tested by task running).
    # 2. Update status to POSE_DETECTION_IN_PROGRESS via set_video_status_from_task.
    # 3. Update pose data and status to POSE_DETECTED via update_video_pose_data_and_status.
    # 4. Update status to ANGLE_CALCULATION_PENDING via set_video_status_from_task.
    # These will be verified by DB assertions.

    # ACT
    task_result = await detect_pose_celery_task.__wrapped__(str(video_id), s3_keys)

    # ASSERT MOCK CALLS
    mock_get_settings_override.assert_called_once()
    assert mock_storage_download_file.call_count == num_frames
    mock_ai_process_frames.assert_called_once_with(
        frames_data_np=ANY,
        min_pose_confidence_threshold=settings_return_value.AI_MIN_DETECTION_CONFIDENCE
    )
    
    mock_calculate_angles_task.apply_async.assert_called_once_with(args=[str(video_id)], countdown=10)

    # ASSERT TASK RESULT
    assert task_result is not None
    assert task_result["status"] == "success"
    assert task_result["video_id"] == str(video_id)
    assert task_result["pose_results_count"] == len(expected_saved_pose_data)

    # ASSERT DATABASE STATE
    session_maker = test_async_session_factory
    async with session_maker() as new_db_session:
        new_db_session.expire_all() 
        refreshed_video = await new_db_session.get(Video, video_id)
        assert refreshed_video is not None
        # The final status set by the task flow is ANGLE_CALCULATION_PENDING
        assert refreshed_video.status == VideoStatus.ANGLE_CALCULATION_PENDING
        assert refreshed_video.error_message is None
        assert refreshed_video.raw_pose_data == expected_saved_pose_data # CORRECTED ASSERTION

@pytest.mark.asyncio
@patch('app.tasks.ai_tasks.get_settings_override')
@patch('app.tasks.ai_tasks.process_form_check_task') # Mock the next task in the chain
async def test_calculate_angles_celery_task_successful_flow(
    mock_process_form_check_task: MagicMock,
    mock_get_settings_override: MagicMock,
    video_for_angle_calculation: Video, # Use the new fixture
    test_async_session_factory: async_sessionmaker[AsyncSession]
):
    video_id = video_for_angle_calculation.id

    # ARRANGE
    settings_return_value = mock_get_settings_override.return_value
    # Potentially set specific settings if AIService methods depend on them for angle calculation/smoothing
    # e.g., settings_return_value.ANGLE_SMOOTHING_WINDOW = 5

    # AIService and VideoService will be real for this integration test.

    # ACT
    # Directly invoke the task's async function part for testing
    result = await calculate_angles_celery_task.__wrapped__(
        str(video_id)
    )

    # ASSERT MOCK CALLS
    mock_get_settings_override.assert_called()
    # mock_process_form_check_task.apply_async.assert_called_once_with(args=[str(video_id)], countdown=ANY)
    # TODO: The task currently has the next step call commented out. Uncomment when ready.
    mock_process_form_check_task.apply_async.assert_not_called() # Placeholder until next task is active

    # ASSERT DATABASE STATE
    session_maker = test_async_session_factory
    async with session_maker() as new_db_session:
        refreshed_video = await new_db_session.get(Video, video_id)
        assert refreshed_video is not None
        assert refreshed_video.status == VideoStatus.ANGLES_CALCULATED
        assert refreshed_video.error_message is None
        
        assert refreshed_video.calculated_angles is not None
        assert isinstance(refreshed_video.calculated_angles, list)
        assert len(refreshed_video.calculated_angles) == len(video_for_angle_calculation.raw_pose_data) # 3 frames

        # Check structure of calculated_angles for each frame
        # Frame 0 (all landmarks) should have many angles
        if refreshed_video.calculated_angles[0] is not None:
            assert isinstance(refreshed_video.calculated_angles[0], dict)
            assert len(refreshed_video.calculated_angles[0]) > 0 # Expect some angles
            for angle_name, angle_value in refreshed_video.calculated_angles[0].items():
                assert isinstance(angle_name, str)
                assert isinstance(angle_value, float)
        else:
            # This might happen if all universal angles required landmarks that were somehow invalid
            # even if present. For this test, assume some angles should be calculated for a full landmark set.
            pytest.fail("Frame 0 should have calculated angles.")

        # Frame 1 (all landmarks None in raw_pose_data) -> angles should be None for this frame after calculation,
        # and smoothing should also result in None for this frame if it cannot interpolate.
        assert refreshed_video.calculated_angles[1] is None, \
            f"Frame 1 had None raw_pose_data, so calculated_angles should be None. Got: {refreshed_video.calculated_angles[1]}"

        # Frame 2 (some landmarks None) should have some angles, possibly fewer than frame 0
        if refreshed_video.calculated_angles[2] is not None:
            assert isinstance(refreshed_video.calculated_angles[2], dict)
            # It might be an empty dict if no universal angles could be formed from the partial landmarks.
            # Or it could have some angles.
            # For this test, we accept a dict (possibly empty if no angles could be formed).
        else:
            # This is also possible if the remaining landmarks couldn't form any universal angles.
            # The definition of UNIVERSAL_ANGLE_DEFINITIONS matters here.
            # Let's assume for now it's okay if it's None if no angles could be formed.
            pass #  Allowing None if no angles could be calculated from partial landmarks.

        # Further checks: specific angle values if we had a known input pose and expected outputs.
        # For now, structural checks are primary.

    # ASSERT TASK RESULT
    assert result["status"] == "success"
    assert result["video_id"] == str(video_id)
    assert "num_angle_frames" in result
    assert result["num_angle_frames"] == len(video_for_angle_calculation.raw_pose_data)

# Test for when video is not found
@pytest.mark.asyncio
@patch('app.tasks.ai_tasks.get_settings_override')
async def test_calculate_angles_celery_task_video_not_found(
    mock_get_settings_override: MagicMock,
    test_async_session_factory: async_sessionmaker[AsyncSession]
):
    non_existent_video_id = str(uuid7())
    # ARRANGE
    mock_get_settings_override.return_value # Basic setup

    # ACT & ASSERT
    with pytest.raises(Ignore):
        await calculate_angles_celery_task.__wrapped__(
            non_existent_video_id
        )
    # Verify no DB changes or that status remains if video somehow existed and was wrong

# Test for when raw_pose_data is missing
@pytest.mark.asyncio
@patch('app.tasks.ai_tasks.get_settings_override')
async def test_calculate_angles_celery_task_no_raw_pose_data(
    mock_get_settings_override: MagicMock,
    video_for_pose_detection: Video, # Use a video that wouldn't have raw_pose_data yet or set it to None
    test_async_session_factory: async_sessionmaker[AsyncSession]
):
    video_id = video_for_pose_detection.id
    # ARRANGE
    mock_get_settings_override.return_value
    async with test_async_session_factory() as session:
        video = await session.get(Video, video_id)
        video.raw_pose_data = None # Ensure it's None for this test
        video.status = VideoStatus.ANGLE_CALCULATION_PENDING # Set appropriate pending status
        await session.commit()
        await session.refresh(video)

    # ACT
    result = await calculate_angles_celery_task.__wrapped__(
        str(video_id)
    )

    # ASSERT
    assert result["status"] == "failed"
    assert result["error"] == "No raw_pose_data"
    async with test_async_session_factory() as session:
        refreshed_video = await session.get(Video, video_id)
        assert refreshed_video.status == VideoStatus.ANGLE_CALCULATION_FAILED
        assert refreshed_video.error_message == "No raw_pose_data available for angle calculation."
        assert refreshed_video.calculated_angles is None

@pytest.mark.asyncio
@patch('app.tasks.ai_tasks.get_settings_override')
@patch('app.tasks.ai_tasks.AIService.calculate_angles_for_pose_sequence') # Mocking the target method
@patch('app.tasks.ai_tasks.calculate_angles_celery_task.retry') # ADDED PATCH
async def test_calculate_angles_celery_task_unexpected_error_in_angle_calculation(
    mock_task_retry: MagicMock, # ADDED MOCK
    mock_calculate_angles_method: MagicMock,
    mock_get_settings_override: MagicMock,
    video_for_angle_calculation: Video, # Reusing existing fixture
    test_async_session_factory: async_sessionmaker[AsyncSession]
):
    video_id = video_for_angle_calculation.id
    simulated_error_message = "Simulated error in calculate_angles_for_pose_sequence"

    # ARRANGE
    mock_get_settings_override.return_value # Basic setup
    mock_calculate_angles_method.side_effect = RuntimeError(simulated_error_message)
    mock_task_retry.side_effect = Ignore() # ADDED BEHAVIOR

    # ACT
    # The task should catch the exception, update video status/error, and then Ignore will be raised
    with pytest.raises(Ignore): # EXPECT Ignore now
        await calculate_angles_celery_task.__wrapped__(
            str(video_id)
        )

    # ASSERT TASK RESULT (optional, but good for completeness)
    # The task result might not be directly available if Ignore is raised early.
    # Focus on DB state.
    # assert result["status"] == "failed" 
    # assert "error" in result
    # assert simulated_error_message in result["error"]


    # ASSERT DATABASE STATE
    async with test_async_session_factory() as session:
        refreshed_video = await session.get(Video, video_id)
        assert refreshed_video is not None
        assert refreshed_video.status == VideoStatus.ANGLE_CALCULATION_FAILED
        
        # Check that error_message contains the simulated error
        # The exact format might depend on how the task formats it (e.g., if it wraps it in JSON)
        # For a simple string error:
        assert simulated_error_message in refreshed_video.error_message 
        # If it's JSON:
        # error_data = json.loads(refreshed_video.error_message)
        # assert error_data["details"] == simulated_error_message
        # assert error_data["error_type"] == "RuntimeError"

        assert refreshed_video.calculated_angles is None

@pytest.mark.asyncio
@patch('app.tasks.ai_tasks.get_settings_override')
@patch('app.tasks.ai_tasks.AIService.calculate_angles_for_pose_sequence') # Mock raw angle calculation to return something valid
@patch('app.tasks.ai_tasks.AIService.smooth_angle_trajectories') # Mock smoothing to raise error
@patch('app.tasks.ai_tasks.calculate_angles_celery_task.retry') # ADDED PATCH
async def test_calculate_angles_celery_task_unexpected_error_in_smoothing(
    mock_task_retry: MagicMock, # ADDED MOCK
    mock_smooth_angles_method: MagicMock,
    mock_calculate_angles_method: MagicMock,
    mock_get_settings_override: MagicMock,
    video_for_angle_calculation: Video, 
    test_async_session_factory: async_sessionmaker[AsyncSession]
):
    video_id = video_for_angle_calculation.id
    simulated_error_message = "Simulated error in smooth_angle_trajectories"

    # ARRANGE
    mock_get_settings_override.return_value
    # Simulate that raw angle calculation was successful
    # The exact structure of this return value should match what smooth_angle_trajectories expects
    # Based on `smooth_angle_trajectories` signature: List[Optional[Dict[str, float]]]
    # Let's assume video_for_angle_calculation.raw_pose_data has 3 frames.
    mock_calculate_angles_method.return_value = [
        {"left_knee": 90.0}, 
        None, 
        {"left_knee": 100.0}
    ] 
    mock_smooth_angles_method.side_effect = RuntimeError(simulated_error_message)
    mock_task_retry.side_effect = Ignore() # ADDED BEHAVIOR

    # ACT
    with pytest.raises(Ignore): # EXPECT Ignore now
        await calculate_angles_celery_task.__wrapped__(
            str(video_id)
        )

    # ASSERT TASK RESULT
    # The task result might not be directly available if Ignore is raised early.
    # Focus on DB state.
    # assert result["status"] == "failed"
    # assert "error" in result
    # assert simulated_error_message in result["error"]

    # ASSERT DATABASE STATE
    async with test_async_session_factory() as session:
        refreshed_video = await session.get(Video, video_id)
        assert refreshed_video is not None
        assert refreshed_video.status == VideoStatus.ANGLE_CALCULATION_FAILED
        assert refreshed_video.calculated_angles is None # No angles should be stored
        assert simulated_error_message in refreshed_video.error_message # THIS LINE WAS MISSING

@pytest.mark.asyncio
@patch('app.tasks.ai_tasks.get_settings_override')
@patch('app.tasks.ai_tasks.process_form_check_task') # Mock the next task in the chain
async def test_calculate_angles_celery_task_with_empty_raw_pose_data(
    mock_process_form_check_task: MagicMock,
    mock_get_settings_override: MagicMock,
    video_for_angle_calculation: Video, # Reusing, but will modify raw_pose_data
    test_async_session_factory: async_sessionmaker[AsyncSession]
):
    video_id = video_for_angle_calculation.id

    # ARRANGE
    mock_get_settings_override.return_value
    # Modify the video to have empty raw_pose_data
    async with test_async_session_factory() as session:
        video = await session.get(Video, video_id)
        video.raw_pose_data = [] # Set to empty list
        video.status = VideoStatus.ANGLE_CALCULATION_PENDING # Ensure correct starting status
        await session.commit()
        await session.refresh(video)

    # AIService and VideoService will be real for this integration test.
    # calculate_angles_for_pose_sequence should return []
    # smooth_angle_trajectories should also return [] if input is []

    # ACT
    result = await calculate_angles_celery_task.__wrapped__(
        str(video_id)
    )

    # ASSERT MOCK CALLS
    mock_get_settings_override.assert_called()
    # Depending on if the next task is called with empty results, adjust this:
    # mock_process_form_check_task.apply_async.assert_called_once_with(args=[str(video_id)], countdown=ANY)
    mock_process_form_check_task.apply_async.assert_not_called() # Assuming it won't be called for empty angles

    # ASSERT DATABASE STATE
    async with test_async_session_factory() as session:
        refreshed_video = await session.get(Video, video_id)
        assert refreshed_video is not None
        assert refreshed_video.status == VideoStatus.ANGLES_CALCULATED
        assert refreshed_video.error_message is None
        assert refreshed_video.calculated_angles == [] # Expect empty list

    # ASSERT TASK RESULT
    assert result["status"] == "success"
    assert result["video_id"] == str(video_id)
    assert result["num_angle_frames"] == 0 # Expect 0 frames processed

@patch('app.tasks.ai_tasks.get_settings_override')
@patch('app.tasks.ai_tasks.AIService.calculate_angles_for_pose_sequence') # ADDED
@patch('app.tasks.ai_tasks.AIService.smooth_angle_trajectories') # ADDED
@patch('app.tasks.ai_tasks.calculate_angles_celery_task.retry') # ADDED to mock self.retry
@pytest.mark.asyncio
async def test_calculate_angles_celery_task_angle_calculation_general_exception(
    mock_task_retry: MagicMock, # ADDED
    mock_smooth_angles: MagicMock, # RENAMED & ADDED
    mock_calculate_angles: MagicMock, # RENAMED & ADDED
    mock_get_settings_override: MagicMock,
    video_for_angle_calculation: Video,
    test_async_session_factory: async_sessionmaker[AsyncSession]
):
    video_id = video_for_angle_calculation.id
    simulated_error_message = "Simulated general exception in angle calculation"
    expected_error_details_json_str = json.dumps({"error_type": "Exception", "details": simulated_error_message}) # Updated error type to general Exception for this test

    # ARRANGE
    settings = mock_get_settings_override.return_value
    # No specific settings needed for this test path usually, but good to have the mock

    # Configure the patched AIService.calculate_angles_for_pose_sequence to raise an exception
    mock_calculate_angles.side_effect = Exception(simulated_error_message)
    # smooth_angle_trajectories might not be called if calculate_angles_for_pose_sequence fails first,
    # but it's good practice to have it if it's part of the try block that might be reached.
    # Let's assume it's not called for this specific failure scenario, or set a benign return if it were.
    mock_smooth_angles.return_value = [] # Or another suitable benign return if it were to be called

    mock_task_retry.side_effect = Ignore() # Task should call self.retry, which we mock to raise Ignore

    # ACT & ASSERT
    # The task should catch the Exception from calculate_angles_for_pose_sequence,
    # log it, update DB, and then call self.retry(exc=e), which raises Ignore.
    with pytest.raises(Ignore):
        await calculate_angles_celery_task.__wrapped__(
            str(video_id)
        )

    # ASSERT MOCK CALLS
    mock_get_settings_override.assert_called()
    mock_calculate_angles.assert_called_once() 
    # mock_smooth_angles.assert_not_called() # Or called depending on exact flow if calculate_angles fails
    mock_task_retry.assert_called_once() # self.retry should be called

    # ASSERT DATABASE STATE
    session_maker = test_async_session_factory
    async with session_maker() as new_db_session:
        refreshed_video = await new_db_session.get(Video, video_id)
        assert refreshed_video is not None
        assert refreshed_video.status == VideoStatus.ANGLE_CALCULATION_FAILED
        assert refreshed_video.calculated_angles is None
        # The error message in DB should now reflect the type from the caught exception
        # which is a generic Exception in this case.
        assert refreshed_video.error_message == expected_error_details_json_str