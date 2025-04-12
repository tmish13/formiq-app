import { createSlice, PayloadAction } from '@reduxjs/toolkit';

interface UIState {
  isLoading: boolean;
  error: string | null;
  isOffline: boolean;
}

const initialState: UIState = {
  isLoading: false,
  error: null,
  isOffline: false
};

const uiSlice = createSlice({
  name: 'ui',
  initialState,
  reducers: {
    setLoading: (state, action: PayloadAction<boolean>) => {
      state.isLoading = action.payload;
    },
    setError: (state, action: PayloadAction<string | null>) => {
      state.error = action.payload;
    },
    setOffline: (state, action: PayloadAction<boolean>) => {
      state.isOffline = action.payload;
    },
    clearError: (state) => {
      state.error = null;
    }
  }
});

export const { setLoading, setError, setOffline, clearError } = uiSlice.actions;
export default uiSlice.reducer; 