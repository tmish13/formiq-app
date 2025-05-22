import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { BrowserRouter } from 'react-router-dom';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import authReducer from '../../../store/slices/authSlice';
import UserProfile from '../UserProfile';
import ProfileSettings from '../ProfileSettings';
import AchievementDisplay from '../AchievementDisplay';

// Create a mock theme for Material UI components
const theme = createTheme();

// Mock the profile service
const mockProfileService = {
  getUserProfile: jest.fn(),
  updateUserProfile: jest.fn(),
  updateUserSettings: jest.fn(),
  getUserAchievements: jest.fn(),
  uploadProfileImage: jest.fn()
};

// Mock the storage service for profile data
const mockStorageService = {
  getUserProfile: jest.fn(),
  setUserProfile: jest.fn(),
  getUserSettings: jest.fn(),
  setUserSettings: jest.fn(),
  clearUserData: jest.fn()
};

// Mock icons
jest.mock('@mui/icons-material', () => ({
  Edit: () => <span data-testid="edit-icon">Edit</span>,
  Save: () => <span data-testid="save-icon">Save</span>,
  Cancel: () => <span data-testid="cancel-icon">Cancel</span>,
  Settings: () => <span data-testid="settings-icon">Settings</span>,
  EmojiEvents: () => <span data-testid="achievements-icon">Achievements</span>
}));

// Mock the profile API service module
jest.mock('../../../services/profileService', () => ({
  profileService: mockProfileService
}));

// Mock the storage service module
jest.mock('../../../services/storageService', () => ({
  storageService: mockStorageService
}));

// Mock the file uploader component
jest.mock('../../common/FileUpload', () => ({
  FileUpload: ({ onUpload }) => (
    <div data-testid="file-uploader">
      <input 
        type="file" 
        data-testid="file-input" 
        onChange={(e) => {
          const file = new File(['(⌐□_□)'], 'profile.png', { type: 'image/png' });
          onUpload(file);
        }} 
      />
      <button onClick={() => onUpload(new File(['(⌐□_□)'], 'profile.png', { type: 'image/png' }))}>
        Upload
      </button>
    </div>
  )
}));

// Sample user data for tests
const mockUser = {
  id: 'user123',
  username: 'fitnessuser',
  fullName: 'Fitness User',
  email: 'fitness@example.com',
  bio: 'Fitness enthusiast focused on strength training',
  profileImage: 'https://example.com/profile.jpg',
  fitnessLevel: 'intermediate',
  joinDate: '2023-05-15',
  metrics: {
    workoutsCompleted: 68,
    averageScore: 87,
    improvementRate: 12
  }
};

// Sample achievements for tests
const mockAchievements = [
  {
    id: 'ach1',
    title: 'First Perfect Form',
    description: 'Achieved a 100% form score',
    earnedDate: '2023-06-20',
    icon: 'perfect_form'
  },
  {
    id: 'ach2',
    title: 'Consistency Champion',
    description: 'Completed workouts for 7 days in a row',
    earnedDate: '2023-07-15',
    icon: 'streak'
  },
  {
    id: 'ach3',
    title: 'Diversity Master',
    description: 'Tried all exercise types',
    earnedDate: '2023-08-10',
    icon: 'diversity'
  }
];

// Sample user settings for tests
const mockSettings = {
  notifications: {
    email: true,
    push: false,
    achievements: true,
    weeklyProgress: true
  },
  privacy: {
    profileVisibility: 'public',
    shareWorkouts: true,
    showRealName: false
  },
  preferences: {
    theme: 'light',
    language: 'en',
    units: 'metric'
  }
};

// Helper function to render with providers
const renderWithProviders = (ui) => {
  const store = configureStore({
    reducer: {
      auth: authReducer
    },
    preloadedState: {
      auth: {
        isAuthenticated: true,
        user: { id: mockUser.id, name: mockUser.fullName },
        isLoading: false,
        error: null
      }
    }
  });

  return render(
    <Provider store={store}>
      <ThemeProvider theme={theme}>
        <BrowserRouter>
          {ui}
        </BrowserRouter>
      </ThemeProvider>
    </Provider>
  );
};

