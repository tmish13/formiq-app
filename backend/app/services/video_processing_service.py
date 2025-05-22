"""Video processing service for exercise form analysis."""
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import cv2
from datetime import datetime
import tempfile
import os
import subprocess # Added for FFmpeg integration
import asyncio # Add asyncio import

from app.core.monitoring import track_model_inference
from app.models.enums import ExerciseType
from app.core.config import Settings
from app.core.exceptions import VideoProcessingError, VideoValidationError, VideoReadError

class VideoProcessingService:
    """Service for processing exercise videos."""
    
    def __init__(self, app_settings: Settings):
        """Initialize video processing service."""
        self.settings = app_settings
        self.frame_rate = self.settings.VIDEO_FRAME_RATE # This will be the target_fps for FFmpeg
        self.max_frames = self.settings.MAX_VIDEO_FRAMES
        # Use new settings for target_size
        self.target_size = (
            self.settings.AI_TARGET_FRAME_WIDTH, 
            self.settings.AI_TARGET_FRAME_HEIGHT
        )
        
        # Exercise-specific frame selection configs
        self.frame_selection_configs = {
            ExerciseType.SQUAT: {
                "key_frames": ["start", "descent", "bottom", "ascent", "end"],
                "frame_count": 5
            },
            ExerciseType.PUSH_UP: {
                "key_frames": ["start", "descent", "bottom", "ascent", "end"],
                "frame_count": 5
            },
            ExerciseType.PLANK: {
                "key_frames": ["setup", "hold", "end"],
                "frame_count": 3
            }
        }
    
    async def process_video(
        self,
        video_data: bytes,
        exercise_type: ExerciseType,
        save_processed_frames: bool = False,
        base_output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process video data for exercise analysis.
        If save_processed_frames is True and base_output_path is provided, 
        saves frames there and returns paths.
        Otherwise, returns frames in memory (for non-Celery use or simple pipelines).
        
        Args:
            video_data: Raw video bytes
            exercise_type: Type of exercise being performed
            save_processed_frames: Whether to save processed frames to disk
            base_output_path: Base path for saving processed frames
            
        Returns:
            Dictionary containing processed frames and metadata
        
        Raises:
            VideoValidationError: If the video fails validation checks.
            VideoReadError: If the video file cannot be opened or read.
            VideoProcessingError: For other video processing failures.
        """
        start_time = datetime.now().timestamp()
        processed_frame_paths: List[str] = []
        output_frames_data: List[np.ndarray] = []

        if not video_data:
            # Added check for empty video data
            track_model_inference(
                exercise_type=exercise_type.value,
                frame_count=0,
                has_errors=True,
                model_type="video_processing",
                duration=datetime.now().timestamp() - start_time,
                confidence=0.0,
                error_type="EmptyVideoData"
            )
            raise VideoReadError("Input video data is empty.")

        with tempfile.TemporaryDirectory() as processing_temp_dir:
            temp_video_path = os.path.join(processing_temp_dir, "input_video.mp4")
            normalized_video_path = os.path.join(processing_temp_dir, "normalized_video.mp4") # Path for FFmpeg output

            try:
                with open(temp_video_path, 'wb') as temp_file:
                    temp_file.write(video_data)
            except IOError as e:
                # Added specific error handling for IOError during temp file write
                track_model_inference(
                    exercise_type=exercise_type.value,
                    frame_count=0,
                    has_errors=True,
                    model_type="video_processing",
                    duration=datetime.now().timestamp() - start_time,
                    confidence=0.0,
                    error_type=f"TempFileIOError: {type(e).__name__}"
                )
                raise VideoProcessingError(f"Could not write temporary video file: {e}")

            # Step 1: Normalize video using FFmpeg (if frame_rate is set, e.g. > 0)
            # The _normalize_video_with_ffmpeg method is synchronous, 
            # but called within an async method. Consider running in a thread pool if it's blocking.
            # For now, direct call assuming it's acceptably fast or will be made async later.
            if self.frame_rate and self.frame_rate > 0:
                try:
                    # Wrap synchronous subprocess call in asyncio.to_thread
                    ffmpeg_success = await asyncio.to_thread(
                        self._normalize_video_with_ffmpeg,
                        temp_video_path, 
                        normalized_video_path, 
                        target_fps=self.frame_rate
                    )
                    if not ffmpeg_success:
                        # FFmpeg failure is critical, treat as a processing error.
                        # _normalize_video_with_ffmpeg should log specifics.
                        raise VideoProcessingError(f"FFmpeg normalization failed for {temp_video_path}")
                    video_to_validate_path = normalized_video_path # Use normalized video for subsequent steps
                except Exception as e: # Catch any exception from FFmpeg processing
                    track_model_inference(
                        exercise_type=exercise_type.value,
                        frame_count=0,
                        has_errors=True,
                        model_type="video_processing_ffmpeg",
                        duration=datetime.now().timestamp() - start_time,
                        confidence=0.0,
                        error_type=f"FFmpegError: {type(e).__name__} - {str(e)}"
                    )
                    raise VideoProcessingError(f"Error during FFmpeg normalization: {e}")
            else:
                # If no target frame_rate for normalization, use the original video
                video_to_validate_path = temp_video_path

            # Integrate _validate_video call using the (potentially) normalized video
            # Wrap synchronous call in asyncio.to_thread
            is_valid, validation_message, video_metadata = await asyncio.to_thread(
                self._validate_video, 
                video_to_validate_path
            )
            if not is_valid:
                track_model_inference(
                    exercise_type=exercise_type.value,
                    frame_count=0,
                    has_errors=True,
                    model_type="video_processing_validation", # Differentiate validation error
                    duration=datetime.now().timestamp() - start_time,
                    confidence=0.0,
                    error_type=f"VideoValidationError: {validation_message}"
                )
                # Ensure validation_message is not None before raising
                error_msg = validation_message if validation_message else "Video validation failed due to an unspecified reason."
                raise VideoValidationError(error_msg)

            try:
                # Note: _extract_frames will now operate on video_to_validate_path,
                # which is the FFmpeg-processed file if normalization was applied.
                frames = await asyncio.to_thread(self._extract_frames_sync, video_to_validate_path, exercise_type) # Call synchronous version with to_thread
                
                if not frames:
                    # Added check if no frames were extracted
                    track_model_inference(
                        exercise_type=exercise_type.value,
                        frame_count=0,
                        has_errors=True,
                        model_type="video_processing",
                        duration=datetime.now().timestamp() - start_time,
                        confidence=0.0,
                        error_type="NoFramesExtracted"
                    )
                    raise VideoProcessingError("No frames could be extracted from the video.")

                # Wrap synchronous call in asyncio.to_thread
                key_frames = await asyncio.to_thread(
                    self._select_key_frames, 
                    frames, 
                    exercise_type
                )
                if not key_frames:
                     # Added check if no key frames were selected
                    track_model_inference(
                        exercise_type=exercise_type.value,
                        frame_count=len(frames), # original frames extracted
                        has_errors=True,
                        model_type="video_processing",
                        duration=datetime.now().timestamp() - start_time,
                        confidence=0.0,
                        error_type="NoKeyFramesSelected"
                    )
                    raise VideoProcessingError("No key frames could be selected from the extracted frames.")

                # Wrap synchronous call in asyncio.to_thread
                processed_frames_in_memory = await asyncio.to_thread(
                    self._preprocess_frames, 
                    key_frames
                )

                if save_processed_frames and base_output_path:
                    if not os.path.exists(base_output_path):
                        # This os.makedirs is synchronous, but usually very fast.
                        # If base_output_path could be on a slow network filesystem, consider to_thread for it too.
                        os.makedirs(base_output_path, exist_ok=True)
                    
                    # Wrap frame saving logic in asyncio.to_thread
                    # Define a helper or use a lambda if simple enough, or just loop with to_thread per imwrite.
                    # For simplicity here, let's wrap each imwrite if the list isn't excessively large.
                    # A more optimized way for many frames would be a dedicated sync helper for the loop.
                    
                    # Let's create a small helper function for saving frames to make the to_thread call cleaner
                    def _save_frames_sync(frames_to_save: List[np.ndarray], path: str) -> List[str]:
                        saved_paths = []
                        for i, frame_array in enumerate(frames_to_save):
                            img_to_save = (frame_array * 255).astype(np.uint8)
                            img_to_save_bgr = cv2.cvtColor(img_to_save, cv2.COLOR_RGB2BGR)
                            frame_filename = f"frame_{i:04d}.png"
                            frame_file_path = os.path.join(path, frame_filename)
                            cv2.imwrite(frame_file_path, img_to_save_bgr) # This is blocking
                            saved_paths.append(frame_file_path)
                        return saved_paths

                    processed_frame_paths = await asyncio.to_thread(
                        _save_frames_sync,
                        processed_frames_in_memory,
                        base_output_path
                    )
                    output_frames_data = processed_frame_paths
                else:
                    output_frames_data = processed_frames_in_memory
                
                # Construct the result dictionary
                result_dict = {
                    "frame_paths": output_frames_data, # Changed key from "frames" to "frame_paths"
                    "frame_count": len(output_frames_data) if isinstance(output_frames_data, list) else 0,
                    "duration_seconds": (datetime.now().timestamp() - start_time),
                    "exercise_type": exercise_type.value,
                    "normalized_video_path": video_to_validate_path, # This is a temp local path
                    "video_metadata": video_metadata
                }

                track_model_inference(
                    exercise_type=exercise_type.value,
                    frame_count=len(processed_frames_in_memory),
                    has_errors=False,
                    model_type="video_processing",
                    duration=datetime.now().timestamp() - start_time,
                    confidence=1.0, # Assuming success if we reach here
                    error_type=None
                )
                return result_dict # Return the constructed dictionary
                
            except cv2.error as e:
                # Added specific handling for cv2.error
                track_model_inference(
                    exercise_type=exercise_type.value,
                    frame_count=0, # Or count at point of failure if available
                    has_errors=True,
                    model_type="video_processing_cv2",
                    duration=datetime.now().timestamp() - start_time,
                    confidence=0.0,
                    error_type=f"OpenCVError: {type(e).__name__} - {e.msg}"
                )
                raise VideoProcessingError(f"OpenCV error during video processing: {e.msg}")
            except VideoValidationError as ve:
                # Re-raise specific validation errors to be caught by the caller
                # Logging or specific error handling for VideoValidationError could be done here if needed
                # track_model_inference is already called inside _validate_video upon failure
                raise ve
            except VideoReadError as vre:
                # Re-raise specific read errors
                # track_model_inference is already called at the beginning for empty data
                raise vre
            except Exception as e:
                track_model_inference(
                    exercise_type=exercise_type.value,
                    frame_count=0, # Or len(frames) if frames were extracted before error
                    has_errors=True,
                    model_type="video_processing_general",
                    duration=datetime.now().timestamp() - start_time,
                    confidence=0.0,
                    error_type=f"{type(e).__name__}: {str(e)}"
                )
                # Wrap generic exceptions in VideoProcessingError for consistent error handling
                raise VideoProcessingError(f"An unexpected error occurred during video processing: {e}")
    
    # This method is now synchronous
    def _normalize_video_with_ffmpeg(
        self,
        input_path: str,
        output_path: str,
        target_fps: int
    ) -> bool:
        """
        Normalizes video resolution and FPS using FFmpeg. Runs synchronously.
        Returns True on success, False on failure.
        Logs errors internally.
        """
        # Ensure target_fps is a positive integer
        if not isinstance(target_fps, int) or target_fps <= 0:
            # Log this misconfiguration, but perhaps don't fail the whole process,
            # or raise a specific configuration error. For now, just skip normalization.
            # Consider adding logging here: e.g., self.logger.warning("Invalid target_fps...")
            return True # Or False, depending on desired behavior for invalid FPS config

        ffmpeg_cmd = [
            "ffmpeg",
            "-i", input_path,
            "-vf", f"fps={target_fps}",
            "-c:v", "libx264",       # Example codec, might need adjustment
            "-preset", "ultrafast",   # Prioritize speed for processing
            "-an",                   # No audio
            "-y",                    # Overwrite output file without asking
            output_path
        ]
        try:
            # Using subprocess.run for simplicity. For long operations in async code,
            # consider asyncio.create_subprocess_exec or running in a thread pool.
            process = subprocess.run(ffmpeg_cmd, capture_output=True, text=True, check=False, timeout=self.settings.FFMPEG_TIMEOUT) # Added timeout

            if process.returncode != 0:
                # Log detailed FFmpeg error
                # Consider adding logging here: 
                # self.logger.error(f"FFmpeg failed for {input_path} to {output_path}. FPS: {target_fps}")
                # self.logger.error(f"FFmpeg stdout: {process.stdout}")
                # self.logger.error(f"FFmpeg stderr: {process.stderr}")
                return False
            return True
        except FileNotFoundError:
            # FFmpeg command not found
            # Consider adding logging here: self.logger.error("FFmpeg command not found. Ensure FFmpeg is installed and in PATH.")
            # This is a system configuration issue.
            raise VideoProcessingError("FFmpeg command not found. Ensure FFmpeg is installed and in PATH.")
        except subprocess.TimeoutExpired:
            # Consider adding logging here: self.logger.error(f"FFmpeg command timed out for {input_path}")
            raise VideoProcessingError(f"FFmpeg command timed out after {self.settings.FFMPEG_TIMEOUT} seconds for {input_path}")
        except Exception as e:
            # Catch any other subprocess-related errors
            # Consider adding logging here: self.logger.error(f"Subprocess error during FFmpeg execution: {e}")
            raise VideoProcessingError(f"Subprocess error during FFmpeg execution: {e}")
    
    # Renamed and changed to synchronous: _extract_frames_sync
    def _extract_frames_sync(
        self,
        video_path: str,
        exercise_type: ExerciseType
    ) -> List[np.ndarray]:
        """Extracts frames from video using OpenCV. Runs synchronously."""
        frames: List[np.ndarray] = []
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            # This case should ideally be caught by _validate_video first.
            # If it reaches here, it implies _validate_video might have passed (e.g. file existed)
            # but OpenCV still couldn't open it for reading frames for some other reason.
            cap.release() # Ensure release even if not opened.
            raise VideoReadError(f"Could not open video file for frame extraction: {video_path}")
        
        try:
            # Get video properties
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = int(cap.get(cv2.CAP_PROP_FPS))
            
            # Calculate frame interval
            interval = max(1, total_frames // self.max_frames)
            
            frame_count = 0
            while cap.isOpened() and frame_count < self.max_frames:
                ret, frame = cap.read()
                if not ret:
                    break
                
                if frame_count % interval == 0:
                    frames.append(frame)
                
                frame_count += 1
                
        finally:
            cap.release()
        
        return frames
    
    def _select_key_frames(
        self,
        frames: List[np.ndarray],
        exercise_type: ExerciseType
    ) -> List[np.ndarray]:
        """Select key frames for exercise analysis."""
        if not frames:
            return []
            
        config = self.frame_selection_configs.get(exercise_type)
        if not config:
            return frames
            
        frame_count = config["frame_count"]
        if len(frames) <= frame_count:
            return frames
            
        # Calculate indices for key frames
        indices = [
            int(i * (len(frames) - 1) / (frame_count - 1))
            for i in range(frame_count)
        ]
        
        return [frames[i] for i in indices]
    
    def _preprocess_frames(self, frames: List[np.ndarray]) -> List[np.ndarray]:
        """Preprocess frames for ML model input."""
        processed_frames = []
        
        for frame in frames:
            # Resize frame
            resized = cv2.resize(frame, self.target_size)
            
            # Convert to RGB
            rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
            
            # Normalize pixel values
            normalized = rgb.astype(np.float32) / 255.0
            
            processed_frames.append(normalized)
        
        return processed_frames
    
    def _validate_video(self, video_path: str) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """Validate video file format and properties. Returns (is_valid, message, video_metadata)."""
        video_metadata: Optional[Dict[str, Any]] = None
        try:
            cap = cv2.VideoCapture(video_path)
            
            if not cap.isOpened():
                return False, "Could not open video file (validation step)", None
            
            # Check video properties
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS) # Keep as float for precision
            actual_frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            if fps == 0 or actual_frame_count == 0: # Avoid division by zero or meaningless data
                return False, "Video has zero FPS or zero frames.", None

            duration = actual_frame_count / fps

            video_metadata = {
                "width": width,
                "height": height,
                "fps": fps,
                "actual_frame_count": actual_frame_count,
                "duration": duration
            }
            
            # Validate dimensions
            if width < 320 or height < 240:
                return False, "Video resolution too low", video_metadata
            
            # Validate frame rate
            if fps < 10: # Lowered slightly from 15 as some phone videos might be lower
                return False, "Frame rate too low (less than 10 FPS)", video_metadata
            
            # Validate duration
            if duration > self.settings.MAX_VIDEO_DURATION:
                return False, f"Video duration exceeds {self.settings.MAX_VIDEO_DURATION} seconds", video_metadata
            
            return True, None, video_metadata
            
        except Exception as e:
            return False, str(e), None
            
        finally:
            if 'cap' in locals() and cap.isOpened(): # Check if cap is opened before releasing
                cap.release()

# Dependency Injector
from fastapi import Depends
from app.core.deps import get_settings

async def get_async_video_processing_service(app_settings: Settings = Depends(get_settings)) -> VideoProcessingService:
    """Get an instance of the VideoProcessingService."""
    return VideoProcessingService(app_settings=app_settings) 