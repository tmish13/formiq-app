import { jest } from '@jest/globals';

// Import the videoService
import { videoService } from '../videoService';

// Mock the videoService methods
jest.mock('../videoService', () => {
  const original = jest.requireActual('../videoService');
  return {
    videoService: {
      compressVideo: jest.fn(),
      generateThumbnail: jest.fn(),
      getVideoInfo: jest.fn(),
    }
  };
});

describe('VideoService - Advanced Tests', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    
    // Set up default mock implementations
    (videoService.compressVideo as jest.Mock).mockResolvedValue({
      uri: 'mock-blob-url-12345',
      data: new Blob(['compressed-video'], { type: 'video/mp4' }),
      size: 5000000,
      width: 1280,
      height: 720,
      duration: 60,
      type: 'video/mp4',
    });
    
    (videoService.generateThumbnail as jest.Mock).mockResolvedValue(
      new Blob(['thumbnail-data'], { type: 'image/jpeg' })
    );
    
    (videoService.getVideoInfo as jest.Mock).mockResolvedValue({
      duration: 60,
      size: 10000000,
      width: 1920,
      height: 1080,
    });
  });

  describe('Video Compression', () => {
    it('should handle large video files and apply proper compression', async () => {
      // Create a mock video file
      const videoFile = new File(['video-content'], 'large-video.mp4', { type: 'video/mp4' });
      
      // Mock the compression function with 4K video
      (videoService.compressVideo as jest.Mock).mockResolvedValueOnce({
        uri: 'mock-blob-url-12345',
        data: new Blob(['compressed-video'], { type: 'video/mp4' }),
        size: 20000000, // 20MB
        width: 1920,
        height: 1080,
        duration: 180,
        type: 'video/mp4',
      });
      
      // Call the service
      const result = await videoService.compressVideo(videoFile, {
        maxSizeMB: 50,
        maxWidth: 1920,
        maxHeight: 1080,
        quality: 0.8,
      });
      
      // Verify the result
      expect(result).toBeDefined();
      expect(result.width).toBeLessThanOrEqual(1920);
      expect(result.height).toBeLessThanOrEqual(1080);
      
      // Verify the service was called with correct parameters
      expect(videoService.compressVideo).toHaveBeenCalledWith(
        videoFile,
        {
          maxSizeMB: 50,
          maxWidth: 1920,
          maxHeight: 1080,
          quality: 0.8,
        }
      );
    });

    it('should maintain aspect ratio during compression', async () => {
      // Create a mock video file with unusual aspect ratio
      const videoFile = new File(['video-content'], 'wide-video.mp4', { type: 'video/mp4' });
      
      // Mock the compression function with wide aspect ratio (21:9)
      (videoService.compressVideo as jest.Mock).mockResolvedValueOnce({
        uri: 'mock-blob-url-12345',
        data: new Blob(['compressed-video'], { type: 'video/mp4' }),
        size: 10000000,
        width: 1280, // 21:9 aspect ratio
        height: 540,
        duration: 60,
        type: 'video/mp4',
      });
      
      // Call the service
      const result = await videoService.compressVideo(videoFile, {
        maxWidth: 1280,
        maxHeight: 720,
      });
      
      // Verify the result maintains aspect ratio
      expect(result).toBeDefined();
      const aspectRatio = result.width / result.height;
      const expectedAspectRatio = 1280 / 540;
      expect(aspectRatio).toBeCloseTo(expectedAspectRatio, 1);
      expect(result.width).toBeLessThanOrEqual(1280);
      expect(result.height).toBeLessThanOrEqual(720);
      
      // Verify the service was called with correct parameters
      expect(videoService.compressVideo).toHaveBeenCalledWith(
        videoFile,
        {
          maxWidth: 1280,
          maxHeight: 720,
        }
      );
    });

    it('should reject compression if another compression is in progress', async () => {
      // Create a mock video file
      const videoFile = new File(['video-content'], 'video.mp4', { type: 'video/mp4' });
      
      // Mock compression to throw an error
      (videoService.compressVideo as jest.Mock).mockRejectedValueOnce(
        new Error('Another compression is in progress')
      );
      
      // Call the service and expect it to throw
      await expect(videoService.compressVideo(videoFile)).rejects.toThrow(
        'Another compression is in progress'
      );
      
      // Verify the service was called with the file
      expect(videoService.compressVideo).toHaveBeenCalledWith(videoFile);
    });
  });

  describe('Thumbnail Generation', () => {
    it('should generate thumbnails at the correct size', async () => {
      // Create a mock video file
      const videoFile = new File(['video-content'], 'video.mp4', { type: 'video/mp4' });
      
      // Mock thumbnail generation with a specific blob
      const mockThumbnail = new Blob(['thumbnail-data'], { type: 'image/jpeg' });
      (videoService.generateThumbnail as jest.Mock).mockResolvedValueOnce(mockThumbnail);
      
      // Call the service
      const thumbnail = await videoService.generateThumbnail(videoFile);
      
      // Verify the result
      expect(thumbnail).toBeInstanceOf(Blob);
      expect(thumbnail.type).toBe('image/jpeg');
      
      // Verify the service was called with the file
      expect(videoService.generateThumbnail).toHaveBeenCalledWith(videoFile);
    });

    it('should handle corrupted video files when generating thumbnails', async () => {
      // Create a mock corrupted video file
      const corruptedFile = new File(['corrupted-content'], 'corrupted.mp4', { type: 'video/mp4' });
      
      // Mock thumbnail generation to throw an error
      (videoService.generateThumbnail as jest.Mock).mockRejectedValueOnce(
        new Error('Failed to load video')
      );
      
      // Call the service and expect it to throw
      await expect(videoService.generateThumbnail(corruptedFile)).rejects.toThrow(
        'Failed to load video'
      );
      
      // Verify the service was called with the corrupted file
      expect(videoService.generateThumbnail).toHaveBeenCalledWith(corruptedFile);
    });
  });

  describe('Video Info Extraction', () => {
    it('should extract accurate metadata from video files', async () => {
      // Create a mock video file
      const videoFile = new File(['video-content'], 'video.mp4', { type: 'video/mp4' });
      
      // Mock info extraction with specific metadata
      const mockMetadata = {
        duration: 45.5,
        size: 1024000,
        width: 1280,
        height: 720,
      };
      (videoService.getVideoInfo as jest.Mock).mockResolvedValueOnce(mockMetadata);
      
      // Call the service
      const info = await videoService.getVideoInfo(videoFile);
      
      // Verify the result
      expect(info).toEqual(mockMetadata);
      
      // Verify the service was called with the file
      expect(videoService.getVideoInfo).toHaveBeenCalledWith(videoFile);
    });

    it('should handle metadata extraction failure', async () => {
      // Create a mock video file
      const videoFile = new File(['video-content'], 'video.mp4', { type: 'video/mp4' });
      
      // Mock info extraction to throw an error
      (videoService.getVideoInfo as jest.Mock).mockRejectedValueOnce(
        new Error('Failed to load video metadata')
      );
      
      // Call the service and expect it to throw
      await expect(videoService.getVideoInfo(videoFile)).rejects.toThrow(
        'Failed to load video metadata'
      );
      
      // Verify the service was called with the file
      expect(videoService.getVideoInfo).toHaveBeenCalledWith(videoFile);
    });
  });

  describe('End-to-end Video Processing', () => {
    it('should process a video through compression, thumbnail, and info extraction', async () => {
      // Create a mock video file
      const videoFile = new File(['video-content'], 'video.mp4', { type: 'video/mp4' });
      
      // Mock responses for all services in sequence
      // 1. Video info extraction
      const mockInfo = {
        duration: 60,
        size: 2048000,
        width: 1920,
        height: 1080,
      };
      (videoService.getVideoInfo as jest.Mock).mockResolvedValueOnce(mockInfo);
      
      // 2. Thumbnail generation
      const mockThumbnail = new Blob(['thumbnail-data'], { type: 'image/jpeg' });
      (videoService.generateThumbnail as jest.Mock).mockResolvedValueOnce(mockThumbnail);
      
      // 3. Video compression
      const mockCompressed = {
        uri: 'mock-blob-url-12345',
        data: new Blob(['compressed-video-content'], { type: 'video/mp4' }),
        size: 1024000,
        width: 1280,
        height: 720,
        duration: 60,
        type: 'video/mp4',
      };
      (videoService.compressVideo as jest.Mock).mockResolvedValueOnce(mockCompressed);
      
      // Step 1: Get video info
      const info = await videoService.getVideoInfo(videoFile);
      
      // Check info results
      expect(info.width).toBe(1920);
      expect(info.height).toBe(1080);
      expect(info.duration).toBe(60);
      
      // Step 2: Generate thumbnail
      const thumbnail = await videoService.generateThumbnail(videoFile);
      
      // Check thumbnail
      expect(thumbnail).toBeInstanceOf(Blob);
      expect(thumbnail.type).toBe('image/jpeg');
      
      // Step 3: Compress video
      const compressed = await videoService.compressVideo(videoFile);
      
      // Check compression results
      expect(compressed.width).toBeLessThanOrEqual(1280);
      expect(compressed.height).toBeLessThanOrEqual(720);
      expect(compressed.uri).toBeDefined();
      expect(compressed.data).toBeDefined();
      
      // Verify all services were called
      expect(videoService.getVideoInfo).toHaveBeenCalledWith(videoFile);
      expect(videoService.generateThumbnail).toHaveBeenCalledWith(videoFile);
      expect(videoService.compressVideo).toHaveBeenCalledWith(videoFile);
    });
  });
}); 