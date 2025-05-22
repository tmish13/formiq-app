import { createSlice, PayloadAction } from '@reduxjs/toolkit';

export interface ModalContent {
  title?: string;
  content: React.ReactNode;
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
}

interface UIState {
  isLoading: boolean;
  error: string | null;
  isOffline: boolean;
  isModalOpen: boolean;
  modalContent: ModalContent | null;
}

const initialState: UIState = {
  isLoading: false,
  error: null,
  isOffline: false,
  isModalOpen: false,
  modalContent: null
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
    },
    openModal: (state, action: PayloadAction<ModalContent>) => {
      state.isModalOpen = true;
      state.modalContent = action.payload;
    },
    closeModal: (state) => {
      state.isModalOpen = false;
      state.modalContent = null;
    }
  }
});

export const { 
  setLoading, 
  setError, 
  setOffline, 
  clearError,
  openModal,
  closeModal 
} = uiSlice.actions;

export default uiSlice.reducer; 