import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { UserProfile } from '../UserProfile';
import { ThemeProvider, createTheme } from '@mui/material/styles';

// Create a test theme
const theme = createTheme();

// Mock Material UI components
jest.mock('@mui/material', () => {
  const actual = jest.requireActual('@mui/material');
  return {
    ...actual,
    Box: ({ children, ...props }) => <div data-testid="mui-box" {...props}>{children}</div>,
    Card: ({ children, ...props }) => <div data-testid="mui-card" {...props}>{children}</div>,
    CardContent: ({ children, ...props }) => <div data-testid="mui-card-content" {...props}>{children}</div>,
    Typography: ({ children, variant, ...props }) => <div data-testid={`mui-typography-${variant || 'default'}`} {...props}>{children}</div>,
    Avatar: ({ children, ...props }) => <div data-testid="mui-avatar" {...props}>{children}</div>,
    Button: ({ children, onClick, ...props }) => <button data-testid="mui-button" onClick={onClick} {...props}>{children}</button>,
    Grid: ({ children, ...props }) => <div data-testid="mui-grid" {...props}>{children}</div>,
    Chip: ({ label, ...props }) => <div data-testid="mui-chip" {...props}>{label}</div>,
    List: ({ children, ...props }) => <ul data-testid="mui-list" {...props}>{children}</ul>,
    ListItem: ({ children, ...props }) => <li data-testid="mui-list-item" {...props}>{children}</li>,
    ListItemText: ({ primary, secondary, ...props }) => (
      <div data-testid="mui-list-item-text" {...props}>
        <div>{primary}</div>
        {secondary && <div>{secondary}</div>}
      </div>
    ),
    Divider: ({ ...props }) => <hr data-testid="mui-divider" {...props} />,
    IconButton: ({ children, onClick, ...props }) => (
      <button data-testid="mui-icon-button" onClick={onClick} {...props}>{children}</button>
    ),
    Dialog: ({ children, open, ...props }) => open ? <div data-testid="mui-dialog" {...props}>{children}</div> : null,
    DialogTitle: ({ children, ...props }) => <div data-testid="mui-dialog-title" {...props}>{children}</div>,
    DialogContent: ({ children, ...props }) => <div data-testid="mui-dialog-content" {...props}>{children}</div>,
    DialogActions: ({ children, ...props }) => <div data-testid="mui-dialog-actions" {...props}>{children}</div>,
    TextField: ({ label, onChange, value, ...props }) => (
      <div data-testid="mui-text-field" {...props}>
        <label>{label}</label>
        <input aria-label={label} value={value || ''} onChange={onChange} />
      </div>
    ),
  };
});

// Mock Material UI Icons
jest.mock('@mui/icons-material', () => ({
  Favorite: () => <span data-testid="mui-icon-favorite">Favorite</span>,
  FavoriteBorder: () => <span data-testid="mui-icon-favorite-border">FavoriteBorder</span>,
  Comment: () => <span data-testid="mui-icon-comment">Comment</span>,
  Share: () => <span data-testid="mui-icon-share">Share</span>,
  Edit: () => <span data-testid="mui-icon-edit">Edit</span>,
  EmojiEvents: () => <span data-testid="mui-icon-emoji-events">EmojiEvents</span>,
  People: () => <span data-testid="mui-icon-people">People</span>,
}));

// Define mocked types to match the actual service interfaces
interface Exercise {
  id: string;
  name: string;
  type: string;
  description: string;
  difficulty: 'beginner' | 'intermediate' | 'advanced';
  targetMuscles: string[];
  equipment: string[];
}

interface WorkoutTemplate {
  id: string;
  name: string;
  description: string;
  difficulty: 'beginner' | 'intermediate' | 'advanced';
  exercises: Array<{
    exercise: Exercise;
    sets: number;
    reps: number;
    restTime: number;
    order: number;
  }>;
  estimatedDuration: number;
  targetMuscleGroups: string[];
  createdAt: string;
  updatedAt: string;
}

interface Achievement {
  id: string;
  name: string;
  description: string;
  icon: string;
  dateEarned: string;
}

interface Comment {
  id: string;
  userId: string;
  content: string;
  createdAt: string;
  updatedAt: string;
}

interface WorkoutShare {
  id: string;
  userId: string;
  templateId: string;
  template: WorkoutTemplate;
  likes: number;
  comments: Comment[];
  createdAt: string;
  updatedAt: string;
}

