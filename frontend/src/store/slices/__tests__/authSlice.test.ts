import { configureStore } from '@reduxjs/toolkit';
import authReducer, {
  setUser,
  setToken,
  setRefreshToken,
  setTokens,
  setLoading,
  setError,
  logout,
  AuthState,
  User,
} from '../authSlice';
import { clearMockStorage } from '../../../tests/mocks/storage';
import { RootState } from '../../rootReducer';

// Creating mock selectors to test
const selectUser = (state: RootState) => state.auth.user;
const selectToken = (state: RootState) => state.auth.token;
const selectRefreshToken = (state: RootState) => state.auth.refreshToken;
const selectIsAuthenticated = (state: RootState) => state.auth.isAuthenticated;
const selectIsLoading = (state: RootState) => state.auth.isLoading;
const selectAuthError = (state: RootState) => state.auth.error;

describe('authSlice', () => {
  const mockUser: User = {
    id: 'user_1',
    email: 'test@example.com',
    name: 'Test User',
    role: 'user',
    subscription_tier: 'basic',
    subscription_end_date: '2024-04-01T00:00:00Z',
    created_at: '2024-03-01T00:00:00Z',
    updated_at: '2024-03-01T00:00:00Z',
  };

  const initialState: AuthState = {
    user: null,
    token: null,
    refreshToken: null,
    isAuthenticated: false,
    isLoading: false,
    error: null,
  };

  afterEach(() => {
    clearMockStorage();
  });

  it('should handle initial state', () => {
    expect(authReducer(undefined, { type: 'unknown' })).toEqual(initialState);
  });

  it('should handle setUser', () => {
    const actual = authReducer(initialState, setUser(mockUser));
    expect(actual.user).toEqual(mockUser);
    expect(actual.isAuthenticated).toBe(true);
  });

  it('should handle setUser with null', () => {
    const stateWithUser = {
      ...initialState,
      user: mockUser,
      isAuthenticated: true,
    };
    const actual = authReducer(stateWithUser, setUser(null));
    expect(actual.user).toBeNull();
    expect(actual.isAuthenticated).toBe(false);
  });

  it('should handle setToken', () => {
    const token = 'test-token';
    const actual = authReducer(initialState, setToken(token));
    expect(actual.token).toBe(token);
  });

  it('should handle setRefreshToken', () => {
    const refreshToken = 'test-refresh-token';
    const actual = authReducer(initialState, setRefreshToken(refreshToken));
    expect(actual.refreshToken).toBe(refreshToken);
  });

  it('should handle setTokens', () => {
    const tokens = {
      token: 'test-token',
      refreshToken: 'test-refresh-token'
    };
    const actual = authReducer(initialState, setTokens(tokens));
    expect(actual.token).toBe(tokens.token);
    expect(actual.refreshToken).toBe(tokens.refreshToken);
  });

  it('should handle setLoading', () => {
    const actual = authReducer(initialState, setLoading(true));
    expect(actual.isLoading).toBe(true);
  });

  it('should handle setError', () => {
    const error = 'Test error message';
    const actual = authReducer(initialState, setError(error));
    expect(actual.error).toBe(error);
  });

  it('should handle logout', () => {
    const authenticatedState: AuthState = {
      user: mockUser,
      token: 'test-token',
      refreshToken: 'test-refresh-token',
      isAuthenticated: true,
      isLoading: false,
      error: null,
    };
    const actual = authReducer(authenticatedState, logout());
    expect(actual).toEqual(initialState);
  });

  it('should maintain other state properties when setting user', () => {
    const stateWithToken = {
      ...initialState,
      token: 'test-token',
    };
    const actual = authReducer(stateWithToken, setUser(mockUser));
    expect(actual.token).toBe('test-token');
    expect(actual.user).toEqual(mockUser);
  });

  it('should maintain other state properties when setting error', () => {
    const stateWithUser = {
      ...initialState,
      user: mockUser,
      isAuthenticated: true,
    };
    const actual = authReducer(stateWithUser, setError('Test error'));
    expect(actual.user).toEqual(mockUser);
    expect(actual.isAuthenticated).toBe(true);
    expect(actual.error).toBe('Test error');
  });

  // Enhanced login/logout action testing
  describe('login/logout flow', () => {
    it('should update all necessary state properties during login', () => {
      const loginData = {
        user: mockUser,
        token: 'login-token',
        refreshToken: 'login-refresh-token',
      };

      // First set the token
      let state = authReducer(initialState, setToken(loginData.token));
      // Then set the refresh token
      state = authReducer(state, setRefreshToken(loginData.refreshToken));
      // Finally set the user, which should also update isAuthenticated
      state = authReducer(state, setUser(loginData.user));

      expect(state.token).toBe(loginData.token);
      expect(state.refreshToken).toBe(loginData.refreshToken);
      expect(state.user).toEqual(loginData.user);
      expect(state.isAuthenticated).toBe(true);
      expect(state.error).toBeNull();
    });

    it('should clear auth-related data on logout', () => {
      const authenticatedState: AuthState = {
        user: mockUser,
        token: 'test-token',
        refreshToken: 'test-refresh-token',
        isAuthenticated: true,
        isLoading: true, // Note: The implementation doesn't reset this
        error: 'Previous error', // Note: The implementation does clear this
      };

      const actual = authReducer(authenticatedState, logout());
      
      // Check individual properties to match the actual implementation behavior
      expect(actual.user).toBeNull();
      expect(actual.token).toBeNull();
      expect(actual.refreshToken).toBeNull();
      expect(actual.isAuthenticated).toBe(false);
      expect(actual.error).toBeNull();
      // The implementation doesn't reset loading state, so it should still be true
      expect(actual.isLoading).toBe(true);
    });

    it('should handle login failure by setting error but not user', () => {
      const errorMessage = 'Invalid credentials';
      
      // First simulate a login attempt by setting loading to true
      let state = authReducer(initialState, setLoading(true));
      // Then simulate a failure by setting an error
      state = authReducer(state, setError(errorMessage));
      
      expect(state.error).toBe(errorMessage);
      expect(state.isLoading).toBe(true); // Loading state should be handled separately
      expect(state.user).toBeNull();
      expect(state.isAuthenticated).toBe(false);
    });
  });

  // Error state transitions
  describe('error state transitions', () => {
    it('should maintain error state when setting user', () => {
      const stateWithError: AuthState = {
        ...initialState,
        error: 'Previous login error',
      };

      // The implementation doesn't automatically clear errors
      const actual = authReducer(stateWithError, setUser(mockUser));
      
      // The error should still be present after setting the user
      expect(actual.error).toBe('Previous login error');
      expect(actual.user).toEqual(mockUser);
    });

    it('should preserve error state when only setting tokens', () => {
      const stateWithError: AuthState = {
        ...initialState,
        error: 'Previous error',
      };

      const tokens = {
        token: 'new-token',
        refreshToken: 'new-refresh-token'
      };

      // Setting tokens alone shouldn't clear errors
      const actual = authReducer(stateWithError, setTokens(tokens));
      
      expect(actual.error).toBe('Previous error');
      expect(actual.token).toBe(tokens.token);
      expect(actual.refreshToken).toBe(tokens.refreshToken);
    });

    it('should handle token expiration by setting error without logging out', () => {
      const authenticatedState: AuthState = {
        user: mockUser,
        token: 'test-token',
        refreshToken: 'test-refresh-token',
        isAuthenticated: true,
        isLoading: false,
        error: null,
      };

      // Setting an error like "token expired" shouldn't log the user out
      const tokenError = 'Token expired';
      const actual = authReducer(authenticatedState, setError(tokenError));
      
      expect(actual.error).toBe(tokenError);
      expect(actual.user).toEqual(mockUser); // User should still be present
      expect(actual.isAuthenticated).toBe(true); // Should still be authenticated
    });
  });

  // Selectors testing with Redux store
  describe('auth selectors', () => {
    let store: any;

    beforeEach(() => {
      // Create a Redux store with the auth reducer
      store = configureStore({
        reducer: {
          auth: authReducer,
        },
      });
    });

    it('should select user from state', () => {
      store.dispatch(setUser(mockUser));
      expect(selectUser(store.getState())).toEqual(mockUser);
    });

    it('should select token from state', () => {
      const token = 'selector-test-token';
      store.dispatch(setToken(token));
      expect(selectToken(store.getState())).toBe(token);
    });

    it('should select refresh token from state', () => {
      const refreshToken = 'selector-test-refresh-token';
      store.dispatch(setRefreshToken(refreshToken));
      expect(selectRefreshToken(store.getState())).toBe(refreshToken);
    });

    it('should select isAuthenticated from state', () => {
      expect(selectIsAuthenticated(store.getState())).toBe(false);
      store.dispatch(setUser(mockUser));
      expect(selectIsAuthenticated(store.getState())).toBe(true);
    });

    it('should select isLoading from state', () => {
      expect(selectIsLoading(store.getState())).toBe(false);
      store.dispatch(setLoading(true));
      expect(selectIsLoading(store.getState())).toBe(true);
    });

    it('should select error from state', () => {
      expect(selectAuthError(store.getState())).toBeNull();
      const error = 'Selector error test';
      store.dispatch(setError(error));
      expect(selectAuthError(store.getState())).toBe(error);
    });

    it('should select all auth state after multiple actions', () => {
      // Dispatch a series of actions to test combined state
      store.dispatch(setLoading(true));
      store.dispatch(setToken('combined-token'));
      store.dispatch(setRefreshToken('combined-refresh'));
      store.dispatch(setUser(mockUser));
      store.dispatch(setLoading(false));

      const state = store.getState();
      expect(selectUser(state)).toEqual(mockUser);
      expect(selectToken(state)).toBe('combined-token');
      expect(selectRefreshToken(state)).toBe('combined-refresh');
      expect(selectIsAuthenticated(state)).toBe(true);
      expect(selectIsLoading(state)).toBe(false);
      expect(selectAuthError(state)).toBeNull();
    });

    it('should select auth state reset after logout', () => {
      // First set up an authenticated state
      store.dispatch(setUser(mockUser));
      store.dispatch(setToken('logout-test-token'));
      store.dispatch(setRefreshToken('logout-test-refresh'));
      
      // Then logout
      store.dispatch(logout());
      
      const state = store.getState();
      expect(selectUser(state)).toBeNull();
      expect(selectToken(state)).toBeNull();
      expect(selectRefreshToken(state)).toBeNull();
      expect(selectIsAuthenticated(state)).toBe(false);
      expect(selectIsLoading(state)).toBe(false); // This will be false because we created a new store
      expect(selectAuthError(state)).toBeNull();
    });
  });
}); 