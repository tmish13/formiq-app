import React, { createContext, useContext, useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api, { endpoints } from '../config/api';
import { User } from '../types';

interface AuthContextType {
  user: User | null;
  loading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, name: string) => Promise<void>;
  logout: () => void;
  updateSubscription: (tier: string) => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      fetchUser();
    } else {
      setLoading(false);
    }
  }, []);

  const fetchUser = async () => {
    try {
      const response = await api.get(endpoints.user.profile);
      setUser(response.data);
    } catch (err) {
      localStorage.removeItem('token');
      setError('Session expired. Please login again.');
    } finally {
      setLoading(false);
    }
  };

  const login = async (email: string, password: string) => {
    try {
      setError(null);
      const response = await api.post(endpoints.auth.login, { email, password });
      localStorage.setItem('token', response.data.access_token);
      await fetchUser();
      navigate('/dashboard');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to login');
      throw err;
    }
  };

  const register = async (email: string, password: string, name: string) => {
    try {
      setError(null);
      await api.post(endpoints.auth.register, { email, password, name });
      await login(email, password);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to register');
      throw err;
    }
  };

  const logout = () => {
    // Attempt to call logout API endpoint, but don't wait for it
    try {
      api.post(endpoints.auth.logout).catch(console.error);
    } catch (e) {
      console.error('Error during logout:', e);
    }
    
    localStorage.removeItem('token');
    setUser(null);
    navigate('/login');
  };

  const updateSubscription = async (tier: string) => {
    try {
      setError(null);
      const response = await api.post(endpoints.user.subscription, { tier });
      setUser(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to update subscription');
      throw err;
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        error,
        login,
        register,
        logout,
        updateSubscription,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export default AuthContext; 