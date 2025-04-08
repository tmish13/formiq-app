import { 
  configureStore, 
  combineReducers, 
  Middleware, 
  AnyAction,
  Action,
  ThunkAction,
  ThunkMiddleware
} from '@reduxjs/toolkit';
import { persistStore, persistReducer, FLUSH, REHYDRATE, PAUSE, PERSIST, PURGE, REGISTER } from 'redux-persist';
import storage from 'redux-persist/lib/storage';
import { TypedUseSelectorHook, useDispatch, useSelector } from 'react-redux';
import logger from 'redux-logger';
import authReducer from './slices/authSlice';
import formCheckReducer from './slices/formCheckSlice';
import subscriptionReducer from './slices/subscriptionSlice';
import workoutReducer from './slices/workoutSlice';
import { apiCache } from '../utils/cache';

// Define root state type
export interface RootState {
  auth: ReturnType<typeof authReducer>;
  formCheck: ReturnType<typeof formCheckReducer>;
  subscription: ReturnType<typeof subscriptionReducer>;
  workout: ReturnType<typeof workoutReducer>;
}

// Define AppThunk type
export type AppThunk<ReturnType = void> = ThunkAction<
  ReturnType,
  RootState,
  unknown,
  Action<string>
>;

const persistConfig = {
  key: 'root',
  storage,
  whitelist: ['auth'], // Only persist auth state
  blacklist: [], // Don't persist these reducers
};

const rootReducer = combineReducers({
  auth: authReducer,
  formCheck: formCheckReducer,
  subscription: subscriptionReducer,
  workout: workoutReducer,
});

const persistedReducer = persistReducer(persistConfig, rootReducer);

// Cache middleware for optimistic updates
const cacheMiddleware: Middleware<{}, RootState> = 
  store => 
  next => 
  (action: AnyAction) => {
    // Handle optimistic updates
    if (action.meta?.optimistic) {
      const { type, meta } = action;
      const { endpoint } = meta;

      // Cache the previous state for rollback
      const previousState = store.getState();
      apiCache.set(`optimistic_${endpoint}`, previousState);

      // Dispatch optimistic update
      next(action);

      // Handle API call
      return meta.promise
        .then((result: unknown) => {
          // Success: Remove optimistic cache
          apiCache.delete(`optimistic_${endpoint}`);
          return result;
        })
        .catch((error: unknown) => {
          // Error: Rollback to previous state
          const previousState = apiCache.get(`optimistic_${endpoint}`);
          if (previousState) {
            store.dispatch({ type: `${type}_ROLLBACK`, payload: previousState });
          }
          apiCache.delete(`optimistic_${endpoint}`);
          throw error;
        });
    }

    return next(action);
};

// Error handling middleware
const errorMiddleware: Middleware<{}, RootState> = 
  () => 
  next => 
  (action: AnyAction) => {
    if (action.error) {
      console.error('Error in action:', action);
      // You can dispatch error notifications or handle errors globally here
    }
    return next(action);
  };

// Analytics middleware
const analyticsMiddleware: Middleware<{}, RootState> = 
  () => 
  next => 
  (action: AnyAction) => {
    // Track specific actions for analytics
    if (action.meta?.track) {
      const { event, properties } = action.meta.track;
      // Implement your analytics tracking here
      console.debug('Analytics event:', event, properties);
    }
    return next(action);
};

// Performance middleware
const performanceMiddleware: Middleware<{}, RootState> = 
  () => 
  next => 
  (action: AnyAction) => {
    const start = performance.now();
    const result = next(action);
    const end = performance.now();
    const duration = end - start;

    if (duration > 16) { // Longer than one frame (60fps)
      console.warn(`Slow action: ${action.type} took ${duration.toFixed(2)}ms`);
    }

    return result;
};

// Configure store with middleware
export const store = configureStore({
  reducer: persistedReducer,
  middleware: (getDefaultMiddleware) => {
    const middleware = getDefaultMiddleware({
      serializableCheck: {
        ignoredActions: [
          FLUSH,
          REHYDRATE,
          PAUSE,
          PERSIST,
          PURGE,
          REGISTER,
          'persist/PERSIST'
        ],
        // Ignore these field paths in all actions
        ignoredActionPaths: ['meta.promise', 'payload.timestamp'],
        // Ignore these paths in the state
        ignoredPaths: ['items.dates'],
      },
      thunk: {
        extraArgument: undefined,
      },
    });

    if (process.env.NODE_ENV === 'development') {
      middleware.push(logger as ThunkMiddleware<RootState>);
    }

    return middleware.concat(
      cacheMiddleware as ThunkMiddleware<RootState>,
      errorMiddleware as ThunkMiddleware<RootState>,
      analyticsMiddleware as ThunkMiddleware<RootState>,
      performanceMiddleware as ThunkMiddleware<RootState>
    );
  },
  devTools: process.env.NODE_ENV !== 'production',
});

export const persistor = persistStore(store);

// Export typed hooks
export type AppDispatch = typeof store.dispatch;
export const useAppDispatch = () => useDispatch<AppDispatch>();
export const useAppSelector: TypedUseSelectorHook<RootState> = useSelector;

// Action creator for optimistic updates
interface OptimisticActionMeta {
  endpoint: string;
  method: string;
  promise: Promise<unknown>;
  track?: {
    event: string;
    properties?: Record<string, unknown>;
  };
}

export const createOptimisticAction = (
  type: string,
  payload: unknown,
  meta: OptimisticActionMeta
): AnyAction => ({
  type,
  payload,
  meta: {
    ...meta,
    optimistic: true,
  },
}); 