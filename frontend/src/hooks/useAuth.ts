import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAppSelector, useAppDispatch } from '../store/hooks';
import { authService } from '../services/auth';
import { setUser, setError } from '../store/slices/authSlice';

export const useAuth = () => {
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  const { user, isAuthenticated, isLoading, error } = useAppSelector(
    (state) => state.auth
  );

  useEffect(() => {
    const checkAuth = async () => {
      try {
        const currentUser = await authService.getCurrentUser();
        dispatch(setUser(currentUser));
      } catch (error: any) {
        dispatch(setError(error.message));
        navigate('/login');
      }
    };

    if (isAuthenticated && !user) {
      checkAuth();
    }
  }, [isAuthenticated, user, dispatch, navigate]);

  const login = async (email: string, password: string) => {
    try {
      await authService.login({ email, password });
      navigate('/dashboard');
    } catch (error: any) {
      dispatch(setError(error.message));
      throw error;
    }
  };

  const logout = async () => {
    try {
      await authService.logout();
      navigate('/login');
    } catch (error: any) {
      dispatch(setError(error.message));
      throw error;
    }
  };

  const register = async (email: string, password: string, name: string) => {
    try {
      await authService.register({ email, password, name });
      navigate('/dashboard');
    } catch (error: any) {
      dispatch(setError(error.message));
      throw error;
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
  };
}; 