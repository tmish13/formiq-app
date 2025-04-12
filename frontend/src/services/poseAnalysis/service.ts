import * as tf from '@tensorflow/tfjs';
import * as poseDetection from '@tensorflow-models/pose-detection';
import { VideoProcessor } from './videoProcessing';
import { storageService } from '../storageService';
import {
  PoseAnalysisConfig,
  PoseAnalysisResult,
  JointAngle,
  MovementMetrics,
  FormValidationResult
} from './types';
import { ExerciseType, exerciseConfigs } from './exerciseTypes';
import {
  calculateConfidenceScore,
  calculateMovementMetrics,
  calculateJointAngles,
  isMobileDevice
} from './utils';

export class PoseAnalysisService {
  private static instance: PoseAnalysisService;
  private detector: poseDetection.PoseDetector | null = null;
  private isAnalyzing: boolean = false;
  private readonly MIN_CONFIDENCE_THRESHOLD = 0.3;
  private readonly MAX_RETRY_ATTEMPTS = 3;
  private retryCount = 0;
  private fallbackDetector: poseDetection.PoseDetector | null = null;
  private config: PoseAnalysisConfig;
  private videoProcessor: VideoProcessor;
  private previousKeypoints: poseDetection.Keypoint[] = [];
  private angleHistory: Map<string, number[]> = new Map();
  private movementBuffer: poseDetection.Keypoint[][] = [];
  private tensorCache: Map<string, tf.Tensor> = new Map();
  private currentPhase: 'start' | 'middle' | 'end' = 'start';
  private repetitionCount: number = 0;

  private constructor(config: PoseAnalysisConfig) {
    this.config = {
      ...{
        minConfidence: 0.3,
        modelType: 'MoveNet',
        exerciseType: ExerciseType.SQUAT,
        deviceOptimization: {
          targetFPS: isMobileDevice() ? 15 : 30,
          downsampleFactor: isMobileDevice() ? 0.5 : 1,
          useWebGL: true,
          enableSmoothing: true,
          batchSize: 4,
          kernelOptimization: true
        },
        analysis: {
          smoothingWindow: 5,
          minRequiredKeypoints: 12,
          confidenceThreshold: 0.6,
          jointAngleTolerance: 15,
          movementThresholds: {
            velocity: 0.5,
            acceleration: 0.3,
            jerk: 0.2
          }
        }
      },
      ...config
    };

    this.videoProcessor = new VideoProcessor({
      targetFPS: this.config.deviceOptimization?.targetFPS,
      downsampleFactor: this.config.deviceOptimization?.downsampleFactor
    });
  }

  public static getInstance(config: PoseAnalysisConfig): PoseAnalysisService {
    if (!PoseAnalysisService.instance) {
      PoseAnalysisService.instance = new PoseAnalysisService(config);
    }
    return PoseAnalysisService.instance;
  }

  private async optimizePerformance(): Promise<void> {
    if (this.config.deviceOptimization?.kernelOptimization) {
      await tf.ready();
      if (tf.getBackend() === 'webgl') {
        const gl = (tf.backend() as any).gpgpu.gl;
        gl.getExtension('EXT_color_buffer_float');
        gl.getExtension('OES_texture_float_linear');
        
        tf.env().set('WEBGL_PACK', true);
        tf.env().set('WEBGL_PACK_BINARY_OPERATIONS', true);
        tf.env().set('WEBGL_CONV_IM2COL', true);
        tf.env().set('WEBGL_MAX_TEXTURE_SIZE', 4096);
      }
    }
  }

  private smoothAngles(angles: Record<string, JointAngle>): Record<string, JointAngle> {
    const smoothedAngles: Record<string, JointAngle> = {};
    
    for (const [joint, angle] of Object.entries(angles)) {
      const history = this.angleHistory.get(joint) || [];
      history.push(angle.angle);
      
      if (history.length > this.config.analysis?.smoothingWindow!) {
        history.shift();
      }
      
      this.angleHistory.set(joint, history);
      
      const smoothedAngle = history.reduce((sum, val) => sum + val, 0) / history.length;
      
      smoothedAngles[joint] = {
        ...angle,
        angle: smoothedAngle
      };
    }
    
    return smoothedAngles;
  }

