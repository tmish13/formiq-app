import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAppSelector, useAppDispatch } from '../store/hooks';
import { authService } from '../services/auth';
import { setUser, setToken, setError, setLoading, logout as logoutAction } from '../store/slices/authSlice';
import type { User } from '../types';

export const useAuth = () => {
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  const { user, isAuthenticated, isLoading, error, token } = useAppSelector(
    (state) => state.auth
  );

  useEffect(() => {
    const checkAuth = async () => {
      if (!token) return;
      
      try {
        dispatch(setLoading(true));
        const currentUser = await authService.getCurrentUser();
        dispatch(setUser(currentUser));
      } catch (error: any) {
        dispatch(setError(error.message));
        dispatch(logoutAction());
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