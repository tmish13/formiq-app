/**
 * Unit tests for API Service
 * 
 * This test suite focuses on testing the core API functionality without network dependencies.
 * It uses jest.mock() to mock axios and related dependencies, allowing for fast and reliable testing
 * of the API service methods, parameter handling, and basic error scenarios.
 * 
 * Coverage includes:
 * - Authentication methods (login, register, logout, token refresh, etc.)
 * - User profile management
 * - Generic HTTP methods (GET, POST, PUT, PATCH, DELETE)
 * - Video upload workflow
 * - Exercise and analytics data fetching
 * - Error handling and response transformation
 * - Authentication state checking
 */

import axios, { AxiosError, AxiosInstance, AxiosResponse } from 'axios';
import { storageService } from '../../src/services/storageService';
import { logError, logNetworkError } from '../../src/utils/errorLogging';

// Mock axios instance
const mockAxiosInstance = {
  get: jest.fn(),
  post: jest.fn(),
  put: jest.fn(),
  patch: jest.fn(),
  delete: jest.fn(),
  interceptors: {
    request: {
      use: jest.fn(),
    },
    response: {
      use: jest.fn(),
    },
  },
} as any;

// Mock dependencies
jest.mock('axios', () => ({
  ...jest.requireActual('axios'),
  create: jest.fn(() => mockAxiosInstance),
  post: jest.fn(),
}));

jest.mock('../../src/services/storageService');
jest.mock('../../src/utils/errorLogging');
jest.mock('@capacitor/core', () => ({
  Capacitor: {
    isNativePlatform: jest.fn(() => false),
    getPlatform: jest.fn(() => 'web'),
  },
}));

const mockedAxios = axios as jest.Mocked<typeof axios>;
const mockStorageService = storageService as jest.Mocked<typeof storageService>;
const mockLogError = logError as jest.MockedFunction<typeof logError>;
const mockLogNetworkError = logNetworkError as jest.MockedFunction<typeof logNetworkError>;

// Import apiService after mocks are set up
import apiService from '../../src/services/apiService';

