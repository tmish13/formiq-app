import React, { createContext, useContext, useState, useEffect } from 'react';
import { apiService } from '../services/apiService';
import { sessionService } from '../services/sessionService';
import { ApiResponse } from '../types/api';
import { User } from '../types/user';

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, username: string) => Promise<void>;
  logout: () => void;
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
        const sessionData = sessionService.getSessionData<{ user: User }>();
        if (sessionData?.user) {
          setUser(sessionData.user);
        }
      } catch (err) {
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
    sessionService.clearSession();
    setUser(null);
  };

  const value = {
    user,
    isAuthenticated: !!user,
    isLoading,
    error,
    login,
    register,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}; 