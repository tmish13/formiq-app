import { ExerciseType } from '../services/exerciseLibraryService';
import { Keypoint } from '@tensorflow-models/pose-detection';
import { MLScores, PoseData, PoseIssue } from './ml';

export interface Point2D {
  x: number;
  y: number;
}

export interface JointAngle {
  value: number;
  confidence: number;
}

export interface JointAngleMeasurement {
  joint: string;
  angle: number;
  confidence?: number;
}

export interface JointAngles {
  leftKnee?: JointAngle;
  rightKnee?: JointAngle;
  leftHip?: JointAngle;
  rightHip?: JointAngle;
  leftElbow?: JointAngle;
  rightElbow?: JointAngle;
  leftShoulder?: JointAngle;
  rightShoulder?: JointAngle;
}

export interface MovementPath {
  points: Array<{ x: number; y: number; timestamp: number }>;
  smoothness: number;
  consistency: number;
}

export interface FormTip {
  id: string;
  message: string;
  type: 'warning' | 'error' | 'success';
  position: {
    top: string;
    left: string;
  };
  confidence?: number;
  timestamp?: number;
}

export interface FormAnalysis {
  id: string;
  userId: string;
  exerciseType: string;
  videoUrl: string;
  thumbnailUrl?: string;
  score: number;
  tips: FormTip[];
  metadata: {
    duration: number;
    jointAngles?: JointAngles;
    keypoints?: Array<{
      x: number;
      y: number;
      score: number;
      name: string;
    }>;
  };
  feedback: string[];
  riskLevel: 'low' | 'medium' | 'high';
  createdAt: string;
  updatedAt: string;
}

export interface PoseAnalysisResult {
  keypoints: Array<{ x: number; y: number; score: number; name: string }>;
  jointAngles: JointAngles;
  movementPath: MovementPath;
  metrics: {
    alignment: number;
    stability: number;
    symmetry: number;
    consistency: number;
  };
  score: number;
  // Enhanced with ML scores
  ml_scores?: MLScores;
  detected_issues?: PoseIssue[];
  feedback: FormFeedback[];
  timestamp: number;
}

export interface FormFeedback {
  message: string;
  confidence: number;
  type: 'warning' | 'error' | 'success';
  jointName?: string;
  suggestion?: string;
}

export interface FormAnalysisRequest {
  keypoints?: Keypoint[];
  videoUrl?: string;
  exercise_id?: string;
  duration?: number;
}

export interface FormAnalysisResult {
  confidence: number;
  isReliable: boolean;
  keypoints: Keypoint[];
  angles: JointAngles;
  feedback: FormFeedback[];
  suggestions: string[];
  timestamp: number;
  videoUrl: string;
  risk_level?: 'low' | 'medium' | 'high';
  comparison_score?: number;
  // Add missing metrics property for UI components
  metrics: {
    alignment: number;
    stability: number;
    symmetry: number;
    consistency: number;
  };
  // Enhanced with ML analysis
  ml_scores?: MLScores;
  detected_issues?: PoseIssue[];
  pose_data?: PoseData[];
}

export interface FormAnalysisProgress {
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
  message?: string;
}

export interface FormAnalysisStats {
  averageConfidence: number;
  successRate: number;
  processingTime: number;
}

export interface FormAnalysisFilters {
  startDate?: string;
  endDate?: string;
  exerciseType?: ExerciseType;
  status?: FormAnalysisResponse['status'];
}

export interface FormAnalysisHistory {
  id: string;
  user_id: string;
  confidence: number;
  risk_level: 'low' | 'medium' | 'high';
  summary: string;
  created_at: string;
}

export interface FormAnalysisResponse {
  result: FormAnalysisResult;
  stats: FormAnalysisStats;
  status: 'success' | 'error';
  message?: string;
} 