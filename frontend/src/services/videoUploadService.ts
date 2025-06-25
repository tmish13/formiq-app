import apiService from './apiService';
import { videoService } from './videoService';

export interface VideoUploadProgress {
  stage: 'preparing' | 'uploading' | 'processing' | 'analyzing' | 'completed' | 'error';
  progress: number;
  message: string;
  videoId?: string;
  error?: string;
}

export interface VideoUploadOptions {
  exerciseId?: string;
  exerciseName?: string;
  onProgress?: (progress: VideoUploadProgress) => void;
  onStatusUpdate?: (status: any) => void;
}

class VideoUploadService {
  private static instance: VideoUploadService;
  private activeUploads: Map<string, AbortController> = new Map();

  private constructor() {}

  public static getInstance(): VideoUploadService {
    if (!VideoUploadService.instance) {
      VideoUploadService.instance = new VideoUploadService();
    }
    return VideoUploadService.instance;
  }

  /**
   * Upload video using backend Phase 1.0 pipeline
   */
  public async uploadVideo(
    file: File,
    options: VideoUploadOptions = {}
  ): Promise<string> {
    const uploadId = this.generateUploadId();
    const abortController = new AbortController();
    this.activeUploads.set(uploadId, abortController);

    try {
      // Stage 1: Prepare and validate video
      this.updateProgress(options.onProgress, {
        stage: 'preparing',
        progress: 10,
        message: 'Preparing video for upload...'
      });

      // Get video metadata
      const videoInfo = await videoService.getVideoInfo(file);
      
      // Validate video
      this.validateVideo(file, videoInfo);

      // Stage 2: Get presigned upload URL from backend
      this.updateProgress(options.onProgress, {
        stage: 'preparing',
        progress: 20,
        message: 'Getting upload URL...'
      });

      const uploadData = await apiService.getVideoUploadUrl({
        filename: file.name,
        contentType: file.type,
        exerciseId: options.exerciseId,
        userId: 'current-user' // This would come from auth context
      });

      // Stage 3: Upload to S3
      this.updateProgress(options.onProgress, {
        stage: 'uploading',
        progress: 30,
        message: 'Uploading video...',
        videoId: uploadData.videoId
      });

      await this.uploadToS3(
        uploadData.uploadUrl,
        file,
        uploadData.fields,
        (progress) => {
          this.updateProgress(options.onProgress, {
            stage: 'uploading',
            progress: 30 + (progress * 0.4), // 30% to 70%
            message: `Uploading video... ${Math.round(progress)}%`,
            videoId: uploadData.videoId
          });
        }
      );

      // Stage 4: Confirm upload completion
      this.updateProgress(options.onProgress, {
        stage: 'uploading',
        progress: 70,
        message: 'Confirming upload...',
        videoId: uploadData.videoId
      });

      await apiService.confirmVideoUpload(uploadData.videoId, {
        duration: videoInfo.duration,
        size: videoInfo.size,
        width: videoInfo.width,
        height: videoInfo.height
      });

      // Stage 5: Upload complete, processing will continue in background
      this.updateProgress(options.onProgress, {
        stage: 'processing',
        progress: 75,
        message: 'Upload complete! Processing will continue...',
        videoId: uploadData.videoId
      });

      // Return video ID immediately for navigation to processing page
      // Background processing will be monitored by ProcessingProgressPage
      return uploadData.videoId;

    } catch (error) {
      console.error('Video upload failed:', error);
      this.updateProgress(options.onProgress, {
        stage: 'error',
        progress: 0,
        message: 'Upload failed',
        error: error instanceof Error ? error.message : 'Unknown error'
      });
      throw error;
    } finally {
      this.activeUploads.delete(uploadId);
    }
  }

  /**
   * Cancel active upload
   */
  public cancelUpload(uploadId: string): void {
    const controller = this.activeUploads.get(uploadId);
    if (controller) {
      controller.abort();
      this.activeUploads.delete(uploadId);
    }
  }

