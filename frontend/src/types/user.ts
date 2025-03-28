export interface User {
  id: string;
  email: string;
  name: string;
  role: 'user' | 'admin' | 'trainer';
  isActive: boolean;
  subscriptionTier: 'free' | 'basic' | 'premium';
  subscriptionEndDate?: string;
  stripeCustomerId?: string;
  stripeSubscriptionId?: string;
  isEmailVerified: boolean;
  createdAt: string;
  updatedAt: string;
} 