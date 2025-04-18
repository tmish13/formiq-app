import * as poseDetection from '@tensorflow-models/pose-detection';
import { Keypoint } from '@tensorflow-models/pose-detection';

export type ExerciseType = 'squat' | 'pushup' | 'plank' | 'lunges' | 'deadlift' | 'burpees' | 'mountain_climbers';

export interface JointAngle {
  joint: string;
  angle: number;
  confidence: number;
  isCorrect?: boolean;
}

export interface BodyAlignment {
  verticalAlignment: number;
  lateralAlignment: number;
  coreStability: number;
  issues: AlignmentIssue[];
}

export interface AlignmentIssue {
  type: 'vertical' | 'lateral' | 'core';
  severity: 'error' | 'warning';
  description: string;
}

export interface MovementPathway {
  points: {
    x: number;
    y: number;
    timestamp: number;
  }[];
  deviation: number;
  smoothness: number;
}

export interface PathwayDeviation {
  point: {
    x: number;
    y: number;
  };
  expectedPoint: {
    x: number;
    y: number;
  };
  distance: number;
  type: string;
  severity: 'error' | 'warning';
}

export interface Point {
  x: number;
  y: number;
  z?: number;
}

export interface FormValidationResult {
  isValid: boolean;
  score: number;
  issues: {
    message: string;
    severity: 'error' | 'warning';
  }[];
  feedback: string[];
}

export interface MovementMetrics {
  velocity: number;
  acceleration: number;
  jerk: number;
  smoothness: number;
}

export interface FeedbackItem {
  text: string;
  severity: 'high' | 'medium' | 'low';
  type: 'form' | 'range' | 'safety' | 'alignment' | 'tempo' | 'pathway' | 'stability';
  details: string;
  confidence: number;
  timestamp: number;
  affectedJoints?: string[];
  suggestedCorrection?: string;
}

export interface PoseAnalysisResult {
  keypoints: Keypoint[];
  angles: JointAngle[];
  formValidation: FormValidationResult;
  metrics: MovementMetrics;
  confidence: number;
  phase: 'start' | 'middle' | 'end';
  repetitionCount: number;
}

export interface PoseAnalysisConfig {
  minConfidence: number;
  modelType: 'MoveNet' | 'BlazePose';
  exerciseType: string;
  deviceOptimization?: {
    targetFPS: number;
    downsampleFactor: number;
    useWebGL: boolean;
    enableSmoothing: boolean;
    batchSize: number;
    kernelOptimization: boolean;
  };
  analysis?: {
    smoothingWindow: number;
    minRequiredKeypoints: number;
    confidenceThreshold: number;
    jointAngleTolerance: number;
    movementThresholds: {
      velocity: number;
      acceleration: number;
      jerk: number;
    };
  };
} 