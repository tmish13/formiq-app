import { createSlice, PayloadAction } from '@reduxjs/toolkit';

export interface FormCheckFeedback {
  type: 'success' | 'warning' | 'error';
  message: string;
  timestamp: string;
}

export interface FormCheck {
  id: string;
  exerciseName: string;
  timestamp: string;
  feedback: FormCheckFeedback[];
  videoUrl?: string;
  userId: string;
  status: 'pending' | 'completed' | 'failed';
}

export interface FormCheckState {
  checks: FormCheck[];
  isLoading: boolean;
  error: string | null;
  currentCheck: FormCheck | null;
  selectedCheck: FormCheck | null;
}

const initialState: FormCheckState = {
  checks: [],
  isLoading: false,
  error: null,
  currentCheck: null,
  selectedCheck: null,
};

const formCheckSlice = createSlice({
  name: 'formCheck',
  initialState,
  reducers: {
    setLoading: (state, action: PayloadAction<boolean>) => {
      state.isLoading = action.payload;
    },
    setError: (state, action: PayloadAction<string | null>) => {
      state.error = action.payload;
    },
    addFormCheck: (state, action: PayloadAction<FormCheck>) => {
      state.checks.push(action.payload);
    },
    setCurrentCheck: (state, action: PayloadAction<FormCheck | null>) => {
      state.currentCheck = action.payload;
    },
    setSelectedCheck: (state, action: PayloadAction<FormCheck | null>) => {
      state.selectedCheck = action.payload;
    },
    clearCurrentCheck: (state) => {
      state.currentCheck = null;
    },
    updateFormCheck: (state, action: PayloadAction<FormCheck>) => {
      const index = state.checks.findIndex(check => check.id === action.payload.id);
      if (index !== -1) {
        state.checks[index] = action.payload;
      }
      if (state.currentCheck?.id === action.payload.id) {
        state.currentCheck = action.payload;
      }
      if (state.selectedCheck?.id === action.payload.id) {
        state.selectedCheck = action.payload;
      }
    },
    deleteFormCheck: (state, action: PayloadAction<string>) => {
      state.checks = state.checks.filter(check => check.id !== action.payload);
      if (state.currentCheck?.id === action.payload) {
        state.currentCheck = null;
      }
      if (state.selectedCheck?.id === action.payload) {
        state.selectedCheck = null;
      }
    },
  },
});

export const {
  setLoading,
  setError,
  addFormCheck,
  setCurrentCheck,
  setSelectedCheck,
  clearCurrentCheck,
  updateFormCheck,
  deleteFormCheck,
} = formCheckSlice.actions;

export default formCheckSlice.reducer; 