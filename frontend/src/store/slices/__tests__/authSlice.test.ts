import authReducer, {
  setUser,
  setToken,
  setRefreshToken,
  setLoading,
  setError,
  logout,
  AuthState,
  User,
} from '../authSlice';

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
}); 