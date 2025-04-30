import * as tf from '@tensorflow/tfjs';
import * as poseDetection from '@tensorflow-models/pose-detection';
import { videoService } from './videoService';
import { storageService } from './storageService';
import { analyzeExerciseForm } from './poseAnalysis/exerciseAnalysis';
import { calculateVerticalAlignment, calculateLateralAlignment } from './poseAnalysis/utils';
import { apiService } from './apiService';
import { PoseAnalysisResult, JointAngles, MovementPath, FormAnalysisResponse } from '../types/formAnalysis';
import { Keypoint } from '@tensorflow-models/pose-detection';
import { JointAngle, FormFeedback } from '../types/formAnalysis';
import { EventEmitter } from 'events';

// Types and interfaces
export type ExerciseType = 'squat' | 'pushup' | 'plank' | 'lunges' | 'deadlift' | 'burpees' | 'mountain_climbers';

export interface BodyAlignment {
  vertical: number;
  lateral: number;
  confidence: number;
}

export interface MovementMetrics {
  velocity: number;
  acceleration: number;
  smoothness: number;
  range: number;
}

export interface FeedbackItem {
  text: string;
  severity: 'high' | 'medium' | 'low';
  type: 'form' | 'range' | 'safety' | 'alignment' | 'tempo';
  details: string;
  confidence: number;
  timestamp: number;
}

export interface PoseAnalysisConfig {
  minConfidence: number;
  modelType: 'MoveNet' | 'BlazePose';
  exerciseType: ExerciseType;
  onAnalysisResult?: (analysis: PoseAnalysisResult) => void;
  deviceOptimization?: {
    targetFPS?: number;
    downsampleFactor?: number;
    useWebGL?: boolean;
    enableSmoothing?: boolean;
    batchSize?: number;
    kernelOptimization?: boolean;
  };
  analysis?: {
    smoothingWindow?: number;
    minRequiredKeypoints?: number;
    confidenceThreshold?: number;
    jointAngleTolerance?: number;
    movementThresholds?: {
      velocity: number;
      acceleration: number;
      jerk: number;
    };
  };
}

// Service implementation
export class PoseAnalysisService extends EventEmitter {
  private static instance: PoseAnalysisService;
  private detector: poseDetection.PoseDetector | null = null;
  private isAnalyzing: boolean = false;
  private config: PoseAnalysisConfig;
  private lastFrameTime: number = 0;
  private frameInterval: number;
  private downsampleFactor: number;
  private previousKeypoints: poseDetection.Keypoint[] = [];
  private angleHistory: Map<string, number[]> = new Map();
  private movementBuffer: MovementMetrics[] = [];
  private tensorCache: Map<string, tf.Tensor> = new Map();
  private errorCount: number = 0;
  private maxErrors: number = 3;
  private recoveryTimeout: number = 5000; // 5 seconds
  private state: {
    isAnalyzing: boolean;
    error: string | null;
    lastAnalysis: PoseAnalysisResult | null;
    isRecovering: boolean;
  } = {
    isAnalyzing: false,
    error: null,
    lastAnalysis: null,
    isRecovering: false
  };
  private frameSkipInterval: number = 2; // Process every nth frame
  private frameCount: number = 0;

