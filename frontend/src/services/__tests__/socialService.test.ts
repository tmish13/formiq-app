import { socialService } from '../socialService';
import { ApiService } from '../apiService';
import { createMockStorageService } from '../../utils/test-mocks';
import { StorageService } from '../storageService';
import { AxiosRequestConfig } from 'axios';
import { ApiResponse } from '../../types/api';

// Mock the apiService directly since that's what socialService uses
jest.mock('../apiService', () => {
  return {
    apiService: {
      get: jest.fn(),
      post: jest.fn(),
      put: jest.fn(),
      delete: jest.fn()
    },
    ApiService: jest.fn()
  };
});

// Import the mocked apiService after mocking
import { apiService } from '../apiService';

// Mock the StorageService
jest.mock('../storageService', () => ({
  StorageService: {
    getInstance: jest.fn()
  }
}));

describe('SocialService', () => {
  let mockStorage: ReturnType<typeof createMockStorageService>;

  beforeEach(() => {
    jest.clearAllMocks();
    mockStorage = createMockStorageService();
    (StorageService.getInstance as jest.Mock).mockReturnValue(mockStorage);
  });

  describe('user profile', () => {
    it('gets user profile', async () => {
      const mockProfile = {
        id: 'test-user-id',
        username: 'testuser',
        bio: 'Test bio',
        avatarUrl: 'https://example.com/avatar.jpg'
      };
      
      (apiService.get as jest.Mock).mockResolvedValueOnce({ data: mockProfile, status: 200 });

      const profile = await socialService.getUserProfile('test-user-id');
      expect(profile).toEqual(mockProfile);
      expect(apiService.get).toHaveBeenCalledWith('/users/test-user-id/profile');
    });

    it('updates user profile', async () => {
      const mockProfile = {
        username: 'updateduser',
        bio: 'Updated bio'
      };
      
      (apiService.put as jest.Mock).mockResolvedValueOnce({ data: mockProfile, status: 200 });

      const updatedProfile = await socialService.updateUserProfile('test-user-id', mockProfile);
      expect(updatedProfile).toEqual(mockProfile);
      expect(apiService.put).toHaveBeenCalledWith('/users/test-user-id/profile', mockProfile);
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
      
      (apiService.post as jest.Mock).mockResolvedValueOnce({ data: mockWorkout, status: 200 });

      const sharedWorkout = await socialService.shareWorkout('test-workout-id', 'test-user-id');
      expect(sharedWorkout).toEqual(mockWorkout);
      expect(apiService.post).toHaveBeenCalledWith('/workout-shares', {
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
      
      (apiService.get as jest.Mock).mockResolvedValueOnce({ data: mockWorkouts, status: 200 });

      const workouts = await socialService.getSharedWorkouts('test-user-id');
      expect(workouts).toEqual(mockWorkouts);
      expect(apiService.get).toHaveBeenCalledWith('/workout-shares/user/test-user-id');
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
      
      (apiService.post as jest.Mock).mockResolvedValueOnce({ data: mockComment, status: 200 });

      const comment = await socialService.addComment('test-workout-id', 'test-user-id', 'Test comment');
      expect(comment).toEqual(mockComment);
      expect(apiService.post).toHaveBeenCalledWith('/workout-shares/test-workout-id/comments', {
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
      
      (apiService.get as jest.Mock).mockResolvedValueOnce({ data: mockComments, status: 200 });

      const comments = await socialService.getComments('test-workout-id');
      expect(comments).toEqual(mockComments);
      expect(apiService.get).toHaveBeenCalledWith('/workout-shares/test-workout-id/comments');
    });
  });

  describe('following/followers', () => {
    it('follows user', async () => {
      (apiService.post as jest.Mock).mockResolvedValueOnce({ data: { success: true }, status: 200 });

      await socialService.followUser('test-user-id', 'target-user-id');
      expect(apiService.post).toHaveBeenCalledWith('/follows', {
        followerId: 'test-user-id',
        followingId: 'target-user-id'
      });
    });

    it('unfollows user', async () => {
      (apiService.delete as jest.Mock).mockResolvedValueOnce({ data: { success: true }, status: 200 });

      await socialService.unfollowUser('test-user-id', 'target-user-id');
      expect(apiService.delete).toHaveBeenCalledWith('/follows/test-user-id/target-user-id');
    });

    it('gets followers', async () => {
      const mockFollowers = [
        {
          id: 'follower-id',
          username: 'follower',
          avatarUrl: 'https://example.com/avatar.jpg'
        }
      ];
      
      (apiService.get as jest.Mock).mockResolvedValueOnce({ data: mockFollowers, status: 200 });

      const followers = await socialService.getFollowers('test-user-id');
      expect(followers).toEqual(mockFollowers);
      expect(apiService.get).toHaveBeenCalledWith('/users/test-user-id/followers');
    });

    it('gets following', async () => {
      const mockFollowing = [
        {
          id: 'following-id',
          username: 'following',
          avatarUrl: 'https://example.com/avatar.jpg'
        }
      ];
      
      (apiService.get as jest.Mock).mockResolvedValueOnce({ data: mockFollowing, status: 200 });

      const following = await socialService.getFollowing('test-user-id');
      expect(following).toEqual(mockFollowing);
      expect(apiService.get).toHaveBeenCalledWith('/users/test-user-id/following');
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
      
      (apiService.get as jest.Mock).mockResolvedValueOnce({ data: mockAchievements, status: 200 });

      const achievements = await socialService.getAchievements('test-user-id');
      expect(achievements).toEqual(mockAchievements);
      expect(apiService.get).toHaveBeenCalledWith('/users/test-user-id/achievements');
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
      
      (apiService.get as jest.Mock).mockResolvedValueOnce({ data: mockStats, status: 200 });

      const stats = await socialService.getSocialStats('test-user-id');
      expect(stats).toEqual(mockStats);
      expect(apiService.get).toHaveBeenCalledWith('/users/test-user-id/social-stats');
    });
  });
}); 