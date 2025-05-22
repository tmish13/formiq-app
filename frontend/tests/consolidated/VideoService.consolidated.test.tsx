/**
 * Consolidated Tests for Camera and Video User Interactions
 * 
 * This file tests user interactions with video recording, playback, and uploading features:
 * 1. Recording videos with device camera
 * 2. Uploading videos for form checks
 * 3. Viewing and controlling video playback
 * 4. Managing camera permissions
 */
import React, { useState, useEffect, useRef } from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { http, HttpResponse } from 'msw';

// Import from shared mocks
import {
  setupMockServer,
  setupServerLifecycle,
  createMockVideo,
  createMockVideoFile,
  videoHandlers,
  setupVideoElementMocks,
  createMockMediaDevices
} from '../utils/sharedMocks';

// Custom handlers for specific test cases
const customHandlers = [
  // Mock POST endpoint for video processing failure
  http.post('/api/videos/process', () => {
    return new HttpResponse(
      JSON.stringify({ message: 'Video processing failed' }),
      { status: 500 }
    );
  }),
  
  // Mock endpoint for video playback error
  http.get('/api/videos/error-video', () => {
    return new HttpResponse(
      JSON.stringify({ message: 'Video not found or corrupted' }),
      { status: 404 }
    );
  })
];

// Setup MSW server
const server = setupMockServer([
  ...videoHandlers,
  ...customHandlers
]);
setupServerLifecycle(server);

// Setup for tests
beforeAll(() => {
  // Mock mediaDevices
  Object.defineProperty(global.navigator, 'mediaDevices', {
    value: createMockMediaDevices(),
    writable: true
  });
  
  // Mock URL.createObjectURL for video blobs
  global.URL.createObjectURL = jest.fn().mockImplementation(blob => {
    return `blob:mock-url-${Math.random().toString(36).substring(2, 15)}`;
  });
});

afterAll(() => {
  jest.restoreAllMocks();
});

/**
 * Video User Interaction Tests
 */
