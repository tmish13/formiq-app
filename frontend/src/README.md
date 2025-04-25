# FormIQ Frontend Structure

## Directory Structure

- `components/` – Reusable UI components
  - `common/` - Common UI components like buttons, inputs, etc.
  - `layout/` - Layout components like header, footer, etc.
  - `auth/` - Authentication-related components
  - `camera/` - Camera and form capture components
  - `**/` - Other feature-specific components

- `contexts/` - React contexts for global state management
  - `AuthContext.tsx` - Authentication context
  - `ThemeContext.tsx` - Theme context with light/dark mode support
  - `LoadingContext.tsx` - Loading state context
  - `*Context.tsx` - Other context providers

- `hooks/` – Custom React hooks
  - `useAuth.ts` - Authentication hook
  - `useCameraPermissions.ts` - Camera permissions hook
  - `use*.ts` - Other custom hooks

- `services/` – API service calls and data handling
  - `api/` - API-related services including handlers for mock data
  - `auth.ts` - Authentication service
  - `*.ts` - Other feature-specific services

- `routes/` – Routing and navigation config
  - `index.tsx` - Main routes component
  - `routes.tsx` - Route definitions

- `theme/` - Centralized theming
  - `theme.ts` - Theme definitions (light/dark)

- `types/` - TypeScript type definitions
  - `theme.d.ts` - Theme type definitions
  - `*.d.ts` - Other type definitions

- `utils/` - Helper functions
  - `themeUtils.ts` - Theme utility functions
  - `*.ts` - Other utility functions

- `styles/` - Global styles
  - `GlobalStyle.ts` - Global style definitions

- `pages/` - Page components
  - `*/` - Feature-specific pages

## Best Practices

- Components should be organized by feature or domain
- Use contexts for global state management
- Use hooks for shared logic
- Keep business logic in services
- Use types for better type safety
- Keep styling consistent using the theme

This layout ensures separation of concerns and scalable modular design for web and mobile platforms.

# FormIQ Frontend Testing Structure

This document outlines the testing structure for the FormIQ frontend application.

## Test Setup

The testing setup is centralized in the following files:

- `setupTests.ts`: Contains all global test setup, including mocks for browser APIs, console suppression, and server setup.
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
  pages/
    MyPage/
      MyPage.tsx
      __tests__/
        MyPage.test.tsx
  hooks/
    useMyHook/
      useMyHook.ts
      __tests__/
        useMyHook.test.ts
```

## Writing Tests

When writing tests, use the following utilities:

```tsx
import { renderWithProviders, generateTestFormAnalysis } from '../test-utils';

// Example test
it('displays form check data correctly', async () => {
  const mockFormCheck = generateTestFormAnalysis();
  
  renderWithProviders(<Results />, { 
    route: '/results/123',
    preloadedState: { /* initial state */ }
  });
  
  // Test assertions
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
2. Use the `renderWithProviders` function to render components with all necessary providers
3. Use test data generators to create consistent test data
4. Mock external dependencies using Jest's mocking capabilities
5. Use `data-testid` attributes to select elements in tests
6. Write tests that focus on behavior, not implementation details 