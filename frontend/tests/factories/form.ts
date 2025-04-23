import { faker } from '@faker-js/faker';
import { Form, FormStatus, FormType } from '../../src/types/form';

export const createForm = (overrides = {}): Form => ({
  id: faker.string.uuid(),
  title: faker.lorem.words(3),
  description: faker.lorem.paragraph(),
  type: 'standard' as FormType,
  status: 'draft' as FormStatus,
  createdBy: faker.string.uuid(),
  createdAt: faker.date.past().toISOString(),
  updatedAt: faker.date.recent().toISOString(),
  fields: Array.from({ length: faker.number.int({ min: 1, max: 5 }) }, () => ({
    id: faker.string.uuid(),
    label: faker.lorem.words(2),
    type: faker.helpers.arrayElement(['text', 'number', 'email', 'select']),
    required: faker.datatype.boolean(),
    options: [],
    validation: {
      required: faker.datatype.boolean(),
      min: null,
      max: null,
      pattern: null
    }
  })),
  submissions: [],
  isPublished: false,
  ...overrides
});

export const createForms = (count: number, overrides = {}): Form[] =>
  Array.from({ length: count }, () => createForm(overrides)); 