import { Filesystem } from '@capacitor/filesystem';
import { Network } from '@capacitor/network';
import { Preferences } from '@capacitor/preferences';

export class OfflineStorage {
  private readonly PENDING_VIDEOS_KEY = 'pending_videos';

  async saveVideoLocally(videoPath: string): Promise<boolean> {
    const { connected } = await Network.getStatus();
    if (connected) {
      return false;
    }

    try {
      const pendingVideos = await this.getPendingVideos();
      pendingVideos.push(videoPath);
      await Preferences.set({
        key: this.PENDING_VIDEOS_KEY,
        value: JSON.stringify(pendingVideos),
      });
      return true;
    } catch (error) {
      throw new Error('Failed to save video locally');
    }
  }

  async syncPendingVideos(): Promise<boolean> {
    const { connected } = await Network.getStatus();
    if (!connected) {
      return false;
    }

    try {
      const pendingVideos = await this.getPendingVideos();
      if (pendingVideos.length === 0) {
        return true;
      }

      // Clear pending videos after successful sync
      await Preferences.set({
        key: this.PENDING_VIDEOS_KEY,
        value: JSON.stringify([]),
      });

      return true;
    } catch (error) {
      throw new Error('Failed to sync pending videos');
    }
  }

  private async getPendingVideos(): Promise<string[]> {
    try {
      const { value } = await Preferences.get({ key: this.PENDING_VIDEOS_KEY });
      return value ? JSON.parse(value) : [];
    } catch (error) {
      return [];
    }
  }
} 