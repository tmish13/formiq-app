import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

// Mock components and services
// VideoPlayer Component Mock
const VideoPlayer = ({ 
  src, 
  onPlay, 
  onPause,
  onSeek,
  onEnded,
  controls = true,
  autoPlay = false,
  loop = false,
  muted = false,
  width = '100%',
  height = 'auto',
  testId = 'video-player'
}) => {
  const videoRef = React.useRef(null);
  const [isPlaying, setIsPlaying] = React.useState(false);
  const [currentTime, setCurrentTime] = React.useState(0);
  const [duration, setDuration] = React.useState(0);
  
  const handlePlay = () => {
    setIsPlaying(true);
    if (onPlay) onPlay();
  };
  
  const handlePause = () => {
    setIsPlaying(false);
    if (onPause) onPause();
  };
  
  const handleSeek = (time) => {
    setCurrentTime(time);
    if (onSeek) onSeek(time);
  };
  
  const handleEnded = () => {
    setIsPlaying(false);
    if (onEnded) onEnded();
  };
  
  const togglePlayPause = () => {
    if (isPlaying) {
      handlePause();
    } else {
      handlePlay();
    }
  };
  
  // Format time as MM:SS
  const formatTime = (timeInSeconds) => {
    const minutes = Math.floor(timeInSeconds / 60);
    const seconds = Math.floor(timeInSeconds % 60);
    return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
  };
  
  return (
    <div className="video-player-container" data-testid={testId}>
      <video
        ref={videoRef}
        src={src}
        autoPlay={autoPlay}
        loop={loop}
        muted={muted}
        width={width}
        height={height}
        data-testid="video-element"
        onPlay={handlePlay}
        onPause={handlePause}
        onEnded={handleEnded}
      />
      
      {controls && (
        <div className="video-controls" data-testid="video-controls">
          <button 
            data-testid="play-pause-button" 
            onClick={togglePlayPause}
          >
            {isPlaying ? 'Pause' : 'Play'}
          </button>
          
          <input
            type="range"
            min="0"
            max={duration || 100}
            value={currentTime}
            onChange={(e) => handleSeek(parseFloat(e.target.value))}
            data-testid="progress-slider"
          />
          
          <span data-testid="time-display">
            {formatTime(currentTime)} / {formatTime(duration || 0)}
          </span>
        </div>
      )}
    </div>
  );
};

// Mock video service
const videoService = {
  loadVideo: jest.fn().mockResolvedValue({
    url: 'https://example.com/test-video.mp4',
    duration: 120, // 2 minutes
    width: 1280,
    height: 720
  }),
  
  generateThumbnail: jest.fn().mockResolvedValue('data:image/jpeg;base64,mockBase64Data'),
  
  seekToPosition: jest.fn((videoElement, timeInSeconds) => {
    videoElement.currentTime = timeInSeconds;
    return Promise.resolve(timeInSeconds);
  }),
  
  extractFrame: jest.fn((videoElement, time) => {
    return Promise.resolve('data:image/jpeg;base64,mockFrameData');
  })
};

