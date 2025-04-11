import * as poseDetection from '@tensorflow-models/pose-detection';
import '@tensorflow/tfjs-backend-webgl';
import { Device } from '@capacitor/device';

export interface MobilePoseDetectionOptions {
  modelType?: 'MoveNet' | 'BlazePose';
  detectorConfig?: poseDetection.PoseDetectorConfig;
  maxPoses?: number;
}

export class MobilePoseDetectionService {
  private static instance: MobilePoseDetectionService;
  private detector: poseDetection.PoseDetector | null = null;
  private isInitialized = false;
  private deviceInfo: any;

  private constructor() {}

  public static getInstance(): MobilePoseDetectionService {
    if (!MobilePoseDetectionService.instance) {
      MobilePoseDetectionService.instance = new MobilePoseDetectionService();
    }
    return MobilePoseDetectionService.instance;
  }

  public async initialize(options: MobilePoseDetectionOptions = {}): Promise<void> {
    if (this.isInitialized) return;

    try {
      // Get device info for optimizations
      this.deviceInfo = await Device.getInfo();
      
      // Choose optimal model based on device capabilities
      const modelType = this.selectOptimalModel();
      
      // Configure detector based on device
      const detectorConfig = this.getOptimizedConfig(modelType);

      // Create detector
      this.detector = await poseDetection.createDetector(
        modelType,
        {
          ...detectorConfig,
          ...options.detectorConfig
        }
      );

      this.isInitialized = true;
    } catch (error) {
      console.error('Failed to initialize mobile pose detector:', error);
      throw error;
    }
  }

  private selectOptimalModel(): poseDetection.SupportedModels {
    // Select model based on device capabilities
    if (this.deviceInfo.platform === 'ios') {
      return this.deviceInfo.isVirtual ? 
        poseDetection.SupportedModels.MoveNet :
        poseDetection.SupportedModels.BlazePose;
    }

    // For Android, use MoveNet on lower-end devices
    return this.deviceInfo.memUsed < 2000000000 ? 
      poseDetection.SupportedModels.MoveNet :
      poseDetection.SupportedModels.BlazePose;
  }

  private getOptimizedConfig(modelType: poseDetection.SupportedModels): poseDetection.PoseDetectorConfig {
    const baseConfig: poseDetection.PoseDetectorConfig = {
      modelType: modelType === poseDetection.SupportedModels.MoveNet ? 
        'lightning' : undefined,
      enableSmoothing: true,
    };

    // Add model-specific optimizations
    if (modelType === poseDetection.SupportedModels.BlazePose) {
      return {
        ...baseConfig,
        runtime: 'tfjs',
        enableSegmentation: false,
        smoothSegmentation: false,
        multiPoseMaxDimension: 256,
      };
    }

    // MoveNet optimizations
    return {
      ...baseConfig,
      modelType: 'lightning',
      enableTracking: true,
      trackerType: 'boundingBox',
      trackerConfig: {
        maxTracks: 1,
        maxAge: 1000,
        minSimilarity: 0.2,
      },
    };
  }

  public async detectPoses(
    image: ImageData | HTMLVideoElement | HTMLImageElement | HTMLCanvasElement,
    timestamp?: number
  ): Promise<poseDetection.Pose[]> {
    if (!this.detector || !this.isInitialized) {
      throw new Error('Pose detector not initialized');
    }

    try {
      const poses = await this.detector.estimatePoses(image, {
        maxPoses: 1,
        flipHorizontal: false,
        timestamp
      });

      return this.postProcessPoses(poses);
    } catch (error) {
      console.error('Failed to detect poses:', error);
      throw error;
    }
  }

  private postProcessPoses(poses: poseDetection.Pose[]): poseDetection.Pose[] {
    return poses.map(pose => ({
      ...pose,
      keypoints: pose.keypoints.map(keypoint => ({
        ...keypoint,
        score: keypoint.score || 0,
        // Apply additional smoothing for mobile
        x: Math.round(keypoint.x * 100) / 100,
        y: Math.round(keypoint.y * 100) / 100
      }))
    }));
  }

  public async dispose(): Promise<void> {
    if (this.detector) {
      await this.detector.dispose();
      this.detector = null;
      this.isInitialized = false;
    }
  }
}

export const mobilePoseDetectionService = MobilePoseDetectionService.getInstance(); 