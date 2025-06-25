export type ExerciseType = 'squat' | 'deadlift' | 'bench_press' | 'overhead_press' | 'barbell_row' | 'pullup' | 'pushup';

export type FormCheckStatus = 'pending' | 'analyzing' | 'completed' | 'failed';

export type FeedbackType = 'posture' | 'form' | 'technique' | 'safety' | 'general' | 'range_of_motion' | 'balance' | 'tempo';

export type FeedbackSeverity = 'low' | 'medium' | 'high';

export interface FeedbackItem {
  id?: number;
  form_check_id?: number;
  type: FeedbackType;
  severity: FeedbackSeverity;
  timestamp: number;
  description: string;
  message?: string;
  suggestions: string;
  joint_angles?: Record<string, number>;
  is_ai_generated?: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface FormCheck {
  id: number;
  user_id: number;
  exercise_type: ExerciseType;
  video_url: string;
  analysis_url?: string;
  score?: number;
  overall_score?: number;
  summary?: string;
  notes?: string;
  overall_feedback?: string;
  issues?: string[];
  status: FormCheckStatus;
  processing_time?: number;
  confidence_score?: number;
  form_metadata?: Record<string, any>;
  results?: Record<string, any>;
  thumbnail_url?: string;
  created_at: string;
  updated_at: string;
  feedback_items?: FeedbackItem[];
  // ML Model Scores (0-100 scale)
  posture_score?: number;        // Alignment and correctness of body positioning
  stability_score?: number;      // Balance and control during exercise
  depth_score?: number;          // Range of motion and movement depth
  ml_model_version?: string;     // Version of ML model used for analysis
  classification_confidence?: number; // Model confidence in exercise classification
}

export interface FormCheckResponse {
  id: string;
  video_url: string;
  exercise_id: string;
  user_id: string;
  status: 'pending' | 'processing' | 'completed';
  score?: number;
  overall_feedback?: string;
  analysis_url?: string;
  created_at: string;
  updated_at?: string;
  // ML Model Scores (0-100 scale)
  posture_score?: number;
  stability_score?: number;
  depth_score?: number;
  ml_model_version?: string;
  classification_confidence?: number;
} 