  private cleanup(): void {
    this.videoProcessor.destroy();
    Array.from(this.tensorCache.values()).forEach(tensor => {
      tensor.dispose();
    });
    this.tensorCache.clear();
    this.angleHistory.clear();
    this.movementBuffer = [];
    this.previousKeypoints = [];
    
    if (this.detector) {
      this.detector.dispose();
      this.detector = null;
    }
  }

  async initialize(): Promise<void> {
    try {
      await this.optimizePerformance();
      
      // Initialize primary detector
      const modelConfig = this.getPrimaryModelConfig();
      this.detector = await this.createDetector(modelConfig);

      // Initialize fallback detector with simpler model
      const fallbackConfig = this.getFallbackModelConfig();
      this.fallbackDetector = await this.createDetector(fallbackConfig);

      this.emit('detectorReady');
    } catch (error) {
      console.error('Failed to initialize pose detector:', error);
      this.emit('detectorError', error);
      throw new Error('Failed to initialize pose detection model: ' + error.message);
    }
  }

  private getPrimaryModelConfig(): poseDetection.ModelConfig {
    return {
      modelType: poseDetection.movenet.modelType.SINGLEPOSE_THUNDER,
      enableSmoothing: true,
      minPoseScore: this.MIN_CONFIDENCE_THRESHOLD
    };
  }

  private getFallbackModelConfig(): poseDetection.ModelConfig {
    return {
      modelType: poseDetection.movenet.modelType.SINGLEPOSE_LIGHTNING,
      enableSmoothing: true,
      minPoseScore: this.MIN_CONFIDENCE_THRESHOLD * 0.8 // Lower threshold for fallback
    };
  }

  private async createDetector(config: poseDetection.ModelConfig): Promise<poseDetection.PoseDetector> {
    try {
      return await poseDetection.createDetector(
        poseDetection.SupportedModels.MoveNet,
        config
      );
    } catch (error) {
      console.error('Failed to create detector:', error);
      throw error;
    }
  }

  public async detectPose(videoElement: HTMLVideoElement): Promise<PoseAnalysisResult> {
    if (!this.detector && !this.fallbackDetector) {
      throw new Error('Pose detectors not initialized');
    }

    try {
      // Try primary detector first
      if (this.detector) {
        const poses = await this.detector.estimatePoses(videoElement, {
          maxPoses: 1,
          flipHorizontal: false
        });

        if (this.validatePoseResult(poses)) {
          this.retryCount = 0; // Reset retry count on success
          return this.processPoseResult(poses[0]);
        }
      }

      // Fall back to simpler model if primary fails
      if (this.fallbackDetector && this.retryCount < this.MAX_RETRY_ATTEMPTS) {
        this.retryCount++;
        console.warn(`Falling back to simpler model, attempt ${this.retryCount}`);
        
        const poses = await this.fallbackDetector.estimatePoses(videoElement, {
          maxPoses: 1,
          flipHorizontal: false
        });

        if (this.validatePoseResult(poses)) {
          return this.processPoseResult(poses[0]);
        }
      }

      throw new Error('Failed to detect pose with both primary and fallback models');
    } catch (error) {
      console.error('Error during pose detection:', error);
      this.emit('detectionError', error);
      throw error;
    }
  }

  private validatePoseResult(poses: poseDetection.Pose[]): boolean {
    if (!poses || poses.length === 0) return false;

    const pose = poses[0];
    if (!pose.keypoints || pose.keypoints.length === 0) return false;

    // Check if enough keypoints have sufficient confidence
    const confidentKeypoints = pose.keypoints.filter(
      kp => kp.score && kp.score >= this.MIN_CONFIDENCE_THRESHOLD
    );

    return confidentKeypoints.length >= pose.keypoints.length * 0.7; // At least 70% confident keypoints
  }

  private processPoseResult(pose: poseDetection.Pose): PoseAnalysisResult {
    return {
      keypoints: this.normalizeKeypoints(pose.keypoints),
      confidence: this.calculateOverallConfidence(pose.keypoints),
      timestamp: Date.now()
    };
  }

  private calculateOverallConfidence(keypoints: poseDetection.Keypoint[]): number {
    const scores = keypoints
      .map(kp => kp.score || 0)
      .filter(score => score > 0);
    
    return scores.length > 0 ? 
      scores.reduce((sum, score) => sum + score, 0) / scores.length : 
      0;
  }

