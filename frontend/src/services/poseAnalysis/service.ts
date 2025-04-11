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
      
      const modelConfig = this.config.modelType === 'MoveNet' 
        ? {
            modelType: poseDetection.movenet.modelType.SINGLEPOSE_LIGHTNING,
            enableSmoothing: this.config.deviceOptimization?.enableSmoothing
          }
        : {
            runtime: 'tfjs',
            enableSmoothing: this.config.deviceOptimization?.enableSmoothing
          };

      this.detector = await poseDetection.createDetector(
        this.config.modelType === 'MoveNet' 
          ? poseDetection.SupportedModels.MoveNet
          : poseDetection.SupportedModels.BlazePose,
        modelConfig
      );
    } catch (error) {
      console.error('Failed to initialize pose detector:', error);
      throw error;
    }
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