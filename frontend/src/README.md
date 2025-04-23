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