describe('Profile Management', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    
    // Set up default mock implementations
    mockProfileService.getUserProfile.mockResolvedValue(mockUser);
    mockProfileService.getUserAchievements.mockResolvedValue(mockAchievements);
    mockProfileService.updateUserProfile.mockResolvedValue({ ...mockUser, fullName: 'Updated Name' });
    mockProfileService.updateUserSettings.mockResolvedValue(mockSettings);
    mockProfileService.uploadProfileImage.mockResolvedValue({ 
      url: 'https://example.com/new-profile.jpg'
    });
    
    mockStorageService.getUserProfile.mockResolvedValue(mockUser);
    mockStorageService.getUserSettings.mockResolvedValue(mockSettings);
  });

  /**
   * Tests for profile data display
   */
  describe('Profile Display', () => {
    it('renders user profile information correctly', async () => {
      renderWithProviders(<UserProfile userId={mockUser.id} />);
      
      // Wait for profile data to load
      await waitFor(() => {
        expect(screen.getByText(mockUser.fullName)).toBeInTheDocument();
        expect(screen.getByText(mockUser.username)).toBeInTheDocument();
        expect(screen.getByText(mockUser.bio)).toBeInTheDocument();
      });
      
      // Check that metrics are displayed
      expect(screen.getByText(/68/)).toBeInTheDocument(); // workouts completed
      expect(screen.getByText(/87/)).toBeInTheDocument(); // average score
      
      // Verify API was called correctly
      expect(mockProfileService.getUserProfile).toHaveBeenCalledWith(mockUser.id);
    });

    it('displays achievements on the profile', async () => {
      renderWithProviders(<AchievementDisplay userId={mockUser.id} />);
      
      // Wait for achievements to load
      await waitFor(() => {
        expect(mockProfileService.getUserAchievements).toHaveBeenCalledWith(mockUser.id);
        expect(screen.getByText('First Perfect Form')).toBeInTheDocument();
        expect(screen.getByText('Consistency Champion')).toBeInTheDocument();
        expect(screen.getByText('Diversity Master')).toBeInTheDocument();
      });
    });

    it('shows appropriate message when user has no achievements', async () => {
      // Override mock to return empty achievements array
      mockProfileService.getUserAchievements.mockResolvedValue([]);
      
      renderWithProviders(<AchievementDisplay userId={mockUser.id} />);
      
      // Wait for achievements request to complete
      await waitFor(() => {
        expect(mockProfileService.getUserAchievements).toHaveBeenCalledWith(mockUser.id);
        expect(screen.getByText(/No achievements yet/i)).toBeInTheDocument();
      });
    });

    it('handles error when loading profile fails', async () => {
      // Mock API error
      mockProfileService.getUserProfile.mockRejectedValue(new Error('Failed to load profile'));
      
      renderWithProviders(<UserProfile userId={mockUser.id} />);
      
      // Wait for error handling
      await waitFor(() => {
        expect(screen.getByText(/Could not load profile/i)).toBeInTheDocument();
      });
    });
  });

  /**
   * Tests for profile editing
   */
  describe('Profile Editing', () => {
    it('allows user to edit their profile', async () => {
      const user = userEvent.setup();
      renderWithProviders(<UserProfile userId={mockUser.id} isCurrentUser={true} />);
      
      // Wait for profile to load
      await waitFor(() => {
        expect(screen.getByText(mockUser.fullName)).toBeInTheDocument();
      });
      
      // Click edit button
      const editButton = screen.getByTestId('edit-profile-button');
      await user.click(editButton);
      
      // Find and update name field
      const nameInput = screen.getByLabelText(/Full Name/i);
      await user.clear(nameInput);
      await user.type(nameInput, 'Updated Name');
      
      // Find and update bio field
      const bioInput = screen.getByLabelText(/Bio/i);
      await user.clear(bioInput);
      await user.type(bioInput, 'Updated bio information');
      
      // Save changes
      const saveButton = screen.getByTestId('save-profile-button');
      await user.click(saveButton);
      
      // Verify API was called with updated data
      expect(mockProfileService.updateUserProfile).toHaveBeenCalledWith(
        mockUser.id,
        expect.objectContaining({
          fullName: 'Updated Name',
          bio: 'Updated bio information'
        })
      );
      
      // Verify success message
      await waitFor(() => {
        expect(screen.getByText(/Profile updated successfully/i)).toBeInTheDocument();
      });
    });

    it('validates required fields during profile editing', async () => {
      const user = userEvent.setup();
      renderWithProviders(<UserProfile userId={mockUser.id} isCurrentUser={true} />);
      
      // Wait for profile to load
      await waitFor(() => {
        expect(screen.getByText(mockUser.fullName)).toBeInTheDocument();
      });
      
      // Click edit button
      const editButton = screen.getByTestId('edit-profile-button');
      await user.click(editButton);
      
      // Clear required name field
      const nameInput = screen.getByLabelText(/Full Name/i);
      await user.clear(nameInput);
      
      // Try to save changes
      const saveButton = screen.getByTestId('save-profile-button');
      await user.click(saveButton);
      
      // Verify validation error
      await waitFor(() => {
        expect(screen.getByText(/Name is required/i)).toBeInTheDocument();
      });
      
      // Verify API was not called
      expect(mockProfileService.updateUserProfile).not.toHaveBeenCalled();
    });

    it('allows user to upload a new profile picture', async () => {
      const user = userEvent.setup();
      renderWithProviders(<UserProfile userId={mockUser.id} isCurrentUser={true} />);
      
      // Wait for profile to load
      await waitFor(() => {
        expect(screen.getByText(mockUser.fullName)).toBeInTheDocument();
      });
      
      // Click edit button
      const editButton = screen.getByTestId('edit-profile-button');
      await user.click(editButton);
      
      // Find and click profile picture upload button
      const uploadButton = screen.getByTestId('upload-profile-picture');
      await user.click(uploadButton);
      
      // Mock file upload component should be visible
      expect(screen.getByTestId('file-uploader')).toBeInTheDocument();
      
      // Simulate file selection
      const fileInput = screen.getByTestId('file-input');
      await user.upload(fileInput, new File(['(⌐□_□)'], 'profile.png', { type: 'image/png' }));
      
      // Verify upload API was called
      expect(mockProfileService.uploadProfileImage).toHaveBeenCalled();
      
      // Verify profile update API was called with new image URL
      await waitFor(() => {
        expect(mockProfileService.updateUserProfile).toHaveBeenCalledWith(
          mockUser.id,
          expect.objectContaining({
            profileImage: 'https://example.com/new-profile.jpg'
          })
        );
      });
    });

    it('handles cancelling profile edit', async () => {
      const user = userEvent.setup();
      renderWithProviders(<UserProfile userId={mockUser.id} isCurrentUser={true} />);
      
      // Wait for profile to load
      await waitFor(() => {
        expect(screen.getByText(mockUser.fullName)).toBeInTheDocument();
      });
      
      // Click edit button
      const editButton = screen.getByTestId('edit-profile-button');
      await user.click(editButton);
      
      // Edit name field
      const nameInput = screen.getByLabelText(/Full Name/i);
      await user.clear(nameInput);
      await user.type(nameInput, 'Updated Name');
      
      // Click cancel button
      const cancelButton = screen.getByTestId('cancel-edit-button');
      await user.click(cancelButton);
      
      // Verify we exit edit mode
      await waitFor(() => {
        // Original name should still be shown
        expect(screen.getByText(mockUser.fullName)).toBeInTheDocument();
        // Edit button should be visible again
        expect(screen.getByTestId('edit-profile-button')).toBeInTheDocument();
      });
      
      // Verify API was NOT called
      expect(mockProfileService.updateUserProfile).not.toHaveBeenCalled();
    });
  });

  /**
   * Tests for profile settings
   */
  describe('Profile Settings', () => {
    it('renders user settings correctly', async () => {
      renderWithProviders(<ProfileSettings userId={mockUser.id} />);
      
      // Wait for settings to load
      await waitFor(() => {
        expect(mockProfileService.getUserProfile).toHaveBeenCalledWith(mockUser.id);
      });
      
      // Check that notification settings are displayed
      expect(screen.getByLabelText(/Email notifications/i)).toBeChecked();
      expect(screen.getByLabelText(/Push notifications/i)).not.toBeChecked();
      
      // Check that privacy settings are displayed
      expect(screen.getByLabelText(/Share workouts/i)).toBeChecked();
      expect(screen.getByLabelText(/Show real name/i)).not.toBeChecked();
      
      // Check that preference settings are displayed
      expect(screen.getByTestId('theme-selector')).toHaveValue('light');
      expect(screen.getByTestId('language-selector')).toHaveValue('en');
    });

    it('allows user to update notification settings', async () => {
      const user = userEvent.setup();
      renderWithProviders(<ProfileSettings userId={mockUser.id} />);
      
      // Wait for settings to load
      await waitFor(() => {
        expect(mockProfileService.getUserProfile).toHaveBeenCalledWith(mockUser.id);
      });
      
      // Toggle email notifications off
      const emailToggle = screen.getByLabelText(/Email notifications/i);
      await user.click(emailToggle);
      
      // Toggle push notifications on
      const pushToggle = screen.getByLabelText(/Push notifications/i);
      await user.click(pushToggle);
      
      // Save settings
      const saveButton = screen.getByRole('button', { name: /Save Settings/i });
      await user.click(saveButton);
      
      // Verify API was called with updated settings
      expect(mockProfileService.updateUserSettings).toHaveBeenCalledWith(
        mockUser.id,
        expect.objectContaining({
          notifications: expect.objectContaining({
            email: false,
            push: true
          })
        })
      );
      
      // Verify success message
      await waitFor(() => {
        expect(screen.getByText(/Settings updated successfully/i)).toBeInTheDocument();
      });
    });

    it('allows user to update privacy settings', async () => {
      const user = userEvent.setup();
      renderWithProviders(<ProfileSettings userId={mockUser.id} />);
      
      // Wait for settings to load
      await waitFor(() => {
        expect(mockProfileService.getUserProfile).toHaveBeenCalledWith(mockUser.id);
      });
      
      // Change profile visibility
      const visibilitySelect = screen.getByTestId('visibility-selector');
      await user.selectOptions(visibilitySelect, 'private');
      
      // Toggle share workouts off
      const shareWorkoutsToggle = screen.getByLabelText(/Share workouts/i);
      await user.click(shareWorkoutsToggle);
      
      // Save settings
      const saveButton = screen.getByRole('button', { name: /Save Settings/i });
      await user.click(saveButton);
      
      // Verify API was called with updated settings
      expect(mockProfileService.updateUserSettings).toHaveBeenCalledWith(
        mockUser.id,
        expect.objectContaining({
          privacy: expect.objectContaining({
            profileVisibility: 'private',
            shareWorkouts: false
          })
        })
      );
    });

    it('allows user to update preferences', async () => {
      const user = userEvent.setup();
      renderWithProviders(<ProfileSettings userId={mockUser.id} />);
      
      // Wait for settings to load
      await waitFor(() => {
        expect(mockProfileService.getUserProfile).toHaveBeenCalledWith(mockUser.id);
      });
      
      // Change theme
      const themeSelect = screen.getByTestId('theme-selector');
      await user.selectOptions(themeSelect, 'dark');
      
      // Change units
      const unitsSelect = screen.getByTestId('units-selector');
      await user.selectOptions(unitsSelect, 'imperial');
      
      // Save settings
      const saveButton = screen.getByRole('button', { name: /Save Settings/i });
      await user.click(saveButton);
      
      // Verify API was called with updated settings
      expect(mockProfileService.updateUserSettings).toHaveBeenCalledWith(
        mockUser.id,
        expect.objectContaining({
          preferences: expect.objectContaining({
            theme: 'dark',
            units: 'imperial'
          })
        })
      );
    });

    it('handles errors when updating settings fails', async () => {
      // Mock API error
      mockProfileService.updateUserSettings.mockRejectedValue(new Error('Failed to update settings'));
      
      const user = userEvent.setup();
      renderWithProviders(<ProfileSettings userId={mockUser.id} />);
      
      // Wait for settings to load
      await waitFor(() => {
        expect(mockProfileService.getUserProfile).toHaveBeenCalledWith(mockUser.id);
      });
      
      // Toggle email notifications off
      const emailToggle = screen.getByLabelText(/Email notifications/i);
      await user.click(emailToggle);
      
      // Save settings
      const saveButton = screen.getByRole('button', { name: /Save Settings/i });
      await user.click(saveButton);
      
      // Verify error message
      await waitFor(() => {
        expect(screen.getByText(/Failed to update settings/i)).toBeInTheDocument();
      });
    });
  });

  /**
   * Tests for account management
   */
  describe('Account Management', () => {
    it('allows user to delete their account', async () => {
      // Mock delete account function
      const mockDeleteAccount = jest.fn().mockResolvedValue({ success: true });
      mockProfileService.deleteAccount = mockDeleteAccount;
      
      const user = userEvent.setup();
      renderWithProviders(<ProfileSettings userId={mockUser.id} />);
      
      // Wait for settings to load
      await waitFor(() => {
        expect(mockProfileService.getUserProfile).toHaveBeenCalledWith(mockUser.id);
      });
      
      // Click delete account button
      const deleteButton = screen.getByRole('button', { name: /Delete Account/i });
      await user.click(deleteButton);
      
      // Confirmation dialog should appear
      expect(screen.getByText(/This action cannot be undone/i)).toBeInTheDocument();
      
      // Confirm deletion
      const confirmButton = screen.getByRole('button', { name: /Confirm/i });
      await user.click(confirmButton);
      
      // Verify delete API was called
      expect(mockDeleteAccount).toHaveBeenCalledWith(mockUser.id);
      
      // Verify success message
      await waitFor(() => {
        expect(screen.getByText(/Account deleted successfully/i)).toBeInTheDocument();
      });
    });

    it('allows user to cancel account deletion', async () => {
      // Mock delete account function
      const mockDeleteAccount = jest.fn().mockResolvedValue({ success: true });
      mockProfileService.deleteAccount = mockDeleteAccount;
      
      const user = userEvent.setup();
      renderWithProviders(<ProfileSettings userId={mockUser.id} />);
      
      // Wait for settings to load
      await waitFor(() => {
        expect(mockProfileService.getUserProfile).toHaveBeenCalledWith(mockUser.id);
      });
      
      // Click delete account button
      const deleteButton = screen.getByRole('button', { name: /Delete Account/i });
      await user.click(deleteButton);
      
      // Confirmation dialog should appear
      expect(screen.getByText(/This action cannot be undone/i)).toBeInTheDocument();
      
      // Cancel deletion
      const cancelButton = screen.getByRole('button', { name: /Cancel/i });
      await user.click(cancelButton);
      
      // Verify delete API was NOT called
      expect(mockDeleteAccount).not.toHaveBeenCalled();
      
      // Dialog should be closed
      expect(screen.queryByText(/This action cannot be undone/i)).not.toBeInTheDocument();
    });
  });
}); 