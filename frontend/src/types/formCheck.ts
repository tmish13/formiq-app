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
} 