import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import authReducer from '../../../store/slices/authSlice';
import ResetPassword from '../ResetPassword';
import * as useAuthModule from '../../../hooks/useAuth';

// Increase jest timeout globally for this file
jest.setTimeout(30000);

// Mock the useAuth hook
jest.mock('../../../hooks/useAuth', () => ({
  useAuth: jest.fn()
}));

// Mock useNavigate and useParams
const mockNavigate = jest.fn();
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
  useParams: () => ({ token: 'mock-reset-token' }),
}));

describe('ResetPassword Component', () => {
  // Setup store for testing
  const store = configureStore({
    reducer: {
      auth: authReducer,
    },
  });

  // Setup mock implementations
  const mockResetPassword = jest.fn();
  const mockUseAuth = jest.fn();

  beforeEach(() => {
    // Reset mocks
    jest.clearAllMocks();
    
    // Default mock implementation for useAuth
    mockUseAuth.mockReturnValue({
      resetPassword: mockResetPassword,
      error: null,
      isLoading: false,
    });
    
    // Apply mock to the module
    (useAuthModule.useAuth as jest.Mock).mockImplementation(mockUseAuth);
    
    // Mock timers for setTimeout
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  // Helper function to render the component with necessary providers
  const renderResetPassword = () => {
    return render(
      <Provider store={store}>
        <BrowserRouter>
          <Routes>
            <Route path="*" element={<ResetPassword />} />
          </Routes>
        </BrowserRouter>
      </Provider>
    );
  };

  it('renders reset password form correctly', async () => {
    renderResetPassword();
    
    // Check that the form elements are rendered
    await waitFor(() => {
      expect(screen.getByText(/Reset Your Password/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Reset Password/i })).toBeInTheDocument();
      expect(screen.getByText(/Remember your password/i)).toBeInTheDocument();
    });
  });

  it('updates form values when user types in inputs', async () => {
    const user = userEvent.setup({ delay: null });
    const { container } = renderResetPassword();
    
    // Use data-testid to find elements
    const passwordInput = container.querySelector('input[name="password"]');
    const confirmPasswordInput = container.querySelector('input[name="confirmPassword"]');
    
    if (passwordInput && confirmPasswordInput) {
      // Simulate user typing with null delay
      await user.type(passwordInput, 'newpassword123');
      await user.type(confirmPasswordInput, 'newpassword123');
      
      // Check if values are updated
      await waitFor(() => {
        expect(passwordInput).toHaveValue('newpassword123');
        expect(confirmPasswordInput).toHaveValue('newpassword123');
      });
    } else {
      throw new Error('Password inputs not found');
    }
  });

  it('shows validation error when passwords do not match', async () => {
    const user = userEvent.setup({ delay: null });
    const { container } = renderResetPassword();
    
    // Find elements by name attribute
    const passwordInput = container.querySelector('input[name="password"]');
    const confirmPasswordInput = container.querySelector('input[name="confirmPassword"]');
    const resetButton = screen.getByRole('button', { name: /Reset Password/i });
    
    if (passwordInput && confirmPasswordInput) {
      // Fill form with non-matching passwords
      await user.type(passwordInput, 'newpassword123');
      await user.type(confirmPasswordInput, 'differentpassword');
      
      // Submit the form
      await user.click(resetButton);
      
      // Check for validation error
      await waitFor(() => {
        expect(screen.getByText(/Passwords do not match/i)).toBeInTheDocument();
        // Verify resetPassword was not called
        expect(mockResetPassword).not.toHaveBeenCalled();
      });
    } else {
      throw new Error('Password inputs not found');
    }
  });

  it('shows validation error when password is too short', async () => {
    const user = userEvent.setup({ delay: null });
    const { container } = renderResetPassword();
    
    // Find elements by name attribute
    const passwordInput = container.querySelector('input[name="password"]');
    const confirmPasswordInput = container.querySelector('input[name="confirmPassword"]');
    const resetButton = screen.getByRole('button', { name: /Reset Password/i });
    
    if (passwordInput && confirmPasswordInput) {
      // Fill form with short password
      await user.type(passwordInput, 'short');
      await user.type(confirmPasswordInput, 'short');
      
      // Submit the form
      await user.click(resetButton);
      
      // Check for validation error
      await waitFor(() => {
        expect(screen.getByText(/Password must be at least 8 characters long/i)).toBeInTheDocument();
        // Verify resetPassword was not called
        expect(mockResetPassword).not.toHaveBeenCalled();
      });
    } else {
      throw new Error('Password inputs not found');
    }
  });

  it('calls resetPassword function with correct token and password on valid form submission', async () => {
    const user = userEvent.setup({ delay: null });
    // Mock successful password reset
    mockResetPassword.mockResolvedValue(undefined);
    const { container } = renderResetPassword();
    
    // Find elements by name attribute
    const passwordInput = container.querySelector('input[name="password"]');
    const confirmPasswordInput = container.querySelector('input[name="confirmPassword"]');
    const resetButton = screen.getByRole('button', { name: /Reset Password/i });
    
    if (passwordInput && confirmPasswordInput) {
      // Fill form with valid data
      await user.type(passwordInput, 'newpassword123');
      await user.type(confirmPasswordInput, 'newpassword123');
      
      // Submit the form
      await user.click(resetButton);
      
      // Verify resetPassword was called with correct data
      await waitFor(() => {
        expect(mockResetPassword).toHaveBeenCalledWith('mock-reset-token', 'newpassword123');
      });
    } else {
      throw new Error('Password inputs not found');
    }
  });

  it('displays loading state while resetting password', async () => {
    const user = userEvent.setup({ delay: null });
    // Create a mock implementation that delays resolution
    mockResetPassword.mockImplementation(() => {
      return new Promise(resolve => {
        setTimeout(() => {
          resolve(undefined);
        }, 500);
      });
    });
    
    // Use normal auth mock (not with isLoading pre-set)
    mockUseAuth.mockReturnValue({
      resetPassword: mockResetPassword,
      error: null,
      isLoading: false, // Start with false
    });
    
    const { container } = renderResetPassword();
    
    // Find elements
    const passwordInput = container.querySelector('input[name="password"]');
    const confirmPasswordInput = container.querySelector('input[name="confirmPassword"]');
    const resetButton = screen.getByRole('button', { name: /Reset Password/i });
    
    if (passwordInput && confirmPasswordInput) {
      // Fill form with valid data
      await user.type(passwordInput, 'newpassword123');
      await user.type(confirmPasswordInput, 'newpassword123');
      
      // Submit the form - this will trigger loading state
      await user.click(resetButton);
      
      // Now the button should be disabled and show loading state
      expect(resetButton).toBeDisabled();
    } else {
      throw new Error('Password inputs not found');
    }
  });

  it('shows success message after successful password reset', async () => {
    const user = userEvent.setup({ delay: null });
    // Mock successful password reset
    mockResetPassword.mockResolvedValue(undefined);
    const { container } = renderResetPassword();
    
    // Find elements by name attribute
    const passwordInput = container.querySelector('input[name="password"]');
    const confirmPasswordInput = container.querySelector('input[name="confirmPassword"]');
    const resetButton = screen.getByRole('button', { name: /Reset Password/i });
    
    if (passwordInput && confirmPasswordInput) {
      // Fill form with valid data
      await user.type(passwordInput, 'newpassword123');
      await user.type(confirmPasswordInput, 'newpassword123');
      
      // Submit the form
      await user.click(resetButton);
      
      // Wait for the success message
      await waitFor(() => {
        expect(screen.getByText(/Password has been reset successfully/i)).toBeInTheDocument();
      });
    } else {
      throw new Error('Password inputs not found');
    }
  });

  it('redirects to login page after successful password reset', async () => {
    const user = userEvent.setup({ delay: null });
    // Mock successful password reset
    mockResetPassword.mockResolvedValue(undefined);
    const { container } = renderResetPassword();
    
    // Find elements by name attribute
    const passwordInput = container.querySelector('input[name="password"]');
    const confirmPasswordInput = container.querySelector('input[name="confirmPassword"]');
    const resetButton = screen.getByRole('button', { name: /Reset Password/i });
    
    if (passwordInput && confirmPasswordInput) {
      // Fill form with valid data
      await user.type(passwordInput, 'newpassword123');
      await user.type(confirmPasswordInput, 'newpassword123');
      
      // Submit the form
      await user.click(resetButton);
      
      // Fast-forward timers
      jest.advanceTimersByTime(3000);
      
      // Verify redirect to login page
      await waitFor(() => {
        expect(mockNavigate).toHaveBeenCalledWith('/login');
      });
    } else {
      throw new Error('Password inputs not found');
    }
  });

  it('displays API error when password reset fails', async () => {
    const user = userEvent.setup({ delay: null });
    // Mock failed password reset
    const mockError = 'Invalid or expired reset token';
    mockUseAuth.mockReturnValue({
      resetPassword: mockResetPassword,
      error: mockError,
      isLoading: false,
    });
    
    renderResetPassword();
    
    // Check that error message is displayed
    await waitFor(() => {
      expect(screen.getByText(mockError)).toBeInTheDocument();
    });
  });

  it('navigates to login page when clicking "Login here" button', async () => {
    const user = userEvent.setup({ delay: null });
    renderResetPassword();
    
    const loginButton = screen.getByRole('button', { name: /Login here/i });
    await user.click(loginButton);
    
    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/login');
    });
  });
}); 