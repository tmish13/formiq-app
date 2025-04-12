import { combineReducers } from '@reduxjs/toolkit';
import formCheckReducer from './slices/formCheckSlice';
import authReducer from './slices/authSlice';
import uiReducer from './slices/uiSlice';

const rootReducer = combineReducers({
  formCheck: formCheckReducer,
  auth: authReducer,
  ui: uiReducer
});

export type RootState = ReturnType<typeof rootReducer>;
export default rootReducer; 