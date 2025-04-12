import { Camera } from '@capacitor/camera';
import { Filesystem } from '@capacitor/filesystem';

export class VideoRecorder {
  private isRecording: boolean = false;

  async checkPermissions(): Promise<boolean> {
    const { camera } = await Camera.checkPermissions();
    return camera === 'granted';
  }

  async requestPermissions(): Promise<boolean> {
    const { camera } = await Camera.requestPermissions();
    return camera === 'granted';
  }

  async startRecording(): Promise<boolean> {
    if (!await this.checkPermissions()) {
      throw new Error('Camera permissions not granted');
    }

    try {
      await Camera.startRecording({
        quality: '720p',
        maxDuration: 60,
      });
      this.isRecording = true;
      return true;
    } catch (error) {
      throw new Error('Failed to start recording');
    }
  }

  async stopRecording(): Promise<string> {
    if (!this.isRecording) {
      throw new Error('No active recording');
    }

    try {
      const { videoPath } = await Camera.stopRecording();
      this.isRecording = false;
      return videoPath;
    } catch (error) {
      throw new Error('Failed to stop recording');
    }
  }
} 