import { faker } from '@faker-js/faker';

export interface FormCheck {
  id: string;
  userId: string;
  exercise: string;
  videoUrl: string;
  feedback: string[];
  score: number;
  createdAt: string;
  updatedAt: string;
  status: 'pending' | 'completed' | 'failed';
}

export const exercises = [
  'squat',
  'deadlift',
  'bench_press',
  'overhead_press',
  'row'
] as const;

export const createFormCheck = (overrides: Partial<FormCheck> = {}): FormCheck => ({
  id: faker.string.uuid(),
  userId: faker.string.uuid(),
  exercise: faker.helpers.arrayElement(exercises),
  videoUrl: faker.internet.url(),
  feedback: Array.from(
    { length: faker.number.int({ min: 1, max: 5 }) },
    () => faker.lorem.sentence()
  ),
  score: faker.number.int({ min: 0, max: 100 }),
  createdAt: faker.date.past().toISOString(),
  updatedAt: faker.date.recent().toISOString(),
  status: faker.helpers.arrayElement(['pending', 'completed', 'failed']),
  ...overrides,
});

export const createFormChecks = (count: number, overrides: Partial<FormCheck> = {}): FormCheck[] =>
  Array.from({ length: count }, () => createFormCheck(overrides)); 