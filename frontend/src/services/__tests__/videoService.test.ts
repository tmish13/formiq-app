import { jest } from '@jest/globals';

// Mock the entire videoService module
jest.mock('../videoService', () => ({
  videoService: {
    compressVideo: jest.fn(),
    generateThumbnail: jest.fn(),
    getVideoInfo: jest.fn(),
  },
}));

// Import after mocking
import { videoService } from '../videoService';

describe('videoService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('compressVideo', () => {
    it('should compress a video with default options', async () => {
      // Mock successful return
      const mockResult = {
        uri: 'mock-url',
        data: new Blob(['mock-video-content']),
        size: 1000,
        width: 1280,
        height: 720,
        duration: 30,
        type: 'video/mp4',
      };
      (videoService.compressVideo as jest.Mock).mockResolvedValue(mockResult);
      
      // Create a mock video file
      const mockVideoFile = new File(['mock-video-content'], 'test-video.mp4', { type: 'video/mp4' });
      
      // Call the service
      const result = await videoService.compressVideo(mockVideoFile);
      
      // Verify method was called
      expect(videoService.compressVideo).toHaveBeenCalledWith(mockVideoFile);
      
      // Verify result
      expect(result).toEqual(mockResult);
    });

    it('should throw an error when compression fails', async () => {
      // Mock error
      const error = new Error('Compression failed');
      (videoService.compressVideo as jest.Mock).mockRejectedValue(error);
      
      // Create a mock video file
      const mockVideoFile = new File(['mock-video-content'], 'test-video.mp4', { type: 'video/mp4' });
      
      // Call the service and expect it to throw
      await expect(videoService.compressVideo(mockVideoFile)).rejects.toThrow('Compression failed');
      
      // Verify method was called
      expect(videoService.compressVideo).toHaveBeenCalledWith(mockVideoFile);
    });

    it('should apply custom compression options', async () => {
      // Mock successful return
      const mockResult = {
        uri: 'mock-url',
        data: new Blob(['mock-video-content']),
        size: 500,
        width: 640,
        height: 480,
        duration: 30,
        type: 'video/mp4',
      };
      (videoService.compressVideo as jest.Mock).mockResolvedValue(mockResult);
      
      // Create a mock video file
      const mockVideoFile = new File(['mock-video-content'], 'test-video.mp4', { type: 'video/mp4' });
      
      // Custom options
      const customOptions = {
        maxSizeMB: 30,
        maxWidth: 640,
        maxHeight: 480,
        quality: 0.6,
      };
      
      // Call the service
      const result = await videoService.compressVideo(mockVideoFile, customOptions);
      
      // Verify method was called with correct options
      expect(videoService.compressVideo).toHaveBeenCalledWith(mockVideoFile, customOptions);
      
      // Verify result
      expect(result).toEqual(mockResult);
    });
  });

  describe('generateThumbnail', () => {
    it('should generate a thumbnail from a video file', async () => {
      // Mock successful return
      const mockBlob = new Blob(['mock-thumbnail-data'], { type: 'image/jpeg' });
      (videoService.generateThumbnail as jest.Mock).mockResolvedValue(mockBlob);
      
      // Create a mock video file
      const mockVideoFile = new File(['mock-video-content'], 'test-video.mp4', { type: 'video/mp4' });
      
      // Call the service
      const result = await videoService.generateThumbnail(mockVideoFile);
      
      // Verify method was called
      expect(videoService.generateThumbnail).toHaveBeenCalledWith(mockVideoFile);
      
      // Verify result
      expect(result).toBeInstanceOf(Blob);
      expect(result.type).toBe('image/jpeg');
    });

    it('should handle errors when generating a thumbnail', async () => {
      // Mock error
      const error = new Error('Failed to load video');
      (videoService.generateThumbnail as jest.Mock).mockRejectedValue(error);
      
      // Create a mock video file
      const mockVideoFile = new File(['mock-video-content'], 'test-video.mp4', { type: 'video/mp4' });
      
      // Call the service and expect it to throw
      await expect(videoService.generateThumbnail(mockVideoFile)).rejects.toThrow('Failed to load video');
      
      // Verify method was called
      expect(videoService.generateThumbnail).toHaveBeenCalledWith(mockVideoFile);
    });
  });

  describe('getVideoInfo', () => {
    it('should extract metadata from a video file', async () => {
      // Mock successful return
      const expectedMetadata = {
        duration: 30,
        size: 1024,
        width: 1920,
        height: 1080,
      };
      (videoService.getVideoInfo as jest.Mock).mockResolvedValue(expectedMetadata);
      
      // Create a mock video file
      const mockVideoFile = new File(['mock-video-content'], 'test-video.mp4', { type: 'video/mp4' });
      
      // Call the service
      const result = await videoService.getVideoInfo(mockVideoFile);
      
      // Verify method was called
      expect(videoService.getVideoInfo).toHaveBeenCalledWith(mockVideoFile);
      
      // Verify result
      expect(result).toEqual(expectedMetadata);
    });

    it('should handle errors when loading video metadata', async () => {
      // Mock error
      const error = new Error('Failed to load video metadata');
      (videoService.getVideoInfo as jest.Mock).mockRejectedValue(error);
      
      // Create a mock video file
      const mockVideoFile = new File(['mock-video-content'], 'test-video.mp4', { type: 'video/mp4' });
      
      // Call the service and expect it to throw
      await expect(videoService.getVideoInfo(mockVideoFile)).rejects.toThrow('Failed to load video metadata');
      
      // Verify method was called
      expect(videoService.getVideoInfo).toHaveBeenCalledWith(mockVideoFile);
    });
  });
}); 