# Frontend Testing Utilities

This directory contains utilities and setup files for testing the frontend application.

## Key Testing Files

- `setup.tsx`: Global test setup that runs before tests
- `/utils/testRender.tsx`: Custom render function that wraps components in required providers
- `/utils/testServer.ts`: MSW server setup with common handlers
- `/__mocks__/mockTheme.ts`: Mock theme for styled-components

## Best Practices

### Rendering Components

Always use the `render` function imported from `tests/utils/testRender` rather than directly from `@testing-library/react`. This ensures your components are wrapped with all necessary providers.

```tsx
// ✅ Good
import { render, screen } from '../../../tests/utils/testRender';

// ❌ Bad
import { render, screen } from '@testing-library/react';
```

### Custom Rendering Options

The `render` function accepts additional options to customize the rendering behavior:

```tsx
render(<MyComponent />, {
  initialRoute: '/dashboard', // Initial route path
  useMemoryRouter: true,      // Use MemoryRouter instead of BrowserRouter
  routePath: '/dashboard',    // Route path to render component at
  withoutTheme: false,        // Render without ThemeProvider
  withoutRouter: false,       // Render without Router
  withoutRedux: false,        // Render without Redux Provider
});
```

### API Mocking

Use the MSW server exported from `utils/testServer.ts` for API mocking:

```tsx
import { server, commonHandlers } from '../../../tests/utils/testServer';
import { rest } from 'msw';

// Add custom handlers for this test
beforeAll(() => {
  server.use(
    rest.get('/api/custom-endpoint', (req, res, ctx) => {
      return res(ctx.json({ data: 'mock data' }));
    })
  );
});
```

### Theme Testing

Components that use theme values will automatically get the mock theme. The mock theme should match the structure of the real theme with test-friendly values.

## Converting Existing Tests

1. Replace imports from `@testing-library/react` with imports from `tests/utils/testRender`
2. Remove manual provider wrapping from your tests
3. Use the server from `utils/testServer.ts` instead of creating custom MSW servers

For advanced test setup needs, check the implementation in `utils/testRender.tsx`. 