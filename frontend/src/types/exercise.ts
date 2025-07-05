import { Keypoint } from '@tensorflow-models/pose-detection';

export interface FeedbackItem {
  type: 'success' | 'warning' | 'error';
  message: string;
  suggestion: string;
  severity?: 'low' | 'medium' | 'high';
  text?: string;
  details?: string;
  timestamp?: number;
}

export interface ExerciseConfig {
  exerciseType: string;
  targetAngles: {
    [key: string]: {
      angle: number;
      tolerance: number;
    };
  };
  phases: string[];
  metrics: {
    [key: string]: {
      min: number;
      max: number;
      optimal: number;
    };
  };
} 