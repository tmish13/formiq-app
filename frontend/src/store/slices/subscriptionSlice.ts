import { createSlice, PayloadAction } from '@reduxjs/toolkit';

export interface SubscriptionPlan {
  id: string;
  name: string;
  price: number;
  features: string[];
  interval: 'monthly' | 'yearly';
  stripePriceId: string;
  stripeProductId: string;
  isPopular?: boolean;
}

export interface Subscription {
  id: string;
  userId: string;
  planId: string;
  status: 'active' | 'cancelled' | 'expired' | 'past_due' | 'unpaid';
  startDate: string;
  endDate: string;
  autoRenew: boolean;
  stripeSubscriptionId: string;
  currentPeriodStart: string;
  currentPeriodEnd: string;
  cancelAtPeriodEnd: boolean;
  canceledAt?: string;
  trialEnd?: string;
}

export interface SubscriptionState {
  plans: SubscriptionPlan[];
  currentSubscription: Subscription | null;
  isLoading: boolean;
  error: string | null;
  selectedPlan: SubscriptionPlan | null;
}

const initialState: SubscriptionState = {
  plans: [],
  currentSubscription: null,
  isLoading: false,
  error: null,
  selectedPlan: null,
};

const subscriptionSlice = createSlice({
  name: 'subscription',
  initialState,
  reducers: {
    setLoading: (state, action: PayloadAction<boolean>) => {
      state.isLoading = action.payload;
    },
    setError: (state, action: PayloadAction<string | null>) => {
      state.error = action.payload;
    },
    setPlans: (state, action: PayloadAction<SubscriptionPlan[]>) => {
      state.plans = action.payload;
    },
    setCurrentSubscription: (state, action: PayloadAction<Subscription | null>) => {
      state.currentSubscription = action.payload;
    },
    setSelectedPlan: (state, action: PayloadAction<SubscriptionPlan | null>) => {
      state.selectedPlan = action.payload;
    },
    updateSubscriptionStatus: (state, action: PayloadAction<{ id: string; status: Subscription['status'] }>) => {
      if (state.currentSubscription?.id === action.payload.id) {
        state.currentSubscription.status = action.payload.status;
      }
    },
    updateSubscription: (state, action: PayloadAction<Subscription>) => {
      if (state.currentSubscription?.id === action.payload.id) {
        state.currentSubscription = action.payload;
      }
    },
    cancelSubscription: (state, action: PayloadAction<string>) => {
      if (state.currentSubscription?.id === action.payload) {
        state.currentSubscription = {
          ...state.currentSubscription,
          status: 'cancelled',
          cancelAtPeriodEnd: true,
          canceledAt: new Date().toISOString(),
        };
      }
    },
  },
});

export const {
  setLoading,
  setError,
  setPlans,
  setCurrentSubscription,
  setSelectedPlan,
  updateSubscriptionStatus,
  updateSubscription,
  cancelSubscription,
} = subscriptionSlice.actions;

export default subscriptionSlice.reducer; 