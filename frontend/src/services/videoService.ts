import { Platform } from 'react-native';

interface VideoCompressionOptions {
  maxSizeMB?: number;
  maxWidth?: number;
  maxHeight?: number;
  quality?: number;
}

interface CompressedVideo {
  uri: string;
  data: Blob;
  size: number;
  width: number;
  height: number;
  duration: number;
  type: string;
}

class VideoService {
  private static instance: VideoService;
  private compressionInProgress: boolean = false;

  private constructor() {}

  public static getInstance(): VideoService {
    if (!VideoService.instance) {
      VideoService.instance = new VideoService();
    }
    return VideoService.instance;
  }

  public async compressVideo(
    videoFile: File,
    options: VideoCompressionOptions = {}
  ): Promise<CompressedVideo> {
    if (this.compressionInProgress) {
      throw new Error('Another compression is in progress');
    }

    this.compressionInProgress = true;

    try {
      const defaultOptions: VideoCompressionOptions = {
        maxSizeMB: 50,
        maxWidth: 1280,
        maxHeight: 720,
        quality: 0.8,
        ...options,
      };

      // Create a video element to get video metadata
      const video = document.createElement('video');
      video.preload = 'metadata';
      
      // Create a promise to handle video metadata loading
      const metadataPromise = new Promise<{width: number, height: number, duration: number}>((resolve, reject) => {
        video.onloadedmetadata = () => {
          resolve({
            width: video.videoWidth,
            height: video.videoHeight,
            duration: video.duration
          });
        };
        video.onerror = () => reject(new Error('Failed to load video metadata'));
      });
      
      // Set video source and load metadata
      video.src = URL.createObjectURL(videoFile);
      const metadata = await metadataPromise;
      
      // Calculate target dimensions while maintaining aspect ratio
      const aspectRatio = metadata.width / metadata.height;
      let targetWidth = metadata.width;
      let targetHeight = metadata.height;
      
      if (targetWidth > defaultOptions.maxWidth!) {
        targetWidth = defaultOptions.maxWidth!;
        targetHeight = Math.round(targetWidth / aspectRatio);
      }
      
      if (targetHeight > defaultOptions.maxHeight!) {
        targetHeight = defaultOptions.maxHeight!;
        targetWidth = Math.round(targetHeight * aspectRatio);
      }
      
      // Create a canvas for video frame extraction
      const canvas = document.createElement('canvas');
      canvas.width = targetWidth;
      canvas.height = targetHeight;
      const ctx = canvas.getContext('2d');
      
      if (!ctx) {
        throw new Error('Failed to get canvas context');
      }
      
      // Draw the first frame to the canvas
      video.currentTime = 0;
      await new Promise<void>((resolve) => {
        video.onseeked = () => {
          ctx.drawImage(video, 0, 0, targetWidth, targetHeight);
          resolve();
        };
      });
      
      // Generate thumbnail from the first frame
      const thumbnailBlob = await new Promise<Blob>((resolve) => {
        canvas.toBlob((blob) => {
          resolve(blob as Blob);
        }, 'image/jpeg', 0.8);
      });
      
      // For actual video compression, we would use a WebAssembly-based solution
      // For now, we'll just return the original video with metadata
      // In a real implementation, you would use a library like ffmpeg.wasm
      
      return {
        uri: URL.createObjectURL(videoFile),
        data: videoFile,
        size: videoFile.size,
        width: targetWidth,
        height: targetHeight,
        duration: metadata.duration,
        type: videoFile.type,
      };
    } finally {
      this.compressionInProgress = false;
    }
  }

  public async generateThumbnail(videoFile: File): Promise<Blob> {
    // Create a video element
    const video = document.createElement('video');
    video.preload = 'metadata';
    
    // Create a promise to handle video loading
    const loadPromise = new Promise<void>((resolve, reject) => {
      video.onloadeddata = () => resolve();
      video.onerror = () => reject(new Error('Failed to load video'));
    });
    
    // Set video source and load
    video.src = URL.createObjectURL(videoFile);
    await loadPromise;
    
    // Create a canvas for thumbnail
    const canvas = document.createElement('canvas');
    canvas.width = 320; // Thumbnail width
    canvas.height = 180; // Thumbnail height (16:9 aspect ratio)
    const ctx = canvas.getContext('2d');
    
    if (!ctx) {
      throw new Error('Failed to get canvas context');
    }
    
    // Draw the first frame to the canvas
    video.currentTime = 0;
    await new Promise<void>((resolve) => {
      video.onseeked = () => {
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        resolve();
      };
    });
    
    // Convert canvas to blob
    return new Promise<Blob>((resolve) => {
      canvas.toBlob((blob) => {
        resolve(blob as Blob);
      }, 'image/jpeg', 0.8);
    });
  }

  public async getVideoInfo(videoFile: File): Promise<{
    duration: number;
    size: number;
    width: number;
    height: number;
  }> {
    // Create a video element
    const video = document.createElement('video');
    video.preload = 'metadata';
    
    // Create a promise to handle video metadata loading
    const metadataPromise = new Promise<{width: number, height: number, duration: number}>((resolve, reject) => {
      video.onloadedmetadata = () => {
        resolve({
          width: video.videoWidth,
          height: video.videoHeight,
          duration: video.duration
        });
      };
      video.onerror = () => reject(new Error('Failed to load video metadata'));
    });
    
    // Set video source and load metadata
    video.src = URL.createObjectURL(videoFile);
    const metadata = await metadataPromise;
    
    return {
      duration: metadata.duration,
      size: videoFile.size,
      width: metadata.width,
      height: metadata.height,
    };
  }
}

export const videoService = VideoService.getInstance(); 