  private async analyzeFrame(videoElement: HTMLVideoElement): Promise<void> {
    if (!this.detector || !this.isAnalyzing) return;

    try {
      // Process video frame
      const processedFrame = this.videoProcessor.processFrame(videoElement);
      if (!processedFrame) {
        requestAnimationFrame(() => this.analyzeFrame(videoElement));
        return;
      }

      // Detect poses
      const poses = await this.detector.estimatePoses(processedFrame, {
        flipHorizontal: false,
        maxPoses: 1
      });

      if (poses.length > 0) {
        const keypoints = poses[0].keypoints;
        const exerciseConfig = exerciseConfigs[this.config.exerciseType as ExerciseType];
        
        // Check if we have all required keypoints
        const hasRequiredKeypoints = exerciseConfig.requiredKeypoints.every(name => 
          keypoints.find(kp => kp.name === name && kp.score && kp.score > this.config.minConfidence)
        );

        if (hasRequiredKeypoints) {
          const angles = calculateJointAngles(keypoints);
          const metrics = calculateMovementMetrics(keypoints, this.previousKeypoints);
          const formValidation = this.validateForm(keypoints, angles, exerciseConfig);
          const confidence = calculateConfidenceScore(keypoints);
          
          // Update phase and rep count
          this.updatePhaseAndReps(angles, exerciseConfig);

          const analysis: PoseAnalysisResult = {
            keypoints,
            angles,
            formValidation,
            metrics,
            confidence,
            phase: this.currentPhase,
            repetitionCount: this.repetitionCount
          };

          this.processAnalysisResult(analysis);
          this.previousKeypoints = keypoints;
        }
      }

      requestAnimationFrame(() => this.analyzeFrame(videoElement));
    } catch (error) {
      console.error('Error analyzing frame:', error);
      this.stopAnalysis();
    }
  }

  private validateForm(
    keypoints: poseDetection.Keypoint[],
    angles: { [key: string]: JointAngle },
    exerciseConfig: typeof exerciseConfigs[ExerciseType]
  ): FormValidationResult[] {
    return exerciseConfig.formChecks.map(check => check.validate(keypoints, angles));
  }

  private updatePhaseAndReps(
    angles: { [key: string]: JointAngle },
    exerciseConfig: typeof exerciseConfigs[ExerciseType]
  ): void {
    const primaryJoint = Object.keys(exerciseConfig.phases.middle)[0];
    const currentAngle = angles[primaryJoint]?.angle || 0;
    const { start, middle, end } = exerciseConfig.phases;

    // Determine current phase based on joint angles
    if (Math.abs(currentAngle - start[primaryJoint]) <= 15) {
      if (this.currentPhase === 'end') {
        this.repetitionCount++;
      }
      this.currentPhase = 'start';
    } else if (Math.abs(currentAngle - middle[primaryJoint]) <= 15) {
      this.currentPhase = 'middle';
    } else if (Math.abs(currentAngle - end[primaryJoint]) <= 15) {
      this.currentPhase = 'end';
    }
  }

  private async processAnalysisResult(analysis: PoseAnalysisResult): Promise<void> {
    // Store analysis result or send to callback
    if (this.config.onAnalysisResult) {
      this.config.onAnalysisResult(analysis);
    }
  }

  public async startAnalysis(videoElement: HTMLVideoElement): Promise<void> {
    if (!this.detector) {
      await this.initialize();
    }

    this.isAnalyzing = true;
    this.currentPhase = 'start';
    this.repetitionCount = 0;
    this.analyzeFrame(videoElement);
  }

  public stopAnalysis(): void {
    this.isAnalyzing = false;
    this.cleanup();
  }

  public setExerciseType(type: ExerciseType): void {
    if (exerciseConfigs[type]) {
      this.config.exerciseType = type;
      this.currentPhase = 'start';
      this.repetitionCount = 0;
    } else {
      throw new Error(`Unsupported exercise type: ${type}`);
    }
  }
}

export const poseAnalysisService = PoseAnalysisService.getInstance({
  minConfidence: 0.3,
  modelType: 'MoveNet',
  exerciseType: ExerciseType.SQUAT
}); 