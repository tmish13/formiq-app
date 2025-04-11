export type SubscriptionTier = 'free' | 'basic' | 'pro';

export type ExerciseType = 'squat' | 'deadlift' | 'bench_press' | 'overhead_press';

export interface User {
  id: string;
  email: string;
  name: string;
  role: string;
  subscription_tier: SubscriptionTier;
  subscription_end_date: string | null;
  created_at: string;
  updated_at: string;
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

export interface AuthResponse {
  access_token: string;
  refresh_token?: string;
  token_type?: string;
  expires_in?: number;
  user: User;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterData {
  email: string;
  password: string;
  name: string;
}

export interface Subscription {
  id: string;
  user_id: string;
  tier: SubscriptionTier;
  status: 'active' | 'cancelled' | 'expired';
  start_date: string;
  end_date: string;
  cancel_at_period_end: boolean;
  canceled_at?: string;
  created_at: string;
  updated_at: string;
}

export interface SubscriptionPlan {
  id: string;
  name: string;
  description: string;
  price: number;
  interval: 'monthly' | 'yearly';
  features: string[];
  stripe_price_id: string;
  stripe_product_id: string;
  is_popular?: boolean;
  created_at: string;
  updated_at: string;
}

export * from './workout';
export * from './user';
export * from './subscription';
export * from './formCheck'; 