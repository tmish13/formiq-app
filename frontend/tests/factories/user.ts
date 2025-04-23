import { faker } from '@faker-js/faker';
import { User, SubscriptionTier } from '../../src/types/user';

export const createUser = (overrides = {}): User => ({
  id: faker.string.uuid(),
  email: faker.internet.email(),
  name: faker.person.fullName(),
  role: 'user',
  subscriptionTier: 'free' as SubscriptionTier,
  isActive: true,
  isVerified: true,
  createdAt: faker.date.past().toISOString(),
  subscriptionEndDate: faker.date.future().toISOString(),
  stripeCustomerId: `cus_${faker.string.alphanumeric(14)}`,
  ...overrides
});

export const createUsers = (count: number, overrides = {}): User[] => 
  Array.from({ length: count }, () => createUser(overrides)); 