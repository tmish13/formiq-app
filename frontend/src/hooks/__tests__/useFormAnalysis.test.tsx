import React from 'react';
import { renderHook, act } from '@testing-library/react';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import { useFormAnalysis } from '../useFormAnalysis';
import formAnalysisReducer, { FormAnalysisState } from '../../store/slices/formAnalysisSlice';
import { handleApiError, AppError, ErrorCode } from '../../utils/errorHandling';

// Mock the error handling utility
jest.mock('../../utils/errorHandling', () => ({
  handleApiError: jest.fn((error) => error instanceof Error ? error.message : 'Unknown error'),
  AppError: jest.fn().mockImplementation((message, code, status) => ({
    message,
    code,
    status,
    name: 'AppError'
  })),
  ErrorCode: {
    UNKNOWN_ERROR: 'UNKNOWN_ERROR'
  }
}));

// Create a test store with the form analysis reducer
const createTestStore = (preloadedState: Partial<FormAnalysisState> = {}) => {
  return configureStore({
    reducer: {
      formAnalysis: formAnalysisReducer
    },
    preloadedState: {
      formAnalysis: {
        isAnalyzing: false,
        progress: 0,
        error: null,
        videoFile: null,
        analysisResults: null,
        ...preloadedState
      }
    }
  });
};

describe('useFormAnalysis', () => {
  it('should initialize with default state', () => {
    const store = createTestStore();
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <Provider store={store}>{children}</Provider>
    );
    const { result } = renderHook(() => useFormAnalysis(), { wrapper });

    expect(result.current.isAnalyzing).toBe(false);
    expect(result.current.progress).toBe(0);
    expect(result.current.error).toBe(null);
    expect(result.current.videoFile).toBe(null);
    expect(result.current.analysisResults).toBe(null);
  });

  it('should start analysis', () => {
    const store = createTestStore();
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <Provider store={store}>{children}</Provider>
    );
    const { result } = renderHook(() => useFormAnalysis(), { wrapper });

    act(() => {
      result.current.startAnalysis();
    });

    expect(result.current.isAnalyzing).toBe(true);
  });

  it('should stop analysis', () => {
    const store = createTestStore({ isAnalyzing: true });
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <Provider store={store}>{children}</Provider>
    );
    const { result } = renderHook(() => useFormAnalysis(), { wrapper });

    act(() => {
      result.current.stopAnalysis();
    });

    expect(result.current.isAnalyzing).toBe(false);
  });

  it('should update progress', () => {
    const store = createTestStore();
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <Provider store={store}>{children}</Provider>
    );
    const { result } = renderHook(() => useFormAnalysis(), { wrapper });

    act(() => {
      result.current.updateProgress(50);
    });

    expect(result.current.progress).toBe(50);
  });

  it('should handle errors', () => {
    const store = createTestStore();
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <Provider store={store}>{children}</Provider>
    );
    const { result } = renderHook(() => useFormAnalysis(), { wrapper });

    const testError = new AppError('Test error', ErrorCode.UNKNOWN_ERROR, 500);
    act(() => {
      result.current.handleError(testError);
    });

    expect(handleApiError).toHaveBeenCalledWith(testError);
    expect(result.current.error).toBe('Test error');
  });

  it('should set video file', () => {
    const store = createTestStore();
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <Provider store={store}>{children}</Provider>
    );
    const { result } = renderHook(() => useFormAnalysis(), { wrapper });

    const testFile = new File([''], 'test.mp4', { type: 'video/mp4' });
    act(() => {
      result.current.setVideo(testFile);
    });

    expect(result.current.videoFile).toBe(testFile);
  });

  it('should set analysis results', () => {
    const store = createTestStore();
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <Provider store={store}>{children}</Provider>
    );
    const { result } = renderHook(() => useFormAnalysis(), { wrapper });

    const testResults = {
      score: 85,
      feedback: ['Good form'],
      videoUrl: 'http://example.com/video.mp4'
    };

    act(() => {
      result.current.setResults(testResults);
    });

    expect(result.current.analysisResults).toEqual(testResults);
  });

  it('should reset state', () => {
    const preloadedState: FormAnalysisState = {
      isAnalyzing: true,
      progress: 50,
      error: null,
      videoFile: new File([''], 'test.mp4', { type: 'video/mp4' }),
      analysisResults: {
        score: 85,
        feedback: ['Good form'],
        videoUrl: 'http://example.com/video.mp4'
      }
    };

    const store = createTestStore(preloadedState);
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <Provider store={store}>{children}</Provider>
    );
    const { result } = renderHook(() => useFormAnalysis(), { wrapper });

    act(() => {
      result.current.reset();
    });

    expect(result.current.isAnalyzing).toBe(false);
    expect(result.current.progress).toBe(0);
    expect(result.current.error).toBe(null);
    expect(result.current.videoFile).toBe(null);
    expect(result.current.analysisResults).toBe(null);
  });
}); 