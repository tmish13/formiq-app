import formCheckReducer, {
  addFormCheck,
  setCurrentCheck,
  setLoading,
  setError,
  FormCheckState,
  FormCheck,
  FormCheckFeedback,
} from '../formCheckSlice';

describe('formCheckSlice', () => {
  const mockFeedback: FormCheckFeedback[] = [
    {
      type: 'success',
      message: 'Good form overall',
      timestamp: '2024-03-20T10:00:00Z',
    },
    {
      type: 'warning',
      message: 'Slight knee valgus',
      timestamp: '2024-03-20T10:00:00Z',
    },
  ];

  const mockFormChecks: FormCheck[] = [
    {
      id: '1',
      userId: 'user1',
      exerciseName: 'SQUAT',
      videoUrl: 'https://example.com/video1.mp4',
      timestamp: '2024-03-20T10:00:00Z',
      feedback: mockFeedback,
      status: 'completed',
    },
    {
      id: '2',
      userId: 'user1',
      exerciseName: 'DEADLIFT',
      videoUrl: 'https://example.com/video2.mp4',
      timestamp: '2024-03-20T11:00:00Z',
      feedback: [],
      status: 'completed',
    },
  ];

  const initialState: FormCheckState = {
    checks: [],
    isLoading: false,
    error: null,
    currentCheck: null,
    selectedCheck: null,
  };

  it('should handle initial state', () => {
    expect(formCheckReducer(undefined, { type: 'unknown' })).toEqual(initialState);
  });

  it('should handle addFormCheck', () => {
    const actual = formCheckReducer(initialState, addFormCheck(mockFormChecks[0]));
    expect(actual.checks).toEqual([mockFormChecks[0]]);
  });

  it('should handle setCurrentCheck', () => {
    const currentFormCheck = mockFormChecks[0];
    const actual = formCheckReducer(initialState, setCurrentCheck(currentFormCheck));
    expect(actual.currentCheck).toEqual(currentFormCheck);
  });

  it('should handle setLoading', () => {
    const actual = formCheckReducer(initialState, setLoading(true));
    expect(actual.isLoading).toBe(true);
  });

  it('should handle setError', () => {
    const error = 'Test error message';
    const actual = formCheckReducer(initialState, setError(error));
    expect(actual.error).toBe(error);
  });

  it('should clear error when adding form check', () => {
    const stateWithError = {
      ...initialState,
      error: 'Previous error',
    };
    const actual = formCheckReducer(stateWithError, addFormCheck(mockFormChecks[0]));
    expect(actual.error).toBeNull();
  });

  it('should clear error when setting current form check', () => {
    const stateWithError = {
      ...initialState,
      error: 'Previous error',
    };
    const actual = formCheckReducer(stateWithError, setCurrentCheck(mockFormChecks[0]));
    expect(actual.error).toBeNull();
  });

  it('should maintain existing form checks when setting current form check', () => {
    const stateWithFormChecks = {
      ...initialState,
      checks: mockFormChecks,
    };
    const actual = formCheckReducer(stateWithFormChecks, setCurrentCheck(mockFormChecks[0]));
    expect(actual.checks).toEqual(mockFormChecks);
  });
}); 