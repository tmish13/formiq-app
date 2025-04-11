import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { UserProfile } from '../../../components/social/UserProfile';
import { socialService } from '../../../services/socialService';
import { formatDistanceToNow } from 'date-fns';

// Mock the socialService
jest.mock('../../../services/socialService');

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
    (socialService.followUser as jest.Mock).mockResolvedValue(undefined);
    (socialService.unfollowUser as jest.Mock).mockResolvedValue(undefined);
    (socialService.likeWorkoutShare as jest.Mock).mockResolvedValue(undefined);
    (socialService.addComment as jest.Mock).mockResolvedValue(undefined);
    (socialService.updateUserProfile as jest.Mock).mockResolvedValue(undefined);
  });

  it('renders user profile data correctly', async () => {
    render(<UserProfile userId="1" currentUserId="2" />);

    // Wait for the profile data to load
    await waitFor(() => {
      expect(screen.getByText('Test User')).toBeInTheDocument();
      expect(screen.getByText('Test bio')).toBeInTheDocument();
      expect(screen.getByText('100 followers')).toBeInTheDocument();
      expect(screen.getByText('50 following')).toBeInTheDocument();
    });

    // Check if achievements are rendered
    expect(screen.getByText('First Workout')).toBeInTheDocument();
    expect(screen.getByText('Consistency')).toBeInTheDocument();

    // Check if recent workout is rendered
    expect(screen.getByText('Squat')).toBeInTheDocument();
    expect(screen.getByText('2 days ago')).toBeInTheDocument();
  });

  it('handles follow/unfollow actions correctly', async () => {
    render(<UserProfile userId="1" currentUserId="2" />);

    // Wait for the profile to load
    await waitFor(() => {
      expect(screen.getByText('Follow')).toBeInTheDocument();
    });

    // Click follow button
    fireEvent.click(screen.getByText('Follow'));
    await waitFor(() => {
      expect(socialService.followUser).toHaveBeenCalledWith('2', '1');
    });

    // Mock the updated user data after following
    (socialService.getUserProfile as jest.Mock).mockResolvedValueOnce({
      ...mockUser,
      followers: 101,
    });

    // Click unfollow button
    fireEvent.click(screen.getByText('Unfollow'));
    await waitFor(() => {
      expect(socialService.unfollowUser).toHaveBeenCalledWith('2', '1');
    });
  });

  it('handles workout interactions correctly', async () => {
    render(<UserProfile userId="1" currentUserId="2" />);

    // Wait for the workout to load
    await waitFor(() => {
      expect(screen.getByText('Squat')).toBeInTheDocument();
    });

    // Like workout
    fireEvent.click(screen.getByTestId('like-button'));
    await waitFor(() => {
      expect(socialService.likeWorkoutShare).toHaveBeenCalledWith('1', '2');
    });

    // Add comment
    const commentInput = screen.getByPlaceholderText('Add a comment...');
    fireEvent.change(commentInput, { target: { value: 'Great workout!' } });
    fireEvent.click(screen.getByText('Post'));
    await waitFor(() => {
      expect(socialService.addComment).toHaveBeenCalledWith('1', '2', 'Great workout!');
    });
  });

  it('handles profile editing correctly', async () => {
    render(<UserProfile userId="1" currentUserId="1" />);

    // Wait for the profile to load
    await waitFor(() => {
      expect(screen.getByText('Test User')).toBeInTheDocument();
    });

    // Open edit dialog
    fireEvent.click(screen.getByText('Edit Profile'));

    // Update profile fields
    fireEvent.change(screen.getByLabelText('Full Name'), {
      target: { value: 'Updated Name' },
    });
    fireEvent.change(screen.getByLabelText('Bio'), {
      target: { value: 'Updated bio' },
    });

    // Save changes
    fireEvent.click(screen.getByText('Save'));
    await waitFor(() => {
      expect(socialService.updateUserProfile).toHaveBeenCalledWith('1', {
        fullName: 'Updated Name',
        bio: 'Updated bio',
      });
    });
  });

  it('handles errors gracefully', async () => {
    // Mock an error response
    (socialService.getUserProfile as jest.Mock).mockRejectedValueOnce(
      new Error('Failed to load profile')
    );

    // Spy on console.error
    const consoleSpy = jest.spyOn(console, 'error').mockImplementation();

    render(<UserProfile userId="1" currentUserId="2" />);

    // Wait for error handling
    await waitFor(() => {
      expect(consoleSpy).toHaveBeenCalledWith(
        'Error loading user profile:',
        expect.any(Error)
      );
    });

    // Clean up
    consoleSpy.mockRestore();
  });
}); 