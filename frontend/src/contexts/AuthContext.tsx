import React, { createContext, useContext, useState, useEffect } from 'react';
import { apiService } from '../services/apiService';
import { sessionService } from '../services/sessionService';
import { ApiResponse } from '../types/api';
import { User } from '../types/user';
import { AuthTokens } from '../types/auth';

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, username: string) => Promise<void>;
  logout: () => void;
  refreshToken: () => Promise<void>;
  updateProfile: (profileData: Partial<User>) => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const initAuth = async () => {
      try {
        setIsLoading(true);
        // Check if we have a valid session
        if (sessionService.validateSession()) {
          const sessionData = sessionService.getSessionData<{ user: User }>();
          if (sessionData?.user) {
            // If we have a user in the session, validate with the API
            try {
              const response = await apiService.auth.validate();
              if (response.data) {
                setUser(response.data);
              }
            } catch (error) {
              console.error('Error validating session:', error);
              sessionService.clearSession();
            }
          }
        } else {
          // No valid session, ensure user is logged out
          setUser(null);
        }
        
        // Initialize activity tracking
        sessionService.initActivityTracking();
      } catch (err) {
        console.error('Failed to initialize auth state:', err);
        setError('Failed to initialize auth state');
      } finally {
        setIsLoading(false);
      }
    };

    initAuth();
  }, []);

  const login = async (email: string, password: string) => {
    try {
      setError(null);
      const response = await apiService.auth.login({ email, password });
      if (response.data) {
        const { user, tokens } = response.data;
        sessionService.setTokens(tokens);
        sessionService.setSessionData({ user });
        setUser(user);
      }
    } catch (err) {
      setError('Login failed');
      throw err;
    }
  };

  const register = async (email: string, password: string, username: string) => {
    try {
      setError(null);
      const response = await apiService.auth.register({ email, password, username });
      if (response.data) {
        const { user, tokens } = response.data;
        sessionService.setTokens(tokens);
        sessionService.setSessionData({ user });
        setUser(user);
      }
    } catch (err) {
      setError('Registration failed');
      throw err;
    }
  };

  const logout = () => {
    try {
      apiService.auth.logout();
    } catch (error) {
      console.error('Error during logout:', error);
    } finally {
      sessionService.clearSession();
      setUser(null);
    }
  };

  const refreshToken = async () => {
    try {
      setError(null);
      const tokens = sessionService.getTokens();
      if (!tokens) {
        throw new Error('No tokens found');
      }
      
      const response = await apiService.auth.refreshToken(tokens.refreshToken);
      if (response.data) {
        sessionService.setTokens(response.data.tokens);
      }
    } catch (err) {
      setError('Token refresh failed');
      throw err;
    }
  };

  const updateProfile = async (profileData: Partial<User>) => {
    try {
      setError(null);
      const response = await apiService.profile.update(profileData);
      if (response.data) {
        // Update the user in state and session
        setUser(response.data);
        sessionService.updateSessionData({ user: response.data });
      }
    } catch (err) {
      setError('Profile update failed');
      throw err;
    }
  };

  const value = {
    user,
    isAuthenticated: !!user,
    isLoading,
    error,
    login,
    register,
    logout,
    refreshToken,
    updateProfile
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}; 