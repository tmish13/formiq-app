import uiReducer, {
  setLoading,
  setError,
  setOffline,
  clearError,
} from '../uiSlice';

describe('uiSlice', () => {
  const initialState = {
    isLoading: false,
    error: null,
    isOffline: false
  };

  it('should handle initial state', () => {
    expect(uiReducer(undefined, { type: 'unknown' })).toEqual(initialState);
  });

  describe('loading state', () => {
    it('should handle setLoading to true', () => {
      const actual = uiReducer(initialState, setLoading(true));
      expect(actual.isLoading).toBe(true);
    });

    it('should handle setLoading to false', () => {
      const loadingState = {
        ...initialState,
        isLoading: true
      };
      const actual = uiReducer(loadingState, setLoading(false));
      expect(actual.isLoading).toBe(false);
    });
  });

  describe('error handling', () => {
    it('should handle setError', () => {
      const errorMessage = 'Test error message';
      const actual = uiReducer(initialState, setError(errorMessage));
      expect(actual.error).toBe(errorMessage);
    });

    it('should handle clearError', () => {
      const stateWithError = {
        ...initialState,
        error: 'Some error message'
      };
      const actual = uiReducer(stateWithError, clearError());
      expect(actual.error).toBeNull();
    });

    it('should handle setError with null', () => {
      const stateWithError = {
        ...initialState,
        error: 'Some error message'
      };
      const actual = uiReducer(stateWithError, setError(null));
      expect(actual.error).toBeNull();
    });
  });

  describe('offline status', () => {
    it('should handle setOffline to true', () => {
      const actual = uiReducer(initialState, setOffline(true));
      expect(actual.isOffline).toBe(true);
    });

    it('should handle setOffline to false', () => {
      const offlineState = {
        ...initialState,
        isOffline: true
      };
      const actual = uiReducer(offlineState, setOffline(false));
      expect(actual.isOffline).toBe(false);
    });

    it('should maintain other state when setting offline status', () => {
      const stateWithError = {
        ...initialState,
        error: 'Some error message'
      };
      const actual = uiReducer(stateWithError, setOffline(true));
      expect(actual.error).toBe('Some error message');
      expect(actual.isOffline).toBe(true);
    });
  });

  describe('state combinations', () => {
    it('should handle multiple actions in sequence', () => {
      // Start with initial state
      let state = uiReducer(undefined, { type: 'unknown' });

      // Set loading
      state = uiReducer(state, setLoading(true));
      expect(state.isLoading).toBe(true);

      // Set error
      state = uiReducer(state, setError('An error occurred'));
      expect(state.error).toBe('An error occurred');
      expect(state.isLoading).toBe(true); // Loading state should not be affected

      // Set offline
      state = uiReducer(state, setOffline(true));
      expect(state.isOffline).toBe(true);
      expect(state.error).toBe('An error occurred'); // Error should be preserved
      expect(state.isLoading).toBe(true); // Loading state should not be affected

      // Clear error
      state = uiReducer(state, clearError());
      expect(state.error).toBeNull();
      expect(state.isLoading).toBe(true); // Loading state should not be affected
      expect(state.isOffline).toBe(true); // Offline state should not be affected
    });
  });

  describe('async action handling', () => {
    it('should handle thunk pending actions', () => {
      const pendingAction = { type: 'ui/someAsyncAction/pending' };
      const actual = uiReducer(initialState, pendingAction);
      
      // This will only work if the slice is configured to handle async thunks
      // If not configured, this test will just confirm the state doesn't change
      expect(actual).toEqual(initialState);
    });

    it('should handle thunk rejected actions', () => {
      const rejectedAction = { 
        type: 'ui/someAsyncAction/rejected',
        error: { message: 'Network error' }
      };
      const actual = uiReducer(initialState, rejectedAction);
      
      // This will only work if the slice is configured to handle async thunks
      // If not configured, this test will just confirm the state doesn't change
      expect(actual).toEqual(initialState);
    });
  });
}); 