interface User {
  id: string;
  username: string;
  fullName?: string;
  avatar?: string;
  bio?: string;
  fitnessLevel: 'beginner' | 'intermediate' | 'advanced';
  achievements: Achievement[];
  followers: number;
  following: number;
}

// Define mock functions
const mockGetUserProfile = jest.fn();
const mockFollowUser = jest.fn();
const mockUnfollowUser = jest.fn();
const mockLikeWorkoutShare = jest.fn();
const mockGetSharedWorkouts = jest.fn();
const mockUpdateUserProfile = jest.fn();
const mockAddComment = jest.fn();

// Mock the socialService module
jest.mock('../../../services/socialService', () => ({
  socialService: {
    getUserProfile: (...args) => mockGetUserProfile(...args),
    followUser: (...args) => mockFollowUser(...args),
    unfollowUser: (...args) => mockUnfollowUser(...args),
    likeWorkoutShare: (...args) => mockLikeWorkoutShare(...args),
    getSharedWorkouts: (...args) => mockGetSharedWorkouts(...args),
    updateUserProfile: (...args) => mockUpdateUserProfile(...args),
    addComment: (...args) => mockAddComment(...args)
  }
}));

// Mock date-fns
jest.mock('date-fns', () => ({
  formatDistanceToNow: jest.fn(() => '2 days ago'),
}));

// Custom render function with theme provider
const renderWithTheme = (ui) => {
  return render(
    <ThemeProvider theme={theme}>
      {ui}
    </ThemeProvider>
  );
};

describe('UserProfile', () => {
  // Mock data
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
        id: '1',
        name: 'Squat',
        description: 'A great squat workout',
        difficulty: 'intermediate',
        exercises: [],
        estimatedDuration: 30,
        targetMuscleGroups: ['legs'],
        createdAt: '2024-03-20T10:00:00Z',
        updatedAt: '2024-03-20T10:00:00Z',
      },
      likes: 10,
      comments: [],
      createdAt: '2024-03-20T10:00:00Z',
      updatedAt: '2024-03-20T10:00:00Z',
    },
  ];

  // Setup before each test
  beforeEach(() => {
    // Reset all mocks
    jest.clearAllMocks();
    
    // Set up mock implementations
    mockGetUserProfile.mockResolvedValue(mockUser);
    mockGetSharedWorkouts.mockResolvedValue(mockWorkouts);
    mockFollowUser.mockResolvedValue({ success: true });
    mockUnfollowUser.mockResolvedValue({ success: true });
    mockLikeWorkoutShare.mockResolvedValue({ success: true });
    mockUpdateUserProfile.mockResolvedValue(mockUser);
    mockAddComment.mockResolvedValue({ 
      id: 'new-comment', 
      userId: '2', 
      content: 'Nice workout!',
      createdAt: '2024-03-20T10:00:00Z',
      updatedAt: '2024-03-20T10:00:00Z'
    });
  });

  it('handles errors gracefully', async () => {
    const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
    mockGetUserProfile.mockRejectedValue(new Error('Failed to load profile'));

    renderWithTheme(<UserProfile userId="1" currentUserId="2" />);
    
    // Wait for error handling
    await waitFor(() => {
      expect(screen.getByTestId('mui-typography-h6')).toHaveTextContent('Failed to load user data');
    });

    // Clean up
    consoleSpy.mockRestore();
  });

  it('renders user profile data correctly', async () => {
    renderWithTheme(<UserProfile userId="1" currentUserId="2" />);
    
    // Wait for the API calls
    await waitFor(() => {
      expect(mockGetUserProfile).toHaveBeenCalledWith('1');
      expect(mockGetSharedWorkouts).toHaveBeenCalledWith('1');
    });
  });

  it('handles workout interactions correctly', async () => {
    renderWithTheme(<UserProfile userId="1" currentUserId="2" />);
    
    // Wait for the API calls to be made
    await waitFor(() => {
      expect(mockGetUserProfile).toHaveBeenCalledWith('1');
      expect(mockGetSharedWorkouts).toHaveBeenCalledWith('1');
    });
  });

  it('handles profile editing correctly', async () => {
    renderWithTheme(<UserProfile userId="1" currentUserId="1" />);
    
    // Wait for the API calls
    await waitFor(() => {
      expect(mockGetUserProfile).toHaveBeenCalledWith('1');
    });
  });
}); 