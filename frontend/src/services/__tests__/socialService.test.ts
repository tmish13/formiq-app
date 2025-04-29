import { socialService } from '../socialService';
import { ApiService } from '../apiService';
import { createMockStorageService } from '../../utils/test-mocks';
import { StorageService } from '../storageService';
import { AxiosInstance, AxiosRequestConfig } from 'axios';
import { ApiResponse } from '../api/baseApi';

// Create a test subclass that exposes protected methods
class TestApiService extends ApiService {
  constructor() {
    super('http://localhost/api');
  }

  // Expose protected methods for testing
  public get<T>(url: string, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
    return super.get(url, config);
  }

  public post<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
    return super.post(url, data, config);
  }

  public put<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
    return super.put(url, data, config);
  }

  public delete<T>(url: string, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
    return super.delete(url, config);
  }
}

// Mock the API service
jest.mock('../apiService', () => ({
  ApiService: jest.fn().mockImplementation(() => {
    return new TestApiService();
  })
}));

// Mock the StorageService
jest.mock('../storageService', () => ({
  StorageService: {
    getInstance: jest.fn()
  }
}));

describe('SocialService', () => {
  let mockStorage: ReturnType<typeof createMockStorageService>;
  let mockApiService: TestApiService;

  beforeEach(() => {
    jest.clearAllMocks();
    mockStorage = createMockStorageService();
    (StorageService.getInstance as jest.Mock).mockReturnValue(mockStorage);
    mockApiService = new TestApiService();
    (ApiService as jest.Mock).mockImplementation(() => mockApiService);
  });

  describe('user profile', () => {
    it('gets user profile', async () => {
      const mockProfile = {
        id: 'test-user-id',
        username: 'testuser',
        bio: 'Test bio',
        avatarUrl: 'https://example.com/avatar.jpg'
      };
      jest.spyOn(mockApiService, 'get').mockResolvedValueOnce({ data: mockProfile, status: 200 });

      const profile = await socialService.getUserProfile('test-user-id');
      expect(profile).toEqual(mockProfile);
      expect(mockApiService.get).toHaveBeenCalledWith('/users/test-user-id/profile');
    });

    it('updates user profile', async () => {
      const mockProfile = {
        username: 'updateduser',
        bio: 'Updated bio'
      };
      jest.spyOn(mockApiService, 'put').mockResolvedValueOnce({ data: mockProfile, status: 200 });

      const updatedProfile = await socialService.updateUserProfile('test-user-id', mockProfile);
      expect(updatedProfile).toEqual(mockProfile);
      expect(mockApiService.put).toHaveBeenCalledWith('/users/test-user-id/profile', mockProfile);
    });
  });

  describe('workout sharing', () => {
    it('shares workout', async () => {
      const mockWorkout = {
        id: 'test-workout-id',
        userId: 'test-user-id',
        name: 'Test Workout',
        description: 'Test description',
        exercises: []
      };
      jest.spyOn(mockApiService, 'post').mockResolvedValueOnce({ data: mockWorkout, status: 200 });

      const sharedWorkout = await socialService.shareWorkout('test-workout-id', 'test-user-id');
      expect(sharedWorkout).toEqual(mockWorkout);
      expect(mockApiService.post).toHaveBeenCalledWith('/workout-shares', {
        templateId: 'test-workout-id',
        userId: 'test-user-id'
      });
    });

    it('gets shared workouts', async () => {
      const mockWorkouts = [
        {
          id: 'test-workout-id',
          userId: 'test-user-id',
          name: 'Test Workout',
          description: 'Test description',
          exercises: []
        }
      ];
      jest.spyOn(mockApiService, 'get').mockResolvedValueOnce({ data: mockWorkouts, status: 200 });

      const workouts = await socialService.getSharedWorkouts('test-user-id');
      expect(workouts).toEqual(mockWorkouts);
      expect(mockApiService.get).toHaveBeenCalledWith('/workout-shares/user/test-user-id');
    });
  });

  describe('comments', () => {
    it('adds comment', async () => {
      const mockComment = {
        id: 'test-comment-id',
        userId: 'test-user-id',
        workoutId: 'test-workout-id',
        text: 'Test comment',
        createdAt: new Date().toISOString()
      };
      jest.spyOn(mockApiService, 'post').mockResolvedValueOnce({ data: mockComment, status: 200 });

      const comment = await socialService.addComment('test-workout-id', 'test-user-id', 'Test comment');
      expect(comment).toEqual(mockComment);
      expect(mockApiService.post).toHaveBeenCalledWith('/workout-shares/test-workout-id/comments', {
        userId: 'test-user-id',
        content: 'Test comment'
      });
    });

    it('gets comments', async () => {
      const mockComments = [
        {
          id: 'test-comment-id',
          userId: 'test-user-id',
          workoutId: 'test-workout-id',
          text: 'Test comment',
          createdAt: new Date().toISOString()
        }
      ];
      jest.spyOn(mockApiService, 'get').mockResolvedValueOnce({ data: mockComments, status: 200 });

      const comments = await socialService.getComments('test-workout-id');
      expect(comments).toEqual(mockComments);
      expect(mockApiService.get).toHaveBeenCalledWith('/workout-shares/test-workout-id/comments');
    });
  });

  describe('following/followers', () => {
    it('follows user', async () => {
      jest.spyOn(mockApiService, 'post').mockResolvedValueOnce({ data: { success: true }, status: 200 });

      await socialService.followUser('test-user-id', 'target-user-id');
      expect(mockApiService.post).toHaveBeenCalledWith('/follows', {
        followerId: 'test-user-id',
        followingId: 'target-user-id'
      });
    });

    it('unfollows user', async () => {
      jest.spyOn(mockApiService, 'delete').mockResolvedValueOnce({ data: { success: true }, status: 200 });

      await socialService.unfollowUser('test-user-id', 'target-user-id');
      expect(mockApiService.delete).toHaveBeenCalledWith('/follows/test-user-id/target-user-id');
    });

    it('gets followers', async () => {
      const mockFollowers = [
        {
          id: 'follower-id',
          username: 'follower',
          avatarUrl: 'https://example.com/avatar.jpg'
        }
      ];
      jest.spyOn(mockApiService, 'get').mockResolvedValueOnce({ data: mockFollowers, status: 200 });

      const followers = await socialService.getFollowers('test-user-id');
      expect(followers).toEqual(mockFollowers);
      expect(mockApiService.get).toHaveBeenCalledWith('/users/test-user-id/followers');
    });

    it('gets following', async () => {
      const mockFollowing = [
        {
          id: 'following-id',
          username: 'following',
          avatarUrl: 'https://example.com/avatar.jpg'
        }
      ];
      jest.spyOn(mockApiService, 'get').mockResolvedValueOnce({ data: mockFollowing, status: 200 });

      const following = await socialService.getFollowing('test-user-id');
      expect(following).toEqual(mockFollowing);
      expect(mockApiService.get).toHaveBeenCalledWith('/users/test-user-id/following');
    });
  });

  describe('achievements', () => {
    it('gets achievements', async () => {
      const mockAchievements = [
        {
          id: 'test-achievement-id',
          userId: 'test-user-id',
          type: 'workout',
          description: 'Completed 10 workouts',
          createdAt: new Date().toISOString()
        }
      ];
      jest.spyOn(mockApiService, 'get').mockResolvedValueOnce({ data: mockAchievements, status: 200 });

      const achievements = await socialService.getAchievements('test-user-id');
      expect(achievements).toEqual(mockAchievements);
      expect(mockApiService.get).toHaveBeenCalledWith('/users/test-user-id/achievements');
    });
  });

  describe('social stats', () => {
    it('gets social stats', async () => {
      const mockStats = {
        followers: 10,
        following: 5,
        totalWorkouts: 20,
        totalAchievements: 3
      };
      jest.spyOn(mockApiService, 'get').mockResolvedValueOnce({ data: mockStats, status: 200 });

      const stats = await socialService.getSocialStats('test-user-id');
      expect(stats).toEqual(mockStats);
      expect(mockApiService.get).toHaveBeenCalledWith('/users/test-user-id/social-stats');
    });
  });
}); 