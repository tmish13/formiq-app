import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAppSelector, useAppDispatch } from '../store/hooks';
import { authService } from '../services/auth';
import { storageService } from '../services/storageService';
import { setUser, setToken, setRefreshToken, setError, setLoading, logout as logoutAction, setTokens } from '../store/slices/authSlice';
import type { User } from '../types';

export const useAuth = () => {
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  const { user, isAuthenticated, isLoading, error, token, refreshToken } = useAppSelector(
    (state) => state.auth
  );

  // Initial load of auth token from storage on app start
  useEffect(() => {
    const initializeAuth = async () => {
      try {
        // Only attempt to load from storage if not already authenticated
        if (!token) {
          dispatch(setLoading(true));
          // Load auth token and refresh token from storage
          const savedAuthToken = await storageService.getAuthToken();
          // You may also want to get the refresh token if your app uses it
          const savedRefreshToken = await storageService.getRefreshToken();
          
          if (savedAuthToken) {
            // Set the token in Redux store
            dispatch(setTokens({
              token: savedAuthToken,
              refreshToken: savedRefreshToken || ''
            }));
            // Token will trigger the other useEffect to fetch user data
          }
        }
      } catch (error) {
        console.error('Error initializing auth:', error);
      } finally {
        dispatch(setLoading(false));
      }
    };

    initializeAuth();
  }, [dispatch]);

  // When token is available but user isn't, fetch user data
  useEffect(() => {
    const checkAuth = async () => {
      if (!token) return;
      
      try {
        dispatch(setLoading(true));
        const currentUser = await authService.validateToken();
        dispatch(setUser(currentUser));
      } catch (error: any) {
        dispatch(setError(error.message));
        dispatch(logoutAction());
        // Clear stored tokens on error
        await storageService.removeAuthToken();
        await storageService.removeRefreshToken();
        navigate('/login');
      } finally {
        dispatch(setLoading(false));
      }
    };

    if (token && !user) {
      checkAuth();
    }
  }, [token, user, dispatch, navigate]);

  const login = async (email: string, password: string) => {
    try {
      dispatch(setLoading(true));
      const response = await authService.login({ email, password });
      
      // Store tokens in persistent storage
      await storageService.setAuthToken(response.access_token);
      if (response.refresh_token) {
        await storageService.setRefreshToken(response.refresh_token);
        dispatch(setRefreshToken(response.refresh_token));
      }
      
      dispatch(setToken(response.access_token));
      dispatch(setUser(response.user));
      navigate('/dashboard');
    } catch (error: any) {
      dispatch(setError(error.message));
      throw error;
    } finally {
      dispatch(setLoading(false));
    }
  };

  const logout = async () => {
    try {
      dispatch(setLoading(true));
      await authService.logout();
      // Remove tokens from storage
      await storageService.removeAuthToken();
      await storageService.removeRefreshToken();
      dispatch(logoutAction());
      navigate('/login');
    } catch (error: any) {
      dispatch(setError(error.message));
      throw error;
    } finally {
      dispatch(setLoading(false));
    }
  };

  const register = async (email: string, password: string, name: string) => {
    try {
      dispatch(setLoading(true));
      const response = await authService.register({ email, password, name });
      
      // Store tokens in persistent storage
      await storageService.setAuthToken(response.access_token);
      if (response.refresh_token) {
        await storageService.setRefreshToken(response.refresh_token);
        dispatch(setRefreshToken(response.refresh_token));
      }
      
      dispatch(setToken(response.access_token));
      dispatch(setUser(response.user));
      navigate('/dashboard');
    } catch (error: any) {
      dispatch(setError(error.message));
      throw error;
    } finally {
      dispatch(setLoading(false));
    }
  };

  const updateProfile = async (data: Partial<User>) => {
    try {
      dispatch(setLoading(true));
      const updatedUser = await authService.updateProfile(data);
      dispatch(setUser(updatedUser));
    } catch (error: any) {
      dispatch(setError(error.message));
      throw error;
    } finally {
      dispatch(setLoading(false));
    }
  };

  return {
    user,
    isAuthenticated,
    isLoading,
    error,
    login,
    logout,
    register,
    updateProfile,
  };
}; 