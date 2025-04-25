# FormIQ Mobile Testing Structure

This document outlines the testing structure for the FormIQ mobile application.

## Test Setup

The testing setup is centralized in the following files:

- `setupTests.js`: Contains all global test setup for React Native, including mocks for native modules and navigation.
- `test-utils.tsx`: Contains utility functions for testing, including custom render functions, test data generators, and mock helpers.

## Test Directory Structure

Tests should be placed in `__tests__` directories next to the components they test:

```
src/
  components/
    MyComponent/
      MyComponent.tsx
      __tests__/
        MyComponent.test.tsx
  services/
    MyService/
      MyService.ts
      __tests__/
        MyService.test.ts
  hooks/
    useMyHook/
      useMyHook.ts
      __tests__/
        useMyHook.test.ts
```

## Writing Tests

When writing tests, use the following utilities:

```tsx
import { render, createTestStore, generateTestFormAnalysis } from '../test-utils';

// Example test
it('displays form check data correctly', async () => {
  const mockFormCheck = generateTestFormAnalysis();
  
  const { getByText } = render(<Results />, { 
    initialState: { /* initial state */ }
  });
  
  // Test assertions
  expect(getByText('Form Analysis Results')).toBeTruthy();
});
```

## Test Data Generation

Use the test data generators in `test-utils.tsx` to create consistent test data:

- `generateTestUser()`: Creates a mock user
- `generateTestFormAnalysis()`: Creates a mock form analysis
- `createMockFile()`: Creates a mock file for testing uploads
- `createMockApiResponse()`: Creates a mock API response
- `createApiError()`: Creates a mock API error

## Best Practices

1. Place tests in `__tests__` directories next to the components they test
2. Use the `render` function to render components with all necessary providers
3. Use test data generators to create consistent test data
4. Mock external dependencies using Jest's mocking capabilities
5. Use `testID` attributes to select elements in tests
6. Write tests that focus on behavior, not implementation details 