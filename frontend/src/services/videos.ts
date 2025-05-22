import { apiService } from './api';

export interface Video {
  id: string;
  user_id: string;
  filename: string;
  url: string;
  status: VideoStatus;
  size?: number;
  mime_type: string;
  created_at: string;
  updated_at: string;
}

export enum VideoStatus {
  PENDING = 'pending',
  PROCESSING = 'processing',
  READY = 'ready',
  FAILED = 'failed',
  DELETED = 'deleted',
}

export interface PresignedUploadResponse {
  upload_url: string;
  video_id: string;
  object_key: string;
  expires_in: number;
  fields: Record<string, string>;
}

export interface VideoUploadParams {
  filename: string;
  content_type: string;
  metadata?: Record<string, any>;
}

export interface VideoListParams {
  skip?: number;
  limit?: number;
  status?: VideoStatus;
}

class VideoService {
  /**
   * Get a presigned URL for direct video upload to S3
   */
  async getPresignedUploadUrl(params: VideoUploadParams): Promise<PresignedUploadResponse> {
    const response = await apiService.post('/videos/upload/signed-url', params);
    return response.data;
  }

  /**
   * Confirm that a video has been successfully uploaded to S3
   */
  async confirmUpload(videoId: string, objectKey: string, size?: number): Promise<Video> {
    const response = await apiService.post('/videos/upload/confirm', {
      video_id: videoId,
      object_key: objectKey,
      size,
    });
    return response.data;
  }

  /**
   * Get a list of videos
   */
  async listVideos(params?: VideoListParams): Promise<Video[]> {
    const response = await apiService.get('/videos', { params });
    return response.data;
  }

  /**
   * Get a specific video by ID
   */
  async getVideo(videoId: string): Promise<Video> {
    const response = await apiService.get(`/videos/${videoId}`);
    return response.data;
  }

  /**
   * Delete a video
   */
  async deleteVideo(videoId: string): Promise<void> {
    await apiService.delete(`/videos/${videoId}`);
  }
  
  /**
   * Upload a video file directly to S3 with progress tracking
   * 
   * @returns A promise that resolves with the uploaded video data
   */
  async uploadVideo(
    file: File, 
    onProgress?: (progress: number) => void
  ): Promise<Video> {
    if (!file) {
      throw new Error('No file provided');
    }
    
    // Step 1: Get a presigned URL
    const presignedData = await this.getPresignedUploadUrl({
      filename: file.name,
      content_type: file.type,
    });
    
    // Step 2: Upload the file to S3 using the presigned URL
    await this.uploadFileWithXhr(
      presignedData.upload_url,
      file,
      onProgress
    );
    
    // Step 3: Confirm the upload with our backend
    return await this.confirmUpload(
      presignedData.video_id,
      presignedData.object_key,
      file.size
    );
  }
  
  /**
   * Helper method to upload a file using XMLHttpRequest for progress tracking
   */
  private uploadFileWithXhr(
    url: string,
    file: File,
    onProgress?: (progress: number) => void
  ): Promise<void> {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      
      // Set up progress tracking
      if (onProgress) {
        xhr.upload.addEventListener('progress', (event) => {
          if (event.lengthComputable) {
            const progress = Math.round((event.loaded / event.total) * 100);
            onProgress(progress);
          }
        });
      }
      
      xhr.addEventListener('load', () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve();
        } else {
          reject(new Error(`Upload failed with status ${xhr.status}`));
        }
      });
      
      xhr.addEventListener('error', () => {
        reject(new Error('Network error occurred during upload'));
      });
      
      xhr.addEventListener('abort', () => {
        reject(new Error('Upload was cancelled'));
      });
      
      xhr.open('PUT', url);
      xhr.setRequestHeader('Content-Type', file.type);
      xhr.send(file);
    });
  }
}

export const videoService = new VideoService(); 