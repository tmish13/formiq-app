import React, { createContext, useContext, useEffect, useReducer } from 'react';
import { AuthContextType, AuthState, LoginCredentials, RegisterCredentials, User, AuthTokens } from '../types/auth';
import { apiService } from '../services/apiService';
import { sessionService } from '../services/sessionService';

const initialState: AuthState = {
  user: null,
  tokens: null,
  isAuthenticated: false,
  isLoading: true,
  error: null,
};

type AuthAction =
  | { type: 'SET_LOADING'; payload: boolean }
  | { type: 'SET_ERROR'; payload: string | null }
  | { type: 'SET_USER'; payload: User | null }
  | { type: 'SET_TOKENS'; payload: AuthTokens | null }
  | { type: 'LOGOUT' };

const authReducer = (state: AuthState, action: AuthAction): AuthState => {
  switch (action.type) {
    case 'SET_LOADING':
      return { ...state, isLoading: action.payload, error: null };
    case 'SET_ERROR':
      return { ...state, error: action.payload, isLoading: false };
    case 'SET_USER':
      return {
        ...state,
        user: action.payload,
        isAuthenticated: !!action.payload,
        isLoading: false,
      };
    case 'SET_TOKENS':
      return {
        ...state,
        tokens: action.payload,
        isAuthenticated: !!action.payload,
        isLoading: false,
      };
    case 'LOGOUT':
      return {
        ...initialState,
        isLoading: false,
      };
    default:
      return state;
  }
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [state, dispatch] = useReducer(authReducer, initialState);

  // Initialize auth state and session tracking
  useEffect(() => {
    const initializeAuth = async () => {
      try {
        dispatch({ type: 'SET_LOADING', payload: true });
        
        // Validate existing session
        if (!sessionService.validateSession()) {
          dispatch({ type: 'SET_LOADING', payload: false });
          return;
        }

        const tokens = sessionService.getTokens();
        if (tokens) {
          dispatch({ type: 'SET_TOKENS', payload: tokens });
          
          // Validate token and get user data
          const userData = await apiService.auth.validate();
          dispatch({ type: 'SET_USER', payload: userData.data });
        }
      } catch (error) {
        console.error('Auth initialization failed:', error);
        sessionService.clearSession();
        dispatch({ type: 'LOGOUT' });
      }
    };

    initializeAuth();
    sessionService.initActivityTracking();
  }, []);

  // Token refresh interval
  useEffect(() => {
    if (!state.tokens) return;

    const refreshInterval = setInterval(async () => {
      try {
        await refreshTokens();
      } catch (error) {
        console.error('Token refresh failed:', error);
      }
    }, (state.tokens.expiresIn - 300) * 1000); // Refresh 5 minutes before expiry

    return () => clearInterval(refreshInterval);
  }, [state.tokens]);

  const login = async (credentials: LoginCredentials) => {
    try {
      dispatch({ type: 'SET_LOADING', payload: true });
      const response = await apiService.auth.login(credentials.email, credentials.password);
      const { user, tokens } = response.data;
      
      sessionService.setTokens(tokens);
      dispatch({ type: 'SET_TOKENS', payload: tokens });
      dispatch({ type: 'SET_USER', payload: user });
      
      // Store additional session data if needed
      sessionService.setSessionData({
        lastLogin: new Date().toISOString(),
        userPreferences: user.preferences,
      });
    } catch (error: any) {
      dispatch({ type: 'SET_ERROR', payload: error.message || 'Login failed' });
      throw error;
    }
  };

  const register = async (credentials: RegisterCredentials) => {
    try {
      dispatch({ type: 'SET_LOADING', payload: true });
      const response = await apiService.auth.register(credentials);
      const { user, tokens } = response.data;
      
      sessionService.setTokens(tokens);
      dispatch({ type: 'SET_TOKENS', payload: tokens });
      dispatch({ type: 'SET_USER', payload: user });
    } catch (error: any) {
      dispatch({ type: 'SET_ERROR', payload: error.message || 'Registration failed' });
      throw error;
    }
  };

  const logout = async () => {
    try {
      await apiService.auth.logout();
    } finally {
      sessionService.clearSession();
      dispatch({ type: 'LOGOUT' });
    }
  };

  const refreshTokens = async () => {
    try {
      if (!state.tokens?.refreshToken) throw new Error('No refresh token available');
      
      const response = await apiService.auth.refreshToken(state.tokens.refreshToken);
      const { tokens } = response.data;
      
      sessionService.setTokens(tokens);
      dispatch({ type: 'SET_TOKENS', payload: tokens });
    } catch (error) {
      sessionService.clearSession();
      dispatch({ type: 'LOGOUT' });
      throw error;
    }
  };

  const updateUser = async (userData: Partial<User>) => {
    try {
      dispatch({ type: 'SET_LOADING', payload: true });
      const response = await apiService.profile.update(userData);
      dispatch({ type: 'SET_USER', payload: response.data });
      
      // Update session data with new user info
      const sessionData = sessionService.getSessionData() || {};
      sessionService.setSessionData({
        ...sessionData,
        userPreferences: response.data.preferences,
      });
    } catch (error: any) {
      dispatch({ type: 'SET_ERROR', payload: error.message || 'Profile update failed' });
      throw error;
    }
  };

  const value: AuthContextType = {
    ...state,
    login,
    register,
    logout,
    refreshTokens,
    updateUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export default AuthContext; 