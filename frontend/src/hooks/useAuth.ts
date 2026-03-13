import { useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAppSelector, useAppDispatch } from '../store/hooks';
import { setUser, setToken, setRefreshToken, setError, setLoading, logout as logoutAction, setTokens } from '../store/slices/authSlice';
import type { User } from '../types';
import apiService from '../services/apiService';
import { logError } from '../utils/logger';
import { setUserPrefs } from '../utils/userPrefs';
import { progressService } from '../services/progressService';

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
        // Only attempt to load from storage if not already authenticated and not loading
        if (!token && !isLoading) {
          dispatch(setLoading(true));
          
          // Simple localStorage check for web
          const savedAuthToken = localStorage.getItem('formiq_auth_token');
          const savedRefreshToken = localStorage.getItem('formiq_refresh_token');
          
          if (savedAuthToken) {
            // Validate token format (basic check)
            try {
              // Decode JWT to check expiration (without verification)
              const tokenPayload = JSON.parse(atob(savedAuthToken.split('.')[1]));
              const now = Date.now() / 1000;
              
              if (tokenPayload.exp && tokenPayload.exp < now) {
                // Token is expired, clear it
                console.log('Token expired, clearing auth');
                localStorage.removeItem('formiq_auth_token');
                localStorage.removeItem('formiq_refresh_token');
                dispatch(setLoading(false));
                return;
              }
            } catch (e) {
              // Invalid token format, clear it
              console.error('Invalid token format:', e);
              localStorage.removeItem('formiq_auth_token');
              localStorage.removeItem('formiq_refresh_token');
              dispatch(setLoading(false));
              return;
            }
            
            // Set the token in Redux store
            dispatch(setTokens({
              token: savedAuthToken,
              refreshToken: savedRefreshToken || ''
            }));
            dispatch(setLoading(false)); // unblock ProtectedRoute immediately; checkAuth runs in background
            // Token will trigger the other useEffect to fetch user data
          } else {
            // No saved token, user is not authenticated
            dispatch(setLoading(false));
          }
        }
      } catch (error) {
        console.error('Error initializing auth:', error);
        dispatch(setLoading(false));
      }
    };

    initializeAuth();
  }, [dispatch, token, isLoading]);

  // When token is available but user isn't, fetch user data
  useEffect(() => {
    const checkAuth = async () => {
      if (!token || user) return;

      try {
        const response = await apiService.validateSession();
        const currentUser = response.data;
        dispatch(setUser(currentUser));
        // Seed localStorage prefs from backend — only non-null values overwrite existing ones
        setUserPrefs({
          ...(currentUser.fitness_goal != null && { fitnessGoal: currentUser.fitness_goal }),
          ...(currentUser.fitness_level != null && { fitnessLevel: currentUser.fitness_level }),
          ...(currentUser.weight_kg != null && { weightKg: currentUser.weight_kg }),
          ...(currentUser.age != null && { age: currentUser.age }),
          ...(currentUser.height_cm != null && { heightCm: currentUser.height_cm }),
          ...(currentUser.training_experience != null && { trainingExperience: currentUser.training_experience as any }),
        });
      } catch (error: any) {
        dispatch(setError(error.message));
        // Clear invalid token
        dispatch(setTokens({ token: '', refreshToken: '' }));
        localStorage.removeItem('formiq_auth_token');
        localStorage.removeItem('formiq_refresh_token');
      } finally {
        dispatch(setLoading(false));
      }
    };

    checkAuth();
  }, [token, user, dispatch]);

  const login = useCallback(async (email: string, password: string) => {
    try {
      dispatch(setLoading(true));
      dispatch(setError(null));
      
      const response = await apiService.login(email, password);
      const { user, access_token, refresh_token } = response.data;

      // Store tokens
      localStorage.setItem('formiq_auth_token', access_token);
      if (refresh_token) {
        localStorage.setItem('formiq_refresh_token', refresh_token);
      }

      // Update Redux state
      dispatch(setTokens({
        token: access_token,
        refreshToken: refresh_token || ''
      }));
      dispatch(setUser(user));

      // Navigate based on onboarding status
      if (!user.has_completed_onboarding) {
        navigate('/onboarding');
      } else {
        navigate('/dashboard');
      }
    } catch (error: any) {
      let errorMessage = 'Invalid email or password';

      // apiService.handleApiError converts Axios errors to plain ApiError objects
      // { message, status, code, details } — error.response is never set on these.
      // Read status from error.status first, fall back to error.response?.status for safety.
      const httpStatus: number | undefined = error.status ?? error.response?.status;
      const detail: string | undefined =
        error.response?.data?.detail ?? error.response?.data?.message;

      if (detail) {
        errorMessage = detail;
      } else if (httpStatus === 401) {
        errorMessage = 'Invalid email or password. Please check your credentials and try again.';
      } else if (httpStatus === 422) {
        errorMessage = 'Please check your email and password format.';
      } else if (httpStatus != null && httpStatus >= 500) {
        errorMessage = 'Server error. Please try again later.';
      } else if (!httpStatus) {
        errorMessage = 'Network error. Please check your connection and try again.';
      } else if (error.message && error.message !== 'An unknown error occurred') {
        errorMessage = error.message;
      }

      dispatch(setError(errorMessage));
      logError(errorMessage, { context: 'login' });
      throw new Error(errorMessage);
    } finally {
      dispatch(setLoading(false));
    }
  }, [dispatch, navigate]);

  const register = useCallback(async (email: string, password: string, additionalData?: any) => {
    try {
      dispatch(setLoading(true));
      dispatch(setError(null));
      
      const response = await apiService.register({
        email,
        password,
        ...additionalData
      });

      // For now, don't auto-login after registration
      // Just return success - let the UI handle the redirect to login
      return { success: true, message: 'Account created successfully! Please sign in with your new credentials.' };
      
    } catch (error: any) {
      // apiService.handleApiError transforms all errors into plain ApiError objects
      // { message, status, code, details } — so error.response is never set.
      // Read error.message directly; fall back through legacy Axios shape just in case.
      const errorMessage =
        error.message && error.message !== 'An unknown error occurred'
          ? error.message
          : error.response?.data?.detail
          ?? error.response?.data?.message
          ?? 'Registration failed';

      dispatch(setError(errorMessage));
      logError(errorMessage, { context: 'register' });
      throw new Error(errorMessage);
    } finally {
      dispatch(setLoading(false));
    }
  }, [dispatch]);

  const logout = useCallback(async () => {
    try {
      if (token) {
        await apiService.logout();
      }
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      // Clear auth tokens
      localStorage.removeItem('formiq_auth_token');
      localStorage.removeItem('formiq_refresh_token');

      // Clear user-scoped data so next user starts with a clean slate
      localStorage.removeItem('formiq-squat-sessions-v1');
      localStorage.removeItem('formiq-user-prefs-v1');
      localStorage.removeItem('formiq-training-sessions-v1');
      localStorage.removeItem('formiq-equipment-recents-v1');
      // Clear all formiq-training-v1 keys (sessions, setLogs, equipmentProfiles, nextTargets, gyms, lastEquip:*)
      Object.keys(localStorage)
        .filter((k) => k.startsWith('formiq-training-v1:'))
        .forEach((k) => localStorage.removeItem(k));
      // Clear storageService user-scoped keys
      localStorage.removeItem('formiq_user_profile');
      localStorage.removeItem('formiq_analysis_cache');
      localStorage.removeItem('formiq_settings');

      // Invalidate in-memory progress cache so next user doesn't see stale analytics
      progressService.clearCache();

      // Clear Redux state
      dispatch(logoutAction());

      // Navigate to auth page
      navigate('/auth');
    }
  }, [token, dispatch, navigate]);

  const refreshAccessToken = useCallback(async () => {
    try {
      if (!refreshToken) throw new Error('No refresh token available');
      
      const response = await apiService.refreshToken(refreshToken);
      const { access_token, refresh_token } = response;

      // Update tokens
      localStorage.setItem('formiq_auth_token', access_token);
      if (refresh_token) {
        localStorage.setItem('formiq_refresh_token', refresh_token);
      }

      dispatch(setTokens({
        token: access_token,
        refreshToken: refresh_token || refreshToken
      }));

      return access_token;
    } catch (error) {
      const errorMessage = (error as Error).message || 'Token refresh failed';
      dispatch(setError(errorMessage));
      logError(errorMessage, { context: 'refreshAccessToken' });
      logout();
      throw error;
    }
  }, [refreshToken, dispatch, logout]);

  const updateProfile = useCallback(async (profileData: Partial<User>) => {
    try {
      dispatch(setLoading(true));
      const response = await apiService.updateProfile(profileData);
      const updatedUser = response.data;
      dispatch(setUser(updatedUser));
      return updatedUser;
    } catch (error) {
      const errorMessage = (error as Error).message || 'Profile update failed';
      dispatch(setError(errorMessage));
      logError(errorMessage, { context: 'updateProfile' });
      throw error;
    } finally {
      dispatch(setLoading(false));
    }
  }, [dispatch]);

  const changePassword = useCallback(async (currentPassword: string, newPassword: string) => {
    try {
      dispatch(setLoading(true));
      await apiService.changePassword(currentPassword, newPassword);
    } catch (error) {
      const errorMessage = (error as Error).message || 'Password change failed';
      dispatch(setError(errorMessage));
      logError(errorMessage, { context: 'changePassword' });
      throw error;
    } finally {
      dispatch(setLoading(false));
    }
  }, [dispatch]);

  const requestPasswordReset = useCallback(async (email: string) => {
    try {
      dispatch(setLoading(true));
      await apiService.requestPasswordReset(email);
    } catch (error) {
      const errorMessage = (error as Error).message || 'Password reset request failed';
      dispatch(setError(errorMessage));
      logError(errorMessage, { context: 'requestPasswordReset' });
      throw error;
    } finally {
      dispatch(setLoading(false));
    }
  }, [dispatch]);

  const resetPassword = useCallback(async (token: string, newPassword: string) => {
    try {
      dispatch(setLoading(true));
      await apiService.resetPassword(token, newPassword);
    } catch (error) {
      const errorMessage = (error as Error).message || 'Password reset failed';
      dispatch(setError(errorMessage));
      logError(errorMessage, { context: 'resetPassword' });
      throw error;
    } finally {
      dispatch(setLoading(false));
    }
  }, [dispatch]);

  const requestEmailVerification = useCallback(async (email: string) => {
    try {
      dispatch(setLoading(true));
      await apiService.requestEmailVerification(email);
    } catch (error) {
      const errorMessage = (error as Error).message || 'Email verification request failed';
      dispatch(setError(errorMessage));
      logError(errorMessage, { context: 'requestEmailVerification' });
      throw error;
    } finally {
      dispatch(setLoading(false));
    }
  }, [dispatch]);

  const confirmEmailVerification = useCallback(async (token: string) => {
    try {
      dispatch(setLoading(true));
      await apiService.confirmEmailVerification(token);
    } catch (error) {
      const errorMessage = (error as Error).message || 'Email verification failed';
      dispatch(setError(errorMessage));
      logError(errorMessage, { context: 'confirmEmailVerification' });
      throw error;
    } finally {
      dispatch(setLoading(false));
    }
  }, [dispatch]);

  const socialLogin = useCallback(async (provider: 'google' | 'apple', token: string) => {
    try {
      dispatch(setLoading(true));
      dispatch(setError(null));
      
      let response;
      if (provider === 'google') {
        response = await apiService.googleAuth(token);
      } else {
        response = await apiService.appleAuth(token);
      }

      const { user, access_token, refresh_token } = response.data;

      // Store tokens
      localStorage.setItem('formiq_auth_token', access_token);
      if (refresh_token) {
        localStorage.setItem('formiq_refresh_token', refresh_token);
      }

      // Update Redux state
      dispatch(setTokens({
        token: access_token,
        refreshToken: refresh_token || ''
      }));
      dispatch(setUser(user));

      // Navigate based on onboarding status
      if (!user.has_completed_onboarding) {
        navigate('/onboarding');
      } else {
        navigate('/dashboard');
      }
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || `${provider} authentication failed`;
      dispatch(setError(errorMessage));
      logError(error, { context: `${provider}Login` });
      throw error;
    } finally {
      dispatch(setLoading(false));
    }
  }, [dispatch, navigate]);

  const completeOnboarding = useCallback(async (preferences?: {
    fitness_goal?: string;
    preferred_exercises?: string[];
  }) => {
    try {
      dispatch(setLoading(true));
      dispatch(setError(null));

      const response = await apiService.completeOnboarding(preferences);
      const { user: updatedUser } = response.data;

      // Update user in Redux store
      dispatch(setUser(updatedUser));

      // Navigate to dashboard
      navigate('/dashboard');
    } catch (error: any) {
      const errorMessage = error.message || error.response?.data?.detail || 'Failed to complete onboarding';
      dispatch(setError(errorMessage));
      logError(error, { context: 'completeOnboarding' });
      throw error;
    } finally {
      dispatch(setLoading(false));
    }
  }, [dispatch, navigate]);

  return {
    user,
    token,
    isAuthenticated,
    isLoading,
    error,
    login,
    logout,
    register,
    socialLogin,
    refreshAccessToken,
    updateProfile,
    changePassword,
    requestPasswordReset,
    resetPassword,
    requestEmailVerification,
    confirmEmailVerification,
    completeOnboarding
  };
};