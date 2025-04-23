import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { ApiError } from '../../utils/errorHandling';

// TODO: Future optimizations
// - Add thunks for async analysis operations
// - Add selectors for derived state
// - Add middleware for analysis tracking
// - Consider splitting video state into separate slice if it grows
// - Add persistence configuration for analysis results

export interface FormAnalysisState {
  isAnalyzing: boolean;
  progress: number;
  error: ApiError | null;
  videoFile: File | null;
  analysisResults: {
    score: number;
    feedback: string[];
    videoUrl: string;
  } | null;
}

const initialState: FormAnalysisState = {
  isAnalyzing: false,
  progress: 0,
  error: null,
  videoFile: null,
  analysisResults: null,
};

const formAnalysisSlice = createSlice({
  name: 'formAnalysis',
  initialState,
  reducers: {
    setIsAnalyzing: (state, action: PayloadAction<boolean>) => {
      state.isAnalyzing = action.payload;
      if (!action.payload) {
        state.progress = 0;
      }
    },
    setProgress: (state, action: PayloadAction<number>) => {
      state.progress = action.payload;
    },
    setError: (state, action: PayloadAction<ApiError | null>) => {
      state.error = action.payload;
    },
    setVideoFile: (state, action: PayloadAction<File | null>) => {
      state.videoFile = action.payload;
      if (!action.payload) {
        state.analysisResults = null;
      }
    },
    setAnalysisResults: (state, action: PayloadAction<{
      score: number;
      feedback: string[];
      videoUrl: string;
    } | null>) => {
      state.analysisResults = action.payload;
    },
    resetState: (state) => {
      Object.assign(state, initialState);
    },
  },
});

export const {
  setIsAnalyzing,
  setProgress,
  setError,
  setVideoFile,
  setAnalysisResults,
  resetState,
} = formAnalysisSlice.actions;

export default formAnalysisSlice.reducer; 