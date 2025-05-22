import { AxiosResponse, AxiosError } from 'axios';

/**
 * Factory for creating standardized API responses for testing.
 * This helps ensure consistent API simulation across tests.
 */
export class ApiResponseFactory {
  /**
   * Creates a successful API response with the given data.
   * @param data The data to include in the response
   * @param status The HTTP status code (defaults to 200)
   * @returns A successful API response object
   */
  static success<T = any>(data: T, status = 200) {
    return {
      status,
      data,
      error: null
    };
  }

  /**
   * Creates an error API response.
   * @param message The error message
   * @param status The HTTP status code (defaults to 400)
   * @returns An error API response object
   */
  static error(message: string, status = 400) {
    return {
      status,
      data: null,
      error: {
        message,
        code: status.toString()
      }
    };
  }

  /**
   * Creates a network error response.
   * @returns A network error response
   */
  static networkError() {
    return {
      status: 0,
      data: null,
      error: {
        message: 'Network error',
        code: 'NETWORK_ERROR'
      }
    };
  }

  /**
   * Creates an unauthorized error response.
   * @returns An unauthorized error response
   */
  static unauthorized() {
    return this.error('Unauthorized. Please login and try again.', 401);
  }

  /**
   * Creates a forbidden error response.
   * @returns A forbidden error response
   */
  static forbidden() {
    return this.error('You do not have permission to access this resource.', 403);
  }

  /**
   * Creates a not found error response.
   * @returns A not found error response
   */
  static notFound() {
    return this.error('The requested resource was not found.', 404);
  }

  /**
   * Creates a server error response.
   * @returns A server error response
   */
  static serverError() {
    return this.error('An unexpected server error occurred.', 500);
  }

  /**
   * Creates a mock form analysis result with feedback.
   * @returns A sample form analysis response
   */
  static formAnalysisResponse() {
    return this.success({
      id: 'mock-analysis-id',
      exercise_type: 'squat',
      score: 8.5,
      feedback: [
        {
          type: 'form',
          severity: 'medium',
          message: 'Knees are caving inward',
          details: 'Keep your knees aligned with your toes',
          timestamp: 2.5,
          confidence: 0.85
        },
        {
          type: 'range',
          severity: 'high',
          message: 'Not reaching full depth',
          details: 'Lower your hips below parallel with knees',
          timestamp: 4.2,
          confidence: 0.92
        },
        {
          type: 'form',
          severity: 'low',
          message: 'Slight forward lean',
          details: 'Try to keep torso more upright',
          timestamp: 6.1,
          confidence: 0.78
        }
      ],
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    });
  }

  /**
   * Creates a mock user profile response.
   * @returns A sample user profile response
   */
  static userProfileResponse() {
    return this.success({
      id: 'user-123',
      username: 'test_user',
      email: 'test@example.com',
      first_name: 'Test',
      last_name: 'User',
      profile_pic_url: 'https://example.com/profile.jpg',
      subscription_tier: 'pro',
      is_active: true,
      last_login: new Date().toISOString(),
      created_at: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString() // 30 days ago
    });
  }

  /**
   * Creates a mock login response.
   * @returns A sample login response with tokens
   */
  static loginResponse() {
    return this.success({
      access_token: 'mock-jwt-token',
      refresh_token: 'mock-refresh-token',
      user: {
        id: 'user-123',
        username: 'test_user',
        email: 'test@example.com',
        first_name: 'Test',
        last_name: 'User'
      }
    });
  }

  /**
   * Creates a mock form checks list response.
   * @param count Number of items to include (default: 3)
   * @returns A sample form checks list response
   */
  static formChecksListResponse(count = 3) {
    const formChecks = [];
    
    for (let i = 0; i < count; i++) {
      formChecks.push({
        id: `form-check-${i}`,
        exercise_type: i % 2 === 0 ? 'squat' : 'deadlift',
        video_url: `https://example.com/videos/workout-${i}.mp4`,
        thumbnail_url: `https://example.com/thumbnails/workout-${i}.jpg`,
        status: 'completed',
        score: Math.floor(Math.random() * 3) + 7, // 7-10 range
        feedback_count: Math.floor(Math.random() * 5) + 1,
        created_at: new Date(Date.now() - i * 24 * 60 * 60 * 1000).toISOString(),
        updated_at: new Date(Date.now() - i * 24 * 60 * 60 * 1000).toISOString()
      });
    }
    
    return this.success(formChecks);
  }

  /**
   * Creates a mock upload success response.
   * @returns A sample upload success response
   */
  static uploadSuccessResponse() {
    return this.success({
      id: 'upload-123',
      file_url: 'https://example.com/uploads/video.mp4',
      mime_type: 'video/mp4',
      size: 1024 * 1024 * 5, // 5MB
      created_at: new Date().toISOString()
    });
  }

  /**
   * Creates a mock progress stats response.
   * @returns A sample progress stats response
   */
  static progressStatsResponse() {
    return this.success({
      total_workouts: 15,
      exercise_breakdown: {
        squat: 5,
        deadlift: 4,
        plank: 3,
        pushup: 2,
        lunge: 1
      },
      average_scores: {
        squat: 8.2,
        deadlift: 7.9,
        plank: 8.5,
        pushup: 7.8,
        lunge: 8.1
      },
      recent_improvements: [
        {
          exercise_type: 'squat',
          improvement: 0.7,
          date: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString()
        },
        {
          exercise_type: 'deadlift',
          improvement: 0.5,
          date: new Date(Date.now() - 14 * 24 * 60 * 60 * 1000).toISOString()
        }
      ],
      streak_days: 3
    });
  }

  /**
   * Creates a mock notification settings response.
   * @returns A sample notification settings response
   */
  static notificationSettingsResponse() {
    return this.success({
      email_notifications: true,
      push_notifications: true,
      workout_reminders: false,
      analysis_completed: true,
      weekly_summary: true,
      tips_and_recommendations: true,
      marketing_communications: false
    });
  }
} 