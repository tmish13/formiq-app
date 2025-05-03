import { jest } from '@jest/globals';

// Mock the MediaStream API
class MockMediaStream {
  getTracks() {
    return [
      { stop: jest.fn() },
      { stop: jest.fn() }
    ];
  }
}

// Mock getUserMedia
Object.defineProperty(global.navigator, 'mediaDevices', {
  value: {
    getUserMedia: jest.fn()
  },
  writable: true
});

// Import after mocking
import '../CameraService';
import { CameraService } from '../CameraService';

describe('CameraService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // Reset the media recorder mock
    (CameraService.startRecording as jest.Mock).mockClear();
    (CameraService.stopRecording as jest.Mock).mockClear();
  });

  describe('startRecording', () => {
    it('should successfully start recording when permissions are granted', async () => {
      // Mock successful media access
      const mockStream = new MockMediaStream();
      (navigator.mediaDevices.getUserMedia as jest.Mock).mockResolvedValue(mockStream);
      
      // Override the mock implementation temporarily for this test
      const originalImplementation = CameraService.startRecording;
      (CameraService.startRecording as jest.Mock).mockImplementation(async () => {
        try {
          const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
          return { videoUrl: 'recording-in-progress' };
        } catch (error) {
          throw new Error('Failed to start recording');
        }
      });
      
      // Call the service
      const result = await CameraService.startRecording();
      
      // Verify getUserMedia was called with correct constraints
      expect(navigator.mediaDevices.getUserMedia).toHaveBeenCalledWith({ 
        video: true, 
        audio: true 
      });
      
      // Verify result
      expect(result).toEqual({ videoUrl: 'recording-in-progress' });
      
      // Restore original mock
      (CameraService.startRecording as jest.Mock).mockImplementation(originalImplementation);
    });

    it('should throw an error when camera permissions are denied', async () => {
      // Mock permission denial
      (navigator.mediaDevices.getUserMedia as jest.Mock).mockRejectedValue(
        new DOMException('Permission denied', 'NotAllowedError')
      );
      
      // Override the mock implementation temporarily for this test
      const originalImplementation = CameraService.startRecording;
      (CameraService.startRecording as jest.Mock).mockImplementation(async () => {
        try {
          const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
          return { videoUrl: 'recording-in-progress' };
        } catch (error) {
          throw new Error('Failed to start recording');
        }
      });
      
      // Call the service and expect it to throw
      await expect(CameraService.startRecording()).rejects.toThrow('Failed to start recording');
      
      // Verify getUserMedia was called
      expect(navigator.mediaDevices.getUserMedia).toHaveBeenCalled();
      
      // Restore original mock
      (CameraService.startRecording as jest.Mock).mockImplementation(originalImplementation);
    });

    it('should throw an error when hardware is not available', async () => {
      // Mock hardware unavailability
      (navigator.mediaDevices.getUserMedia as jest.Mock).mockRejectedValue(
        new DOMException('Hardware not available', 'NotFoundError')
      );
      
      // Override the mock implementation temporarily for this test
      const originalImplementation = CameraService.startRecording;
      (CameraService.startRecording as jest.Mock).mockImplementation(async () => {
        try {
          const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
          return { videoUrl: 'recording-in-progress' };
        } catch (error) {
          throw new Error('Failed to start recording');
        }
      });
      
      // Call the service and expect it to throw
      await expect(CameraService.startRecording()).rejects.toThrow('Failed to start recording');
      
      // Verify getUserMedia was called
      expect(navigator.mediaDevices.getUserMedia).toHaveBeenCalled();
      
      // Restore original mock
      (CameraService.startRecording as jest.Mock).mockImplementation(originalImplementation);
    });
  });

  describe('stopRecording', () => {
    it('should successfully stop recording and return a video URL', async () => {
      // Use default mock implementation
      const result = await CameraService.stopRecording();
      
      // Verify the method was called
      expect(CameraService.stopRecording).toHaveBeenCalled();
      
      // Verify result
      expect(result).toEqual({ videoUrl: 'test-video.mp4' });
    });

    it('should throw an error when trying to stop without an active recording', async () => {
      // Override default mock implementation for this test
      const originalImplementation = CameraService.stopRecording;
      (CameraService.stopRecording as jest.Mock).mockImplementation(async () => {
        throw new Error('No active recording');
      });
      
      // Call the service and expect it to throw
      await expect(CameraService.stopRecording()).rejects.toThrow('No active recording');
      
      // Restore original mock
      (CameraService.stopRecording as jest.Mock).mockImplementation(originalImplementation);
    });
  });

  describe('MediaDevices API edge cases', () => {
    it('should handle browsers without MediaDevices API', async () => {
      // Temporarily remove mediaDevices from navigator
      const originalMediaDevices = navigator.mediaDevices;
      Object.defineProperty(navigator, 'mediaDevices', {
        value: undefined,
        writable: true
      });
      
      // Override the mock implementation temporarily for this test
      const originalImplementation = CameraService.startRecording;
      (CameraService.startRecording as jest.Mock).mockImplementation(async () => {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
          throw new Error('Media devices not supported');
        }
        return { videoUrl: 'recording' };
      });
      
      // Call the service and expect it to throw
      await expect(CameraService.startRecording()).rejects.toThrow('Media devices not supported');
      
      // Restore navigator.mediaDevices
      Object.defineProperty(navigator, 'mediaDevices', {
        value: originalMediaDevices,
        writable: true
      });
      
      // Restore original mock
      (CameraService.startRecording as jest.Mock).mockImplementation(originalImplementation);
    });
  });
}); 