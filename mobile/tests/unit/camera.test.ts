import { Camera } from '@capacitor/camera';
import { Filesystem } from '@capacitor/filesystem';
import { Network } from '@capacitor/network';
import { Preferences } from '@capacitor/preferences';
import { VideoRecorder } from '../../src/services/VideoRecorder';
import { VideoUploader } from '../../src/services/VideoUploader';
import { OfflineStorage } from '../../src/services/OfflineStorage';

jest.mock('@capacitor/camera');
jest.mock('@capacitor/filesystem');
jest.mock('@capacitor/network');
jest.mock('@capacitor/preferences');

describe('VideoRecorder', () => {
  let videoRecorder: VideoRecorder;
  let videoUploader: VideoUploader;
  let offlineStorage: OfflineStorage;

  beforeEach(() => {
    videoRecorder = new VideoRecorder();
    videoUploader = new VideoUploader();
    offlineStorage = new OfflineStorage();
    jest.clearAllMocks();
  });

  describe('Camera Permissions', () => {
    it('should request camera permissions successfully', async () => {
      (Camera.checkPermissions as jest.Mock).mockResolvedValue({ camera: 'granted' });
      const result = await videoRecorder.checkPermissions();
      expect(result).toBe(true);
    });

    it('should handle denied camera permissions', async () => {
      (Camera.checkPermissions as jest.Mock).mockResolvedValue({ camera: 'denied' });
      const result = await videoRecorder.checkPermissions();
      expect(result).toBe(false);
    });

    it('should request permissions when not granted', async () => {
      (Camera.checkPermissions as jest.Mock).mockResolvedValue({ camera: 'prompt' });
      (Camera.requestPermissions as jest.Mock).mockResolvedValue({ camera: 'granted' });
      const result = await videoRecorder.requestPermissions();
      expect(result).toBe(true);
    });
  });

  describe('Video Recording', () => {
    it('should start recording successfully', async () => {
      (Camera.startRecording as jest.Mock).mockResolvedValue({ recording: true });
      const result = await videoRecorder.startRecording();
      expect(result).toBe(true);
    });

    it('should stop recording and save video', async () => {
      const mockVideoPath = 'file:///data/video.mp4';
      (Camera.stopRecording as jest.Mock).mockResolvedValue({ videoPath: mockVideoPath });
      (Filesystem.writeFile as jest.Mock).mockResolvedValue({ uri: mockVideoPath });
      
      const result = await videoRecorder.stopRecording();
      expect(result).toBe(mockVideoPath);
    });

    it('should handle recording errors', async () => {
      (Camera.startRecording as jest.Mock).mockRejectedValue(new Error('Recording failed'));
      await expect(videoRecorder.startRecording()).rejects.toThrow('Recording failed');
    });
  });

  describe('Offline Mode', () => {
    it('should save video locally when offline', async () => {
      (Network.getStatus as jest.Mock).mockResolvedValue({ connected: false });
      const mockVideoPath = 'file:///data/video.mp4';
      (Filesystem.writeFile as jest.Mock).mockResolvedValue({ uri: mockVideoPath });
      
      const result = await offlineStorage.saveVideoLocally(mockVideoPath);
      expect(result).toBe(true);
    });

    it('should sync videos when coming back online', async () => {
      (Network.getStatus as jest.Mock).mockResolvedValue({ connected: true });
      (Preferences.get as jest.Mock).mockResolvedValue({ value: JSON.stringify(['video1.mp4']) });
      
      const result = await offlineStorage.syncPendingVideos();
      expect(result).toBe(true);
    });
  });

  describe('Video Upload', () => {
    it('should upload video successfully when online', async () => {
      (Network.getStatus as jest.Mock).mockResolvedValue({ connected: true });
      const mockVideoPath = 'file:///data/video.mp4';
      (Filesystem.readFile as jest.Mock).mockResolvedValue({ data: 'video-data' });
      
      const result = await videoUploader.uploadVideo(mockVideoPath);
      expect(result).toBe(true);
    });

    it('should handle upload errors gracefully', async () => {
      (Network.getStatus as jest.Mock).mockResolvedValue({ connected: true });
      (Filesystem.readFile as jest.Mock).mockRejectedValue(new Error('Upload failed'));
      
      await expect(videoUploader.uploadVideo('video.mp4')).rejects.toThrow('Upload failed');
    });
  });
}); 