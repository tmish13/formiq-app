import React from 'react';
import { renderHook, act } from '@testing-library/react-hooks';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import { useFormCheck } from '../useFormCheck';
import formCheckReducer, { setFormChecks } from '../../store/slices/formCheckSlice';
import { FormCheck, ExerciseType } from '../../types';

// Mock the api service to prevent any real network requests
jest.mock('../../services/api', () => ({
  apiService: {
    get: jest.fn(),
    post: jest.fn(),
    put: jest.fn(),
    delete: jest.fn(),
    patch: jest.fn(),
  }
}));

// Import the mocked module
import { apiService } from '../../services/api';

// Create mock form check data
const mockFormCheck: FormCheck = {
  id: 1,
  user_id: 1,
  exercise_type: 'squat',
  video_url: 'https://example.com/video.mp4',
  status: 'pending',
  created_at: '2025-04-15T19:10:15.715Z',
  updated_at: '2025-04-15T19:10:15.716Z',
};

const mockFormChecks = [mockFormCheck];

interface FormCheckState {
  formChecks: FormCheck[];
  currentFormCheck: FormCheck | null;
  isLoading: boolean;
  error: string | null;
}

const initialState = {
  formCheck: {
    formChecks: [],
    currentFormCheck: null,
    isLoading: false,
    error: null,
  } as FormCheckState,
};

// Helper to create store with optional preloaded state
const createTestStore = (preloadedState = initialState) => {
  return configureStore({
    reducer: {
      formCheck: formCheckReducer,
    },
    preloadedState: preloadedState,
  });
};

