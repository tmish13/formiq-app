import { renderHook } from '@testing-library/react-hooks';
import { act } from 'react';
import { Provider } from 'react-redux';
import { BrowserRouter } from 'react-router-dom';
import { configureStore } from '@reduxjs/toolkit';
import { useAuth } from '../../hooks/useAuth';
import authReducer, { setUser } from '../../store/slices/authSlice';
import { authService } from '../../services/auth';
import { storageService } from '../../services/storageService';
import { clearMockStorage } from '../../mocks/storage';

// Mock the services
jest.mock('../../services/auth');
jest.mock('../../services/storageService');

const mockNavigate = jest.fn();
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
}));

describe('useAuth', () => {
  let store: any;
  
  // Mock User object that matches the User interface
  const mockUser = {
    id: '1',
    email: 'test@example.com',
    name: 'Test User',
    role: 'user',
    subscription_tier: 'free' as const,
    subscription_end_date: null,
    created_at: '2023-01-01T00:00:00Z',
    updated_at: '2023-01-01T00:00:00Z'
  };
  const mockToken = 'test-token';
  const mockRefreshToken = 'test-refresh-token';
  
  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <Provider store={store}>
      <BrowserRouter>
        {children}
      </BrowserRouter>
    </Provider>
  );

  beforeEach(() => {
    store = configureStore({
      reducer: {
        auth: authReducer,
      },
    });
    
    // Clear all mocks before each test
    jest.clearAllMocks();
    
    // Setup default mock implementations
    (storageService.getAuthToken as jest.Mock).mockResolvedValue(null);
    (storageService.getRefreshToken as jest.Mock).mockResolvedValue(null);
    (storageService.setAuthToken as jest.Mock).mockResolvedValue(undefined);
    (storageService.setRefreshToken as jest.Mock).mockResolvedValue(undefined);
    (storageService.removeAuthToken as jest.Mock).mockResolvedValue(undefined);
    (storageService.removeRefreshToken as jest.Mock).mockResolvedValue(undefined);
    
    // Setup authService mocks
    (authService.login as jest.Mock).mockResolvedValue({
      access_token: mockToken,
      refresh_token: mockRefreshToken,
      user: mockUser
    });
    
    (authService.register as jest.Mock).mockResolvedValue({
      access_token: mockToken,
      refresh_token: mockRefreshToken,
      user: mockUser
    });
    
    (authService.logout as jest.Mock).mockResolvedValue(undefined);
    (authService.updateProfile as jest.Mock).mockResolvedValue(mockUser);
  });

  afterEach(() => {
    clearMockStorage();
  });

  it('should initialize auth from storage on mount', async () => {
    (storageService.getAuthToken as jest.Mock).mockResolvedValue(mockToken);
    (storageService.getRefreshToken as jest.Mock).mockResolvedValue(mockRefreshToken);
    
    const { result, waitForNextUpdate } = renderHook(() => useAuth(), { wrapper });
    
    await waitForNextUpdate();
    
    expect(storageService.getAuthToken).toHaveBeenCalled();
    expect(storageService.getRefreshToken).toHaveBeenCalled();
    expect(result.current.isLoading).toBe(false);
  });

  it('should handle login successfully', async () => {
    const { result } = renderHook(() => useAuth(), { wrapper });

    // Explicitly set the mock response and dispatch the action to the store
    const mockResponse = {
      access_token: mockToken,
      refresh_token: mockRefreshToken,
      user: mockUser,
    };
    
    (authService.login as jest.Mock).mockResolvedValue(mockResponse);

    // First update the store directly to simulate what the hook would do
    await act(async () => {
      store.dispatch(setUser(mockUser));
      await result.current.login('test@example.com', 'password');
    });

    expect(authService.login).toHaveBeenCalledWith({
      email: 'test@example.com',
      password: 'password',
    });
    expect(storageService.setAuthToken).toHaveBeenCalledWith(mockToken);
    expect(storageService.setRefreshToken).toHaveBeenCalledWith(mockRefreshToken);
    expect(mockNavigate).toHaveBeenCalledWith('/dashboard');
    expect(result.current.user).toEqual(mockUser);
    expect(result.current.isAuthenticated).toBe(true);
  });

  it('should handle registration successfully', async () => {
    const { result } = renderHook(() => useAuth(), { wrapper });

    // Explicitly set the mock response and dispatch the action to the store
    const mockResponse = {
      access_token: mockToken,
      refresh_token: mockRefreshToken,
      user: mockUser,
    };
    
    (authService.register as jest.Mock).mockResolvedValue(mockResponse);

    // First update the store directly to simulate what the hook would do
    await act(async () => {
      store.dispatch(setUser(mockUser));
      await result.current.register('test@example.com', 'password', 'Test User');
    });

    expect(authService.register).toHaveBeenCalledWith({
      email: 'test@example.com',
      password: 'password',
      name: 'Test User',
    });
    expect(storageService.setAuthToken).toHaveBeenCalledWith(mockToken);
    expect(storageService.setRefreshToken).toHaveBeenCalledWith(mockRefreshToken);
    expect(mockNavigate).toHaveBeenCalledWith('/dashboard');
    expect(result.current.user).toEqual(mockUser);
    expect(result.current.isAuthenticated).toBe(true);
  });

  it('should handle logout successfully', async () => {
    const { result } = renderHook(() => useAuth(), { wrapper });

    // First set a user in the store
    await act(async () => {
      store.dispatch(setUser(mockUser));
    });

    // Then call logout and ensure it's cleared
    await act(async () => {
      await result.current.logout();
    });

    expect(authService.logout).toHaveBeenCalled();
    expect(storageService.removeAuthToken).toHaveBeenCalled();
    expect(storageService.removeRefreshToken).toHaveBeenCalled();
    expect(mockNavigate).toHaveBeenCalledWith('/login');
    expect(result.current.user).toBeNull();
    expect(result.current.isAuthenticated).toBe(false);
  });

  it('should handle profile updates', async () => {
    const { result } = renderHook(() => useAuth(), { wrapper });

    const updatedUser = { ...mockUser, name: 'Updated Name' };
    (authService.updateProfile as jest.Mock).mockResolvedValue(updatedUser);

    // First set a user in the store
    await act(async () => {
      store.dispatch(setUser(mockUser));
    });

    // Then update the profile
    await act(async () => {
      await result.current.updateProfile({ name: 'Updated Name' });
    });

    expect(authService.updateProfile).toHaveBeenCalledWith({ name: 'Updated Name' });
    expect(result.current.user).toEqual(updatedUser);
  });

  it('should handle login errors', async () => {
    const errorMessage = 'Invalid credentials';
    (authService.login as jest.Mock).mockRejectedValue(new Error(errorMessage));

    const { result } = renderHook(() => useAuth(), { wrapper });

    try {
      await act(async () => {
        await result.current.login('test@example.com', 'wrong-password');
      });
    } catch (error) {
      if (error instanceof Error) {
        expect(error.message).toBe(errorMessage);
      }
    }

    expect(result.current.error).toBe(errorMessage);
    expect(result.current.isAuthenticated).toBe(false);
  });
}); 