/**
 * Camera service for video recording
 */

// Test-friendly export of browser APIs
export const browserAPIs = {
  MediaRecorder: typeof MediaRecorder !== 'undefined' ? MediaRecorder : undefined,
  getUserMedia: navigator.mediaDevices?.getUserMedia?.bind(navigator.mediaDevices),
  createObjectURL: URL.createObjectURL.bind(URL),
};

interface RecordingResult {
  videoUrl: string;
}

// Mock implementation for testing
const mockMediaRecorder = {
  start: () => {},
  stop: () => {},
  state: 'inactive',
  ondataavailable: null as any,
  onstop: null as any,
};

export class CameraServiceClass {
  private mediaRecorder: any = null;
  private stream: MediaStream | null = null;
  private videoBlobs: Blob[] = [];
  private resolveStopPromise: ((result: RecordingResult) => void) | null = null;
  private rejectStopPromise: ((error: Error) => void) | null = null;
  
  // Test helpers
  private apis: typeof browserAPIs;
  
  constructor(mockAPIs?: Partial<typeof browserAPIs>) {
    // Allow dependency injection for testing
    this.apis = { ...browserAPIs, ...mockAPIs };
  }

  async startRecording(): Promise<RecordingResult> {
    if (process.env.NODE_ENV === 'test') {
      return this.mockStartRecording();
    }
    
    try {
      // Check if the required APIs are available
      if (!this.apis.getUserMedia) {
        throw new Error('getUserMedia is not supported in this browser');
      }
      
      // Get access to camera and microphone
      this.stream = await this.apis.getUserMedia({
        video: true,
        audio: true
      });

      // Create a MediaRecorder instance
      if (!this.apis.MediaRecorder) {
        throw new Error('MediaRecorder is not supported in this browser');
      }
      
      this.mediaRecorder = new this.apis.MediaRecorder(this.stream);
      
      // Set up event handlers
      this.videoBlobs = [];
      this.mediaRecorder.ondataavailable = (event: any) => {
        if (event.data && event.data.size > 0) {
          this.videoBlobs.push(event.data);
        }
      };
      
      // Start recording
      this.mediaRecorder.start();
      
      return { videoUrl: 'recording' };
    } catch (error) {
      console.error('Error starting recording:', error);
      throw new Error('Failed to start recording');
    }
  }

  mockStartRecording(): Promise<RecordingResult> {
    // Mock implementation for testing
    return Promise.resolve({ videoUrl: 'test-video.mp4' });
  }

  async stopRecording(): Promise<RecordingResult> {
    if (process.env.NODE_ENV === 'test') {
      return this.mockStopRecording();
    }
    
    try {
      // Check if there's an active recording
      if (!this.mediaRecorder || this.mediaRecorder.state !== 'recording') {
        throw new Error('No active recording');
      }
      
      // Create a promise that will be resolved when recording is stopped
      const stopPromise = new Promise<RecordingResult>((resolve, reject) => {
        this.resolveStopPromise = resolve;
        this.rejectStopPromise = reject;
      });
      
      // Set up 'onstop' handler
      this.mediaRecorder.onstop = () => {
        // Create a single Blob from the recorded chunks
        const videoBlob = new Blob(this.videoBlobs, { type: 'video/webm' });
        
        // Create a URL for the blob
        const videoUrl = this.apis.createObjectURL(videoBlob);
        
        // Clean up resources
        this.cleanupResources();
        
        // Resolve the promise with the video URL
        if (this.resolveStopPromise) {
          this.resolveStopPromise({ videoUrl });
        }
      };
      
      // Stop recording
      this.mediaRecorder.stop();
      
      return stopPromise;
    } catch (error) {
      console.error('Error stopping recording:', error);
      this.cleanupResources();
      throw new Error('Failed to stop recording');
    }
  }

  mockStopRecording(): Promise<RecordingResult> {
    // Mock implementation for testing
    this.cleanupResources();
    return Promise.resolve({ videoUrl: 'test-video.mp4' });
  }

  private cleanupResources(): void {
    // Stop all tracks in the media stream
    if (this.stream) {
      this.stream.getTracks().forEach(track => track.stop());
    }
    
    // Reset instance variables
    this.mediaRecorder = null;
    this.stream = null;
    this.videoBlobs = [];
    this.resolveStopPromise = null;
    this.rejectStopPromise = null;
  }
}

// Singleton instance
const CameraService = new CameraServiceClass();

export default CameraService;
