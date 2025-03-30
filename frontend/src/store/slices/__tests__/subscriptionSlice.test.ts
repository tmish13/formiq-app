import subscriptionReducer, {
  setPlans,
  setCurrentSubscription,
  setSelectedPlan,
  setLoading,
  setError,
  updateSubscriptionStatus,
  updateSubscription,
  cancelSubscription,
  SubscriptionState,
  SubscriptionPlan,
  Subscription,
} from '../subscriptionSlice';

describe('subscriptionSlice', () => {
  const mockSubscriptionPlans: SubscriptionPlan[] = [
    {
      id: '1',
      name: 'Basic',
      price: 9.99,
      features: ['Feature 1', 'Feature 2'],
      interval: 'monthly',
      stripePriceId: 'price_basic_monthly',
      stripeProductId: 'prod_basic',
      isPopular: false,
    },
    {
      id: '2',
      name: 'Premium',
      price: 19.99,
      features: ['Feature 1', 'Feature 2', 'Feature 3'],
      interval: 'monthly',
      stripePriceId: 'price_premium_monthly',
      stripeProductId: 'prod_premium',
      isPopular: true,
    },
  ];

  const mockSubscription: Subscription = {
    id: 'sub_123',
    userId: 'user_1',
    planId: '1',
    status: 'active',
    startDate: '2024-03-01T00:00:00Z',
    endDate: '2024-04-01T00:00:00Z',
    autoRenew: true,
    stripeSubscriptionId: 'sub_stripe_123',
    currentPeriodStart: '2024-03-01T00:00:00Z',
    currentPeriodEnd: '2024-04-01T00:00:00Z',
    cancelAtPeriodEnd: false,
  };

  const initialState: SubscriptionState = {
    plans: [],
    currentSubscription: null,
    isLoading: false,
    error: null,
    selectedPlan: null,
  };

  it('should handle initial state', () => {
    expect(subscriptionReducer(undefined, { type: 'unknown' })).toEqual(initialState);
  });

  it('should handle setPlans', () => {
    const actual = subscriptionReducer(initialState, setPlans(mockSubscriptionPlans));
    expect(actual.plans).toEqual(mockSubscriptionPlans);
  });

  it('should handle setCurrentSubscription', () => {
    const actual = subscriptionReducer(initialState, setCurrentSubscription(mockSubscription));
    expect(actual.currentSubscription).toEqual(mockSubscription);
  });

  it('should handle setSelectedPlan', () => {
    const selectedPlan = mockSubscriptionPlans[0];
    const actual = subscriptionReducer(initialState, setSelectedPlan(selectedPlan));
    expect(actual.selectedPlan).toEqual(selectedPlan);
  });

  it('should handle setLoading', () => {
    const actual = subscriptionReducer(initialState, setLoading(true));
    expect(actual.isLoading).toBe(true);
  });

  it('should handle setError', () => {
    const error = 'Test error message';
    const actual = subscriptionReducer(initialState, setError(error));
    expect(actual.error).toBe(error);
  });

  it('should handle updateSubscriptionStatus', () => {
    const stateWithSubscription = {
      ...initialState,
      currentSubscription: mockSubscription,
    };
    const actual = subscriptionReducer(
      stateWithSubscription,
      updateSubscriptionStatus({ id: mockSubscription.id, status: 'past_due' })
    );
    expect(actual.currentSubscription?.status).toBe('past_due');
  });

  it('should handle updateSubscription', () => {
    const stateWithSubscription = {
      ...initialState,
      currentSubscription: mockSubscription,
    };
    const updatedSubscription = {
      ...mockSubscription,
      autoRenew: false,
    };
    const actual = subscriptionReducer(stateWithSubscription, updateSubscription(updatedSubscription));
    expect(actual.currentSubscription).toEqual(updatedSubscription);
  });

  it('should handle cancelSubscription', () => {
    const stateWithSubscription = {
      ...initialState,
      currentSubscription: mockSubscription,
    };
    const actual = subscriptionReducer(stateWithSubscription, cancelSubscription(mockSubscription.id));
    expect(actual.currentSubscription?.status).toBe('cancelled');
    expect(actual.currentSubscription?.cancelAtPeriodEnd).toBe(true);
    expect(actual.currentSubscription?.canceledAt).toBeDefined();
  });

  it('should not update subscription status for non-matching id', () => {
    const stateWithSubscription = {
      ...initialState,
      currentSubscription: mockSubscription,
    };
    const actual = subscriptionReducer(
      stateWithSubscription,
      updateSubscriptionStatus({ id: 'wrong_id', status: 'past_due' })
    );
    expect(actual.currentSubscription?.status).toBe('active');
  });
}); 