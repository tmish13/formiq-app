// Local minimal Keypoint definition — avoids dependency on @tensorflow-models/pose-detection
export interface Keypoint {
  x: number;
  y: number;
  score?: number;
  name?: string;
}

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