describe('VideoPlayer Consolidated Tests', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    
    // Mock the HTMLMediaElement API
    Object.defineProperty(window.HTMLMediaElement.prototype, 'play', {
      configurable: true,
      writable: true,
      value: jest.fn().mockResolvedValue(undefined)
    });
    
    Object.defineProperty(window.HTMLMediaElement.prototype, 'pause', {
      configurable: true,
      writable: true,
      value: jest.fn()
    });
    
    Object.defineProperty(window.HTMLMediaElement.prototype, 'load', {
      configurable: true,
      writable: true,
      value: jest.fn()
    });
    
    Object.defineProperty(window.HTMLMediaElement.prototype, 'currentTime', {
      configurable: true,
      writable: true,
      value: 0
    });
    
    Object.defineProperty(window.HTMLMediaElement.prototype, 'duration', {
      configurable: true,
      writable: true,
      value: 120 // 2 minutes
    });
    
    Object.defineProperty(window.HTMLMediaElement.prototype, 'paused', {
      configurable: true,
      get: jest.fn(() => true),
      set: jest.fn()
    });
  });
  
  describe('Basic Video Player Functionality', () => {
    it('renders video player with a video element', () => {
      render(<VideoPlayer src="https://example.com/test-video.mp4" />);
      
      expect(screen.getByTestId('video-player')).toBeInTheDocument();
      expect(screen.getByTestId('video-element')).toBeInTheDocument();
    });
    
    it('renders video controls when controls prop is true', () => {
      render(<VideoPlayer src="https://example.com/test-video.mp4" controls={true} />);
      
      expect(screen.getByTestId('video-controls')).toBeInTheDocument();
      expect(screen.getByTestId('play-pause-button')).toBeInTheDocument();
      expect(screen.getByTestId('progress-slider')).toBeInTheDocument();
      expect(screen.getByTestId('time-display')).toBeInTheDocument();
    });
    
    it('does not render video controls when controls prop is false', () => {
      render(<VideoPlayer src="https://example.com/test-video.mp4" controls={false} />);
      
      expect(screen.queryByTestId('video-controls')).not.toBeInTheDocument();
    });
    
    it('has correct initial button label', () => {
      render(<VideoPlayer src="https://example.com/test-video.mp4" />);
      
      expect(screen.getByTestId('play-pause-button')).toHaveTextContent('Play');
    });
    
    it('changes button label when play/pause is clicked', async () => {
      render(<VideoPlayer src="https://example.com/test-video.mp4" />);
      
      const playPauseButton = screen.getByTestId('play-pause-button');
      
      // Initial state
      expect(playPauseButton).toHaveTextContent('Play');
      
      // Click to play
      fireEvent.click(playPauseButton);
      expect(playPauseButton).toHaveTextContent('Pause');
      
      // Click to pause
      fireEvent.click(playPauseButton);
      expect(playPauseButton).toHaveTextContent('Play');
    });
    
    it('calls onPlay callback when play button is clicked', () => {
      const handlePlay = jest.fn();
      render(
        <VideoPlayer 
          src="https://example.com/test-video.mp4" 
          onPlay={handlePlay} 
        />
      );
      
      fireEvent.click(screen.getByTestId('play-pause-button'));
      
      expect(handlePlay).toHaveBeenCalledTimes(1);
    });
    
    it('calls onPause callback when pause button is clicked', () => {
      const handlePause = jest.fn();
      render(
        <VideoPlayer 
          src="https://example.com/test-video.mp4" 
          onPause={handlePause} 
        />
      );
      
      // First click to play
      fireEvent.click(screen.getByTestId('play-pause-button'));
      // Second click to pause
      fireEvent.click(screen.getByTestId('play-pause-button'));
      
      expect(handlePause).toHaveBeenCalledTimes(1);
    });
    
    it('renders with custom dimensions', () => {
      render(
        <VideoPlayer 
          src="https://example.com/test-video.mp4" 
          width="640px"
          height="360px"
        />
      );
      
      const videoElement = screen.getByTestId('video-element');
      expect(videoElement).toHaveAttribute('width', '640px');
      expect(videoElement).toHaveAttribute('height', '360px');
    });
  });
  
  describe('Video Playback Features', () => {
    it('updates time display during playback', async () => {
      jest.useFakeTimers();
      
      render(<VideoPlayer src="https://example.com/test-video.mp4" />);
      
      // Start playback
      fireEvent.click(screen.getByTestId('play-pause-button'));
      
      // Update current time to simulate playback
      const videoElement = screen.getByTestId('video-element');
      Object.defineProperty(videoElement, 'currentTime', {
        writable: true,
        value: 10 // 10 seconds
      });
      
      // Trigger timeupdate event
      fireEvent.timeUpdate(videoElement);
      
      // Verify time display shows updated time
      const timeDisplay = screen.getByTestId('time-display');
      expect(timeDisplay).toHaveTextContent('00:10 / 02:00');
      
      jest.useRealTimers();
    });
    
    it('handles video end correctly', () => {
      const handleEnded = jest.fn();
      
      render(
        <VideoPlayer 
          src="https://example.com/test-video.mp4" 
          onEnded={handleEnded}
        />
      );
      
      // Simulate video end
      fireEvent.ended(screen.getByTestId('video-element'));
      
      expect(handleEnded).toHaveBeenCalledTimes(1);
      expect(screen.getByTestId('play-pause-button')).toHaveTextContent('Play');
    });
  });
  
  describe('Seeking Functionality', () => {
    it('updates current time when progress slider is changed', () => {
      const handleSeek = jest.fn();
      
      render(
        <VideoPlayer 
          src="https://example.com/test-video.mp4" 
          onSeek={handleSeek}
        />
      );
      
      const slider = screen.getByTestId('progress-slider');
      
      // Set slider to 30 seconds
      fireEvent.change(slider, { target: { value: 30 } });
      
      expect(handleSeek).toHaveBeenCalledWith(30);
    });
    
    it('calls videoService.seekToPosition with correct arguments', async () => {
      // Mock component that uses the video service
      const VideoSeekDemo = () => {
        const videoRef = React.useRef(null);
        
        const handleSeekTo = (timeInSeconds) => {
          if (videoRef.current) {
            videoService.seekToPosition(videoRef.current, timeInSeconds);
          }
        };
        
        return (
          <div>
            <video 
              ref={videoRef} 
              src="https://example.com/test-video.mp4"
              data-testid="service-video"
            />
            <button 
              onClick={() => handleSeekTo(30)} 
              data-testid="seek-to-30s"
            >
              Seek to 30s
            </button>
            <button 
              onClick={() => handleSeekTo(60)} 
              data-testid="seek-to-60s"
            >
              Seek to 1m
            </button>
          </div>
        );
      };
      
      render(<VideoSeekDemo />);
      
      // Click the button to seek to 30 seconds
      fireEvent.click(screen.getByTestId('seek-to-30s'));
      
      // Verify seekToPosition was called with the right arguments
      expect(videoService.seekToPosition).toHaveBeenCalledWith(
        expect.any(HTMLVideoElement),
        30
      );
      
      // Click the button to seek to 60 seconds (1 minute)
      fireEvent.click(screen.getByTestId('seek-to-60s'));
      
      expect(videoService.seekToPosition).toHaveBeenCalledWith(
        expect.any(HTMLVideoElement),
        60
      );
    });
  });
  
  describe('Thumbnails and Frame Extraction', () => {
    it('calls videoService.generateThumbnail with video file', async () => {
      // Mock the File API
      const mockVideoFile = new File(['mock video content'], 'test-video.mp4', { type: 'video/mp4' });
      
      // Mock component that generates thumbnails
      const ThumbnailGenerator = () => {
        const [thumbnail, setThumbnail] = React.useState(null);
        
        const handleGenerateThumbnail = async () => {
          const thumbnailUrl = await videoService.generateThumbnail(mockVideoFile);
          setThumbnail(thumbnailUrl);
        };
        
        return (
          <div>
            <button 
              onClick={handleGenerateThumbnail} 
              data-testid="generate-thumbnail"
            >
              Generate Thumbnail
            </button>
            {thumbnail && (
              <img 
                src={thumbnail} 
                alt="Video thumbnail" 
                data-testid="thumbnail-image" 
              />
            )}
          </div>
        );
      };
      
      render(<ThumbnailGenerator />);
      
      // Click to generate thumbnail
      fireEvent.click(screen.getByTestId('generate-thumbnail'));
      
      await waitFor(() => {
        expect(videoService.generateThumbnail).toHaveBeenCalledWith(mockVideoFile);
      });
      
      await waitFor(() => {
        expect(screen.getByTestId('thumbnail-image')).toBeInTheDocument();
      });
      
      expect(screen.getByTestId('thumbnail-image')).toHaveAttribute(
        'src',
        'data:image/jpeg;base64,mockBase64Data'
      );
    });
    
    it('calls videoService.extractFrame at specific timestamp', async () => {
      // Mock component that extracts frames
      const FrameExtractor = () => {
        const videoRef = React.useRef(null);
        const [frame, setFrame] = React.useState(null);
        
        const handleExtractFrame = async (timeInSeconds) => {
          if (videoRef.current) {
            const frameData = await videoService.extractFrame(videoRef.current, timeInSeconds);
            setFrame(frameData);
          }
        };
        
        return (
          <div>
            <video 
              ref={videoRef} 
              src="https://example.com/test-video.mp4"
              data-testid="extract-video"
            />
            <button 
              onClick={() => handleExtractFrame(15)} 
              data-testid="extract-frame-15s"
            >
              Extract Frame at 15s
            </button>
            {frame && (
              <img 
                src={frame} 
                alt="Extracted frame" 
                data-testid="extracted-frame" 
              />
            )}
          </div>
        );
      };
      
      render(<FrameExtractor />);
      
      // Click to extract frame at 15 seconds
      fireEvent.click(screen.getByTestId('extract-frame-15s'));
      
      await waitFor(() => {
        expect(videoService.extractFrame).toHaveBeenCalledWith(
          expect.any(HTMLVideoElement),
          15
        );
      });
      
      await waitFor(() => {
        expect(screen.getByTestId('extracted-frame')).toBeInTheDocument();
      });
      
      expect(screen.getByTestId('extracted-frame')).toHaveAttribute(
        'src',
        'data:image/jpeg;base64,mockFrameData'
      );
    });
  });
  
  describe('Error Handling', () => {
    it('handles video loading errors', async () => {
      // Override the mock to simulate an error
      videoService.loadVideo.mockRejectedValueOnce(new Error('Failed to load video'));
      
      // Mock error handling component
      const VideoLoader = () => {
        const [video, setVideo] = React.useState(null);
        const [error, setError] = React.useState(null);
        
        const handleLoadVideo = async (id) => {
          try {
            setError(null);
            const videoData = await videoService.loadVideo(id);
            setVideo(videoData);
          } catch (err) {
            setError(err.message);
          }
        };
        
        return (
          <div>
            <button 
              onClick={() => handleLoadVideo('video123')} 
              data-testid="load-video"
            >
              Load Video
            </button>
            
            {error && <div data-testid="video-error">{error}</div>}
            
            {video && (
              <VideoPlayer 
                src={video.url}
                width={`${video.width / 2}px`}
                height={`${video.height / 2}px`}
              />
            )}
          </div>
        );
      };
      
      render(<VideoLoader />);
      
      // Click to load video (which will fail)
      fireEvent.click(screen.getByTestId('load-video'));
      
      await waitFor(() => {
        expect(videoService.loadVideo).toHaveBeenCalledWith('video123');
      });
      
      await waitFor(() => {
        expect(screen.getByTestId('video-error')).toBeInTheDocument();
      });
      
      expect(screen.getByTestId('video-error')).toHaveTextContent('Failed to load video');
      expect(screen.queryByTestId('video-player')).not.toBeInTheDocument();
    });
    
    it('handles thumbnail generation errors', async () => {
      // Override the mock to simulate an error
      videoService.generateThumbnail.mockRejectedValueOnce(new Error('Failed to generate thumbnail'));
      
      // Mock error handling component
      const ErrorHandlingThumbnailGenerator = () => {
        const [thumbnail, setThumbnail] = React.useState(null);
        const [error, setError] = React.useState(null);
        
        const handleGenerateThumbnail = async () => {
          try {
            setError(null);
            const mockVideoFile = new File(['mock video content'], 'test-video.mp4', { type: 'video/mp4' });
            const thumbnailUrl = await videoService.generateThumbnail(mockVideoFile);
            setThumbnail(thumbnailUrl);
          } catch (err) {
            setError(err.message);
          }
        };
        
        return (
          <div>
            <button 
              onClick={handleGenerateThumbnail} 
              data-testid="generate-thumbnail-with-error"
            >
              Generate Thumbnail
            </button>
            
            {error && <div data-testid="thumbnail-error">{error}</div>}
            
            {thumbnail && (
              <img 
                src={thumbnail} 
                alt="Video thumbnail" 
                data-testid="thumbnail-image-2" 
              />
            )}
          </div>
        );
      };
      
      render(<ErrorHandlingThumbnailGenerator />);
      
      // Click to generate thumbnail (which will fail)
      fireEvent.click(screen.getByTestId('generate-thumbnail-with-error'));
      
      await waitFor(() => {
        expect(videoService.generateThumbnail).toHaveBeenCalled();
      });
      
      await waitFor(() => {
        expect(screen.getByTestId('thumbnail-error')).toBeInTheDocument();
      });
      
      expect(screen.getByTestId('thumbnail-error')).toHaveTextContent('Failed to generate thumbnail');
      expect(screen.queryByTestId('thumbnail-image-2')).not.toBeInTheDocument();
    });
  });
  
  describe('Keyboard Controls', () => {
    it('toggles playback with Space key', () => {
      render(<VideoPlayer src="https://example.com/test-video.mp4" />);
      
      const videoContainer = screen.getByTestId('video-player');
      
      // Focus on video container
      videoContainer.focus();
      
      // Press Space key to play
      fireEvent.keyDown(videoContainer, { key: ' ', code: 'Space' });
      
      expect(screen.getByTestId('play-pause-button')).toHaveTextContent('Pause');
      
      // Press Space key again to pause
      fireEvent.keyDown(videoContainer, { key: ' ', code: 'Space' });
      
      expect(screen.getByTestId('play-pause-button')).toHaveTextContent('Play');
    });
    
    it('jumps backward with Left Arrow key', () => {
      const handleSeek = jest.fn();
      
      render(
        <VideoPlayer 
          src="https://example.com/test-video.mp4" 
          onSeek={handleSeek}
        />
      );
      
      const videoContainer = screen.getByTestId('video-player');
      const videoElement = screen.getByTestId('video-element');
      
      // Set initial time
      Object.defineProperty(videoElement, 'currentTime', {
        writable: true,
        value: 30 // 30 seconds
      });
      
      // Focus on video container
      videoContainer.focus();
      
      // Press Left Arrow key
      fireEvent.keyDown(videoContainer, { key: 'ArrowLeft', code: 'ArrowLeft' });
      
      // Should seek back 5 seconds (to 25 seconds)
      expect(handleSeek).toHaveBeenCalledWith(25);
    });
    
    it('jumps forward with Right Arrow key', () => {
      const handleSeek = jest.fn();
      
      render(
        <VideoPlayer 
          src="https://example.com/test-video.mp4" 
          onSeek={handleSeek}
        />
      );
      
      const videoContainer = screen.getByTestId('video-player');
      const videoElement = screen.getByTestId('video-element');
      
      // Set initial time
      Object.defineProperty(videoElement, 'currentTime', {
        writable: true,
        value: 30 // 30 seconds
      });
      
      // Focus on video container
      videoContainer.focus();
      
      // Press Right Arrow key
      fireEvent.keyDown(videoContainer, { key: 'ArrowRight', code: 'ArrowRight' });
      
      // Should seek forward 5 seconds (to 35 seconds)
      expect(handleSeek).toHaveBeenCalledWith(35);
    });
  });
  
  describe('Video Integration Features', () => {
    it('integrates with form checking annotations', async () => {
      // Mock form check annotations
      const mockHighlights = [
        { id: '1', timeMs: 15000, label: 'Incorrect Form', description: 'Knees too far forward' },
        { id: '2', timeMs: 45000, label: 'Good Form', description: 'Perfect squat depth' }
      ];
      
      // Mock component that displays video with annotations
      const VideoWithAnnotations = () => {
        const [selectedHighlight, setSelectedHighlight] = React.useState(null);
        
        const handleHighlightClick = (highlight) => {
          setSelectedHighlight(highlight);
          // In a real implementation, this would seek the video
          // videoRef.current.currentTime = highlight.timeMs / 1000;
        };
        
        return (
          <div>
            <VideoPlayer 
              src="https://example.com/test-video.mp4"
              testId="annotated-video" 
            />
            
            <div data-testid="highlights-container">
              <h3>Form Check Highlights</h3>
              <ul>
                {mockHighlights.map(highlight => (
                  <li 
                    key={highlight.id} 
                    data-testid={`highlight-${highlight.id}`}
                    onClick={() => handleHighlightClick(highlight)}
                  >
                    {highlight.label} at {(highlight.timeMs / 1000).toFixed(1)}s
                  </li>
                ))}
              </ul>
            </div>
            
            {selectedHighlight && (
              <div data-testid="highlight-details">
                <h4>{selectedHighlight.label}</h4>
                <p>{selectedHighlight.description}</p>
                <span>Time: {(selectedHighlight.timeMs / 1000).toFixed(1)}s</span>
              </div>
            )}
          </div>
        );
      };
      
      render(<VideoWithAnnotations />);
      
      // Verify video and highlights are rendered
      expect(screen.getByTestId('annotated-video')).toBeInTheDocument();
      expect(screen.getByTestId('highlights-container')).toBeInTheDocument();
      expect(screen.getByTestId('highlight-1')).toBeInTheDocument();
      expect(screen.getByTestId('highlight-2')).toBeInTheDocument();
      
      // Click on a highlight
      fireEvent.click(screen.getByTestId('highlight-1'));
      
      // Verify highlight details are displayed
      expect(screen.getByTestId('highlight-details')).toBeInTheDocument();
      expect(screen.getByTestId('highlight-details')).toHaveTextContent('Incorrect Form');
      expect(screen.getByTestId('highlight-details')).toHaveTextContent('Knees too far forward');
      expect(screen.getByTestId('highlight-details')).toHaveTextContent('Time: 15.0s');
    });
    
    it('loops video segments for training analysis', async () => {
      // Mock component that loops video segments
      const VideoLooper = () => {
        const videoRef = React.useRef(null);
        const [loopStart, setLoopStart] = React.useState(0);
        const [loopEnd, setLoopEnd] = React.useState(0);
        const [isLooping, setIsLooping] = React.useState(false);
        
        const handleStartLoop = () => {
          // In a real implementation, there would be a mechanism to
          // loop the video between loopStart and loopEnd times
          setIsLooping(true);
        };
        
        return (
          <div>
            <video 
              ref={videoRef}
              src="https://example.com/test-video.mp4"
              data-testid="loop-video"
            />
            
            <div>
              <label htmlFor="loop-start">Loop Start (s):</label>
              <input 
                id="loop-start"
                type="number" 
                value={loopStart}
                onChange={(e) => setLoopStart(Number(e.target.value))}
                data-testid="loop-start-input"
              />
              
              <label htmlFor="loop-end">Loop End (s):</label>
              <input 
                id="loop-end"
                type="number" 
                value={loopEnd}
                onChange={(e) => setLoopEnd(Number(e.target.value))}
                data-testid="loop-end-input"
              />
              
              <button 
                onClick={handleStartLoop}
                data-testid="start-loop-button"
              >
                Start Loop
              </button>
            </div>
            
            {isLooping && (
              <div data-testid="looping-indicator">
                Looping from {loopStart}s to {loopEnd}s
              </div>
            )}
          </div>
        );
      };
      
      render(<VideoLooper />);
      
      // Set loop start and end times
      fireEvent.change(screen.getByTestId('loop-start-input'), { target: { value: 10 } });
      fireEvent.change(screen.getByTestId('loop-end-input'), { target: { value: 20 } });
      
      // Start looping
      fireEvent.click(screen.getByTestId('start-loop-button'));
      
      // Verify looping indicator is displayed
      expect(screen.getByTestId('looping-indicator')).toBeInTheDocument();
      expect(screen.getByTestId('looping-indicator')).toHaveTextContent('Looping from 10s to 20s');
    });
  });
}); 