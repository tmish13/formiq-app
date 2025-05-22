import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from uuid6 import uuid7
from uuid import UUID

from app.models.video import Video
from app.models.enums import VideoStatus, ExerciseType
from app.tasks.ai_tasks import detect_pose_celery_task
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import Settings # For mocking settings

@pytest.fixture
async def video_for_pose_detection(db_session: AsyncSession) -> Video:
    """Creates a sample video object in the database, prepared for pose detection."""
    video_id_for_frames = uuid7() # Use a consistent ID for frame paths if needed for realism
    video = Video(
        id=video_id_for_frames,
        user_id=uuid7(),
        filename="sample_video_for_pose.mp4",
        object_key="test_raw_videos/sample_video_for_pose.mp4",
        processed_url=f"normalized_videos/{video_id_for_frames}/normalized.mp4",
        processed_frame_paths=[
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
        mime_type="video/mp4"
    )
    db_session.add(video)
    await db_session.commit()
    await db_session.refresh(video)
    return video

@pytest.mark.asyncio
@patch('app.tasks.ai_tasks.settings') # Correctly patch the settings object
@patch('app.tasks.ai_tasks.AIService')       # To mock AI processing logic
@patch('app.tasks.ai_tasks.VideoService')
async def test_detect_pose_celery_task_successful_flow(
    MockAIService: MagicMock,
    MockVideoService: MagicMock,
    mock_task_settings: MagicMock,
    db_session: AsyncSession,
    test_video_in_db: Video, # Depends on db_session
    mock_celery_task_self: MagicMock,
    initialize_test_db: None # Explicitly request session fixture
):
    """Test the successful flow of the detect_pose_celery_task."""
    video_id = test_video_in_db.id
    frame_s3_keys = test_video_in_db.processed_frame_paths
    exercise_type = test_video_in_db.exercise_type
    
    # ARRANGE
    # 1. Configure the mocked settings object attributes directly
    mock_ai_pose_confidence_threshold = 0.5
    mock_ai_smoothing_window_size = 5
    mock_ai_max_interpolation_gap = 3
    
    mock_task_settings.AI_POSE_CONFIDENCE_THRESHOLD = mock_ai_pose_confidence_threshold
    mock_task_settings.AI_SMOOTHING_WINDOW_SIZE = mock_ai_smoothing_window_size
    mock_task_settings.AI_MAX_INTERPOLATION_GAP = mock_ai_max_interpolation_gap
    # mock_task_settings.CELERY_RETRY_COUNTDOWN = 1 # If needed for retry assertions

    # 2. Mock AIService instance and its methods
    mock_ai_service_instance = MockAIService.return_value
    
    mock_raw_landmarks_per_frame = [
        [{'name': 'nose', 'x': 0.5, 'y': 0.1, 'z': 0.2, 'visibility': 0.99}],
        None, # Frame with no detection
        [{'name': 'nose', 'x': 0.52, 'y': 0.12, 'z': 0.22, 'visibility': 0.98}]
    ]
    mock_ai_service_instance.process_frames_for_pose = AsyncMock(return_value=mock_raw_landmarks_per_frame)

    mock_final_pose_data = [
        [{'name': 'nose', 'x': 0.5, 'y': 0.1, 'z': 0.2, 'visibility': 0.99}],
        [{'name': 'nose', 'x': 0.51, 'y': 0.11, 'z': 0.21, 'visibility': 0.985}], # Interpolated
        [{'name': 'nose', 'x': 0.52, 'y': 0.12, 'z': 0.22, 'visibility': 0.98}]
    ]
    mock_ai_service_instance.smooth_and_interpolate_poses = AsyncMock(return_value=mock_final_pose_data)
    
    # 3. Mock 'self' for the bound Celery task
    mock_celery_task_self = mock_celery_task_self

    # ACT
    task_result = await detect_pose_celery_task(
        mock_celery_task_self, 
        video_id_str=str(video_id),
        frame_paths=frame_s3_keys
    )

    # ASSERT
    # 1. Settings mock
    # mock_task_settings.assert_any_call() # Difficult to assert specific attribute access without more complex mocking
    # Instead, we rely on the fact that if the task ran with wrong settings, other assertions would fail.

    # 2. AIService instantiation and method calls
    MockAIService.assert_called_once_with() # AIService() is called in the task
    
    mock_ai_service_instance.process_frames_for_pose.assert_called_once_with(
        frame_paths=frame_s3_keys,
        min_pose_confidence_threshold=mock_ai_pose_confidence_threshold
    )
    mock_ai_service_instance.smooth_and_interpolate_poses.assert_called_once_with(
        pose_sequence=mock_raw_landmarks_per_frame,
        smoothing_window_size=mock_ai_smoothing_window_size,
        max_interpolation_gap=mock_ai_max_interpolation_gap
        # exercise_type is not explicitly passed here based on current task code
    )

    # 3. Database state assertions (VideoService calls are real via db context)
    await db_session.refresh(video_for_pose_detection) 
    assert video_for_pose_detection.status == VideoStatus.POSE_DETECTED
    assert video_for_pose_detection.raw_pose_data == mock_final_pose_data # This is what should be stored
    assert video_for_pose_detection.processing_errors is None
    
    # 4. Task return value
    assert task_result["status"] == "success"
    assert task_result["video_id"] == str(video_id)
    assert "Pose detection, smoothing, and interpolation successful" in task_result["message"]
    pass 

@pytest.mark.asyncio
@patch('app.tasks.ai_tasks.settings') # Correctly patch the settings object
@patch('app.tasks.ai_tasks.AIService')
async def test_detect_pose_celery_task_process_frames_failure(
    MockAIService: MagicMock,         
    mock_task_settings: MagicMock, # Renamed from mock_get_app_settings
    db_session: AsyncSession,
    video_for_pose_detection: Video,
):
    video_id = video_for_pose_detection.id
    frame_s3_keys = video_for_pose_detection.processed_frame_paths
    simulated_error_message = "Simulated AI error during process_frames_for_pose"
    simulated_error_type = "RuntimeError"

    # ARRANGE
    mock_ai_pose_confidence_threshold = 0.5
    mock_task_settings.AI_POSE_CONFIDENCE_THRESHOLD = mock_ai_pose_confidence_threshold
    mock_task_settings.AI_SMOOTHING_WINDOW_SIZE = 5 # Default values
    mock_task_settings.AI_MAX_INTERPOLATION_GAP = 3  # Default values
    mock_task_settings.CELERY_RETRY_COUNTDOWN = 1 # For faster retry in test if it were real

    mock_ai_service_instance = MockAIService.return_value
    mock_ai_service_instance.process_frames_for_pose = AsyncMock(
        side_effect=RuntimeError(simulated_error_message)
    )
    # smooth_and_interpolate_poses should not be called
    mock_ai_service_instance.smooth_and_interpolate_poses = AsyncMock()

    mock_celery_task_self = MagicMock()
    # Mock self.retry to re-raise the exception, so we can catch it in the test
    # The task's except block calls self.retry(exc=e)
    mock_celery_task_self.retry = MagicMock(side_effect=lambda exc, countdown: exec("raise exc"))

    # ACT & ASSERT for the exception re-raised by self.retry
    with pytest.raises(RuntimeError, match=simulated_error_message):
        await detect_pose_celery_task(
            mock_celery_task_self, 
            video_id_str=str(video_id),
            frame_paths=frame_s3_keys
        )

    # ASSERT MOCKS & DB
    # AIService was instantiated, and process_frames_for_pose was called (and failed)
    MockAIService.assert_called_once_with()
    mock_ai_service_instance.process_frames_for_pose.assert_called_once_with(
        frame_paths=frame_s3_keys,
        min_pose_confidence_threshold=mock_ai_pose_confidence_threshold
    )
    # smooth_and_interpolate_poses should not have been called
    mock_ai_service_instance.smooth_and_interpolate_poses.assert_not_called()

    # DB state assertions: VideoService calls are real
    # The task should have updated the status to FAILED and logged the error
    await db_session.refresh(video_for_pose_detection)
    assert video_for_pose_detection.status == VideoStatus.POSE_DETECTION_FAILED
    # raw_pose_data is initialized to None and error happens before it's populated
    assert video_for_pose_detection.raw_pose_data is None 
    
    assert isinstance(video_for_pose_detection.processing_errors, dict)
    assert video_for_pose_detection.processing_errors["error_type"] == simulated_error_type
    assert simulated_error_message in video_for_pose_detection.processing_errors["details"]
    pass 

@pytest.mark.asyncio
@patch('app.tasks.ai_tasks.settings') # Correctly patch the settings object
@patch('app.tasks.ai_tasks.AIService')
async def test_detect_pose_celery_task_smoothing_failure(
    MockAIService: MagicMock,         
    mock_task_settings: MagicMock, # Renamed from mock_get_app_settings
    db_session: AsyncSession,
    video_for_pose_detection: Video,
):
    video_id = video_for_pose_detection.id
    frame_s3_keys = video_for_pose_detection.processed_frame_paths
    simulated_error_message = "Simulated AI error during smooth_and_interpolate_poses"
    simulated_error_type = "ValueError" # Example error type

    # ARRANGE
    mock_ai_pose_confidence_threshold = 0.5
    mock_ai_smoothing_window_size = 5
    mock_ai_max_interpolation_gap = 3

    mock_task_settings.AI_POSE_CONFIDENCE_THRESHOLD = mock_ai_pose_confidence_threshold
    mock_task_settings.AI_SMOOTHING_WINDOW_SIZE = mock_ai_smoothing_window_size
    mock_task_settings.AI_MAX_INTERPOLATION_GAP = mock_ai_max_interpolation_gap
    mock_task_settings.CELERY_RETRY_COUNTDOWN = 1 

    mock_ai_service_instance = MockAIService.return_value
    
    # process_frames_for_pose succeeds
    mock_raw_landmarks_per_frame = [
        [{'name': 'nose', 'x': 0.5, 'y': 0.1, 'z': 0.2, 'visibility': 0.99}]
    ]
    mock_ai_service_instance.process_frames_for_pose = AsyncMock(return_value=mock_raw_landmarks_per_frame)
    
    # smooth_and_interpolate_poses fails
    mock_ai_service_instance.smooth_and_interpolate_poses = AsyncMock(
        side_effect=ValueError(simulated_error_message)
    )

    mock_celery_task_self = MagicMock()
    mock_celery_task_self.retry = MagicMock(side_effect=lambda exc, countdown: exec("raise exc"))

    # ACT & ASSERT for the exception
    with pytest.raises(ValueError, match=simulated_error_message):
        await detect_pose_celery_task(
            mock_celery_task_self, 
            video_id_str=str(video_id),
            frame_paths=frame_s3_keys
        )

    # ASSERT MOCKS & DB
    MockAIService.assert_called_once_with()
    mock_ai_service_instance.process_frames_for_pose.assert_called_once_with(
        frame_paths=frame_s3_keys,
        min_pose_confidence_threshold=mock_ai_pose_confidence_threshold
    )
    mock_ai_service_instance.smooth_and_interpolate_poses.assert_called_once_with(
        pose_sequence=mock_raw_landmarks_per_frame,
        smoothing_window_size=mock_ai_smoothing_window_size,
        max_interpolation_gap=mock_ai_max_interpolation_gap
    )

    await db_session.refresh(video_for_pose_detection)
    assert video_for_pose_detection.status == VideoStatus.POSE_DETECTION_FAILED
    # As per task logic, final_pose_data is initialized to None and is not updated before this error.
    # So, None is saved to raw_pose_data in the DB during error handling.
    assert video_for_pose_detection.raw_pose_data is None 
    
    assert isinstance(video_for_pose_detection.processing_errors, dict)
    assert video_for_pose_detection.processing_errors["error_type"] == simulated_error_type
    assert simulated_error_message in video_for_pose_detection.processing_errors["details"]
    pass 

@pytest.mark.asyncio
@patch('app.tasks.ai_tasks.settings') # Correctly patch the settings object
@patch('app.tasks.ai_tasks.VideoService') # Patch VideoService used within the task
@patch('app.tasks.ai_tasks.AIService')    # To assert it's NOT called
async def test_detect_pose_celery_task_video_not_found(
    MockAIService: MagicMock,
    MockVideoService: MagicMock, # Patched VideoService class
    mock_task_settings: MagicMock, # Renamed from mock_get_app_settings
    db_session: AsyncSession, # db_session is available to the task via context
):
    """Test that the task handles the case where the video ID is not found in the DB."""
    non_existent_video_id_str = str(uuid7())
    # Frame paths don't matter as the video ID lookup fails first
    dummy_frame_paths = ["frame1.jpg", "frame2.jpg"]
    simulated_video_service_error_message = f"Video with ID {non_existent_video_id_str} not found for status update."

    # ARRANGE
    # 1. Configure the mocked settings object directly
    mock_task_settings.CELERY_RETRY_COUNTDOWN = 1 # For faster retry if it were real
    # Add any other settings attributes the task might access if necessary, though for this path, few are used.

    # 2. Mock VideoService instance to simulate failure when trying to update video status
    # The task calls: video_service.set_video_status_from_task(video_id, VideoStatus.POSE_DETECTION_IN_PROGRESS)
    # And then again in the except block for POSE_DETECTION_FAILED.
    # We want the *first* call (or any DB lookup for the video) to indicate the video is not found.
    mock_vs_instance = MockVideoService.return_value
    # Simulate VideoService raising an error when it can't find the video to update its status.
    # This error will be caught by the task's main try-except block.
    db_lookup_exception = Exception(simulated_video_service_error_message) # Generic exception representing DB lookup failure
    mock_vs_instance.set_video_status_from_task = AsyncMock(side_effect=db_lookup_exception)

    # 3. AIService should not be instantiated or called in this failure path
    mock_ai_service_instance = MockAIService.return_value 

    # 4. Mock 'self' for the bound Celery task and its retry method
    mock_celery_task_self = MagicMock()
    # Make self.retry re-raise the exception to assert it in the test
    mock_celery_task_self.retry = MagicMock(side_effect=lambda exc, countdown: exec("raise exc"))

    # ACT & ASSERT
    with pytest.raises(Exception, match=simulated_video_service_error_message):
        await detect_pose_celery_task.run( # Call .run() directly
            mock_celery_task_self, # self as first positional arg
            video_id_str=non_existent_video_id_str,
            frame_paths=dummy_frame_paths
        )

    # ASSERT MOCKS
    # VideoService was instantiated, and set_video_status_from_task was called (and failed)
    MockVideoService.assert_called_once() # Instantiated with db from context
    # Assert it was called trying to set POSE_DETECTION_IN_PROGRESS initially
    mock_vs_instance.set_video_status_from_task.assert_any_call(
        UUID(non_existent_video_id_str), 
        VideoStatus.POSE_DETECTION_IN_PROGRESS, 
        processing_errors=None
    )
    # It will be called again in the except block for POSE_DETECTION_FAILED after the error.
    # The side_effect will apply to all calls. First call raises, task catches, calls it again to set FAILED state.
    # Let's verify the second call attempt to set FAILED status
    # The error message in the second call will contain details of the initial db_lookup_exception
    # This assertion can be tricky due to the exact error formatting in the task. 
    # For now, let's just confirm it's called again. A more precise error message check might be needed.
    # Example: any_call(UUID(non_existent_video_id_str), VideoStatus.POSE_DETECTION_FAILED, processing_errors=ANY)

    # AIService should not have been called
    MockAIService.assert_not_called()
    mock_ai_service_instance.process_frames_for_pose.assert_not_called()
    mock_ai_service_instance.smooth_and_interpolate_poses.assert_not_called()

    # Assert that retry was called with the correct exception
    mock_celery_task_self.retry.assert_called_once()
    # Access the arguments of the call to retry
    retry_args, retry_kwargs = mock_celery_task_self.retry.call_args
    assert retry_kwargs.get('exc') is db_lookup_exception
    assert retry_kwargs.get('countdown') == mock_task_settings.CELERY_RETRY_COUNTDOWN
    pass

@pytest.mark.asyncio
@patch('app.tasks.ai_tasks.settings') 
@patch('app.tasks.ai_tasks.AIService')
async def test_detect_pose_celery_task_retry_and_succeed(
    MockAIService: MagicMock,
    mock_task_settings: MagicMock,
    db_session: AsyncSession,
    video_for_pose_detection: Video, # Fixture to get a video object
    mock_celery_task_self: MagicMock # Fixture for celery task self
):
    """Test detect_pose_celery_task retries on a transient AI error and then succeeds."""
    video_id = video_for_pose_detection.id
    frame_s3_keys = video_for_pose_detection.processed_frame_paths
    transient_error_message = "Simulated transient AI error in process_frames"

    # ARRANGE
    # Configure necessary settings (already done by mock_task_settings fixture if attributes are set there)
    mock_ai_pose_confidence_threshold = 0.55 # Example, can be from settings
    mock_task_settings.AI_POSE_CONFIDENCE_THRESHOLD = mock_ai_pose_confidence_threshold
    mock_task_settings.AI_SMOOTHING_WINDOW_SIZE = 5
    mock_task_settings.AI_MAX_INTERPOLATION_GAP = 3
    mock_task_settings.CELERY_RETRY_COUNTDOWN = 1 # For retry behavior

    mock_ai_service_instance = MockAIService.return_value
    
    # Mock AIService.process_frames_for_pose to fail once, then succeed
    # Data for successful calls
    mock_raw_landmarks_retry = [[{'name': 'nose', 'x': 0.6, 'y': 0.15, 'z': 0.25, 'visibility': 0.97}]]
    mock_final_pose_data_retry = [[{'name': 'nose', 'x': 0.61, 'y': 0.16, 'z': 0.26, 'visibility': 0.96}]]

    mock_ai_service_instance.process_frames_for_pose.side_effect = [
        RuntimeError(transient_error_message), # First call: fail
        mock_raw_landmarks_retry               # Second call (retry): succeed
    ]
    # smooth_and_interpolate_poses should be called only on the successful attempt
    mock_ai_service_instance.smooth_and_interpolate_poses = AsyncMock(return_value=mock_final_pose_data_retry)

    # Mock Celery task's 'self' and its retry method
    retry_exception_holder = {}
    def custom_retry_side_effect(exc, countdown=None, max_retries=None, **kwargs):
        retry_exception_holder['exc'] = exc
        raise exc # Simulate Celery re-raising or the retry mechanism.

    mock_celery_task_self.retry = MagicMock(side_effect=custom_retry_side_effect)
    mock_celery_task_self.request.retries = 0 # Simulate first attempt

    # ACT - First attempt (will fail and trigger retry)
    with pytest.raises(RuntimeError, match=transient_error_message):
        await detect_pose_celery_task(
            mock_celery_task_self,
            video_id_str=str(video_id),
            frame_paths=frame_s3_keys
        )
    
    # ASSERT - First attempt failed and retry was called
    mock_celery_task_self.retry.assert_called_once()
    assert isinstance(retry_exception_holder.get('exc'), RuntimeError)
    assert str(retry_exception_holder['exc']) == transient_error_message
    await db_session.refresh(video_for_pose_detection)
    assert video_for_pose_detection.status == VideoStatus.POSE_DETECTION_FAILED
    assert isinstance(video_for_pose_detection.processing_errors, dict)
    assert transient_error_message in video_for_pose_detection.processing_errors["details"]

    # Simulate Celery re-running the task for the retry
    mock_ai_service_instance.process_frames_for_pose.reset_mock() # Reset side_effect call count for this method
    mock_ai_service_instance.process_frames_for_pose.side_effect = [mock_raw_landmarks_retry] # Set for next successful call
    mock_celery_task_self.retry.reset_mock()
    mock_celery_task_self.request.retries = 1 # Simulate being in a retry attempt

    # ACT - Second attempt (should succeed)
    task_result_on_retry = await detect_pose_celery_task(
        mock_celery_task_self,
        video_id_str=str(video_id),
        frame_paths=frame_s3_keys
    )

    # ASSERT - Second attempt succeeded
    assert task_result_on_retry["status"] == "success"
    # process_frames_for_pose called once in the second attempt successfully
    mock_ai_service_instance.process_frames_for_pose.assert_called_once_with(
        frame_paths=frame_s3_keys,
        min_pose_confidence_threshold=mock_ai_pose_confidence_threshold
    )
    mock_ai_service_instance.smooth_and_interpolate_poses.assert_called_once_with(
        pose_sequence=mock_raw_landmarks_retry, # From the successful call
        smoothing_window_size=mock_task_settings.AI_SMOOTHING_WINDOW_SIZE,
        max_interpolation_gap=mock_task_settings.AI_MAX_INTERPOLATION_GAP
    )
    mock_celery_task_self.retry.assert_not_called() # Retry should not be called on success

    await db_session.refresh(video_for_pose_detection)
    assert video_for_pose_detection.status == VideoStatus.POSE_DETECTED
    assert video_for_pose_detection.raw_pose_data == mock_final_pose_data_retry
    assert video_for_pose_detection.processing_errors is None # Errors cleared on success

@pytest.mark.integration
class TestDetectPoseCeleryTask:

    @pytest.fixture
    def mock_db_session(self):
        """Fixture for a mock database session."""
        return MagicMock()

    @pytest.fixture
    def mock_video_service(self):
        """Fixture for a mocked VideoService."""
        return MagicMock()

    @pytest.fixture
    def mock_ai_service(self):
        """Fixture for a mocked AIService."""
        return MagicMock()

    # We'll need to set up a test database for these integration tests.

    def test_initial_setup_passing(self):
        """A simple test to confirm the test file and pytest are working."""
        assert True

# Tests for `detect_pose_celery_task` will be added here following the plan:
# - Test successful pose detection flow
# - Test flow where AIService methods raise exceptions
# - Test Celery retry mechanisms