export type SubscriptionTier = 'free' | 'basic' | 'pro';

export type ExerciseType = 'squat' | 'deadlift' | 'bench_press' | 'overhead_press';

export interface FormCheck {
  id: number;
  user_id: number;
  exercise_type: ExerciseType;
  video_url: string;
  score: number;
  overall_feedback: string;
  issues: string[];
  created_at: string;
}

export interface User {
  id: number;
  email: string;
  username: string;
  subscription_tier: SubscriptionTier;
  subscription_end_date: string | null;
  is_email_verified: boolean;
}

export interface ApiRequestConfig {
  method?: 'get' | 'post' | 'put' | 'delete';
  data?: any;
  params?: any;
}

export interface ApiResponseType<T> {
  data: T;
  status: number;
  message?: string;
}

export interface ApiError {
  message: string;
  status: number;
  response?: {
    data: any;
    status: number;
  };
} 