  private constructor(config: PoseAnalysisConfig) {
    super();
    this.config = {
      ...{
        minConfidence: 0.3,
        modelType: 'MoveNet',
        exerciseType: 'squat',
        deviceOptimization: {
          targetFPS: this.isMobileDevice() ? 15 : 30,
          downsampleFactor: this.isMobileDevice() ? 0.5 : 1,
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

    this.frameInterval = 1000 / (this.config.deviceOptimization?.targetFPS || 30);
    this.downsampleFactor = this.config.deviceOptimization?.downsampleFactor || 1;
  }

  public static async getInstance(config: PoseAnalysisConfig): Promise<PoseAnalysisService> {
    if (!PoseAnalysisService.instance) {
      PoseAnalysisService.instance = new PoseAnalysisService(config);
      await PoseAnalysisService.instance.initialize();
    }
    return PoseAnalysisService.instance;
  }

  /**
   * Reset the singleton instance for testing purposes.
   * This should only be used in test environments.
   */
  public static resetInstance(): void {
    if (PoseAnalysisService.instance) {
      // @ts-ignore - we're explicitly resetting for tests
      PoseAnalysisService.instance = null;
    }
  }

  private isMobileDevice(): boolean {
    return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
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

    // Implement frame skipping for performance
    const now = Date.now();
    if (now - this.lastFrameTime < this.frameInterval) {
      return;
    }
    this.lastFrameTime = now;
  }

  private calculateConfidenceScore(keypoints: poseDetection.Keypoint[]): number {
    const visibleKeypoints = keypoints.filter(kp => kp.score && kp.score > this.config.analysis?.confidenceThreshold!);
    const avgConfidence = visibleKeypoints.reduce((sum, kp) => sum + (kp.score || 0), 0) / visibleKeypoints.length;
    const coverageScore = visibleKeypoints.length / keypoints.length;
    return avgConfidence * coverageScore;
  }

  private calculateMovementMetrics(
    currentKeypoints: poseDetection.Keypoint[],
    previousKeypoints: poseDetection.Keypoint[]
  ): MovementMetrics {
    const velocities: number[] = [];
    const accelerations: number[] = [];
    
    currentKeypoints.forEach((kp, i) => {
      if (previousKeypoints[i] && kp.score && kp.score > this.config.analysis?.confidenceThreshold!) {
        const velocity = this.getJointVelocity(kp, previousKeypoints[i]);
        velocities.push(velocity);
        
        if (this.movementBuffer.length > 0) {
          const prevVelocity = this.getJointVelocity(previousKeypoints[i], this.previousKeypoints[i]);
          const acceleration = (velocity - prevVelocity) / this.frameInterval;
          accelerations.push(acceleration);
        }
      }
    });
    
    const avgVelocity = velocities.reduce((sum, v) => sum + v, 0) / velocities.length;
    const avgAcceleration = accelerations.reduce((sum, a) => sum + a, 0) / accelerations.length;
    const smoothness = this.calculateMovementSmoothness(velocities);
    const range = this.calculateMovementRange(currentKeypoints);
    
    return {
      velocity: avgVelocity,
      acceleration: avgAcceleration,
      smoothness,
      range
    };
  }

  private calculateMovementSmoothness(velocities: number[]): number {
    if (velocities.length < 2) return 1;
    const velocityChanges = velocities.slice(1).map((v, i) => Math.abs(v - velocities[i]));
    const avgChange = velocityChanges.reduce((sum, v) => sum + v, 0) / velocityChanges.length;
    return 1 / (1 + avgChange);
  }

  private calculateMovementRange(keypoints: poseDetection.Keypoint[]): number {
    const verticalRange = this.calculateVerticalRange(keypoints);
    const lateralRange = this.calculateLateralRange(keypoints);
    return Math.sqrt(verticalRange * verticalRange + lateralRange * lateralRange);
  }

  private calculateVerticalRange(keypoints: poseDetection.Keypoint[]): number {
    const topPoint = Math.min(...keypoints.map(kp => kp.y));
    const bottomPoint = Math.max(...keypoints.map(kp => kp.y));
    return bottomPoint - topPoint;
  }

  private calculateLateralRange(keypoints: poseDetection.Keypoint[]): number {
    const leftPoint = Math.min(...keypoints.map(kp => kp.x));
    const rightPoint = Math.max(...keypoints.map(kp => kp.x));
    return rightPoint - leftPoint;
  }

  private cleanup(): void {
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
      if (this.config.deviceOptimization?.useWebGL) {
        await tf.setBackend('webgl');
        // Enable float textures if available
        const gl = (tf.backend() as any).gpgpu?.gl;
        if (gl) {
          gl.getExtension('EXT_color_buffer_float');
        }
      }
      await tf.ready();
      
      const modelConfig = this.config.modelType === 'MoveNet' 
        ? {
            modelType: poseDetection.movenet.modelType.SINGLEPOSE_THUNDER,
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
      this.emit('detectorReady');
    } catch (error) {
      console.error('Failed to initialize pose detector:', error);
      throw error;
    }
  }

  async startAnalysis(videoElement: HTMLVideoElement): Promise<void> {
    if (!this.detector) {
      throw new Error('Pose detector not initialized');
    }

    this.isAnalyzing = true;
    this.lastFrameTime = performance.now();
    this.frameCount = 0;

    while (this.isAnalyzing) {
      try {
        this.frameCount++;
        
        // Performance optimization: Skip frames
        if (this.frameCount % this.frameSkipInterval !== 0) {
          continue;
        }

        const currentTime = performance.now();
        const frameTime = currentTime - this.lastFrameTime;
        this.lastFrameTime = currentTime;

        const result = await this.analyzePose(videoElement);
        this.emit('poseDetected', result);
      } catch (error) {
        this.handleError(error as Error);
      }
    }
  }

  private async analyzePose(videoElement: HTMLVideoElement): Promise<PoseAnalysisResult> {
    if (!this.detector || this.isAnalyzing) return;

    try {
      this.isAnalyzing = true;
      const poses = await this.detector.estimatePoses(videoElement, {
        flipHorizontal: false,
        maxPoses: 1
      });

      if (poses.length > 0) {
        const keypoints = poses[0].keypoints;
        const confidence = this.calculateConfidenceScore(keypoints);

        if (confidence >= this.config.minConfidence) {
          const analysis = this.analyzeForm(keypoints);
          await this.processAnalysisResult(analysis);
        }
      }
    } catch (error) {
      console.error('Error analyzing frame:', error);
    } finally {
      this.isAnalyzing = false;
    }
  }

  private analyzeForm(keypoints: poseDetection.Keypoint[]): PoseAnalysisResult {
    const confidence = this.calculateConfidenceScore(keypoints);
    const angles = this.calculateJointAngles(keypoints);
    const alignment = this.calculateBodyAlignment(keypoints);
    const movement = this.calculateMovementMetrics(keypoints, this.previousKeypoints);
    
    // Get exercise-specific feedback
    const feedback = analyzeExerciseForm(
      this.config.exerciseType,
      keypoints,
      this.previousKeypoints
    );

    // Calculate overall score
    const score = this.calculateOverallScore(confidence, angles, alignment, movement);

    this.previousKeypoints = keypoints;

    return {
      score,
      confidence,
      feedback,
      keypoints,
      angles,
      alignment,
      movement,
      timestamp: Date.now(),
      metrics: {
        alignment: calculateVerticalAlignment(keypoints),
        stability: 0,
        symmetry: 0,
        consistency: 0
      }
    };
  }

  private calculateOverallScore(
    confidence: number,
    angles: Record<string, JointAngle>,
    alignment: BodyAlignment,
    movement: MovementMetrics
  ): number {
    // Weight the components
    const confidenceWeight = 0.2;
    const anglesWeight = 0.3;
    const alignmentWeight = 0.3;
    const movementWeight = 0.2;

    // Calculate angle score
    const angleScores = Object.values(angles).map(a => a.isCorrect ? 1 : 0);
    const angleScore = angleScores.length > 0 
      ? angleScores.reduce<number>((sum, score) => sum + score, 0) / angleScores.length
      : 0;

    // Calculate alignment score
    const alignmentScore = (alignment.vertical + alignment.lateral) / 2;

    // Calculate movement score
    const movementScore = (movement.smoothness + (1 - Math.abs(movement.acceleration))) / 2;

    // Combine scores with weights
    return (
      confidence * confidenceWeight +
      angleScore * anglesWeight +
      alignmentScore * alignmentWeight +
      movementScore * movementWeight
    );
  }

  private calculateJointAngles(keypoints: poseDetection.Keypoint[]): JointAngles {
    const getKeypoint = (name: string) => 
      keypoints.find(kp => kp.name === name);

    const calculateAngle = (p1: poseDetection.Keypoint, p2: poseDetection.Keypoint, p3: poseDetection.Keypoint) => {
      const radians = Math.atan2(p3.y - p2.y, p3.x - p2.x) -
                     Math.atan2(p1.y - p2.y, p1.x - p2.x);
      let angle = Math.abs(radians * 180.0 / Math.PI);
      if (angle > 180.0) {
        angle = 360 - angle;
      }
      return angle;
    };

    const leftShoulder = getKeypoint('left_shoulder');
    const leftElbow = getKeypoint('left_elbow');
    const leftWrist = getKeypoint('left_wrist');
    const leftHip = getKeypoint('left_hip');
    const leftKnee = getKeypoint('left_knee');
    const leftAnkle = getKeypoint('left_ankle');

    const rightShoulder = getKeypoint('right_shoulder');
    const rightElbow = getKeypoint('right_elbow');
    const rightWrist = getKeypoint('right_wrist');
    const rightHip = getKeypoint('right_hip');
    const rightKnee = getKeypoint('right_knee');
    const rightAnkle = getKeypoint('right_ankle');

    return {
      leftElbow: leftShoulder && leftElbow && leftWrist ?
        calculateAngle(leftShoulder, leftElbow, leftWrist) : 0,
      rightElbow: rightShoulder && rightElbow && rightWrist ?
        calculateAngle(rightShoulder, rightElbow, rightWrist) : 0,
      leftShoulder: leftElbow && leftShoulder && leftHip ?
        calculateAngle(leftElbow, leftShoulder, leftHip) : 0,
      rightShoulder: rightElbow && rightShoulder && rightHip ?
        calculateAngle(rightElbow, rightShoulder, rightHip) : 0,
      leftHip: leftShoulder && leftHip && leftKnee ?
        calculateAngle(leftShoulder, leftHip, leftKnee) : 0,
      rightHip: rightShoulder && rightHip && rightKnee ?
        calculateAngle(rightShoulder, rightHip, rightKnee) : 0,
      leftKnee: leftHip && leftKnee && leftAnkle ?
        calculateAngle(leftHip, leftKnee, leftAnkle) : 0,
      rightKnee: rightHip && rightKnee && rightAnkle ?
        calculateAngle(rightHip, rightKnee, rightAnkle) : 0
    };
  }

  private createFeedback(
    message: string,
    severity: 'low' | 'medium' | 'high',
    type: 'form' | 'alignment' | 'range' | 'tempo' | 'safety',
    suggestion: string
  ): FeedbackItem {
    return {
      text: message,
      severity,
      type,
      details: suggestion,
      confidence: 1,
      timestamp: Date.now()
    };
  }

  private analyzeSquatForm(keypoints: poseDetection.Keypoint[]): FeedbackItem[] {
    const feedback: FeedbackItem[] = [];
    
    // Get relevant keypoints
    const leftHip = keypoints.find(kp => kp.name === 'left_hip');
    const rightHip = keypoints.find(kp => kp.name === 'right_hip');
    const leftKnee = keypoints.find(kp => kp.name === 'left_knee');
    const rightKnee = keypoints.find(kp => kp.name === 'right_knee');
    const leftAnkle = keypoints.find(kp => kp.name === 'left_ankle');
    const rightAnkle = keypoints.find(kp => kp.name === 'right_ankle');
    const leftShoulder = keypoints.find(kp => kp.name === 'left_shoulder');
    const rightShoulder = keypoints.find(kp => kp.name === 'right_shoulder');
    const nose = keypoints.find(kp => kp.name === 'nose');

    if (!leftHip || !rightHip || !leftKnee || !rightKnee || 
        !leftAnkle || !rightAnkle || !leftShoulder || !rightShoulder || !nose) {
      return [this.createFeedback(
        "Please ensure your full body is visible in the camera",
        'high',
        'safety',
        "Adjust your position or camera angle to capture your entire body"
      )];
    }

    // Analyze squat depth
    const kneeAngle = (
      this.calculateAngle(leftHip, leftKnee, leftAnkle) +
      this.calculateAngle(rightHip, rightKnee, rightAnkle)
    ) / 2;

    if (kneeAngle > 170) {
      feedback.push(this.createFeedback(
        "Squat depth is too shallow",
        'medium',
        'range',
        "Lower your body until your thighs are parallel to the ground"
      ));
    } else if (kneeAngle < 70) {
      feedback.push(this.createFeedback(
        "Squat depth is too deep",
        'medium',
        'range',
        "Keep your thighs parallel to the ground at the bottom position"
      ));
    }

    // Analyze knee alignment
    const kneeAlignmentDiff = Math.abs(
      this.calculateAngle(leftHip, leftKnee, leftAnkle) -
      this.calculateAngle(rightHip, rightKnee, rightAnkle)
    );

    if (kneeAlignmentDiff > 15) {
      feedback.push(this.createFeedback(
        "Uneven knee bend",
        'high',
        'alignment',
        "Keep both knees equally bent throughout the movement"
      ));
    }

    // Analyze back position
    const backAngle = Math.abs(90 - this.calculateAngle(nose, leftShoulder, leftHip));
    if (backAngle > 30) {
      feedback.push(this.createFeedback(
        "Back is not straight",
        'high',
        'form',
        "Keep your chest up and maintain a neutral spine position"
      ));
    }

    // Check feet position
    const ankleDistance = this.calculateDistance(leftAnkle, rightAnkle);
    const shoulderDistance = this.calculateDistance(leftShoulder, rightShoulder);
    
    if (ankleDistance < shoulderDistance * 0.8) {
      feedback.push(this.createFeedback(
        "Stance too narrow",
        'medium',
        'form',
        "Place your feet slightly wider than shoulder-width apart"
      ));
    } else if (ankleDistance > shoulderDistance * 1.5) {
      feedback.push(this.createFeedback(
        "Stance too wide",
        'medium',
        'form',
        "Bring your feet closer, just slightly wider than shoulder-width"
      ));
    }

    // Add positive feedback if form is good
    if (feedback.length === 0) {
      feedback.push(this.createFeedback(
        "Excellent squat form!",
        'low',
        'form',
        "Keep maintaining this proper form"
      ));
    }

    return feedback;
  }

  private analyzePushupForm(keypoints: poseDetection.Keypoint[]): FeedbackItem[] {
    const feedback: FeedbackItem[] = [];
    
    // Get relevant keypoints
    const leftShoulder = keypoints.find(kp => kp.name === 'left_shoulder');
    const rightShoulder = keypoints.find(kp => kp.name === 'right_shoulder');
    const leftElbow = keypoints.find(kp => kp.name === 'left_elbow');
    const rightElbow = keypoints.find(kp => kp.name === 'right_elbow');
    const leftWrist = keypoints.find(kp => kp.name === 'left_wrist');
    const rightWrist = keypoints.find(kp => kp.name === 'right_wrist');
    const leftHip = keypoints.find(kp => kp.name === 'left_hip');
    const rightHip = keypoints.find(kp => kp.name === 'right_hip');
    const leftAnkle = keypoints.find(kp => kp.name === 'left_ankle');
    const rightAnkle = keypoints.find(kp => kp.name === 'right_ankle');

    if (!leftShoulder || !rightShoulder || !leftElbow || !rightElbow || 
        !leftWrist || !rightWrist || !leftHip || !rightHip || 
        !leftAnkle || !rightAnkle) {
      return [this.createFeedback(
        "Please ensure your full body is visible in the camera",
        'high',
        'safety',
        "Adjust your position or camera angle to capture your entire body"
      )];
    }

    // Calculate angles
    const leftElbowAngle = this.calculateAngle(leftShoulder, leftElbow, leftWrist);
    const rightElbowAngle = this.calculateAngle(rightShoulder, rightElbow, rightWrist);
    const bodyAngle = this.calculateAngle(leftShoulder, leftHip, leftAnkle);

    // Check elbow angles (should be 90° at bottom position)
    const avgElbowAngle = (leftElbowAngle + rightElbowAngle) / 2;
    if (avgElbowAngle > 100) {
      feedback.push(this.createFeedback(
        "Lower your body - bend your elbows more",
        'medium',
        'form',
        "Lower your body until your elbows are at 90 degrees"
      ));
    } else if (avgElbowAngle < 80) {
      feedback.push(this.createFeedback(
        "You're going too low - keep elbows at 90 degrees",
        'high',
        'form',
        "Keep your elbows at 90 degrees throughout the movement"
      ));
    }

    // Check body alignment (should be straight)
    if (Math.abs(bodyAngle - 180) > 15) {
      feedback.push(this.createFeedback(
        "Keep your body straight - don't let your hips sag",
        'high',
        'form',
        "Keep your body straight and maintain a neutral spine position"
      ));
    }

    // Check elbow alignment
    const elbowAlignmentDiff = Math.abs(leftElbowAngle - rightElbowAngle);
    if (elbowAlignmentDiff > 15) {
      feedback.push(this.createFeedback(
        "Keep your elbows equally bent",
        'high',
        'alignment',
        "Keep both elbows equally bent throughout the movement"
      ));
    }

    // Check hand position
    const wristDistance = Math.abs(leftWrist.x - rightWrist.x);
    const shoulderDistance = Math.abs(leftShoulder.x - rightShoulder.x);
    if (wristDistance < shoulderDistance * 0.8) {
      feedback.push(this.createFeedback(
        "Widen your hand placement - should be slightly wider than shoulders",
        'medium',
        'form',
        "Place your hands slightly wider than your shoulders"
      ));
    } else if (wristDistance > shoulderDistance * 1.5) {
      feedback.push(this.createFeedback(
        "Bring your hands closer - should be just wider than shoulders",
        'medium',
        'form',
        "Bring your hands closer to your shoulders"
      ));
    }

    if (feedback.length === 0) {
      feedback.push(this.createFeedback(
        "Great push-up form! Keep it up!",
        'low',
        'form',
        "Keep maintaining this proper form"
      ));
    }

    return feedback;
  }

  private analyzePlankForm(keypoints: poseDetection.Keypoint[]): FeedbackItem[] {
    const feedback: FeedbackItem[] = [];
    
    // Get relevant keypoints
    const leftShoulder = keypoints.find(kp => kp.name === 'left_shoulder');
    const rightShoulder = keypoints.find(kp => kp.name === 'right_shoulder');
    const leftElbow = keypoints.find(kp => kp.name === 'left_elbow');
    const rightElbow = keypoints.find(kp => kp.name === 'right_elbow');
    const leftHip = keypoints.find(kp => kp.name === 'left_hip');
    const rightHip = keypoints.find(kp => kp.name === 'right_hip');
    const leftKnee = keypoints.find(kp => kp.name === 'left_knee');
    const rightKnee = keypoints.find(kp => kp.name === 'right_knee');
    const leftAnkle = keypoints.find(kp => kp.name === 'left_ankle');
    const rightAnkle = keypoints.find(kp => kp.name === 'right_ankle');

    if (!leftShoulder || !rightShoulder || !leftElbow || !rightElbow || 
        !leftHip || !rightHip || !leftKnee || !rightKnee || 
        !leftAnkle || !rightAnkle) {
      return [this.createFeedback(
        "Please ensure your full body is visible in the camera",
        'high',
        'safety',
        "Adjust your position or camera angle to capture your entire body"
      )];
    }

    // Calculate body angles
    const upperBodyAngle = this.calculateAngle(leftElbow, leftShoulder, leftHip);
    const lowerBodyAngle = this.calculateAngle(leftShoulder, leftHip, leftAnkle);
    const kneeAngle = this.calculateAngle(leftHip, leftKnee, leftAnkle);

    // Check shoulder-hip alignment (should be straight)
    if (Math.abs(upperBodyAngle - 180) > 15) {
      feedback.push(this.createFeedback(
        "Keep your upper body straight - align shoulders and hips",
        'high',
        'form',
        "Keep your shoulders and hips in a straight line"
      ));
    }

    // Check hip-ankle alignment (should be straight)
    if (Math.abs(lowerBodyAngle - 180) > 15) {
      feedback.push(this.createFeedback(
        "Keep your lower body straight - don't let your hips sag",
        'high',
        'form',
        "Keep your hips level and maintain a straight line"
      ));
    }

    // Check knee angle (should be straight)
    if (Math.abs(kneeAngle - 180) > 15) {
      feedback.push(this.createFeedback(
        "Keep your legs straight - don't bend your knees",
        'high',
        'form',
        "Keep your legs straight and maintain a straight line"
      ));
    }

    // Check hip height
    const hipHeight = (leftHip.y + rightHip.y) / 2;
    const shoulderHeight = (leftShoulder.y + rightShoulder.y) / 2;
    if (Math.abs(hipHeight - shoulderHeight) > 50) {
      if (hipHeight < shoulderHeight) {
        feedback.push(this.createFeedback(
          "Lower your hips - maintain a straight line",
          'medium',
          'form',
          "Lower your hips until they are level with your shoulders"
        ));
      } else {
        feedback.push(this.createFeedback(
          "Raise your hips - maintain a straight line",
          'medium',
          'form',
          "Raise your hips until they are level with your shoulders"
        ));
      }
    }

    if (feedback.length === 0) {
      feedback.push(this.createFeedback(
        "Perfect plank form! Keep holding!",
        'low',
        'form',
        "Keep maintaining this proper form"
      ));
    }

    return feedback;
  }

  private analyzeLungeForm(keypoints: poseDetection.Keypoint[]): FeedbackItem[] {
    const feedback: FeedbackItem[] = [];
    
    // Get relevant keypoints
    const leftHip = keypoints.find(kp => kp.name === 'left_hip');
    const rightHip = keypoints.find(kp => kp.name === 'right_hip');
    const leftKnee = keypoints.find(kp => kp.name === 'left_knee');
    const rightKnee = keypoints.find(kp => kp.name === 'right_knee');
    const leftAnkle = keypoints.find(kp => kp.name === 'left_ankle');
    const rightAnkle = keypoints.find(kp => kp.name === 'right_ankle');
    const leftShoulder = keypoints.find(kp => kp.name === 'left_shoulder');
    const rightShoulder = keypoints.find(kp => kp.name === 'right_shoulder');
    const nose = keypoints.find(kp => kp.name === 'nose');

    if (!leftHip || !rightHip || !leftKnee || !rightKnee || 
        !leftAnkle || !rightAnkle || !leftShoulder || !rightShoulder || !nose) {
      return [this.createFeedback(
        "Please ensure your full body is visible in the camera",
        'high',
        'safety',
        "Adjust your position or camera angle to capture your entire body"
      )];
    }

    // Check front knee angle (should be ~90 degrees)
    const frontKneeAngle = Math.min(
      this.calculateAngle(leftHip, leftKnee, leftAnkle),
      this.calculateAngle(rightHip, rightKnee, rightAnkle)
    );
    if (frontKneeAngle < 80 || frontKneeAngle > 100) {
      feedback.push(this.createFeedback(
        "Front knee should be at 90 degrees - adjust your stance",
        'high',
        'form',
        "Adjust your stance to ensure your front knee is at 90 degrees"
      ));
    }

    // Check back knee position
    const backKneeAngle = Math.max(
      this.calculateAngle(leftHip, leftKnee, leftAnkle),
      this.calculateAngle(rightHip, rightKnee, rightAnkle)
    );
    if (backKneeAngle < 130) {
      feedback.push(this.createFeedback(
        "Back leg should be more extended",
        'medium',
        'form',
        "Extend your back leg further"
      ));
    }

    // Check torso alignment
    const torsoAngle = this.calculateAngle(nose, leftShoulder, leftHip);
    if (torsoAngle < 80 || torsoAngle > 100) {
      feedback.push(this.createFeedback(
        "Keep your torso upright",
        'high',
        'form',
        "Keep your torso straight and maintain a neutral spine position"
      ));
    }

    // Check hip alignment
    const hipHeight = Math.abs(leftHip.y - rightHip.y);
    if (hipHeight > 50) {
      feedback.push(this.createFeedback(
        "Keep your hips level throughout the movement",
        'high',
        'form',
        "Keep your hips level and maintain a straight line"
      ));
    }

    if (feedback.length === 0) {
      feedback.push(this.createFeedback(
        "Excellent lunge form! Keep it up!",
        'low',
        'form',
        "Keep maintaining this proper form"
      ));
    }

    return feedback;
  }

  private analyzeDeadliftForm(keypoints: poseDetection.Keypoint[]): FeedbackItem[] {
    const feedback: FeedbackItem[] = [];
    
    // Get relevant keypoints
    const leftHip = keypoints.find(kp => kp.name === 'left_hip');
    const rightHip = keypoints.find(kp => kp.name === 'right_hip');
    const leftKnee = keypoints.find(kp => kp.name === 'left_knee');
    const rightKnee = keypoints.find(kp => kp.name === 'right_knee');
    const leftAnkle = keypoints.find(kp => kp.name === 'left_ankle');
    const rightAnkle = keypoints.find(kp => kp.name === 'right_ankle');
    const leftShoulder = keypoints.find(kp => kp.name === 'left_shoulder');
    const rightShoulder = keypoints.find(kp => kp.name === 'right_shoulder');
    const nose = keypoints.find(kp => kp.name === 'nose');

    if (!leftHip || !rightHip || !leftKnee || !rightKnee || 
        !leftAnkle || !rightAnkle || !leftShoulder || !rightShoulder || !nose) {
      return [this.createFeedback(
        "Please ensure your full body is visible in the camera",
        'high',
        'safety',
        "Adjust your position or camera angle to capture your entire body"
      )];
    }

    // Check hip hinge
    const hipAngle = this.calculateAngle(leftShoulder, leftHip, leftKnee);
    if (hipAngle > 100) {
      feedback.push(this.createFeedback(
        "Hinge more at your hips - push them back",
        'medium',
        'form',
        "Hinge more at your hips to push them back"
      ));
    }

    // Check back position
    const backAngle = this.calculateAngle(nose, leftShoulder, leftHip);
    if (backAngle < 160) {
      feedback.push(this.createFeedback(
        "Keep your back straight throughout the movement",
        'high',
        'form',
        "Keep your back straight and maintain a neutral spine position"
      ));
    }

    // Check knee position
    const kneeAngle = (
      this.calculateAngle(leftHip, leftKnee, leftAnkle) +
      this.calculateAngle(rightHip, rightKnee, rightAnkle)
    ) / 2;
    if (kneeAngle < 130) {
      feedback.push(this.createFeedback(
        "Don't bend your knees too much - this is a hip hinge",
        'high',
        'form',
        "Keep your knees straight and maintain a straight line"
      ));
    }

    // Check bar path (approximated by shoulder position)
    const shoulderDistance = Math.abs(leftShoulder.x - leftAnkle.x);
    if (shoulderDistance > 50) {
      feedback.push(this.createFeedback(
        "Keep the bar close to your legs",
        'medium',
        'safety',
        "Keep the bar close to your legs"
      ));
    }

    // Check shoulder blade position
    const shoulderAlignment = Math.abs(leftShoulder.y - rightShoulder.y);
    if (shoulderAlignment > 20) {
      feedback.push(this.createFeedback(
        "Keep your shoulders level",
        'high',
        'form',
        "Keep your shoulders level"
      ));
    }

    if (feedback.length === 0) {
      feedback.push(this.createFeedback(
        "Great deadlift form! Maintain this technique!",
        'low',
        'form',
        "Keep maintaining this proper form"
      ));
    }

    return feedback;
  }

  private analyzeBurpeeForm(keypoints: poseDetection.Keypoint[]): FeedbackItem[] {
    const feedback: FeedbackItem[] = [];
    
    // Get relevant keypoints
    const leftShoulder = keypoints.find(kp => kp.name === 'left_shoulder');
    const rightShoulder = keypoints.find(kp => kp.name === 'right_shoulder');
    const leftHip = keypoints.find(kp => kp.name === 'left_hip');
    const rightHip = keypoints.find(kp => kp.name === 'right_hip');
    const leftKnee = keypoints.find(kp => kp.name === 'left_knee');
    const rightKnee = keypoints.find(kp => kp.name === 'right_knee');
    const leftAnkle = keypoints.find(kp => kp.name === 'left_ankle');
    const rightAnkle = keypoints.find(kp => kp.name === 'right_ankle');
    const leftWrist = keypoints.find(kp => kp.name === 'left_wrist');
    const rightWrist = keypoints.find(kp => kp.name === 'right_wrist');

    if (!leftShoulder || !rightShoulder || !leftHip || !rightHip || 
        !leftKnee || !rightKnee || !leftAnkle || !rightAnkle ||
        !leftWrist || !rightWrist) {
      return [this.createFeedback(
        "Please ensure your full body is visible in the camera",
        'high',
        'safety',
        "Adjust your position or camera angle to capture your entire body"
      )];
    }

    // Check plank position
    const plankAlignment = this.calculateVerticalAlignment([
      leftShoulder, rightShoulder, leftHip, rightHip
    ]);
    if (plankAlignment < 0.7) {
      feedback.push(this.createFeedback(
        "Keep your body straight in plank position",
        'high',
        'form',
        "Maintain a straight line from shoulders to hips"
      ));
    }

    // Check jump height
    const hipHeight = (leftHip.y + rightHip.y) / 2;
    const ankleHeight = (leftAnkle.y + rightAnkle.y) / 2;
    const jumpHeight = Math.abs(hipHeight - ankleHeight);
    
    if (jumpHeight < 100) {
      feedback.push(this.createFeedback(
        "Jump higher for full range of motion",
        'medium',
        'range',
        "Explode upward with more power"
      ));
    }

    // Check hand position in pushup
    const wristPosition = (leftWrist.y + rightWrist.y) / 2;
    const shoulderPosition = (leftShoulder.y + rightShoulder.y) / 2;
    
    if (Math.abs(wristPosition - shoulderPosition) > 50) {
      feedback.push(this.createFeedback(
        "Keep hands under shoulders in pushup position",
        'medium',
        'form',
        "Position your hands directly under your shoulders"
      ));
    }

    if (feedback.length === 0) {
      feedback.push(this.createFeedback(
        "Excellent burpee form!",
        'low',
        'form',
        "Keep maintaining this proper form"
      ));
    }

    return feedback;
  }

  private analyzeMountainClimberForm(keypoints: poseDetection.Keypoint[]): FeedbackItem[] {
    const feedback: FeedbackItem[] = [];
    
    // Get relevant keypoints
    const leftShoulder = keypoints.find(kp => kp.name === 'left_shoulder');
    const rightShoulder = keypoints.find(kp => kp.name === 'right_shoulder');
    const leftHip = keypoints.find(kp => kp.name === 'left_hip');
    const rightHip = keypoints.find(kp => kp.name === 'right_hip');
    const leftKnee = keypoints.find(kp => kp.name === 'left_knee');
    const rightKnee = keypoints.find(kp => kp.name === 'right_knee');
    const leftAnkle = keypoints.find(kp => kp.name === 'left_ankle');
    const rightAnkle = keypoints.find(kp => kp.name === 'right_ankle');
    const leftWrist = keypoints.find(kp => kp.name === 'left_wrist');
    const rightWrist = keypoints.find(kp => kp.name === 'right_wrist');

    if (!leftShoulder || !rightShoulder || !leftHip || !rightHip || 
        !leftKnee || !rightKnee || !leftAnkle || !rightAnkle ||
        !leftWrist || !rightWrist) {
      return [this.createFeedback(
        "Please ensure your full body is visible in the camera",
        'high',
        'safety',
        "Adjust your position or camera angle to capture your entire body"
      )];
    }

    // Check plank position
    const plankAlignment = this.calculateVerticalAlignment([
      leftShoulder, rightShoulder, leftHip, rightHip
    ]);
    if (plankAlignment < 0.7) {
      feedback.push(this.createFeedback(
        "Keep your body straight in plank position",
        'high',
        'form',
        "Maintain a straight line from shoulders to hips"
      ));
    }

    // Check knee drive height and alternation
    const leftKneeHeight = leftKnee.y - leftHip.y;
    const rightKneeHeight = rightKnee.y - rightHip.y;
    
    if (Math.abs(leftKneeHeight) < 30 && Math.abs(rightKneeHeight) < 30) {
      feedback.push(this.createFeedback(
        "Drive knees higher towards chest",
        'medium',
        'range',
        "Bring your knees closer to your chest for better engagement"
      ));
    }

    // Check if knees are alternating properly
    if (Math.abs(leftKneeHeight - rightKneeHeight) < 20) {
      feedback.push(this.createFeedback(
        "Alternate legs more distinctly",
        'medium',
        'form',
        "Drive one knee up while the other leg is extended"
      ));
    }

    // Check hip stability
    const hipMovement = Math.abs(leftHip.x - rightHip.x);
    if (hipMovement > 50) {
      feedback.push(this.createFeedback(
        "Keep hips stable",
        'high',
        'form',
        "Minimize hip rotation and maintain stability"
      ));
    }

    if (feedback.length === 0) {
      feedback.push(this.createFeedback(
        "Excellent mountain climber form!",
        'low',
        'form',
        "Keep maintaining this proper form"
      ));
    }

    return feedback;
  }

  private calculateAngle(a: poseDetection.Keypoint, b: poseDetection.Keypoint, c: poseDetection.Keypoint): number {
    if (!a || !b || !c || !a.score || !b.score || !c.score) return 0;
    
    // Only calculate if confidence is above threshold
    if (a.score < this.config.minConfidence || 
        b.score < this.config.minConfidence || 
        c.score < this.config.minConfidence) {
      return 0;
    }

    const radians = Math.atan2(c.y - b.y, c.x - b.x) - Math.atan2(a.y - b.y, a.x - b.x);
    let angle = Math.abs((radians * 180.0) / Math.PI);
    
    if (angle > 180.0) {
      angle = 360 - angle;
    }
    
    return angle;
  }

  private calculateDistance(a: poseDetection.Keypoint, b: poseDetection.Keypoint): number {
    if (!a || !b || !a.score || !b.score) return 0;
    
    // Only calculate if confidence is above threshold
    if (a.score < this.config.minConfidence || b.score < this.config.minConfidence) {
      return 0;
    }

    return Math.sqrt(Math.pow(b.x - a.x, 2) + Math.pow(b.y - a.y, 2));
  }

  private calculateVerticalAlignment(points: poseDetection.Keypoint[]): number {
    if (!points.every(p => p && p.score && p.score >= this.config.minConfidence)) {
      return 0;
    }

    // Calculate average x-coordinate
    const avgX = points.reduce((sum, p) => sum + p.x, 0) / points.length;
    
    // Calculate deviation from vertical line
    const deviation = points.reduce((sum, p) => sum + Math.abs(p.x - avgX), 0) / points.length;
    
    // Convert to a score between 0 and 1
    return Math.max(0, 1 - (deviation / 100));
  }

  private calculateLateralAlignment(points: poseDetection.Keypoint[]): number {
    if (!points.every(p => p && p.score && p.score >= this.config.minConfidence)) {
      return 0;
    }

    // Calculate average y-coordinate
    const avgY = points.reduce((sum, p) => sum + p.y, 0) / points.length;
    
    // Calculate deviation from lateral line
    const deviation = points.reduce((sum, p) => sum + Math.abs(p.y - avgY), 0) / points.length;
    
    // Convert to a score between 0 and 1
    return Math.max(0, 1 - (deviation / 100));
  }

  private calculateSymmetry(leftPoint: poseDetection.Keypoint, rightPoint: poseDetection.Keypoint, midline: number): number {
    if (!leftPoint || !rightPoint || !leftPoint.score || !rightPoint.score) return 0;
    
    if (leftPoint.score < this.config.minConfidence || rightPoint.score < this.config.minConfidence) {
      return 0;
    }

    const leftDistance = Math.abs(leftPoint.x - midline);
    const rightDistance = Math.abs(rightPoint.x - midline);
    
    // Calculate symmetry score (1 = perfect symmetry, 0 = completely asymmetric)
    return 1 - Math.min(1, Math.abs(leftDistance - rightDistance) / 50);
  }

  private isAngleWithinRange(angle: number, targetAngle: number, tolerance: number = 15): boolean {
    return Math.abs(angle - targetAngle) <= tolerance;
  }

  private getJointVelocity(currentPoint: poseDetection.Keypoint, previousPoint: poseDetection.Keypoint): number {
    if (!currentPoint || !previousPoint || !currentPoint.score || !previousPoint.score) return 0;
    
    if (currentPoint.score < this.config.minConfidence || previousPoint.score < this.config.minConfidence) {
      return 0;
    }

    return Math.sqrt(
      Math.pow(currentPoint.x - previousPoint.x, 2) + 
      Math.pow(currentPoint.y - previousPoint.y, 2)
    );
  }

  private async processAnalysisResult(analysis: PoseAnalysisResult): Promise<void> {
    // Store analysis results
    await storageService.cacheFormAnalysis(
      `${this.config.exerciseType}-${analysis.timestamp}`,
      analysis
    );
    
    // Emit analysis results for real-time feedback
    if (this.config.onAnalysisResult) {
      this.config.onAnalysisResult(analysis);
    }
  }

  stopAnalysis(): void {
    this.isAnalyzing = false;
  }

  async cleanup(): Promise<void> {
    this.stopAnalysis();
    if (this.detector) {
      await this.detector.dispose();
      this.detector = null;
    }
    this.cleanup();
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

  private calculateBodyAlignment(keypoints: poseDetection.Keypoint[]): BodyAlignment {
    return {
      vertical: calculateVerticalAlignment(keypoints),
      lateral: calculateLateralAlignment(keypoints),
      confidence: this.calculateConfidenceScore(keypoints)
    };
  }

  public getState() {
    return { ...this.state };
  }

  public async analyzePose(videoElement: HTMLVideoElement): Promise<PoseAnalysisResult> {
    if (!this.detector) {
      await this.initialize();
    }

    const poses = await this.detector!.estimatePoses(videoElement, {
      maxPoses: 1,
      flipHorizontal: false
    });

    if (poses.length === 0) {
      throw new Error('No pose detected');
    }

    const pose = poses[0];
    const keypoints = this.normalizeKeypoints(pose.keypoints);
    const jointAngles = this.calculateJointAngles(keypoints);
    const movementPath = this.analyzeMovementPath(keypoints);

    return {
      keypoints,
      jointAngles,
      movementPath,
      metrics: {
        alignment: this.calculateAlignment(keypoints, jointAngles),
        stability: this.calculateStability(movementPath),
        symmetry: this.calculateSymmetry(keypoints),
        consistency: this.calculateConsistency(movementPath)
      }
    };
  }

  private normalizeKeypoints(keypoints: poseDetection.Keypoint[]): poseDetection.Keypoint[] {
    // Normalize coordinates to 0-1 range
    const xCoords = keypoints.map(kp => kp.x);
    const yCoords = keypoints.map(kp => kp.y);
    const minX = Math.min(...xCoords);
    const maxX = Math.max(...xCoords);
    const minY = Math.min(...yCoords);
    const maxY = Math.max(...yCoords);

    return keypoints.map(kp => ({
      ...kp,
      x: (kp.x - minX) / (maxX - minX),
      y: (kp.y - minY) / (maxY - minY)
    }));
  }

  private analyzeMovementPath(keypoints: poseDetection.Keypoint[]): MovementPath {
    // Track movement of key joints
    const trackJoint = (jointName: string) => {
      const joint = keypoints.find(kp => kp.name === jointName);
      return joint ? { x: joint.x, y: joint.y } : null;
    };

    return {
      shoulders: {
        left: trackJoint('left_shoulder'),
        right: trackJoint('right_shoulder')
      },
      hips: {
        left: trackJoint('left_hip'),
        right: trackJoint('right_hip')
      },
      knees: {
        left: trackJoint('left_knee'),
        right: trackJoint('right_knee')
      },
      ankles: {
        left: trackJoint('left_ankle'),
        right: trackJoint('right_ankle')
      }
    };
  }

  private calculateAlignment(
    keypoints: poseDetection.Keypoint[],
    angles: JointAngles
  ): number {
    // Calculate vertical alignment score
    const verticalJoints = ['shoulder', 'hip', 'knee', 'ankle'];
    let alignmentScore = 0;
    let count = 0;

    // Check left side alignment
    const leftSide = verticalJoints.map(joint => 
      keypoints.find(kp => kp.name === `left_${joint}`));
    if (leftSide.every(joint => joint)) {
      const xCoords = leftSide.map(joint => joint!.x);
      const deviation = Math.std(xCoords);
      alignmentScore += 1 - Math.min(deviation, 1);
      count++;
    }

    // Check right side alignment
    const rightSide = verticalJoints.map(joint => 
      keypoints.find(kp => kp.name === `right_${joint}`));
    if (rightSide.every(joint => joint)) {
      const xCoords = rightSide.map(joint => joint!.x);
      const deviation = Math.std(xCoords);
      alignmentScore += 1 - Math.min(deviation, 1);
      count++;
    }

    return count > 0 ? alignmentScore / count : 0;
  }

  private calculateStability(keypoints: poseDetection.Keypoint[]): number {
    // Calculate stability based on joint movement variance
    const stabilityScores = [];
    const keyJoints = ['shoulder', 'hip', 'knee'];

    for (const joint of keyJoints) {
      const leftJoint = keypoints.find(kp => kp.name === `left_${joint}`);
      const rightJoint = keypoints.find(kp => kp.name === `right_${joint}`);

      if (leftJoint && rightJoint) {
        const jointMovement = Math.sqrt(
          Math.pow(leftJoint.x - rightJoint.x, 2) +
          Math.pow(leftJoint.y - rightJoint.y, 2)
        );
        stabilityScores.push(1 - Math.min(jointMovement, 1));
      }
    }

    return stabilityScores.length > 0 ?
      stabilityScores.reduce((a, b) => a + b) / stabilityScores.length : 0;
  }

  private calculateSymmetry(
    keypoints: poseDetection.Keypoint[]
  ): number {
    // Calculate symmetry based on joint angles and positions
    const symmetryScores = [];

    // Compare joint angles
    const jointPairs = [
      ['leftElbow', 'rightElbow'],
      ['leftShoulder', 'rightShoulder'],
      ['leftHip', 'rightHip'],
      ['leftKnee', 'rightKnee']
    ];

    for (const [left, right] of jointPairs) {
      const leftAngle = this.calculateAngle(keypoints, left, right);
      const rightAngle = this.calculateAngle(keypoints, right, left);
      const angleDiff = Math.abs(leftAngle - rightAngle) / 180;
      symmetryScores.push(1 - angleDiff);
    }

    return symmetryScores.length > 0 ?
      symmetryScores.reduce((a, b) => a + b) / symmetryScores.length : 0;
  }

  private calculateConsistency(movementPath: MovementPath): number {
    // Calculate consistency based on movement smoothness
    const consistencyScores = [];

    // Check shoulder movement consistency
    if (movementPath.shoulders.left && movementPath.shoulders.right) {
      const shoulderMovement = Math.sqrt(
        Math.pow(movementPath.shoulders.left.x - movementPath.shoulders.right.x, 2) +
        Math.pow(movementPath.shoulders.left.y - movementPath.shoulders.right.y, 2)
      );
      consistencyScores.push(1 - Math.min(shoulderMovement, 1));
    }

    // Check hip movement consistency
    if (movementPath.hips.left && movementPath.hips.right) {
      const hipMovement = Math.sqrt(
        Math.pow(movementPath.hips.left.x - movementPath.hips.right.x, 2) +
        Math.pow(movementPath.hips.left.y - movementPath.hips.right.y, 2)
      );
      consistencyScores.push(1 - Math.min(hipMovement, 1));
    }

    return consistencyScores.length > 0 ?
      consistencyScores.reduce((a, b) => a + b) / consistencyScores.length : 0;
  }

  private handleError(error: Error) {
    this.errorCount++;
    this.emit('error', error);

    if (this.errorCount >= this.maxErrors) {
      this.stopAnalysis();
      setTimeout(() => this.recover(), this.recoveryTimeout);
    }
  }

  private recover() {
    this.errorCount = 0;
    this.initialize();
  }
}

// Helper function for standard deviation
Math.std = function(arr: number[]): number {
  const mean = arr.reduce((a, b) => a + b) / arr.length;
  const variance = arr.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / arr.length;
  return Math.sqrt(variance);
};

export const poseAnalysisService = PoseAnalysisService.getInstance({
  minConfidence: 0.3,
  modelType: 'MoveNet',
  exerciseType: 'squat'
}); 