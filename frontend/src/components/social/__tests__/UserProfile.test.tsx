import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { UserProfile } from '../../../components/social/UserProfile';
import { socialService } from '../../../services/socialService';
import { formatDistanceToNow } from 'date-fns';

// Mock the socialService
jest.mock('../../../services/socialService', () => ({
  socialService: {
    getUserProfile: jest.fn(),
    followUser: jest.fn(),
    unfollowUser: jest.fn(),
    likeWorkoutShare: jest.fn(),
    getSharedWorkouts: jest.fn(),
  }
}));

// Mock date-fns
jest.mock('date-fns', () => ({
  formatDistanceToNow: jest.fn(() => '2 days ago'),
}));

describe('UserProfile', () => {
  const mockUser = {
    id: '1',
    username: 'testuser',
    fullName: 'Test User',
    bio: 'Test bio',
    avatar: 'profile.jpg',
    fitnessLevel: 'intermediate',
    followers: 100,
    following: 50,
    achievements: [
      { id: '1', name: 'First Workout', description: 'Completed first workout', icon: '🏃', dateEarned: '2024-03-20' },
      { id: '2', name: 'Consistency', description: '7 day streak', icon: '🔥', dateEarned: '2024-03-21' },
    ],
  };

  const mockWorkouts = [
    {
      id: '1',
      userId: '1',
      templateId: '1',
      template: {
        name: 'Squat',
        description: 'A great squat workout',
      },
      likes: 10,
      comments: [],
      createdAt: '2024-03-20T10:00:00Z',
      updatedAt: '2024-03-20T10:00:00Z',
    },
  ];

  beforeEach(() => {
    // Reset all mocks before each test
    jest.clearAllMocks();
    
    // Setup default mock implementations
    (socialService.getUserProfile as jest.Mock).mockResolvedValue(mockUser);
    (socialService.getSharedWorkouts as jest.Mock).mockResolvedValue(mockWorkouts);
    (socialService.followUser as jest.Mock).mockResolvedValue({ success: true });
    (socialService.unfollowUser as jest.Mock).mockResolvedValue({ success: true });
    (socialService.likeWorkoutShare as jest.Mock).mockResolvedValue({ success: true });
  });

  it('renders user profile data correctly', async () => {
    render(<UserProfile userId="1" currentUserId="2" />);
    
    // Wait for the profile data to load
    await waitFor(() => {
      expect(screen.getByText('testuser')).toBeInTheDocument();
      expect(screen.getByText('Test bio')).toBeInTheDocument();
      expect(screen.getByText('100 followers')).toBeInTheDocument();
    });

    // Check if achievements are rendered
    expect(screen.getByText('First Workout')).toBeInTheDocument();
    expect(screen.getByText('Consistency')).toBeInTheDocument();
  });

  it('handles workout interactions correctly', async () => {
    render(<UserProfile userId="1" currentUserId="2" />);
    
    // Wait for the workouts to load
    await waitFor(() => {
      expect(screen.getByText('Squat')).toBeInTheDocument();
    });

    // Find and click the like button
    const likeButton = screen.getByTestId('like-button-1');
    fireEvent.click(likeButton);
    
    await waitFor(() => {
      expect(socialService.likeWorkoutShare).toHaveBeenCalledWith('1', '2');
    });
  });

  it('handles profile editing correctly', async () => {
    render(<UserProfile userId="1" currentUserId="1" />);
    
    // Wait for the profile to load
    await waitFor(() => {
      expect(screen.getByText('testuser')).toBeInTheDocument();
    });

    // Find and click the edit button
    const editButton = screen.getByTestId('edit-profile-button');
    fireEvent.click(editButton);

    // Check if edit form is shown
    expect(screen.getByTestId('edit-profile-form')).toBeInTheDocument();
  });

  it('handles errors gracefully', async () => {
    const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
    (socialService.getUserProfile as jest.Mock).mockRejectedValue(new Error('Failed to load profile'));

    render(<UserProfile userId="1" currentUserId="2" />);
    
    // Wait for error handling
    await waitFor(() => {
      expect(screen.getByText('Failed to load user data')).toBeInTheDocument();
    });

    consoleSpy.mockRestore();
  });
}); 