describe('Camera & Video User Interactions', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  /**
   * Recording Videos
   */
  describe('Recording Video with Device Camera', () => {
    // Component that allows users to record videos
    const VideoRecorder = () => {
      const [isRecording, setIsRecording] = useState(false);
      const [recordedVideo, setRecordedVideo] = useState<string | null>(null);
      const [permissionError, setPermissionError] = useState<string | null>(null);
      const videoRef = useRef<HTMLVideoElement | null>(null);
      const streamRef = useRef<MediaStream | null>(null);
      
      const startRecording = async () => {
        try {
          // Request camera access
          const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
          streamRef.current = stream;
          
          if (videoRef.current) {
            videoRef.current.srcObject = stream;
            videoRef.current.play();
          }
          
          setIsRecording(true);
          setPermissionError(null);
        } catch (err) {
          setPermissionError('Camera permission denied');
        }
      };
      
      const stopRecording = () => {
        // Stop the camera stream
        if (streamRef.current) {
          streamRef.current.getTracks().forEach(track => track.stop());
        }
        
        if (videoRef.current) {
          videoRef.current.srcObject = null;
        }
        
        // In a real app, we would save the recording
        // Here we're just simulating a recorded video URL
        setRecordedVideo('blob:mock-video-recording');
        setIsRecording(false);
      };
      
      return (
        <div>
          <h1>Video Recorder</h1>
          
          {/* Camera preview */}
          <div className="camera-preview">
            <video 
              ref={videoRef}
              autoPlay 
              muted 
              playsInline
              data-testid="camera-preview"
            />
          </div>
          
          {/* Recording controls */}
          <div className="controls">
          {!isRecording ? (
              <button onClick={startRecording} data-testid="start-recording-btn">
                Start Recording
              </button>
            ) : (
              <button onClick={stopRecording} data-testid="stop-recording-btn">
                Stop Recording
              </button>
            )}
          </div>
          
          {/* Error message */}
          {permissionError && (
            <div className="error" role="alert">
              {permissionError}
            </div>
          )}
          
          {/* Recording indicator */}
          {isRecording && (
            <div className="recording-indicator" role="status">
              Recording in progress...
            </div>
          )}
          
          {/* Recorded video playback */}
          {recordedVideo && (
            <div className="recorded-video">
              <h2>Recorded Video</h2>
              <video 
                src={recordedVideo}
                controls 
                data-testid="recorded-video"
              />
              <button data-testid="upload-btn">Upload Video</button>
            </div>
          )}
        </div>
      );
    };
    
    it('GIVEN a user has camera permissions WHEN they record a video THEN they can preview and upload it', async () => {
      const user = userEvent.setup();
      render(<VideoRecorder />);
      
      // Start recording
      await user.click(screen.getByTestId('start-recording-btn'));
      
      // Verify recording has started
      expect(screen.getByRole('status')).toHaveTextContent(/recording in progress/i);
      expect(navigator.mediaDevices.getUserMedia).toHaveBeenCalledWith({ 
        video: true, 
        audio: true 
      });
      
      // Stop recording
      await user.click(screen.getByTestId('stop-recording-btn'));
      
      // Verify recording has stopped and video is available
      await waitFor(() => {
        expect(screen.getByTestId('recorded-video')).toBeInTheDocument();
        expect(screen.getByTestId('upload-btn')).toBeInTheDocument();
      });
    });
    
    it('GIVEN a user does not grant camera permissions WHEN they try to record THEN they see an error message', async () => {
      // Override getUserMedia to simulate permission denial
      const mockMediaDevices = createMockMediaDevices();
      mockMediaDevices.getUserMedia.mockRejectedValueOnce(new Error('Permission denied'));
      
      Object.defineProperty(global.navigator, 'mediaDevices', {
        value: mockMediaDevices,
        writable: true
      });
      
      const user = userEvent.setup();
      render(<VideoRecorder />);
      
      // Try to start recording
      await user.click(screen.getByTestId('start-recording-btn'));
      
      // Verify error message appears
      await waitFor(() => {
        expect(screen.getByRole('alert')).toHaveTextContent(/camera permission denied/i);
      });
      
      // Verify no recording UI is shown
      expect(screen.queryByRole('status')).not.toBeInTheDocument();
    });
  });

  /**
   * Uploading Videos
   */
  describe('Uploading and Processing Videos', () => {
    const VideoUploader = () => {
      const [selectedFile, setSelectedFile] = useState<File | null>(null);
      const [isUploading, setIsUploading] = useState(false);
      const [uploadProgress, setUploadProgress] = useState(0);
      const [uploadedVideo, setUploadedVideo] = useState<{id: string, url: string} | null>(null);
      const [error, setError] = useState<string | null>(null);
      
      const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
        const files = event.target.files;
        if (files && files.length > 0) {
          setSelectedFile(files[0]);
        }
      };
      
      const uploadVideo = async () => {
        if (!selectedFile) {
          setError('Please select a video file first');
          return;
        }
        
        setError(null);
        setIsUploading(true);
        setUploadProgress(0);
        
        try {
          // Simulate upload progress
          const progressInterval = setInterval(() => {
            setUploadProgress(prev => {
              if (prev >= 90) {
                clearInterval(progressInterval);
                return 90;
              }
              return prev + 10;
            });
          }, 100);
          
          // Create FormData for the upload
          const formData = new FormData();
          formData.append('video', selectedFile);
          
          // Send the request
          const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
          });
          
          clearInterval(progressInterval);
          
          if (!response.ok) {
            throw new Error('Upload failed');
          }
          
          const data = await response.json();
          setUploadProgress(100);
          setUploadedVideo({
            id: data.video.id,
            url: data.video.url
          });
        } catch (err) {
          setError(err instanceof Error ? err.message : 'Upload failed');
        } finally {
          setIsUploading(false);
        }
      };
      
      return (
        <div>
          <h1>Upload Video</h1>
          
          <div className="file-input">
            <label htmlFor="video-file">Select Video:</label>
            <input
              id="video-file"
              type="file"
              accept="video/*"
              onChange={handleFileSelect}
              data-testid="video-file-input"
            />
          </div>
          
          {selectedFile && (
            <div className="file-info" data-testid="selected-file-info">
              <p>Selected file: {selectedFile.name}</p>
              <p>Size: {Math.round(selectedFile.size / 1024)} KB</p>
            </div>
          )}
          
          <button
            onClick={uploadVideo}
            disabled={!selectedFile || isUploading}
            data-testid="upload-button"
          >
            {isUploading ? 'Uploading...' : 'Upload Video'}
          </button>
          
          {isUploading && (
            <div className="progress" data-testid="upload-progress">
              <div 
                className="progress-bar" 
                style={{ width: `${uploadProgress}%` }}
                aria-valuenow={uploadProgress}
                aria-valuemin={0}
                aria-valuemax={100}
                role="progressbar"
              >
                {uploadProgress}%
              </div>
            </div>
          )}
          
          {error && (
            <div className="error" role="alert" data-testid="upload-error">
              {error}
            </div>
          )}
          
          {uploadedVideo && (
            <div className="success" data-testid="upload-success">
              <p>Video uploaded successfully!</p>
              <p>Video ID: {uploadedVideo.id}</p>
              <a href={uploadedVideo.url} target="_blank" rel="noopener noreferrer">
                View Video
              </a>
            </div>
          )}
        </div>
      );
    };
    
    it('GIVEN a user selects a video file WHEN they upload it THEN they see successful upload confirmation', async () => {
      const user = userEvent.setup();
      render(<VideoUploader />);
      
      // Create a mock file
      const file = createMockVideoFile();
      
      // Upload the file
      const input = screen.getByTestId('video-file-input');
      await user.upload(input, file);
      
      // Verify file selection info is displayed
      const fileInfo = screen.getByTestId('selected-file-info');
      expect(fileInfo).toHaveTextContent(file.name);
      
      // Click upload button
      await user.click(screen.getByTestId('upload-button'));
      
      // Verify upload progress is shown
      expect(screen.getByTestId('upload-progress')).toBeInTheDocument();
      
      // Verify success message appears
      await waitFor(() => {
        expect(screen.getByTestId('upload-success')).toBeInTheDocument();
      }, { timeout: 2000 });
    });
    
    it('GIVEN a user tries to upload without selecting a file WHEN they click upload THEN they see an error message', async () => {
      const user = userEvent.setup();
      render(<VideoUploader />);
      
      // Try to upload without selecting a file
      await user.click(screen.getByTestId('upload-button'));
      
      // Verify error message appears
      expect(screen.getByTestId('upload-error')).toHaveTextContent('Please select a video file first');
    });
  });

  /**
   * Video Playback
   */
  describe('Video Playback Controls', () => {
    // Mock video element for testing
    const mockVideoElement = setupVideoElementMocks();
    
    // We need to mock the currentTime property since it's not included in the basic mock
    let currentTimeSetter = 0;
    Object.defineProperty(mockVideoElement, 'currentTime', {
      get() { return currentTimeSetter; },
      set(value) { currentTimeSetter = value; }
    });
    
    Object.defineProperty(mockVideoElement, 'duration', { value: 60 });
    
    const VideoPlayer = () => {
      const [isPlaying, setIsPlaying] = useState(false);
      const [currentTime, setCurrentTime] = useState(0);
      const [duration, setDuration] = useState(0);
      const videoRef = useRef<HTMLVideoElement | null>(null);
      
      useEffect(() => {
        // In a real component, this would be set by the actual video element
        if (videoRef.current) {
          setDuration(videoRef.current.duration);
        }
      }, []);
      
      const handlePlay = () => {
        if (videoRef.current) {
          videoRef.current.play();
          setIsPlaying(true);
        }
      };
      
      const handlePause = () => {
        if (videoRef.current) {
          videoRef.current.pause();
          setIsPlaying(false);
        }
      };
      
      const handleTimeUpdate = () => {
        if (videoRef.current) {
          setCurrentTime(videoRef.current.currentTime);
        }
      };
      
      const handleLoadedMetadata = () => {
        if (videoRef.current) {
          setDuration(videoRef.current.duration);
        }
      };
      
      const handleSeek = (event: React.ChangeEvent<HTMLInputElement>) => {
        const newTime = Number(event.target.value);
        if (videoRef.current) {
          videoRef.current.currentTime = newTime;
          setCurrentTime(newTime);
        }
      };
      
      const formatTime = (seconds: number) => {
        const minutes = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${minutes}:${secs < 10 ? '0' : ''}${secs}`;
      };
      
      return (
        <div className="video-player">
          <video
            ref={videoRef}
            src="https://example.com/video.mp4"
            onPlay={() => setIsPlaying(true)}
            onPause={() => setIsPlaying(false)}
            onTimeUpdate={handleTimeUpdate}
            onLoadedMetadata={handleLoadedMetadata}
            data-testid="video-element"
          />
          
          <div className="controls">
            {isPlaying ? (
              <button onClick={handlePause} data-testid="pause-btn">
                Pause
              </button>
            ) : (
              <button onClick={handlePlay} data-testid="play-btn">
                Play
              </button>
            )}
            
            <div className="time-display" data-testid="time-display">
              {formatTime(currentTime)} / {formatTime(duration)}
            </div>
            
            <input
              type="range"
              min="0"
              max={duration || 0}
              value={currentTime}
              onChange={handleSeek}
              data-testid="seek-slider"
            />
          </div>
        </div>
      );
    };
    
    it('GIVEN a video is loaded WHEN a user plays it THEN the video begins playing', async () => {
      const user = userEvent.setup();
      render(<VideoPlayer />);
      
      // Click play button
      await user.click(screen.getByTestId('play-btn'));
      
      // Verify play was called
      expect(mockVideoElement.play).toHaveBeenCalled();
      expect(screen.getByTestId('pause-btn')).toBeInTheDocument();
      expect(screen.queryByTestId('play-btn')).not.toBeInTheDocument();
    });
    
    it('GIVEN a video is playing WHEN a user pauses it THEN the video stops playing', async () => {
      const user = userEvent.setup();
      
      // Start with playing state
      render(<VideoPlayer />);
      await user.click(screen.getByTestId('play-btn'));
      
      // Now pause
      await user.click(screen.getByTestId('pause-btn'));
      
      // Verify pause was called
      expect(mockVideoElement.pause).toHaveBeenCalled();
      expect(screen.getByTestId('play-btn')).toBeInTheDocument();
      expect(screen.queryByTestId('pause-btn')).not.toBeInTheDocument();
    });
    
    it('GIVEN a video is playing WHEN a user seeks to a different position THEN the video jumps to that timestamp', async () => {
      const user = userEvent.setup();
      render(<VideoPlayer />);
      
      // Mock the input event
      const seekSlider = screen.getByTestId('seek-slider');
      
      // Update the slider value
      await user.click(seekSlider);
      
      // Fire input event manually since Jest doesn't support range inputs well
      fireInputEvent(seekSlider, '30');
      
      // Verify current time was updated
      expect(currentTimeSetter).toBe(30);
      expect(screen.getByTestId('time-display')).toHaveTextContent('30:00');
    });
    
    // Helper function to fire input events
    function fireInputEvent(element: Element, value: string) {
      const event = new Event('input', { bubbles: true });
      const inputElement = element as HTMLInputElement;
      inputElement.value = value;
      inputElement.dispatchEvent(event);
      
      // Also dispatch change event to trigger React's onChange
      const changeEvent = new Event('change', { bubbles: true });
      inputElement.dispatchEvent(changeEvent);
    }
  });

  /**
   * Camera Permissions
   */
  describe('Camera Permission Management', () => {
    const CameraPermissions = () => {
      const [hasPermission, setHasPermission] = useState<boolean | null>(null);
      const [isChecking, setIsChecking] = useState(false);
      
      const checkPermissions = async () => {
        setIsChecking(true);
        
        try {
          // Try to access camera to test permissions
          await navigator.mediaDevices.getUserMedia({ video: true });
          setHasPermission(true);
        } catch (err) {
          setHasPermission(false);
        } finally {
          setIsChecking(false);
        }
      };
      
      const requestPermissions = async () => {
        setIsChecking(true);
        
        try {
          await navigator.mediaDevices.getUserMedia({ video: true });
          setHasPermission(true);
        } catch (err) {
          setHasPermission(false);
        } finally {
          setIsChecking(false);
        }
      };
      
      return (
        <div>
          <h1>Camera Permissions</h1>
          
          <button
            onClick={checkPermissions}
            disabled={isChecking}
            data-testid="check-permission-btn"
          >
            Check Camera Permission
          </button>
          
          {hasPermission === null ? (
            <p>Click the button to check camera permissions</p>
          ) : hasPermission ? (
            <div data-testid="permission-granted">
              <p>Camera permission granted!</p>
              <button data-testid="start-camera-btn">Start Camera</button>
            </div>
          ) : (
            <div data-testid="permission-denied">
              <p>Camera permission denied.</p>
              <button 
                onClick={requestPermissions}
                data-testid="request-permission-btn"
              >
                Request Permission
              </button>
            </div>
          )}
        </div>
      );
    };
    
    it('GIVEN a user has granted camera permissions WHEN they check permissions THEN they see permissions are granted', async () => {
      const user = userEvent.setup();
      render(<CameraPermissions />);
      
      // Click check permissions
      await user.click(screen.getByTestId('check-permission-btn'));
      
      // Verify permission granted message appears
      await waitFor(() => {
        expect(screen.getByTestId('permission-granted')).toBeInTheDocument();
      });
    });
    
    it('GIVEN a user has denied camera permissions WHEN they check permissions THEN they see permissions are denied', async () => {
      // Override getUserMedia to simulate permission denial
      const mockMediaDevices = createMockMediaDevices();
      mockMediaDevices.getUserMedia.mockRejectedValueOnce(new Error('Permission denied'));
      
      Object.defineProperty(global.navigator, 'mediaDevices', {
        value: mockMediaDevices,
        writable: true
      });
      
      const user = userEvent.setup();
      render(<CameraPermissions />);
      
      // Click check permissions
      await user.click(screen.getByTestId('check-permission-btn'));
      
      // Verify permission denied message appears
      await waitFor(() => {
        expect(screen.getByTestId('permission-denied')).toBeInTheDocument();
      });
    });
    
    it('GIVEN a user has denied permissions WHEN they request permissions THEN they can be granted access', async () => {
      // First denied, then granted
      const mockMediaDevices = createMockMediaDevices();
      mockMediaDevices.getUserMedia
        .mockRejectedValueOnce(new Error('Permission denied'))
        .mockResolvedValueOnce({} as MediaStream);
      
      Object.defineProperty(global.navigator, 'mediaDevices', {
        value: mockMediaDevices,
        writable: true
      });
      
      const user = userEvent.setup();
      render(<CameraPermissions />);
      
      // Click check permissions (should be denied first)
      await user.click(screen.getByTestId('check-permission-btn'));
      
      // Wait for denial message
      await waitFor(() => {
        expect(screen.getByTestId('permission-denied')).toBeInTheDocument();
      });
      
      // Click request permissions button
      await user.click(screen.getByTestId('request-permission-btn'));
      
      // Verify permission granted message appears
      await waitFor(() => {
        expect(screen.getByTestId('permission-granted')).toBeInTheDocument();
      });
    });
  });
}); 