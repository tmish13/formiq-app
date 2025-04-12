import { renderHook, act } from '@testing-library/react-hooks';
import { Provider } from 'react-redux';
import { BrowserRouter } from 'react-router-dom';
import { configureStore } from '@reduxjs/toolkit';
import { useAuth } from '../../hooks/useAuth';
import authReducer from '../../store/slices/authSlice';
import { authService } from '../../services/auth';
import { storageService } from '../../services/storageService';

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
    jest.clearAllMocks();
  });

  it('should initialize auth from storage on mount', async () => {
    const mockToken = 'test-token';
    const mockRefreshToken = 'test-refresh-token';
    
    (storageService.getAuthToken as jest.Mock).mockResolvedValue(mockToken);
    (storageService.getRefreshToken as jest.Mock).mockResolvedValue(mockRefreshToken);
    
    const { result, waitForNextUpdate } = renderHook(() => useAuth(), { wrapper });
    
    await waitForNextUpdate();
    
    expect(storageService.getAuthToken).toHaveBeenCalled();
    expect(storageService.getRefreshToken).toHaveBeenCalled();
    expect(result.current.isLoading).toBe(false);
  });

  it('should handle login successfully', async () => {
    const mockUser = { id: '1', email: 'test@example.com', name: 'Test User' };
    const mockResponse = {
      access_token: 'test-token',
      refresh_token: 'test-refresh-token',
      user: mockUser,
    };

    (authService.login as jest.Mock).mockResolvedValue(mockResponse);

    const { result } = renderHook(() => useAuth(), { wrapper });

    await act(async () => {
      await result.current.login('test@example.com', 'password');
    });

    expect(authService.login).toHaveBeenCalledWith({
      email: 'test@example.com',
      password: 'password',
    });
    expect(storageService.setAuthToken).toHaveBeenCalledWith('test-token');
    expect(storageService.setRefreshToken).toHaveBeenCalledWith('test-refresh-token');
    expect(mockNavigate).toHaveBeenCalledWith('/dashboard');
    expect(result.current.user).toEqual(mockUser);
    expect(result.current.isAuthenticated).toBe(true);
  });

  it('should handle registration successfully', async () => {
    const mockUser = { id: '1', email: 'test@example.com', name: 'Test User' };
    const mockResponse = {
      access_token: 'test-token',
      refresh_token: 'test-refresh-token',
      user: mockUser,
    };

    (authService.register as jest.Mock).mockResolvedValue(mockResponse);

    const { result } = renderHook(() => useAuth(), { wrapper });

    await act(async () => {
      await result.current.register('test@example.com', 'password', 'Test User');
    });

    expect(authService.register).toHaveBeenCalledWith({
      email: 'test@example.com',
      password: 'password',
      name: 'Test User',
    });
    expect(storageService.setAuthToken).toHaveBeenCalledWith('test-token');
    expect(storageService.setRefreshToken).toHaveBeenCalledWith('test-refresh-token');
    expect(mockNavigate).toHaveBeenCalledWith('/dashboard');
    expect(result.current.user).toEqual(mockUser);
    expect(result.current.isAuthenticated).toBe(true);
  });

  it('should handle logout successfully', async () => {
    const { result } = renderHook(() => useAuth(), { wrapper });

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
    const mockUser = { id: '1', email: 'test@example.com', name: 'Updated Name' };
    (authService.updateProfile as jest.Mock).mockResolvedValue(mockUser);

    const { result } = renderHook(() => useAuth(), { wrapper });

    await act(async () => {
      await result.current.updateProfile({ name: 'Updated Name' });
    });

    expect(authService.updateProfile).toHaveBeenCalledWith({ name: 'Updated Name' });
    expect(result.current.user).toEqual(mockUser);
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