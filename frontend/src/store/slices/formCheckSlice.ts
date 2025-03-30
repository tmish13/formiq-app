import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { FormCheckStatus } from '../../types';
import { FormCheck } from '../../types/formCheck';

export interface FormCheckState {
  formChecks: FormCheck[];
  currentFormCheck: FormCheck | null;
  isLoading: boolean;
  error: string | null;
}

const initialState: FormCheckState = {
  formChecks: [],
  currentFormCheck: null,
  isLoading: false,
  error: null,
};

const formCheckSlice = createSlice({
  name: 'formCheck',
  initialState,
  reducers: {
    setFormChecks: (state, action: PayloadAction<FormCheck[]>) => {
      state.formChecks = action.payload;
    },
    setCurrentFormCheck: (state, action: PayloadAction<FormCheck | null>) => {
      state.currentFormCheck = action.payload;
    },
    addFormCheck: (state, action: PayloadAction<FormCheck>) => {
      state.formChecks.push(action.payload);
    },
    updateFormCheck: (state, action: PayloadAction<FormCheck>) => {
      const index = state.formChecks.findIndex(fc => fc.id === action.payload.id);
      if (index !== -1) {
        state.formChecks[index] = action.payload;
      }
      if (state.currentFormCheck?.id === action.payload.id) {
        state.currentFormCheck = action.payload;
      }
    },
    deleteFormCheck: (state, action: PayloadAction<number>) => {
      state.formChecks = state.formChecks.filter(fc => fc.id !== action.payload);
      if (state.currentFormCheck?.id === action.payload) {
        state.currentFormCheck = null;
      }
    },
    updateFormCheckStatus: (
      state,
      action: PayloadAction<{ id: number; status: FormCheckStatus }>
    ) => {
      const { id, status } = action.payload;
      const formCheck = state.formChecks.find(fc => fc.id === id) as FormCheck;
      if (formCheck) {
        formCheck.status = status;
      }
      if (state.currentFormCheck?.id === id) {
        (state.currentFormCheck as FormCheck).status = status;
      }
    },
    setLoading: (state, action: PayloadAction<boolean>) => {
      state.isLoading = action.payload;
    },
    setError: (state, action: PayloadAction<string | null>) => {
      state.error = action.payload;
    },
  },
});

export const {
  setFormChecks,
  setCurrentFormCheck,
  addFormCheck,
  updateFormCheck,
  deleteFormCheck,
  updateFormCheckStatus,
  setLoading,
  setError,
} = formCheckSlice.actions;

export default formCheckSlice.reducer; 