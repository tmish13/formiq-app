import { useCallback } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { RootState } from '../store';
import {
  setIsAnalyzing,
  setProgress,
  setError,
  setVideoFile,
  setAnalysisResults,
  resetState,
} from '../store/slices/formAnalysisSlice';
import { handleApiError } from '../utils/errorHandling';

// TODO: Future enhancements
// - Add memoized selectors for performance
// - Add batch update functionality
// - Add automatic cleanup on unmount
// - Add analysis history tracking
// - Add offline support for analysis results

export const useFormAnalysis = () => {
  const dispatch = useDispatch();
  const {
    isAnalyzing,
    progress,
    error,
    videoFile,
    analysisResults,
  } = useSelector((state: RootState) => state.formAnalysis);

  const startAnalysis = useCallback(() => {
    dispatch(setIsAnalyzing(true));
  }, [dispatch]);

  const stopAnalysis = useCallback(() => {
    dispatch(setIsAnalyzing(false));
  }, [dispatch]);

  const updateProgress = useCallback((value: number) => {
    dispatch(setProgress(value));
  }, [dispatch]);

  const handleError = useCallback((error: unknown) => {
    const appError = handleApiError(error);
    dispatch(setError(appError));
  }, [dispatch]);

  const setVideo = useCallback((file: File | null) => {
    dispatch(setVideoFile(file));
  }, [dispatch]);

  const setResults = useCallback((results: {
    score: number;
    feedback: string[];
    videoUrl: string;
  } | null) => {
    dispatch(setAnalysisResults(results));
  }, [dispatch]);

  const reset = useCallback(() => {
    dispatch(resetState());
  }, [dispatch]);

  return {
    // State
    isAnalyzing,
    progress,
    error,
    videoFile,
    analysisResults,
    // Actions
    startAnalysis,
    stopAnalysis,
    updateProgress,
    handleError,
    setVideo,
    setResults,
    reset,
  };
}; 