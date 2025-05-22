import { useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAppSelector, useAppDispatch } from '../store/hooks';
import { authService } from '../services/auth';
import { storageService } from '../services/storageService';
import { setUser, setToken, setRefreshToken, setError, setLoading, logout as logoutAction, setTokens } from '../store/slices/authSlice';
import type { User } from '../types';
import apiService from '../services/apiService';
import { logError } from '../utils/logger';

/**
 * Custom hook for authentication
 * Manages user authentication state and provides authentication methods
 */
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

  const verifyEmail = async (token: string): Promise<boolean> => {
    try {
      await apiService.post('/auth/verify-email', { token });
      return true;
    } catch (error) {
      logError('Email verification error', error);
      return false;
    }
  };

  /**
   * Request password reset email
   * @param email User's email address
   */
  const requestPasswordReset = useCallback(async (email: string) => {
    dispatch(setLoading(true));
    dispatch(setError(null));
    
    try {
      await apiService.post('/auth/reset-password/request', { email });
      return true;
    } catch (err: any) {
      if (err.status === 429) {
        // Handle rate limit error
        const retryAfter = err.details?.retryAfter;
        const retryMinutes = retryAfter ? Math.ceil(parseInt(retryAfter) / 60) : 60;
        dispatch(setError(`Too many password reset requests. Please try again in ${retryMinutes} minutes.`));
      } else {
        dispatch(setError(err.message));
      }
      return false;
    } finally {
      dispatch(setLoading(false));
    }
  }, [dispatch]);

  /**
   * Confirm password reset with token and new password
   * @param token Reset token from email
   * @param newPassword New password
   */
  const confirmPasswordReset = useCallback(async (token: string, newPassword: string) => {
    dispatch(setLoading(true));
    dispatch(setError(null));
    
    try {
      await apiService.post('/auth/reset-password/confirm', { 
        token, 
        new_password: newPassword 
      });
      return true;
    } catch (err: any) {
      dispatch(setError(err.message));
      return false;
    } finally {
      dispatch(setLoading(false));
    }
  }, [dispatch]);

  /**
   * Request email verification
   * @param email User's email address
   */
  const requestEmailVerification = useCallback(async (email: string) => {
    dispatch(setLoading(true));
    dispatch(setError(null));
    
    try {
      await apiService.post('/auth/verify-email/request', { email });
      return true;
    } catch (err: any) {
      if (err.status === 429) {
        // Handle rate limit error
        const retryAfter = err.details?.retryAfter;
        const retryMinutes = retryAfter ? Math.ceil(parseInt(retryAfter) / 60) : 60;
        dispatch(setError(`Too many verification requests. Please try again in ${retryMinutes} minutes.`));
      } else {
        dispatch(setError(err.message));
      }
      return false;
    } finally {
      dispatch(setLoading(false));
    }
  }, [dispatch]);

  /**
   * Confirm email verification with token
   * @param token Verification token from email
   */
  const confirmEmailVerification = useCallback(async (token: string) => {
    dispatch(setLoading(true));
    dispatch(setError(null));
    
    try {
      await apiService.post('/auth/verify-email/confirm', { token });
      return true;
    } catch (err: any) {
      dispatch(setError(err.message));
      return false;
    } finally {
      dispatch(setLoading(false));
    }
  }, [dispatch]);

  return {
    user,
    isAuthenticated,
    isLoading,
    error,
    login,
    logout,
    register,
    updateProfile,
    verifyEmail,
    requestPasswordReset,
    confirmPasswordReset,
    requestEmailVerification,
    confirmEmailVerification,
  };
}; 