describe('useFormCheck', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    
    // Set up default mock implementations for apiService
    (apiService.get as jest.Mock).mockImplementation((url) => {
      if (url === '/api/form-checks') {
        return Promise.resolve({ data: mockFormChecks });
      } else if (url.includes('/api/form-checks/history')) {
        return Promise.resolve({ data: [mockFormCheck, { ...mockFormCheck, id: 2 }] });
      } else if (url.includes('/api/form-checks/')) {
        return Promise.resolve({ data: mockFormCheck });
      }
      return Promise.resolve({ data: {} });
    });
    
    (apiService.post as jest.Mock).mockImplementation((url) => {
      if (url.includes('/api/form-checks/upload')) {
        return Promise.resolve({ data: mockFormCheck });
      } else if (url.includes('/api/form-checks') && url.includes('/analyze')) {
        return Promise.resolve({ 
          data: { ...mockFormCheck, status: 'completed' } 
        });
      }
      return Promise.resolve({ data: mockFormCheck });
    });
    
    (apiService.delete as jest.Mock).mockResolvedValue({ data: {} });
  });

  it('should initialize with empty formChecks array', () => {
    const store = createTestStore();
    const wrapper = ({ children }: { children: React.ReactNode }) => <Provider store={store}>{children}</Provider>;
    const { result } = renderHook(() => useFormCheck(), { wrapper });

    expect(result.current.formChecks).toEqual([]);
    expect(result.current.isLoading).toBe(false);
    expect(result.current.error).toBe(null);
  });

  it('should initialize with preloaded formChecks', () => {
    const preloadedState = {
      ...initialState,
      formCheck: {
        ...initialState.formCheck,
        formChecks: mockFormChecks,
      } as FormCheckState,
    };
    const store = createTestStore(preloadedState);
    const wrapper = ({ children }: { children: React.ReactNode }) => <Provider store={store}>{children}</Provider>;
    const { result } = renderHook(() => useFormCheck(), { wrapper });

    expect(result.current.formChecks).toEqual(mockFormChecks);
  });

  it('should fetch form checks successfully', async () => {
    const store = createTestStore();
    const wrapper = ({ children }: { children: React.ReactNode }) => <Provider store={store}>{children}</Provider>;
    const { result, waitForNextUpdate } = renderHook(() => useFormCheck(), { wrapper });
    
    await act(async () => {
      result.current.fetchFormChecks();
      await waitForNextUpdate();
    });
    
    expect(apiService.get).toHaveBeenCalledWith('/api/form-checks');
    expect(result.current.formChecks).toEqual(mockFormChecks);
    expect(result.current.isLoading).toBe(false);
    expect(result.current.error).toBe(null);
  });
  
  it('should handle error when fetching form checks', async () => {
    const errorMessage = 'Failed to fetch form checks';
    (apiService.get as jest.Mock).mockRejectedValueOnce(new Error(errorMessage));
    
    const store = createTestStore();
    const wrapper = ({ children }: { children: React.ReactNode }) => <Provider store={store}>{children}</Provider>;
    const { result, waitForNextUpdate } = renderHook(() => useFormCheck(), { wrapper });
    
    await act(async () => {
      result.current.fetchFormChecks();
      await waitForNextUpdate();
    });
    
    expect(apiService.get).toHaveBeenCalledWith('/api/form-checks');
    expect(result.current.error).toBe(errorMessage);
    expect(result.current.isLoading).toBe(false);
  });
  
  it('should fetch a single form check successfully', async () => {
    const store = createTestStore();
    const wrapper = ({ children }: { children: React.ReactNode }) => <Provider store={store}>{children}</Provider>;
    const { result, waitForNextUpdate } = renderHook(() => useFormCheck(), { wrapper });
    
    await act(async () => {
      result.current.fetchFormCheck('1');
      await waitForNextUpdate();
    });
    
    expect(apiService.get).toHaveBeenCalledWith('/api/form-checks/1');
    expect(result.current.currentFormCheck).toEqual(mockFormCheck);
  });
  
  it('should submit form check successfully', async () => {
    // Instead of waiting for next update, we'll use a resolved promise
    (apiService.post as jest.Mock).mockResolvedValue({ data: mockFormCheck });
    
    const store = createTestStore();
    const wrapper = ({ children }: { children: React.ReactNode }) => <Provider store={store}>{children}</Provider>;
    const { result } = renderHook(() => useFormCheck(), { wrapper });
    
    const mockFile = new File([''], 'test-video.mp4', { type: 'video/mp4' });
    const mockExerciseType: ExerciseType = 'squat';
    const mockOnProgress = jest.fn();
    
    let returnedData: any;
    
    await act(async () => {
      returnedData = await result.current.submitFormCheck(mockFile, mockExerciseType, mockOnProgress);
    });
    
    expect(apiService.post).toHaveBeenCalled();
    expect(returnedData).toEqual(mockFormCheck);
    expect(result.current.currentFormCheck).toEqual(mockFormCheck);
  });
  
  it('should delete form check successfully', async () => {
    const preloadedState = {
      ...initialState,
      formCheck: {
        ...initialState.formCheck,
        formChecks: mockFormChecks,
      } as FormCheckState,
    };
    
    const store = createTestStore(preloadedState);
    const wrapper = ({ children }: { children: React.ReactNode }) => <Provider store={store}>{children}</Provider>;
    const { result } = renderHook(() => useFormCheck(), { wrapper });
    
    await act(async () => {
      await result.current.deleteFormCheckById(1);
    });
    
    expect(apiService.delete).toHaveBeenCalledWith('/api/form-checks/1');
  });
  
  it('should analyze form check successfully', async () => {
    const analyzedFormCheck = { ...mockFormCheck, status: 'completed' };
    // Promise will resolve immediately
    (apiService.post as jest.Mock).mockResolvedValue({ data: analyzedFormCheck });
    
    const store = createTestStore();
    const wrapper = ({ children }: { children: React.ReactNode }) => <Provider store={store}>{children}</Provider>;
    const { result } = renderHook(() => useFormCheck(), { wrapper });
    
    let returnedData: any;
    
    await act(async () => {
      returnedData = await result.current.analyzeFormCheck('1');
    });
    
    expect(apiService.post).toHaveBeenCalledWith('/api/form-checks/1/analyze');
    expect(returnedData).toEqual(analyzedFormCheck);
    expect(result.current.currentFormCheck).toEqual(analyzedFormCheck);
  });
  
  it('should fetch form history successfully', async () => {
    const historyFormChecks = [mockFormCheck, { ...mockFormCheck, id: 2 }];
    
    const store = createTestStore();
    const wrapper = ({ children }: { children: React.ReactNode }) => <Provider store={store}>{children}</Provider>;
    const { result, waitForNextUpdate } = renderHook(() => useFormCheck(), { wrapper });
    
    await act(async () => {
      result.current.fetchHistory();
      await waitForNextUpdate();
    });
    
    expect(apiService.get).toHaveBeenCalledWith('/api/form-checks/history');
    expect(result.current.formChecks).toEqual(historyFormChecks);
  });
}); 