declare module '@capacitor/camera' {
  export interface CameraPlugin {
    checkPermissions(): Promise<{ camera: string }>;
    requestPermissions(): Promise<{ camera: string }>;
    startRecording(options?: { quality?: string; maxDuration?: number }): Promise<void>;
    stopRecording(): Promise<{ videoPath: string }>;
  }

  export const Camera: CameraPlugin;
} 