import { configureStore } from '@reduxjs/toolkit';
import { setUser, setToken, logout } from '../../store/slices/authSlice';
import { setPlans, SubscriptionPlan } from '../../store/slices/subscriptionSlice';
import { addFormCheck, setFormChecks } from '../../store/slices/formCheckSlice';
import { FormCheck, FeedbackItem } from '../../types/formCheck';
import { SubscriptionTier, User } from '../../types';
import authReducer from '../../store/slices/authSlice';
import formCheckReducer from '../../store/slices/formCheckSlice';
import subscriptionReducer from '../../store/slices/subscriptionSlice';
import workoutReducer from '../../store/slices/workoutSlice';
import formAnalysisReducer from '../../store/slices/formAnalysisSlice';

// Define the reducer structure
const rootReducer = {
  auth: authReducer,
  formCheck: formCheckReducer,
  subscription: subscriptionReducer,
  workout: workoutReducer,
  formAnalysis: formAnalysisReducer
};

// Define test store type
type TestStoreType = ReturnType<typeof createTestStore>;
type RootStateType = ReturnType<TestStoreType['getState']>;

// Create a test store factory function
function createTestStore() {
  return configureStore({
    reducer: rootReducer
  });
}

describe('Store Configuration', () => {
  let store: TestStoreType;
  
  beforeEach(() => {
    // Create a new store instance for each test to avoid state pollution
    store = createTestStore();
  });

  const mockUser: User = {
    id: 'user_1',
    email: 'test@example.com',
    name: 'Test User',
    role: 'user',
    subscription_tier: 'basic' as SubscriptionTier,
    subscription_end_date: '2024-04-01T00:00:00Z',
    created_at: '2024-03-01T00:00:00Z',
    updated_at: '2024-03-01T00:00:00Z',
  };

  const mockSubscriptionPlans: SubscriptionPlan[] = [
    {
      id: '1',
      name: 'Basic',
      price: 9.99,
      features: ['Feature 1', 'Feature 2'],
      interval: 'monthly' as const,
      stripePriceId: 'price_basic_monthly',
      stripeProductId: 'prod_basic',
      isPopular: false,
    },
  ];

  const createMockFeedback = (): FeedbackItem[] => ([
    {
      type: 'form',
      severity: 'low',
      timestamp: Date.now(),
      description: 'Good form overall',
      suggestions: '',
    },
  ]);

  const createMockFormCheck = (): FormCheck => ({
    id: 1,
    user_id: 1,
    exercise_type: 'squat',
    video_url: 'https://example.com/video1.mp4',
    created_at: '2024-03-20T10:00:00Z',
    updated_at: '2024-03-20T10:00:00Z',
    feedback_items: createMockFeedback(),
    status: 'completed' as const,
  });

  it('should have the correct initial state', () => {
    const state = store.getState();
    
    // Check auth slice
    expect(state.auth).toEqual({
      user: null,
      token: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,
    });
    
    // Check subscription slice
    expect(state.subscription).toEqual({
      plans: [],
      currentSubscription: null,
      isLoading: false,
      error: null,
      selectedPlan: null,
    });
    
    // Check formCheck slice
    expect(state.formCheck).toEqual({
      formChecks: [],
      isLoading: false,
      error: null,
      currentFormCheck: null,
    });
    
    // Check workout slice
    expect(state.workout).toEqual({
      workouts: [],
      workoutPlans: [],
      currentWorkout: null,
      currentPlan: null,
      isLoading: false,
      error: null,
    });
    
    // Check formAnalysis slice
    expect(state.formAnalysis).toEqual({
      isAnalyzing: false,
      progress: 0,
      error: null,
      videoFile: null,
      analysisResults: null,
    });
  });

  it('should handle auth actions', () => {
    // Create a deep clone to avoid shared references
    const clonedMockUser = JSON.parse(JSON.stringify(mockUser));
    
    store.dispatch(setUser(clonedMockUser));
    store.dispatch(setToken('test-token'));

    const state = store.getState();
    expect(state.auth.user).toEqual(mockUser);
    expect(state.auth.token).toBe('test-token');
    expect(state.auth.isAuthenticated).toBe(true);

    store.dispatch(logout());
    const newState = store.getState();
    expect(newState.auth.user).toBeNull();
    expect(newState.auth.token).toBeNull();
    expect(newState.auth.isAuthenticated).toBe(false);
  });

  it('should handle subscription actions', () => {
    // Create a deep clone to avoid shared references
    const clonedMockPlans = JSON.parse(JSON.stringify(mockSubscriptionPlans));
    
    store.dispatch(setPlans(clonedMockPlans));

    const state = store.getState();
    expect(state.subscription.plans).toEqual(mockSubscriptionPlans);
  });

  it('should handle form check actions', () => {
    // Create a new instance of the form check
    const mockFormCheck = createMockFormCheck();
    
    // Reset formChecks array to ensure it's empty
    store.dispatch(setFormChecks([]));
    
    // Add a form check
    store.dispatch(addFormCheck(mockFormCheck));

    const state = store.getState();
    expect(state.formCheck.formChecks).toHaveLength(1);
    expect(state.formCheck.formChecks[0]).toEqual(mockFormCheck);
  });

  it('should maintain state independence between slices', () => {
    // Reset formChecks to avoid any potential leftover state
    store.dispatch(setFormChecks([]));
    
    // Create fresh objects for this test
    const mockUser = JSON.parse(JSON.stringify({
      id: 'user_1',
      email: 'test@example.com',
      name: 'Test User',
      role: 'user',
      subscription_tier: 'basic' as SubscriptionTier,
      subscription_end_date: '2024-04-01T00:00:00Z',
      created_at: '2024-03-01T00:00:00Z',
      updated_at: '2024-03-01T00:00:00Z',
    }));
    
    const mockPlans = JSON.parse(JSON.stringify(mockSubscriptionPlans));
    const mockFormCheck = createMockFormCheck();
    
    // Dispatch actions
    store.dispatch(setUser(mockUser));
    store.dispatch(setPlans(mockPlans));
    store.dispatch(addFormCheck(mockFormCheck));

    // Verify state
    const state = store.getState();
    expect(state.auth.user).toEqual(mockUser);
    expect(state.subscription.plans).toEqual(mockSubscriptionPlans);
    expect(state.formCheck.formChecks).toHaveLength(1);
    expect(state.formCheck.formChecks[0]).toEqual(mockFormCheck);

    // Logout should only affect auth slice
    store.dispatch(logout());
    const newState = store.getState();
    expect(newState.auth.user).toBeNull();
    expect(newState.subscription.plans).toEqual(mockSubscriptionPlans);
    expect(newState.formCheck.formChecks).toHaveLength(1);
    expect(newState.formCheck.formChecks[0]).toEqual(mockFormCheck);
  });
}); 