  private validateVideo(file: File, info: any): void {
    // Check file size (max 100MB)
    const maxSize = 100 * 1024 * 1024;
    if (file.size > maxSize) {
      throw new Error('Video file too large. Maximum size is 100MB.');
    }

    // Check duration (max 10 minutes)
    if (info.duration > 600) {
      throw new Error('Video too long. Maximum duration is 10 minutes.');
    }

    // Check file type
    const allowedTypes = ['video/mp4', 'video/webm', 'video/quicktime'];
    if (!allowedTypes.includes(file.type)) {
      throw new Error('Unsupported video format. Please use MP4, WebM, or MOV.');
    }
  }

  private async uploadToS3(
    uploadUrl: string,
    file: File,
    fields?: Record<string, string>,
    onProgress?: (progress: number) => void
  ): Promise<void> {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      const formData = new FormData();

      // Add fields first
      if (fields) {
        Object.entries(fields).forEach(([key, value]) => {
          formData.append(key, value);
        });
      }

      // Add file last
      formData.append('file', file);

      xhr.upload.addEventListener('progress', (event) => {
        if (event.lengthComputable && onProgress) {
          const progress = (event.loaded / event.total) * 100;
          onProgress(progress);
        }
      });

      xhr.addEventListener('load', () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve();
        } else {
          reject(new Error(`Upload failed with status ${xhr.status}`));
        }
      });

      xhr.addEventListener('error', () => {
        reject(new Error('Upload failed due to network error'));
      });

      xhr.addEventListener('abort', () => {
        reject(new Error('Upload was cancelled'));
      });

      xhr.open('POST', uploadUrl);
      xhr.send(formData);
    });
  }

  private async pollProcessingStatus(
    videoId: string,
    onProgress?: (progress: VideoUploadProgress) => void,
    onStatusUpdate?: (status: any) => void
  ): Promise<void> {
    const maxAttempts = 60; // 5 minutes with 5-second intervals
    let attempts = 0;

    while (attempts < maxAttempts) {
      try {
        const status = await apiService.getVideoStatus(videoId);
        
        if (onStatusUpdate) {
          onStatusUpdate(status);
        }

        switch (status.status) {
          case 'processing':
            this.updateProgress(onProgress, {
              stage: 'processing',
              progress: 75 + (attempts / maxAttempts) * 15, // 75% to 90%
              message: 'Processing video frames...',
              videoId
            });
            break;

          case 'analyzing':
            this.updateProgress(onProgress, {
              stage: 'analyzing',
              progress: 90 + (attempts / maxAttempts) * 8, // 90% to 98%
              message: 'Analyzing form with AI...',
              videoId
            });
            break;

          case 'completed':
            this.updateProgress(onProgress, {
              stage: 'completed',
              progress: 100,
              message: 'Analysis complete!',
              videoId
            });
            return;

          case 'failed':
            throw new Error(status.error || 'Video processing failed');
        }

        // Wait 5 seconds before next poll
        await new Promise(resolve => setTimeout(resolve, 5000));
        attempts++;

      } catch (error) {
        console.error('Error polling status:', error);
        attempts++;
        await new Promise(resolve => setTimeout(resolve, 5000));
      }
    }

    throw new Error('Processing timeout - please check back later');
  }

  private updateProgress(
    onProgress?: (progress: VideoUploadProgress) => void,
    progress: VideoUploadProgress
  ): void {
    if (onProgress) {
      onProgress(progress);
    }
  }

  private generateUploadId(): string {
    return `upload_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * Get upload history
   */
  public async getUploadHistory(): Promise<any[]> {
    try {
      const response = await apiService.get('/videos');
      return response.data || [];
    } catch (error) {
      console.error('Failed to fetch upload history:', error);
      return [];
    }
  }

  /**
   * Check if video is ready for analysis
   */
  public async isVideoReady(videoId: string): Promise<boolean> {
    try {
      const status = await apiService.getVideoStatus(videoId);
      return status.status === 'completed';
    } catch (error) {
      console.error('Failed to check video status:', error);
      return false;
    }
  }
}

export const videoUploadService = VideoUploadService.getInstance();