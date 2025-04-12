import { Filesystem } from '@capacitor/filesystem';
import { Network } from '@capacitor/network';

export class VideoUploader {
  private readonly API_URL = process.env.API_URL || 'http://localhost:8000';

  async uploadVideo(videoPath: string): Promise<boolean> {
    const { connected } = await Network.getStatus();
    if (!connected) {
      throw new Error('No internet connection');
    }

    try {
      const { data } = await Filesystem.readFile({
        path: videoPath,
      });

      const response = await fetch(`${this.API_URL}/api/videos/upload`, {
        method: 'POST',
        headers: {
          'Content-Type': 'video/mp4',
        },
        body: data,
      });

      if (!response.ok) {
        throw new Error('Upload failed');
      }

      return true;
    } catch (error) {
      throw new Error('Failed to upload video');
    }
  }
} 