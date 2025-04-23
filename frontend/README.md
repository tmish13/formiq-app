# FormIQ Frontend

A cross-platform fitness application for workout tracking and form analysis.

## Directory Structure

- `components/` – Reusable UI components
  - `common/` - Common UI components like buttons, inputs, etc.
  - `layout/` - Layout components like header, footer, etc.
  - `auth/` - Authentication-related components
  - `camera/` - Camera and form capture components
  - `**/` - Other feature-specific components

- `contexts/` - React contexts for global state management
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

- `scripts/` - Utility scripts for the project
  - `theme-audit.js` - Script to audit theme usage and fix common issues

## Installation

```bash
# Install dependencies
npm install

# Setup environment for web
cp .env.example .env
```

## Running Locally

```bash
# Start development server
npm run dev

# Run with specific environment
npm run dev:staging
```

## Building for Production

```bash
# Build for web
npm run build

# Build for native platforms
npx cap sync
npx cap open ios     # For iOS
npx cap open android # For Android
```

## Testing

```bash
# Run tests
npm test

# Run tests with coverage
npm run test:coverage
```

## Theme System

FormIQ uses a comprehensive theming system based on styled-components to maintain consistent styling across the application.

### Theme Structure

The theme is defined in `src/theme/theme.ts` with the following key sections:
- `colors` - Color palettes for primary, secondary, error, etc.
- `typography` - Font families, sizes, weights, and line heights
- `spacing` - Consistent spacing scales
- `borderRadius` - Border radius values
- `shadows` - Box shadow definitions
- `breakpoints` - Responsive breakpoints
- `transitions` - Animation timings and easings
- `zIndex` - Z-index hierarchy

### Usage Guidelines

1. Always use theme properties via the `theme` prop in styled-components:
   ```tsx
   const StyledComponent = styled.div`
     color: ${({ theme }) => theme.colors.text.primary};
     font-size: ${({ theme }) => theme.typography.fontSize.md};
   `;
   ```

2. Use the `getThemeValue` utility for fallback support:
   ```tsx
   import { getThemeValue, fallbacks } from '../utils/themeUtils';
   
   const StyledComponent = styled.div`
     color: ${({ theme }) => getThemeValue(theme, 'colors.text.primary', fallbacks.color.text)};
   `;
   ```

3. Always specify variants for colors (main/light/dark/primary/secondary):
   ```tsx
   // Correct
   colors.primary.main
   colors.error.light
   colors.text.secondary
   
   // Incorrect
   colors.primary
   colors.text
   ```

### Theme Audit Tool

We've developed a theme audit tool to help maintain consistency in theme usage:

```bash
# Run theme audit to identify issues
node scripts/theme-audit.js

# Fix automatically fixable issues
node scripts/theme-audit.js --fix
```

The audit tool checks for:
- Incorrect fallbacks references (`fallbacks.colors` vs `fallbacks.color`)
- Typography size format inconsistencies
- Direct color references without variants
- Other theme-related patterns that should be standardized

## CI/CD Pipeline

The project uses GitHub Actions for continuous integration and deployment:

- Linting and type checking
- Unit and integration tests
- Build verification
- Visual regression testing with BackstopJS
- Bundle size analysis
- Automated deployment to staging/production environments

## Best Practices

- Components should be organized by feature or domain
- Use contexts for global state management
- Use hooks for shared logic
- Keep business logic in services
- Use TypeScript types for better type safety
- Keep styling consistent using the theme

This layout ensures separation of concerns and scalable modular design for web and mobile platforms. 