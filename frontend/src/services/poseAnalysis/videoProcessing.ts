import * as tf from '@tensorflow/tfjs';
import { isMobileDevice } from './utils';

interface VideoProcessorConfig {
  targetFPS?: number;
  downsampleFactor?: number;
  useWebGL?: boolean;
  enableSmoothing?: boolean;
}

const DEFAULT_CONFIG: VideoProcessorConfig = {
  targetFPS: isMobileDevice() ? 15 : 30,
  downsampleFactor: isMobileDevice() ? 0.5 : 0.75,
  useWebGL: false,
  enableSmoothing: false
};

export class VideoProcessor {
  private canvas: HTMLCanvasElement;
  private ctx: CanvasRenderingContext2D;
  private config: VideoProcessorConfig;
  private lastFrameTime: number = 0;
  private frameInterval: number;
  private smoothingBuffer: ImageData[] = [];
  private smoothingWindow: number = 5;

  constructor(config: VideoProcessorConfig = {}) {
    this.config = {
      targetFPS: config.targetFPS || DEFAULT_CONFIG.targetFPS,
      downsampleFactor: config.downsampleFactor || DEFAULT_CONFIG.downsampleFactor,
      useWebGL: config.useWebGL !== false,
      enableSmoothing: config.enableSmoothing !== false
    };

    this.canvas = document.createElement('canvas');
    this.ctx = this.canvas.getContext('2d')!;
    this.frameInterval = 1000 / this.config.targetFPS!;

    if (this.config.useWebGL) {
      this.initializeWebGL();
    }
  }

  private initializeWebGL(): void {
    try {
      tf.setBackend('webgl');
      const gl = (tf.backend() as any).gpgpu?.gl;
      if (gl) {
        gl.getExtension('EXT_color_buffer_float');
      }
    } catch (error) {
      console.warn('WebGL initialization failed, falling back to CPU:', error);
      this.config.useWebGL = false;
    }
  }

  public processFrame(videoElement: HTMLVideoElement): ImageData | null {
    const currentTime = performance.now();
    if (currentTime - this.lastFrameTime < this.frameInterval) {
      return null;
    }

    try {
      // Set canvas dimensions based on downsample factor
      const width = videoElement.videoWidth * (this.config.downsampleFactor || 1);
      const height = videoElement.videoHeight * (this.config.downsampleFactor || 1);
      
      this.canvas.width = width;
      this.canvas.height = height;

      // Draw and process frame
      this.ctx.drawImage(videoElement, 0, 0, width, height);
      const frameData = this.ctx.getImageData(0, 0, width, height);

      // Apply smoothing if enabled
      if (this.config.enableSmoothing) {
        this.smoothingBuffer.push(frameData);
        if (this.smoothingBuffer.length > this.smoothingWindow) {
          this.smoothingBuffer.shift();
        }
        return this.applySmoothing();
      }

      this.lastFrameTime = currentTime;
      return frameData;
    } catch (error) {
      console.error('Error processing video frame:', error);
      return null;
    }
  }

  private applySmoothing(): ImageData {
    if (this.smoothingBuffer.length === 0) {
      return new ImageData(1, 1);
    }

    const width = this.smoothingBuffer[0].width;
    const height = this.smoothingBuffer[0].height;
    const smoothedData = new ImageData(width, height);
    const bufferLength = this.smoothingBuffer.length;

    for (let i = 0; i < smoothedData.data.length; i += 4) {
      let r = 0, g = 0, b = 0, a = 0;

      for (const frame of this.smoothingBuffer) {
        r += frame.data[i];
        g += frame.data[i + 1];
        b += frame.data[i + 2];
        a += frame.data[i + 3];
      }

      smoothedData.data[i] = r / bufferLength;
      smoothedData.data[i + 1] = g / bufferLength;
      smoothedData.data[i + 2] = b / bufferLength;
      smoothedData.data[i + 3] = a / bufferLength;
    }

    return smoothedData;
  }

  public resizeFrame(frameData: ImageData, targetWidth: number, targetHeight: number): ImageData {
    this.canvas.width = targetWidth;
    this.canvas.height = targetHeight;

    // Create temporary canvas for the source frame
    const tempCanvas = document.createElement('canvas');
    tempCanvas.width = frameData.width;
    tempCanvas.height = frameData.height;
    const tempCtx = tempCanvas.getContext('2d')!;
    tempCtx.putImageData(frameData, 0, 0);

    // Draw resized frame
    this.ctx.drawImage(tempCanvas, 0, 0, targetWidth, targetHeight);

    return this.ctx.getImageData(0, 0, targetWidth, targetHeight);
  }

  public normalizeFrame(frameData: ImageData): Float32Array {
    const normalized = new Float32Array(frameData.data.length / 4);
    for (let i = 0; i < frameData.data.length; i += 4) {
      normalized[i / 4] = frameData.data[i] / 255.0;
    }
    return normalized;
  }

  public cleanup(): void {
    if (this.config.useWebGL) {
      tf.dispose();
    }
    this.smoothingBuffer = [];
  }
} 