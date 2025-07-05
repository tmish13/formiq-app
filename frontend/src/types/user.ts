export type SubscriptionTier = 'free' | 'basic' | 'premium';
export type UserRole = 'user' | 'admin' | 'trainer';

export interface User {
  id: string;
  email: string;
  name: string;
  role: UserRole;
  isActive: boolean;
  isVerified: boolean;
  subscriptionTier: SubscriptionTier;
  subscriptionEndDate?: string;
  stripeCustomerId?: string;
  stripeSubscriptionId?: string;
  isEmailVerified: boolean;
  has_completed_onboarding?: boolean;
  onboarding_completed_at?: string;
  createdAt: string;
  updatedAt: string;
} 