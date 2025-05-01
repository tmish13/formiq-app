import { useState } from 'react';

interface User {
  id: string;
  email: string;
  name: string;
  role: string;
}

// Mock implementation of useAuth
const useAuth = () => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);

  const login = jest.fn(async (email: string, password: string) => {
    setIsLoading(true);
    
    try {
      if (!email || !password) {
        throw new Error('Email and password are required');
      }

      // Simulate successful login
      setUser({ email, id: '123', name: 'Test User', role: 'user' });
      setIsAuthenticated(true);
      setError(null);
      return { success: true };
    } catch (err: any) {
      setError(err.message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  });

  const register = jest.fn(async (data: { email: string; password: string; username: string }) => {
    setIsLoading(true);
    
    try {
      if (!data.email || !data.password || !data.username) {
        throw new Error('Missing required fields');
      }

      // Simulate successful registration
      setUser({ email: data.email, id: '123', name: data.username, role: 'user' });
      setIsAuthenticated(true);
      setError(null);
      return { success: true };
    } catch (err: any) {
      setError(err.message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  });

  const logout = jest.fn(() => {
    setUser(null);
    setIsAuthenticated(false);
  });

  return {
    isAuthenticated,
    isLoading,
    user,
    error,
    login,
    register,
    logout
  };
};

export default useAuth; 