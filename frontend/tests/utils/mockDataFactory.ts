/**
 * Mock data factory for testing
 * 
 * This file provides functions to create mock data objects for testing purposes.
 */

// Mock user type
export interface MockUser {
  id: string;
  name: string;
  email: string;
  profile_image?: string;
  created_at: string;
  subscription_tier: 'free' | 'premium' | 'pro';
}

// Mock form check type
export interface MockFormCheck {
  id: string;
  user_id: string;
  exercise_type: string;
  video_url: string;
  score?: number;
  feedback?: string;
  created_at: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
}

// Mock analysis result type
export interface MockAnalysisResult {
  id: string;
  form_check_id: string;
  score: number;
  feedback: string;
  key_points: Array<{
    timestamp: number;
    observation: string;
    severity: 'low' | 'medium' | 'high';
  }>;
  created_at: string;
}

/**
 * Creates a mock user with the given overrides
 * @param overrides - Optional properties to override default values
 */
export const createMockUser = (overrides?: Partial<MockUser>): MockUser => ({
  id: 'user-123',
  name: 'Test User',
  email: 'test@example.com',
  profile_image: 'https://example.com/profile.jpg',
  created_at: new Date().toISOString(),
  subscription_tier: 'free',
  ...overrides
});

/**
 * Creates a mock form check with the given overrides
 * @param overrides - Optional properties to override default values
 */
export const createMockFormCheck = (overrides?: Partial<MockFormCheck>): MockFormCheck => ({
  id: 'form-check-123',
  user_id: 'user-123',
  exercise_type: 'squat',
  video_url: 'https://example.com/video.mp4',
  score: 80,
  feedback: 'Good form, but work on depth and keeping chest up.',
  created_at: new Date().toISOString(),
  status: 'completed',
  ...overrides
});

/**
 * Creates a mock analysis result with the given overrides
 * @param overrides - Optional properties to override default values
 */
export const createMockAnalysisResult = (overrides?: Partial<MockAnalysisResult>): MockAnalysisResult => ({
  id: 'analysis-123',
  form_check_id: 'form-check-123',
  score: 80,
  feedback: 'Your form is good overall, but there are some areas to improve.',
  key_points: [
    {
      timestamp: 3.5,
      observation: 'Knees caving in slightly',
      severity: 'medium'
    },
    {
      timestamp: 7.2,
      observation: 'Good depth achieved',
      severity: 'low'
    },
    {
      timestamp: 12.5,
      observation: 'Back rounding at bottom of movement',
      severity: 'high'
    }
  ],
  created_at: new Date().toISOString(),
  ...overrides
}); 