describe('ApiService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockedAxios.create.mockReturnValue(mockAxiosInstance);
    
    // Setup default storage service mocks
    mockStorageService.getAuthToken.mockResolvedValue('mock-token');
    mockStorageService.getRefreshToken.mockResolvedValue('mock-refresh-token');
    mockStorageService.setAuthToken.mockResolvedValue();
    mockStorageService.setRefreshToken.mockResolvedValue();
    mockStorageService.removeAuthToken.mockResolvedValue();
    mockStorageService.removeRefreshToken.mockResolvedValue();

    // Reset environment variables
    delete process.env.REACT_APP_API_URL;
  });

  describe('Authentication Methods', () => {
    describe('login', () => {
      it('should login successfully and store tokens', async () => {
        const mockResponse = {
          data: {
            access_token: 'new-access-token',
            refresh_token: 'new-refresh-token',
            user: { id: '1', email: 'test@example.com' }
          }
        };
        mockAxiosInstance.post.mockResolvedValue(mockResponse);

        const result = await apiService.login('test@example.com', 'password');

        expect(mockAxiosInstance.post).toHaveBeenCalledWith('/auth/login', {
          email: 'test@example.com',
          password: 'password'
        });
        expect(mockStorageService.setAuthToken).toHaveBeenCalledWith('new-access-token');
        expect(mockStorageService.setRefreshToken).toHaveBeenCalledWith('new-refresh-token');
        expect(result).toEqual(mockResponse);
      });

      it('should handle login without refresh token', async () => {
        const mockResponse = {
          data: {
            access_token: 'new-access-token',
            user: { id: '1', email: 'test@example.com' }
          }
        };
        mockAxiosInstance.post.mockResolvedValue(mockResponse);

        await apiService.login('test@example.com', 'password');

        expect(mockStorageService.setAuthToken).toHaveBeenCalledWith('new-access-token');
        expect(mockStorageService.setRefreshToken).not.toHaveBeenCalled();
      });

      it('should handle login error', async () => {
        const mockError = new AxiosError('Invalid credentials');
        mockError.response = {
          status: 401,
          data: { message: 'Invalid email or password' }
        } as any;
        mockAxiosInstance.post.mockRejectedValue(mockError);

        await expect(apiService.login('test@example.com', 'wrong-password'))
          .rejects.toThrow('Invalid credentials');
      });
    });

    describe('register', () => {
      it('should register user with correct data', async () => {
        const userData = {
          email: 'test@example.com',
          password: 'password123',
          name: 'Test User'
        };
        const mockResponse = { data: { user: userData } };
        mockAxiosInstance.post.mockResolvedValue(mockResponse);

        const result = await apiService.register(userData);

        expect(mockAxiosInstance.post).toHaveBeenCalledWith('/auth/register', userData);
        expect(result).toEqual(mockResponse);
      });
    });

    describe('logout', () => {
      it('should logout successfully and clear tokens', async () => {
        mockAxiosInstance.post.mockResolvedValue({});

        await apiService.logout();

        expect(mockAxiosInstance.post).toHaveBeenCalledWith('/auth/logout');
        expect(mockStorageService.removeAuthToken).toHaveBeenCalled();
        expect(mockStorageService.removeRefreshToken).toHaveBeenCalled();
      });

      it('should clear tokens even if logout API fails', async () => {
        mockAxiosInstance.post.mockRejectedValue(new Error('Network error'));

        await apiService.logout();

        expect(mockStorageService.removeAuthToken).toHaveBeenCalled();
        expect(mockStorageService.removeRefreshToken).toHaveBeenCalled();
      });
    });

    describe('refreshToken', () => {
      it('should refresh token successfully', async () => {
        const mockResponse = {
          data: {
            access_token: 'new-access-token',
            refresh_token: 'new-refresh-token'
          }
        };
        mockedAxios.post.mockResolvedValue(mockResponse);

        const result = await apiService.refreshToken('old-refresh-token');

        expect(mockedAxios.post).toHaveBeenCalledWith(
          expect.stringContaining('/auth/refresh'),
          { refresh_token: 'old-refresh-token' }
        );
        expect(result).toEqual(mockResponse.data);
      });
    });

    describe('validateSession', () => {
      it('should validate session successfully', async () => {
        const mockResponse = { data: { valid: true, user: { id: '1' } } };
        mockAxiosInstance.get.mockResolvedValue(mockResponse);

        const result = await apiService.validateSession();

        expect(mockAxiosInstance.get).toHaveBeenCalledWith('/auth/validate-session');
        expect(result).toEqual(mockResponse);
      });
    });

    describe('password reset methods', () => {
      it('should request password reset', async () => {
        const mockResponse = { data: { message: 'Reset email sent' } };
        mockAxiosInstance.post.mockResolvedValue(mockResponse);

        const result = await apiService.requestPasswordReset('test@example.com');

        expect(mockAxiosInstance.post).toHaveBeenCalledWith('/auth/password-reset-request', {
          email: 'test@example.com'
        });
        expect(result).toEqual(mockResponse);
      });

      it('should confirm password reset', async () => {
        const resetData = { token: 'reset-token', password: 'new-password' };
        const mockResponse = { data: { message: 'Password reset successful' } };
        mockAxiosInstance.post.mockResolvedValue(mockResponse);

        const result = await apiService.confirmPasswordReset(resetData);

        expect(mockAxiosInstance.post).toHaveBeenCalledWith('/auth/password-reset-confirm', resetData);
        expect(result).toEqual(mockResponse);
      });
    });

    describe('verifyEmail', () => {
      it('should verify email with token', async () => {
        const mockResponse = { data: { message: 'Email verified' } };
        mockAxiosInstance.post.mockResolvedValue(mockResponse);

        const result = await apiService.verifyEmail('verification-token');

        expect(mockAxiosInstance.post).toHaveBeenCalledWith('/auth/verify-email', {
          token: 'verification-token'
        });
        expect(result).toEqual(mockResponse);
      });
    });
  });

  describe('User Profile Methods', () => {
    describe('getCurrentUser', () => {
      it('should get current user profile', async () => {
        const mockUser = { id: '1', email: 'test@example.com', name: 'Test User' };
        const mockResponse = { data: mockUser };
        mockAxiosInstance.get.mockResolvedValue(mockResponse);

        const result = await apiService.getCurrentUser();

        expect(mockAxiosInstance.get).toHaveBeenCalledWith('/users/me');
        expect(result).toEqual(mockResponse);
      });
    });

    describe('updateProfile', () => {
      it('should update user profile', async () => {
        const updateData = { name: 'Updated Name', bio: 'New bio' };
        const mockResponse = { data: { ...updateData, id: '1' } };
        mockAxiosInstance.patch.mockResolvedValue(mockResponse);

        const result = await apiService.updateProfile(updateData);

        expect(mockAxiosInstance.patch).toHaveBeenCalledWith('/users/me', updateData);
        expect(result).toEqual(mockResponse);
      });
    });

    describe('updateAvatar', () => {
      it('should update user avatar with FormData', async () => {
        const formData = new FormData();
        formData.append('avatar', new File([''], 'avatar.jpg'));
        const mockResponse = { data: { avatarUrl: 'new-avatar-url' } };
        mockAxiosInstance.post.mockResolvedValue(mockResponse);

        const result = await apiService.updateAvatar(formData);

        expect(mockAxiosInstance.post).toHaveBeenCalledWith('/users/me/avatar', formData, {
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        });
        expect(result).toEqual(mockResponse);
      });
    });
  });

  describe('Generic Request Methods', () => {
    describe('get', () => {
      it('should make GET request with params', async () => {
        const mockResponse = { data: { results: [] } };
        mockAxiosInstance.get.mockResolvedValue(mockResponse);

        const result = await apiService.get('/test-endpoint', { page: 1, limit: 10 });

        expect(mockAxiosInstance.get).toHaveBeenCalledWith('/test-endpoint', {
          params: { page: 1, limit: 10 }
        });
        expect(result).toEqual(mockResponse);
      });

      it('should make GET request without params', async () => {
        const mockResponse = { data: { results: [] } };
        mockAxiosInstance.get.mockResolvedValue(mockResponse);

        const result = await apiService.get('/test-endpoint');

        expect(mockAxiosInstance.get).toHaveBeenCalledWith('/test-endpoint', { params: undefined });
        expect(result).toEqual(mockResponse);
      });
    });

    describe('post', () => {
      it('should make POST request with data', async () => {
        const postData = { name: 'test' };
        const mockResponse = { data: { id: '1', ...postData } };
        mockAxiosInstance.post.mockResolvedValue(mockResponse);

        const result = await apiService.post('/test-endpoint', postData);

        expect(mockAxiosInstance.post).toHaveBeenCalledWith('/test-endpoint', postData);
        expect(result).toEqual(mockResponse);
      });
    });

    describe('put', () => {
      it('should make PUT request with data', async () => {
        const putData = { name: 'updated' };
        const mockResponse = { data: { id: '1', ...putData } };
        mockAxiosInstance.put.mockResolvedValue(mockResponse);

        const result = await apiService.put('/test-endpoint', putData);

        expect(mockAxiosInstance.put).toHaveBeenCalledWith('/test-endpoint', putData);
        expect(result).toEqual(mockResponse);
      });
    });

    describe('patch', () => {
      it('should make PATCH request with data', async () => {
        const patchData = { name: 'patched' };
        const mockResponse = { data: { id: '1', ...patchData } };
        mockAxiosInstance.patch.mockResolvedValue(mockResponse);

        const result = await apiService.patch('/test-endpoint', patchData);

        expect(mockAxiosInstance.patch).toHaveBeenCalledWith('/test-endpoint', patchData);
        expect(result).toEqual(mockResponse);
      });
    });

    describe('delete', () => {
      it('should make DELETE request', async () => {
        const mockResponse = { data: { success: true } };
        mockAxiosInstance.delete.mockResolvedValue(mockResponse);

        const result = await apiService.delete('/test-endpoint');

        expect(mockAxiosInstance.delete).toHaveBeenCalledWith('/test-endpoint');
        expect(result).toEqual(mockResponse);
      });
    });
  });

  describe('Video Upload Methods', () => {
    describe('getVideoUploadUrl', () => {
      it('should get video upload URL with metadata', async () => {
        const metadata = {
          filename: 'test-video.mp4',
          contentType: 'video/mp4',
          exerciseId: 'exercise-1',
          userId: 'user-1'
        };
        const mockResponse = {
          data: {
            uploadUrl: 'https://s3.amazonaws.com/upload-url',
            videoId: 'video-123',
            fields: { key: 'value' }
          }
        };
        mockAxiosInstance.post.mockResolvedValue(mockResponse);

        const result = await apiService.getVideoUploadUrl(metadata);

        expect(mockAxiosInstance.post).toHaveBeenCalledWith('/videos/upload-url', metadata);
        expect(result).toEqual(mockResponse.data);
      });
    });

    describe('uploadVideoToS3', () => {
      it('should upload video to S3 with fields', async () => {
        const file = new File(['video content'], 'test.mp4', { type: 'video/mp4' });
        const uploadUrl = 'https://s3.amazonaws.com/upload-url';
        const fields = { key: 'test-key', policy: 'policy-value' };
        
        mockedAxios.post.mockResolvedValue({ data: {} });

        await apiService.uploadVideoToS3(uploadUrl, file, fields);

        expect(mockedAxios.post).toHaveBeenCalledWith(
          uploadUrl,
          expect.any(FormData),
          {
            headers: {
              'Content-Type': 'multipart/form-data',
            },
          }
        );
      });

      it('should upload video to S3 without fields', async () => {
        const file = new File(['video content'], 'test.mp4', { type: 'video/mp4' });
        const uploadUrl = 'https://s3.amazonaws.com/upload-url';
        
        mockedAxios.post.mockResolvedValue({ data: {} });

        await apiService.uploadVideoToS3(uploadUrl, file);

        expect(mockedAxios.post).toHaveBeenCalledWith(
          uploadUrl,
          expect.any(FormData),
          {
            headers: {
              'Content-Type': 'multipart/form-data',
            },
          }
        );
      });
    });

    describe('confirmVideoUpload', () => {
      it('should confirm video upload with metadata', async () => {
        const videoId = 'video-123';
        const metadata = {
          duration: 30,
          size: 1024000,
          width: 1920,
          height: 1080
        };
        const mockResponse = { data: { success: true, videoId } };
        mockAxiosInstance.post.mockResolvedValue(mockResponse);

        const result = await apiService.confirmVideoUpload(videoId, metadata);

        expect(mockAxiosInstance.post).toHaveBeenCalledWith('/videos/upload-complete', {
          videoId,
          ...metadata
        });
        expect(result).toEqual(mockResponse.data);
      });

      it('should confirm video upload without metadata', async () => {
        const videoId = 'video-123';
        const mockResponse = { data: { success: true, videoId } };
        mockAxiosInstance.post.mockResolvedValue(mockResponse);

        const result = await apiService.confirmVideoUpload(videoId);

        expect(mockAxiosInstance.post).toHaveBeenCalledWith('/videos/upload-complete', {
          videoId
        });
        expect(result).toEqual(mockResponse.data);
      });
    });

    describe('getVideoStatus', () => {
      it('should get video processing status', async () => {
        const videoId = 'video-123';
        const mockResponse = {
          data: {
            status: 'processing',
            progress: 50,
            processedUrl: null
          }
        };
        mockAxiosInstance.get.mockResolvedValue(mockResponse);

        const result = await apiService.getVideoStatus(videoId);

        expect(mockAxiosInstance.get).toHaveBeenCalledWith(`/videos/${videoId}/status`);
        expect(result).toEqual(mockResponse.data);
      });
    });
  });

  describe('Exercise Methods', () => {
    describe('getExercises', () => {
      it('should get exercises with filters', async () => {
        const filters = {
          type: 'strength',
          difficulty: 'beginner',
          muscleGroups: ['legs', 'glutes']
        };
        const mockResponse = { data: [{ id: '1', name: 'Squat' }] };
        mockAxiosInstance.get.mockResolvedValue(mockResponse);

        const result = await apiService.getExercises(filters);

        expect(mockAxiosInstance.get).toHaveBeenCalledWith('/exercises', { params: filters });
        expect(result).toEqual(mockResponse.data);
      });

      it('should get exercises without filters', async () => {
        const mockResponse = { data: [{ id: '1', name: 'Squat' }] };
        mockAxiosInstance.get.mockResolvedValue(mockResponse);

        const result = await apiService.getExercises();

        expect(mockAxiosInstance.get).toHaveBeenCalledWith('/exercises', { params: undefined });
        expect(result).toEqual(mockResponse.data);
      });
    });

    describe('getExercise', () => {
      it('should get exercise by ID', async () => {
        const exerciseId = 'exercise-1';
        const mockResponse = { data: { id: exerciseId, name: 'Squat' } };
        mockAxiosInstance.get.mockResolvedValue(mockResponse);

        const result = await apiService.getExercise(exerciseId);

        expect(mockAxiosInstance.get).toHaveBeenCalledWith(`/exercises/${exerciseId}`);
        expect(result).toEqual(mockResponse.data);
      });
    });

    describe('getReferencePose', () => {
      it('should get reference pose for exercise type', async () => {
        const exerciseType = 'squat';
        const mockResponse = { data: { keypoints: [], angles: {} } };
        mockAxiosInstance.get.mockResolvedValue(mockResponse);

        const result = await apiService.getReferencePose(exerciseType);

        expect(mockAxiosInstance.get).toHaveBeenCalledWith(`/exercises/${exerciseType}/reference-pose`);
        expect(result).toEqual(mockResponse.data);
      });
    });
  });

  describe('Analytics Methods', () => {
    describe('getAnalyticsOverview', () => {
      it('should get analytics overview with time range', async () => {
        const timeRange = '30d';
        const mockResponse = {
          data: {
            totalSessions: 50,
            averageScore: 85.5,
            bestExercise: 'squat',
            weeklyProgress: 12.3,
            improvementRate: 8.7
          }
        };
        mockAxiosInstance.get.mockResolvedValue(mockResponse);

        const result = await apiService.getAnalyticsOverview(timeRange);

        expect(mockAxiosInstance.get).toHaveBeenCalledWith('/analytics/overview', {
          params: { timeRange }
        });
        expect(result).toEqual(mockResponse.data);
      });
    });

    describe('getExerciseStats', () => {
      it('should get exercise statistics', async () => {
        const mockResponse = {
          data: [{
            exercise_type: 'squat',
            count: 25,
            avg_score: 87.2,
            best_score: 95.1,
            improvement: 5.3,
            trend: 'up' as const
          }]
        };
        mockAxiosInstance.get.mockResolvedValue(mockResponse);

        const result = await apiService.getExerciseStats('7d');

        expect(mockAxiosInstance.get).toHaveBeenCalledWith('/analytics/exercise-stats', {
          params: { timeRange: '7d' }
        });
        expect(result).toEqual(mockResponse.data);
      });
    });
  });

  describe('Video Statistics Methods', () => {
    describe('getVideoStatistics', () => {
      it('should get comprehensive video statistics', async () => {
        const mockResponse = {
          data: {
            totalVideos: 100,
            processedVideos: 85,
            failedVideos: 5,
            processingVideos: 10,
            averageProcessingTime: 45.2,
            totalStorageUsed: 2048000000,
            uploadsByExerciseType: { squat: 40, pushup: 35 },
            dailyUploads: [{ date: '2023-01-01', count: 5 }],
            successRate: 0.85
          }
        };
        mockAxiosInstance.get.mockResolvedValue(mockResponse);

        const result = await apiService.getVideoStatistics('30d');

        expect(mockAxiosInstance.get).toHaveBeenCalledWith('/videos/statistics', {
          params: { timeRange: '30d' }
        });
        expect(result).toEqual(mockResponse.data);
      });
    });
  });

  describe('Error Handling', () => {
    it('should handle API errors and reject with error', async () => {
      const mockError = new AxiosError('Request failed');
      mockError.response = {
        status: 400,
        data: {
          message: 'Validation error',
          code: 'VALIDATION_FAILED',
          details: { field: 'email' }
        }
      } as any;
      mockAxiosInstance.get.mockRejectedValue(mockError);

      await expect(apiService.get('/test-endpoint'))
        .rejects.toThrow('Request failed');
    });

    it('should handle network errors', async () => {
      const mockError = new AxiosError('Network Error');
      mockAxiosInstance.get.mockRejectedValue(mockError);

      await expect(apiService.get('/test-endpoint'))
        .rejects.toThrow('Network Error');
    });

    it('should handle errors without response', async () => {
      const mockError = new Error('Unknown error');
      mockAxiosInstance.get.mockRejectedValue(mockError);

      await expect(apiService.get('/test-endpoint'))
        .rejects.toThrow('Unknown error');
    });
  });

  describe('Authentication Check', () => {
    describe('isAuthenticated', () => {
      it('should return true when token exists', async () => {
        mockStorageService.getAuthToken.mockResolvedValue('valid-token');

        const result = await apiService.isAuthenticated();

        expect(result).toBe(true);
        expect(mockStorageService.getAuthToken).toHaveBeenCalled();
      });

      it('should return false when no token exists', async () => {
        mockStorageService.getAuthToken.mockResolvedValue(null);

        const result = await apiService.isAuthenticated();

        expect(result).toBe(false);
        expect(mockStorageService.getAuthToken).toHaveBeenCalled();
      });
    });
  });

  describe('Response Data Transformation', () => {
    it('should return response data directly for video upload URL', async () => {
      const mockApiResponse = {
        data: {
          uploadUrl: 'https://s3.amazonaws.com/bucket/key',
          videoId: 'video-123'
        }
      };
      mockAxiosInstance.post.mockResolvedValue(mockApiResponse);

      const result = await apiService.getVideoUploadUrl({
        filename: 'test.mp4',
        contentType: 'video/mp4'
      });

      // Should return data property directly, not the full response
      expect(result).toEqual(mockApiResponse.data);
      expect(result).not.toHaveProperty('status');
      expect(result).not.toHaveProperty('headers');
    });

    it('should return response data directly for exercises list', async () => {
      const mockApiResponse = {
        data: [{ id: '1', name: 'Squat' }]
      };
      mockAxiosInstance.get.mockResolvedValue(mockApiResponse);

      const result = await apiService.getExercises();

      // Should return data property directly
      expect(result).toEqual(mockApiResponse.data);
      expect(Array.isArray(result)).toBe(true);
    });
  });
});