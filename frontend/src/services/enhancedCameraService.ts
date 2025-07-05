import { Camera, CameraResultType, CameraSource, Photo } from '@capacitor/camera';
import { Capacitor } from '@capacitor/core';
import { Filesystem, Directory, Encoding } from '@capacitor/filesystem';
import { mobileService } from './mobileService';

export interface CameraOptions {
  quality?: number;
  width?: number;
  height?: number;
  allowEditing?: boolean;
  saveToGallery?: boolean;
  source?: 'camera' | 'gallery' | 'prompt';
  direction?: 'front' | 'rear';
}

export interface VideoRecordingOptions {
  maxDuration?: number; // in seconds
  quality?: 'low' | 'medium' | 'high';
  stabilization?: boolean;
  flashMode?: 'auto' | 'on' | 'off';
}

export interface RecordingSession {
  id: string;
  startTime: number;
  duration: number;
  isRecording: boolean;
  isPaused: boolean;
  file?: File;
  thumbnail?: string;
}

/**
 * Enhanced camera service with advanced mobile features
 */
export class EnhancedCameraService {
  private static instance: EnhancedCameraService;
  private currentSession: RecordingSession | null = null;
  private permissionsGranted = false;

  private constructor() {}

  public static getInstance(): EnhancedCameraService {
    if (!EnhancedCameraService.instance) {
      EnhancedCameraService.instance = new EnhancedCameraService();
    }
    return EnhancedCameraService.instance;
  }

  /**
   * Check and request camera permissions
   */
  public async checkPermissions(): Promise<boolean> {
    if (!Capacitor.isNativePlatform()) {
      return true; // Web doesn't need explicit permission check
    }

    try {
      const permissions = await Camera.checkPermissions();
      
      if (permissions.camera === 'granted') {
        this.permissionsGranted = true;
        return true;
      }

      if (permissions.camera === 'prompt' || permissions.camera === 'prompt-with-rationale') {
        const result = await Camera.requestPermissions();
        this.permissionsGranted = result.camera === 'granted';
        return this.permissionsGranted;
      }

      this.permissionsGranted = false;
      return false;
    } catch (error) {
      console.error('Camera permission check failed:', error);
      return false;
    }
  }

  /**
   * Take a photo with enhanced options
   */
  public async takePhoto(options: CameraOptions = {}): Promise<Photo | null> {
    const hasPermissions = await this.checkPermissions();
    if (!hasPermissions) {
      throw new Error('Camera permissions not granted');
    }

    try {
      await mobileService.hapticFeedback('light');

      const photo = await Camera.getPhoto({
        quality: options.quality || 90,
        width: options.width,
        height: options.height,
        allowEditing: options.allowEditing || false,
        resultType: CameraResultType.Uri,
        source: this.mapCameraSource(options.source),
        saveToGallery: options.saveToGallery || false,
        correctOrientation: true
      });

      await mobileService.hapticFeedback('medium');
      return photo;
    } catch (error) {
      console.error('Failed to take photo:', error);
      throw error;
    }
  }

