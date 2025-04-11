import { apiService } from './apiService';
import { WorkoutTemplate } from './workoutPlanningService';

export interface User {
  id: string;
  username: string;
  avatar?: string;
  bio?: string;
  fitnessLevel: 'beginner' | 'intermediate' | 'advanced';
  achievements: Achievement[];
  followers: number;
  following: number;
}

export interface Achievement {
  id: string;
  name: string;
  description: string;
  icon: string;
  dateEarned: string;
}

export interface WorkoutShare {
  id: string;
  userId: string;
  templateId: string;
  template: WorkoutTemplate;
  likes: number;
  comments: Comment[];
  createdAt: string;
  updatedAt: string;
}

export interface Comment {
  id: string;
  userId: string;
  content: string;
  createdAt: string;
  updatedAt: string;
}

export interface SocialStats {
  followers: number;
  following: number;
  totalWorkouts: number;
  totalAchievements: number;
}

class SocialService {
  private isLoading = false;
  private error: string | null = null;

  // User Profile
  async getUserProfile(userId: string): Promise<User> {
    try {
      this.isLoading = true;
      const response = await apiService.get(`/users/${userId}/profile`);
      return response.data;
    } catch (error) {
      this.error = error instanceof Error ? error.message : 'Failed to fetch user profile';
      throw error;
    } finally {
      this.isLoading = false;
    }
  }

  async updateUserProfile(userId: string, profile: Partial<User>): Promise<User> {
    try {
      this.isLoading = true;
      const response = await apiService.put(`/users/${userId}/profile`, profile);
      return response.data;
    } catch (error) {
      this.error = error instanceof Error ? error.message : 'Failed to update user profile';
      throw error;
    } finally {
      this.isLoading = false;
    }
  }

  // Workout Sharing
  async shareWorkout(templateId: string, userId: string): Promise<WorkoutShare> {
    try {
      this.isLoading = true;
      const response = await apiService.post('/workout-shares', {
        templateId,
        userId,
      });
      return response.data;
    } catch (error) {
      this.error = error instanceof Error ? error.message : 'Failed to share workout';
      throw error;
    } finally {
      this.isLoading = false;
    }
  }

  async getSharedWorkouts(userId: string): Promise<WorkoutShare[]> {
    try {
      this.isLoading = true;
      const response = await apiService.get(`/workout-shares/user/${userId}`);
      return response.data;
    } catch (error) {
      this.error = error instanceof Error ? error.message : 'Failed to fetch shared workouts';
      throw error;
    } finally {
      this.isLoading = false;
    }
  }

  async likeWorkoutShare(shareId: string, userId: string): Promise<void> {
    try {
      this.isLoading = true;
      await apiService.post(`/workout-shares/${shareId}/like`, { userId });
    } catch (error) {
      this.error = error instanceof Error ? error.message : 'Failed to like workout';
      throw error;
    } finally {
      this.isLoading = false;
    }
  }

  // Comments
  async addComment(shareId: string, userId: string, content: string): Promise<Comment> {
    try {
      this.isLoading = true;
      const response = await apiService.post(`/workout-shares/${shareId}/comments`, {
        userId,
        content,
      });
      return response.data;
    } catch (error) {
      this.error = error instanceof Error ? error.message : 'Failed to add comment';
      throw error;
    } finally {
      this.isLoading = false;
    }
  }

  async getComments(shareId: string): Promise<Comment[]> {
    try {
      this.isLoading = true;
      const response = await apiService.get(`/workout-shares/${shareId}/comments`);
      return response.data;
    } catch (error) {
      this.error = error instanceof Error ? error.message : 'Failed to fetch comments';
      throw error;
    } finally {
      this.isLoading = false;
    }
  }

  // Following/Followers
  async followUser(followerId: string, followingId: string): Promise<void> {
    try {
      this.isLoading = true;
      await apiService.post('/follows', { followerId, followingId });
    } catch (error) {
      this.error = error instanceof Error ? error.message : 'Failed to follow user';
      throw error;
    } finally {
      this.isLoading = false;
    }
  }

  async unfollowUser(followerId: string, followingId: string): Promise<void> {
    try {
      this.isLoading = true;
      await apiService.delete(`/follows/${followerId}/${followingId}`);
    } catch (error) {
      this.error = error instanceof Error ? error.message : 'Failed to unfollow user';
      throw error;
    } finally {
      this.isLoading = false;
    }
  }

  async getFollowers(userId: string): Promise<User[]> {
    try {
      this.isLoading = true;
      const response = await apiService.get(`/users/${userId}/followers`);
      return response.data;
    } catch (error) {
      this.error = error instanceof Error ? error.message : 'Failed to fetch followers';
      throw error;
    } finally {
      this.isLoading = false;
    }
  }

  async getFollowing(userId: string): Promise<User[]> {
    try {
      this.isLoading = true;
      const response = await apiService.get(`/users/${userId}/following`);
      return response.data;
    } catch (error) {
      this.error = error instanceof Error ? error.message : 'Failed to fetch following';
      throw error;
    } finally {
      this.isLoading = false;
    }
  }

  // Achievements
  async getAchievements(userId: string): Promise<Achievement[]> {
    try {
      this.isLoading = true;
      const response = await apiService.get(`/users/${userId}/achievements`);
      return response.data;
    } catch (error) {
      this.error = error instanceof Error ? error.message : 'Failed to fetch achievements';
      throw error;
    } finally {
      this.isLoading = false;
    }
  }

  // Social Stats
  async getSocialStats(userId: string): Promise<SocialStats> {
    try {
      this.isLoading = true;
      const response = await apiService.get(`/users/${userId}/social-stats`);
      return response.data;
    } catch (error) {
      this.error = error instanceof Error ? error.message : 'Failed to fetch social stats';
      throw error;
    } finally {
      this.isLoading = false;
    }
  }

  getState() {
    return {
      isLoading: this.isLoading,
      error: this.error
    };
  }
}

export const socialService = new SocialService(); 