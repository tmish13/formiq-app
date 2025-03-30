import { renderHook, act } from '@testing-library/react-hooks';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import { useFormCheck } from '../useFormCheck';
import formCheckReducer from '../../store/slices/formCheckSlice';
import { FormCheck, ExerciseType } from '../../types';

// Mock the form check service
jest.mock('../../services/formCheckService', () => ({
  formCheckService: {
    getUserFormChecks: jest.fn(),
    getFormCheck: jest.fn(),
    submitFormCheck: jest.fn(),
    deleteFormCheck: jest.fn(),
    completeAnalysis: jest.fn(),
    getFormChecksByExercise: jest.fn(),
  },
}));

const mockFormCheck: FormCheck = {
  id: '1',
  userId: 'user1',
  exerciseType: 'squat' as ExerciseType,
  videoUrl: 'https://example.com/video.mp4',
  status: 'pending',
  createdAt: new Date().toISOString(),
  updatedAt: new Date().toISOString(),
};

const initialState = {
  formChecks: [],
  currentFormCheck: null,
  isLoading: false,
  error: null,
};

const createTestStore = (preloadedState = initialState) => {
  return configureStore({
    reducer: {
      formCheck: formCheckReducer,
    },
    preloadedState: {
      formCheck: preloadedState,
    },
  });
};

describe('useFormCheck', () => {
  let store: ReturnType<typeof createTestStore>;

  beforeEach(() => {
    store = createTestStore();
    jest.clearAllMocks();
  });

  const TestWrapper = ({ children }: { children: React.ReactNode }) => (
    <Provider store={store}>{children}</Provider>
  );

  it('should fetch form checks successfully', async () => {
    const mockFormChecks = [mockFormCheck];
    (require('../../services/formCheckService').formCheckService.getUserFormChecks as jest.Mock).mockResolvedValue(mockFormChecks);

    const { result } = renderHook(() => useFormCheck(), { wrapper: TestWrapper });

    await act(async () => {
      await result.current.fetchFormChecks();
    });

    expect(result.current.formChecks).toEqual(mockFormChecks);
    expect(result.current.isLoading).toBe(false);
    expect(result.current.error).toBe(null);
  });

  it('should handle error when fetching form checks', async () => {
    const error = new Error('Failed to fetch form checks');
    (require('../../services/formCheckService').formCheckService.getUserFormChecks as jest.Mock).mockRejectedValue(error);

    const { result } = renderHook(() => useFormCheck(), { wrapper: TestWrapper });

    await act(async () => {
      await result.current.fetchFormChecks();
    });

    expect(result.current.error).toBe(error.message);
    expect(result.current.isLoading).toBe(false);
  });

  it('should submit form check successfully', async () => {
    const video = new File([''], 'test.mp4', { type: 'video/mp4' });
    (require('../../services/formCheckService').formCheckService.submitFormCheck as jest.Mock).mockResolvedValue(mockFormCheck);

    const { result } = renderHook(() => useFormCheck(), { wrapper: TestWrapper });

    await act(async () => {
      await result.current.submitFormCheck(video, 'squat');
    });

    expect(result.current.formChecks).toContainEqual(mockFormCheck);
    expect(result.current.isLoading).toBe(false);
    expect(result.current.error).toBe(null);
  });

  it('should delete form check successfully', async () => {
    (require('../../services/formCheckService').formCheckService.deleteFormCheck as jest.Mock).mockResolvedValue(undefined);

    const { result } = renderHook(() => useFormCheck(), { wrapper: TestWrapper });

    await act(async () => {
      await result.current.deleteFormCheck('1');
    });

    expect(result.current.formChecks).not.toContainEqual(mockFormCheck);
    expect(result.current.isLoading).toBe(false);
    expect(result.current.error).toBe(null);
  });

  it('should complete analysis successfully', async () => {
    const updatedFormCheck = { ...mockFormCheck, status: 'completed', score: 85 };
    (require('../../services/formCheckService').formCheckService.completeAnalysis as jest.Mock).mockResolvedValue(updatedFormCheck);

    const { result } = renderHook(() => useFormCheck(), { wrapper: TestWrapper });

    await act(async () => {
      await result.current.completeAnalysis('1', 'Good form overall', 85);
    });

    expect(result.current.formChecks).toContainEqual(updatedFormCheck);
    expect(result.current.isLoading).toBe(false);
    expect(result.current.error).toBe(null);
  });

  it('should fetch form checks by exercise successfully', async () => {
    const mockFormChecks = [mockFormCheck];
    (require('../../services/formCheckService').formCheckService.getFormChecksByExercise as jest.Mock).mockResolvedValue(mockFormChecks);

    const { result } = renderHook(() => useFormCheck(), { wrapper: TestWrapper });

    const formChecks = await act(async () => {
      return await result.current.fetchFormChecksByExercise('squat');
    });

    expect(formChecks).toEqual(mockFormChecks);
    expect(result.current.isLoading).toBe(false);
    expect(result.current.error).toBe(null);
  });
}); 