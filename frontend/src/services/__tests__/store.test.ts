import { store } from '../../store';
import { setUser, setToken, logout } from '../../store/slices/authSlice';
import { setPlans, SubscriptionPlan } from '../../store/slices/subscriptionSlice';
import { addFormCheck } from '../../store/slices/formCheckSlice';
import { FormCheck, FeedbackItem } from '../../types/formCheck';
import { SubscriptionTier, User } from '../../types';

describe('Store Configuration', () => {
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

  const mockFeedback: FeedbackItem[] = [
    {
      type: 'form',
      severity: 'low',
      timestamp: Date.now(),
      description: 'Good form overall',
      suggestions: '',
    },
  ];

  const mockFormCheck: FormCheck = {
    id: 1,
    user_id: 1,
    exercise_type: 'squat',
    video_url: 'https://example.com/video1.mp4',
    created_at: '2024-03-20T10:00:00Z',
    updated_at: '2024-03-20T10:00:00Z',
    feedback_items: mockFeedback,
    status: 'completed' as const,
  };

  it('should have the correct initial state', () => {
    const state = store.getState();
    expect(state.auth).toEqual({
      user: null,
      token: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,
    });
    expect(state.subscription).toEqual({
      plans: [],
      currentSubscription: null,
      isLoading: false,
      error: null,
      selectedPlan: null,
    });
    expect(state.formCheck).toEqual({
      formChecks: [],
      isLoading: false,
      error: null,
      currentCheck: null,
      selectedCheck: null,
    });
  });

  it('should handle auth actions', () => {
    store.dispatch(setUser(mockUser));
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
    store.dispatch(setPlans(mockSubscriptionPlans));

    const state = store.getState();
    expect(state.subscription.plans).toEqual(mockSubscriptionPlans);
  });

  it('should handle form check actions', () => {
    store.dispatch(addFormCheck(mockFormCheck));

    const state = store.getState();
    expect(state.formCheck.formChecks).toEqual([mockFormCheck]);
  });

  it('should maintain state independence between slices', () => {
    store.dispatch(setUser(mockUser));
    store.dispatch(setPlans(mockSubscriptionPlans));
    store.dispatch(addFormCheck(mockFormCheck));

    const state = store.getState();
    expect(state.auth.user).toEqual(mockUser);
    expect(state.subscription.plans).toEqual(mockSubscriptionPlans);
    expect(state.formCheck.formChecks).toEqual([mockFormCheck]);

    store.dispatch(logout());
    const newState = store.getState();
    expect(newState.auth.user).toBeNull();
    expect(newState.subscription.plans).toEqual(mockSubscriptionPlans);
    expect(newState.formCheck.formChecks).toEqual([mockFormCheck]);
  });
}); 