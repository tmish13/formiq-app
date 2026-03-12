"""Video processing service for exercise form analysis."""
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import cv2
from datetime import datetime
import tempfile
import os
import subprocess # Added for FFmpeg integration
import asyncio # Add asyncio import
import logging # Add logging import
import time

from app.core.monitoring import track_model_inference, FRAME_PROCESSING_DURATION, FRAME_PROCESSING_COUNT, CONCURRENT_UPLOADS
from app.models.enums import ExerciseType
from app.core.config import Settings
from app.core.exceptions import VideoProcessingError, VideoValidationError, VideoReadError

class VideoProcessingService:
    """Service for processing exercise videos."""
    
    MIN_DURATION = 1.0  # seconds
    MAX_DURATION = 300.0  # seconds. Increased from 60.
    MIN_RESOLUTION = (240, 320)  # (height, width)
    
    def __init__(self, app_settings: Settings):
        """Initialize video processing service."""
        self.settings = app_settings
        self.logger = logging.getLogger(__name__) # Initialize logger
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
                raise VideoValidationError(error_msg, validation_type="video_validation")

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
    
    def _normalize_video_with_ffmpeg(
        self,
        input_path: str,
        output_path: str,
        target_fps: int
    ) -> bool:
        """Normalize video using FFmpeg: set FPS, scale, and pad to target dimensions."""
        ffmpeg_start_time = time.time()
        
        if not os.path.exists(input_path):
            self.logger.error(f"Input video file not found for FFmpeg: {input_path}")
            return False

        # Target width and height from self.target_size
        target_w, target_h = self.target_size

        # FFmpeg command with scaling and padding
        # Scale to fit within target_w x target_h, maintaining aspect ratio (force_original_aspect_ratio=decrease)
        # Then pad to target_w x target_h with black bars
        vf_filter = (
            f"fps={target_fps},"
            f"scale={target_w}:{target_h}:force_original_aspect_ratio=decrease,"
            f"pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2"
        )

        command = [
            "ffmpeg",
            "-y",
            "-i",
            input_path,
            "-vf",
            vf_filter,
            "-an",  # No audio
            "-vcodec", "libx264",  # Specify video codec
            "-crf", "23",           # Constant Rate Factor (quality, 0-51, lower is better)
            "-preset", "ultrafast", # Encoding speed vs. compression
            # '-vsync', 'cfr', # Consider if constant frame rate issues arise
            output_path
        ]
        self.logger.debug(f"Executing FFmpeg command: {' '.join(command)}")
        try:
            # Using subprocess.run for simplicity. For long operations in async code,
            # consider asyncio.create_subprocess_exec or running in a thread pool.
            process = subprocess.run(command, capture_output=True, text=True, check=False, timeout=self.settings.FFMPEG_TIMEOUT) # Added timeout

            ffmpeg_duration = time.time() - ffmpeg_start_time
            
            # Record FFmpeg processing time
            FRAME_PROCESSING_DURATION.labels(
                exercise_type="unknown",
                processing_stage="ffmpeg_normalize"
            ).observe(ffmpeg_duration)

            if process.returncode != 0:
                self.logger.error(f"FFmpeg failed for {input_path}. Return code: {process.returncode}. Stderr: {process.stderr}")
                return False
                
            self.logger.debug(f"FFmpeg normalization completed in {ffmpeg_duration:.3f}s")
            return True
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Subprocess error during FFmpeg execution: {e}")
            # Re-raise as VideoProcessingError to be handled by the main process_video method
            raise VideoProcessingError(f"Subprocess error during FFmpeg execution: {e}") from e
        except FileNotFoundError:
            # FFmpeg command not found
            self.logger.error("FFmpeg command not found. Please ensure FFmpeg is installed and in the system's PATH.")
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
        """Select key frames based on exercise type configuration."""
        config = self.frame_selection_configs.get(exercise_type)

        if not config:
            self.logger.info(f"No frame selection config for {exercise_type}, returning all frames.")
            return frames

        frame_count = config.get("frame_count", 0)

        if not frames or frame_count == 0:
            return []

        # Handle case where only one frame needs to be selected
        if frame_count == 1:
            return [frames[0]] # Return the first frame if any frames exist

        # If the number of available frames is less than or equal to the desired count,
        # return all available frames.
        if len(frames) <= frame_count:
            return frames

        selected_frames: List[np.ndarray] = []
        for i in range(frame_count):
            # Distribute the selection across the available frames
            # The index is calculated to pick frames as evenly spaced as possible
            index = int(i * (len(frames) - 1) / (frame_count - 1))
            selected_frames.append(frames[index])
        
        return selected_frames
    
    def _preprocess_frames(self, frames: List[np.ndarray]) -> List[np.ndarray]:
        """Preprocess frames for ML model input."""
        processed_frames = []
        
        for frame in frames:
            # Resize frame
            resized = cv2.resize(frame, self.target_size)
            
            # Convert to RGB, which is what MediaPipe expects
            rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
            
            # The frame should be uint8, not normalized to float32
            # The AI service downstream is responsible for any further normalization
            processed_frames.append(rgb)
        
        return processed_frames
    
    def _validate_video(self, video_path: str) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """Validate video file format and properties. Returns (is_valid, message, video_metadata)."""
        video_metadata: Optional[Dict[str, Any]] = None
        try:
            width, height = self._get_video_dimensions(video_path)
            if width == 0 or height == 0:
                return False, "Could not determine video dimensions (validation step)", None
            
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return False, "Could not open video file (validation step)", None
            
            # Check video properties
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
            
            # Validate dimensions - allow for vertical videos
            if min(width, height) < 240:
                return False, "Video resolution too low (minimum dimension < 240px)", video_metadata
            
            # Validate frame rate
            if fps < 10: # Lowered slightly from 15 as some phone videos might be lower
                return False, "Frame rate too low (less than 10 FPS)", video_metadata
            
            # Duration validation
            if not (self.MIN_DURATION <= duration <= self.MAX_DURATION):
                error_msg = f"Video duration {duration:.2f}s is outside the acceptable range of {self.MIN_DURATION}-{self.MAX_DURATION}s."
                self.logger.warning(error_msg)
                raise VideoValidationError(error_msg, validation_type="duration")
            
            return True, None, video_metadata
            
        except Exception as e:
            return False, str(e), None
            
        finally:
            if 'cap' in locals() and cap.isOpened(): # Check if cap is opened before releasing
                cap.release()

    def _get_video_dimensions(self, video_path: str) -> Tuple[int, int]:
        """Gets the width and height of a video using ffprobe."""
        cmd = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height",
            "-of", "csv=s=x:p=0",
            video_path
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=self.settings.FFMPEG_TIMEOUT)
            width, height = map(int, result.stdout.strip().split('x'))
            return width, height
        except (subprocess.CalledProcessError, FileNotFoundError, ValueError) as e:
            self.logger.error(f"Error getting video dimensions for {video_path}: {e}")
            return 0, 0
            
    def _get_video_duration_and_fps(self, video_path: str) -> Tuple[float, float]:
        """Gets the duration and FPS of a video using ffprobe."""
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration,bit_rate",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            video_path
        ]
        self.logger.info(f"Normalizing video {video_path} to {video_path}")
        try:
            # Use ffmpeg from PATH instead of a hardcoded setting
            result = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=self.settings.FFMPEG_TIMEOUT) # Added timeout

            if result.returncode != 0:
                self.logger.error(f"ffprobe failed for {video_path}. Return code: {result.returncode}. Stderr: {result.stderr}")
                return 0.0, 0.0

            # Parse the output
            output_lines = result.stdout.splitlines()
            if len(output_lines) < 2:
                self.logger.error(f"Unexpected output format from ffprobe for {video_path}")
                return 0.0, 0.0

            duration = float(output_lines[0])
            bit_rate = float(output_lines[1])

            width, height = self._get_video_dimensions(video_path)
            if width == 0 or height == 0:
                self.logger.error(f"Could not get dimensions for video {video_path}")
                return 0.0, 0.0

            # Calculate FPS from bitrate if available
            # Note: This is an estimation and might not be perfectly accurate.
            # A more reliable way is to get FPS directly if the format provides it.
            if bit_rate > 0 and width > 0 and height > 0:
                 # Assuming 24 bits per pixel (8 bits per channel for R, G, B)
                fps = bit_rate / (width * height * 24)
            else:
                fps = 0.0 # Cannot determine FPS

            return duration, fps
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Subprocess error during ffprobe execution: {e}")
            # Re-raise as VideoProcessingError to be handled by the main process_video method
            raise VideoProcessingError(f"Subprocess error during ffprobe execution: {e}") from e
        except FileNotFoundError:
            # ffprobe command not found
            self.logger.error("ffprobe command not found. Please ensure ffprobe is installed and in the system's PATH.")
            # This is a system configuration issue.
            raise VideoProcessingError("ffprobe command not found. Ensure ffprobe is installed and in PATH.")
        except subprocess.TimeoutExpired:
            # Consider adding logging here: self.logger.error(f"ffprobe command timed out for {video_path}")
            raise VideoProcessingError(f"ffprobe command timed out after {self.settings.FFMPEG_TIMEOUT} seconds for {video_path}")
        except Exception as e:
            # Catch any other subprocess-related errors
            # Consider adding logging here: self.logger.error(f"Subprocess error during ffprobe execution: {e}")
            raise VideoProcessingError(f"Subprocess error during ffprobe execution: {e}")

# Dependency Injector
from fastapi import Depends
from app.core.deps import get_settings

async def get_async_video_processing_service(app_settings: Settings = Depends(get_settings)) -> VideoProcessingService:
    """Get an instance of the VideoProcessingService."""
    return VideoProcessingService(app_settings=app_settings) 