  /**
   * Start video recording session
   */
  public async startVideoRecording(options: VideoRecordingOptions = {}): Promise<string> {
    const hasPermissions = await this.checkPermissions();
    if (!hasPermissions) {
      throw new Error('Camera permissions not granted');
    }

    if (this.currentSession?.isRecording) {
      throw new Error('Recording already in progress');
    }

    const sessionId = `recording_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    
    this.currentSession = {
      id: sessionId,
      startTime: Date.now(),
      duration: 0,
      isRecording: true,
      isPaused: false
    };

    // Provide haptic feedback
    await mobileService.hapticFeedback('medium');

    // Start platform-specific recording
    if (Capacitor.isNativePlatform()) {
      await this.startNativeVideoRecording(options);
    } else {
      await this.startWebVideoRecording(options);
    }

    return sessionId;
  }

  /**
   * Stop video recording and return file
   */
  public async stopVideoRecording(): Promise<{ file: File; thumbnail?: string } | null> {
    if (!this.currentSession?.isRecording) {
      throw new Error('No recording in progress');
    }

    await mobileService.hapticFeedback('heavy');

    try {
      let result: { file: File; thumbnail?: string };

      if (Capacitor.isNativePlatform()) {
        result = await this.stopNativeVideoRecording();
      } else {
        result = await this.stopWebVideoRecording();
      }

      this.currentSession.isRecording = false;
      this.currentSession.file = result.file;
      this.currentSession.thumbnail = result.thumbnail;

      return result;
    } catch (error) {
      console.error('Failed to stop recording:', error);
      this.currentSession = null;
      throw error;
    }
  }

  /**
   * Pause video recording
   */
  public async pauseVideoRecording(): Promise<void> {
    if (!this.currentSession?.isRecording || this.currentSession.isPaused) {
      return;
    }

    this.currentSession.isPaused = true;
    await mobileService.hapticFeedback('light');

    // Platform-specific pause logic would go here
    console.log('Video recording paused');
  }

  /**
   * Resume video recording
   */
  public async resumeVideoRecording(): Promise<void> {
    if (!this.currentSession?.isRecording || !this.currentSession.isPaused) {
      return;
    }

    this.currentSession.isPaused = false;
    await mobileService.hapticFeedback('light');

    // Platform-specific resume logic would go here
    console.log('Video recording resumed');
  }

  /**
   * Get current recording session info
   */
  public getCurrentSession(): RecordingSession | null {
    return this.currentSession;
  }

  /**
   * Check if currently recording
   */
  public isRecording(): boolean {
    return this.currentSession?.isRecording || false;
  }

  /**
   * Map camera source option to Capacitor enum
   */
  private mapCameraSource(source?: 'camera' | 'gallery' | 'prompt'): CameraSource {
    switch (source) {
      case 'camera':
        return CameraSource.Camera;
      case 'gallery':
        return CameraSource.Photos;
      case 'prompt':
      default:
        return CameraSource.Prompt;
    }
  }

  /**
   * Start native video recording (iOS/Android)
   */
  private async startNativeVideoRecording(options: VideoRecordingOptions): Promise<void> {
    // This would use a native video recording plugin
    // For now, we'll simulate the process
    console.log('Starting native video recording with options:', options);
    
    // You would integrate with plugins like:
    // - @capacitor-community/camera-preview
    // - @capacitor-community/media
    // - Custom native video recording plugin
  }

  /**
   * Stop native video recording
   */
  private async stopNativeVideoRecording(): Promise<{ file: File; thumbnail?: string }> {
    console.log('Stopping native video recording');
    
    // This would return the actual recorded video file
    // For now, return a mock File object
    const mockBlob = new Blob(['mock video data'], { type: 'video/mp4' });
    const file = new File([mockBlob], `video_${Date.now()}.mp4`, { type: 'video/mp4' });
    
    return { 
      file,
      thumbnail: 'data:image/jpeg;base64,mock_thumbnail_data'
    };
  }

  /**
   * Start web-based video recording
   */
  private async startWebVideoRecording(options: VideoRecordingOptions): Promise<void> {
    try {
      const constraints = {
        video: {
          width: { ideal: 1920 },
          height: { ideal: 1080 },
          frameRate: { ideal: 30 },
          facingMode: 'user'
        },
        audio: true
      };

      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      
      // Store stream reference for stopping later
      (this.currentSession as any).stream = stream;
      
      console.log('Web video recording started');
    } catch (error) {
      console.error('Failed to start web video recording:', error);
      throw error;
    }
  }

  /**
   * Stop web-based video recording
   */
  private async stopWebVideoRecording(): Promise<{ file: File; thumbnail?: string }> {
    const stream = (this.currentSession as any)?.stream;
    
    if (stream) {
      stream.getTracks().forEach((track: MediaStreamTrack) => track.stop());
    }

    // Create mock file for now - in real implementation, you'd use MediaRecorder
    const mockBlob = new Blob(['mock video data'], { type: 'video/webm' });
    const file = new File([mockBlob], `video_${Date.now()}.webm`, { type: 'video/webm' });

    return { file };
  }

  /**
   * Create video thumbnail
   */
  public async createThumbnail(videoFile: File): Promise<string> {
    return new Promise((resolve, reject) => {
      const video = document.createElement('video');
      video.src = URL.createObjectURL(videoFile);
      video.muted = true;
      
      video.onloadeddata = () => {
        video.currentTime = 1; // Get frame at 1 second
        
        video.onseeked = () => {
          const canvas = document.createElement('canvas');
          canvas.width = video.videoWidth;
          canvas.height = video.videoHeight;
          
          const ctx = canvas.getContext('2d');
          if (ctx) {
            ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
            const thumbnail = canvas.toDataURL('image/jpeg', 0.7);
            resolve(thumbnail);
          } else {
            reject(new Error('Failed to create canvas context'));
          }
          
          URL.revokeObjectURL(video.src);
        };
      };
      
      video.onerror = () => {
        reject(new Error('Failed to load video'));
        URL.revokeObjectURL(video.src);
      };
    });
  }

  /**
   * Optimize video for upload
   */
  public async optimizeVideo(file: File, quality: 'low' | 'medium' | 'high' = 'medium'): Promise<File> {
    // This would use video compression techniques
    // For now, return the original file
    console.log(`Optimizing video with ${quality} quality`);
    return file;
  }

  /**
   * Get camera capabilities
   */
  public async getCameraCapabilities(): Promise<{
    hasFlash: boolean;
    hasFrontCamera: boolean;
    hasRearCamera: boolean;
    supportsVideoRecording: boolean;
    maxResolution: { width: number; height: number };
  }> {
    const defaultCapabilities = {
      hasFlash: false,
      hasFrontCamera: true,
      hasRearCamera: true,
      supportsVideoRecording: true,
      maxResolution: { width: 1920, height: 1080 }
    };

    if (!Capacitor.isNativePlatform()) {
      // For web, check MediaDevices API
      try {
        const devices = await navigator.mediaDevices.enumerateDevices();
        const cameras = devices.filter(device => device.kind === 'videoinput');
        
        return {
          ...defaultCapabilities,
          hasFrontCamera: cameras.some(cam => cam.label.toLowerCase().includes('front')),
          hasRearCamera: cameras.some(cam => cam.label.toLowerCase().includes('back'))
        };
      } catch (error) {
        console.warn('Failed to enumerate camera devices:', error);
      }
    }

    return defaultCapabilities;
  }

  /**
   * Save video to device gallery
   */
  public async saveToGallery(file: File, albumName: string = 'FormIQ'): Promise<boolean> {
    if (!Capacitor.isNativePlatform()) {
      // For web, trigger download
      const url = URL.createObjectURL(file);
      const a = document.createElement('a');
      a.href = url;
      a.download = file.name;
      a.click();
      URL.revokeObjectURL(url);
      return true;
    }

    try {
      // This would use a gallery plugin to save the video
      console.log(`Saving video to gallery album: ${albumName}`);
      return true;
    } catch (error) {
      console.error('Failed to save video to gallery:', error);
      return false;
    }
  }
}

export const enhancedCameraService = EnhancedCameraService.getInstance();
export default enhancedCameraService;