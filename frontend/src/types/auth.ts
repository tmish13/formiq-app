/**
 * Authentication related types
 */

// User model returned from API
export interface User {
  id: string;
  email: string;
  username: string;
  full_name?: string;
  is_active: boolean;
  is_verified: boolean;
  is_superuser: boolean;
  subscription_tier: string;
  subscription_status?: string;
  created_at: string;
  updated_at?: string;
  last_login?: string;
  profile_image_url?: string;
  fitness_goals?: string[];
  fitness_level?: 'beginner' | 'intermediate' | 'advanced';
  weight?: number;
  height?: number;
}

// Credentials for user login
export interface LoginCredentials {
  email: string;
  password: string;
}

// Data for new user registration
export interface RegisterData {
  email: string;
  password: string;
  username?: string;
  name?: string;
  confirm_password?: string;
}

// Auth response from server for login/register
export interface AuthResponse {
  user: User;
  access_token: string;
  refresh_token: string;
  token_type: string;
  user_id: string;
  expires_in: number;
}

// Password reset request
export interface PasswordResetRequest {
  email: string;
}

// Password reset confirmation
export interface PasswordResetConfirm {
  token: string;
  new_password: string;
  confirm_password: string;
}

// Auth state in Redux store
export interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
}

// CSRF token response
export interface CSRFTokenResponse {
  csrf_token: string;
} 