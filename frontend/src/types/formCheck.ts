export type ExerciseType = 'squat' | 'deadlift' | 'bench_press' | 'overhead_press';

export type FormCheckStatus = 'pending' | 'analyzing' | 'completed' | 'failed';

export type FeedbackType = 'posture' | 'form' | 'technique' | 'safety';

export type FeedbackSeverity = 'low' | 'medium' | 'high';

export interface FeedbackItem {
  type: FeedbackType;
  severity: FeedbackSeverity;
  timestamp: number;
  description: string;
  suggestions: string;
}

export interface FormCheck {
  id: number;
  user_id: number;
  exercise_type: ExerciseType;
  video_url: string;
  analysis_url?: string;
  score?: number;
  overall_feedback?: string;
  issues?: string[];
  status: FormCheckStatus;
  processing_time?: number;
  confidence_score?: number;
  form_metadata?: Record<string, any>;
  results?: Record<string, any>;
  created_at: string;
  updated_at: string;
  feedback_items?: FeedbackItem[];
} 