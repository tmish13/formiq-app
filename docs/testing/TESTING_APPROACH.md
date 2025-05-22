# Testing Approach

This document outlines the FormIQ application's testing strategy, emphasizing behavior-driven testing and consolidated test organization.

## Core Principles

1. **Behavior over Implementation**: Tests focus on user-facing behaviors rather than implementation details.
2. **Consolidation over Fragmentation**: Related tests are grouped into consolidated test files to reduce duplication and improve maintenance.
3. **Integration over Unit**: Prefer testing components with their natural dependencies rather than excessive mocking.
4. **Real User Flows**: End-to-end tests mimic actual user journeys through the application.
5. **Security & Performance**: Beyond functional tests, we include security and performance regression tests.

## Test Organization

Our tests are organized into the following hierarchy:

```
tests/
  ├── consolidated/            # Primary location for consolidated behavioral tests
  │   ├── ComponentName.consolidated.test.tsx
  │   └── ...
  ├── e2e/                     # End-to-end user flow tests
  │   └── EndToEndUserFlows.consolidated.test.tsx
  ├── security/                # Security-specific tests
  │   └── CSPHeaders.test.ts
  ├── utils/                   # Test utilities and helpers
  │   ├── testRender.tsx       # Enhanced render with providers
  │   └── server.ts            # MSW server setup
  └── legacy/                  # Archive of deprecated tests
      └── _archive/            # Tests replaced by consolidated versions
```

## Consolidated Test Files

Our consolidated test files follow a structured pattern:

1. **Grouped by Feature**: Tests are organized by feature or component, not by technical implementation.
2. **Complete Component Coverage**: Each consolidated file covers all behaviors of a component or feature.
3. **MSW for Network Mocking**: We use Mock Service Worker (MSW) to mock API calls.
4. **Real DOM Testing**: We test against a real DOM environment using JSDOM.

## End-to-End Testing

End-to-end tests focus on complete user journeys through the application:

1. **Registration to Form Check Flow**: From user registration to completing a form check and viewing results.
2. **Form Check History Review**: Browsing and filtering form check history.
3. **Profile Update Flow**: Updating user profile information and settings.
4. **Exercise Progression Tracking**: Reviewing progress metrics over time.
5. **Mobile Responsiveness**: Testing responsive behavior on small screens.

## Performance & Security Testing

Beyond functional testing, we include:

1. **Lighthouse CI**: Automatically checking for performance regressions.
2. **CSP Headers**: Verifying security headers are properly configured.
3. **Coverage Thresholds**: Enforcing minimum test coverage requirements.

## Test Utilities

To maintain consistency across tests, we've created reusable utilities:

1. **testRender()**: Enhanced React Testing Library render with full provider setup.
2. **server.ts**: Centralized MSW server configuration for consistent API mocking.
3. **Mock Factory**: Consistent test data generation.

## Maintenance Tools

Scripts to help maintain the test suite:

1. **check-matrix-status.ts**: Validates test status in the functionality matrix.
2. **generate-matrix.ts**: Regenerates the functionality matrix based on actual files.
3. **archive-test-files.sh**: Archives superseded test files.

## Coverage Requirements

We enforce strict coverage requirements to ensure comprehensive testing:

- **Global**: 85% lines, 85% statements, 80% functions, 75% branches
- **Services**: 90% lines, 90% statements, 85% functions, 80% branches
- **Camera Components**: 90% lines, 90% statements, 85% functions, 80% branches
- **Form Components**: 90% lines, 90% statements, 85% functions, 80% branches
- **Redux Store**: 90% lines, 90% statements, 85% functions, 80% branches

## Test-Driven Development Workflow

When adding new features:

1. Create or update the consolidated test file for the feature.
2. Write tests for the new behavior before implementing.
3. Implement the feature until tests pass.
4. Update the test matrix to reflect the new feature.

## Running Tests

```bash
# Run all tests
npm test

# Run with coverage reporting
npm run test:coverage

# Run E2E tests
npm run test:e2e

# Run security tests
npx jest tests/security

# Check lighthouse performance
npx @lhci/cli autorun --budget.path=./lighthouse/budgets.json
```

## Code Quality Tools

### Snapshot Testing

FormIQ uses Jest snapshot testing to verify UI component rendering and prevent unintended visual regressions. Snapshots capture a component's rendered output and compare it against a saved reference version in future test runs.

When making intentional UI changes, snapshots need to be updated. We've created several tools to simplify this process:

```bash
# Update all snapshots
npm test -- -u

# Update snapshots for specific components
npm test -- -u FormAnalysis.consolidated.test.tsx

# Use the snapshot update script to propagate changes to consolidated tests
./scripts/update-snapshots.sh
```

The `update-snapshots.sh` script handles both updating snapshots and ensuring they're properly copied to the consolidated test directories.

### Linting and Type Checking

FormIQ maintains strict code quality standards through ESLint and TypeScript:

```bash
# Run the linter
npm run lint

# Run TypeScript type checking
npm run typecheck
```

These checks are integrated into our CI pipeline to ensure code quality is maintained. The configuration files are:

- `.eslintrc.js` - ESLint configuration
- `tsconfig.json` - TypeScript configuration

### CI Integration

The GitHub Actions workflow automatically runs these checks on pull requests and commits. It includes:

1. Linting the codebase
2. TypeScript type checking
3. Running tests and verifying coverage
4. Updating snapshots when merging to main

## Testing Matrix

```bash
# Run all tests
npm test

# Run with coverage reporting
npm run test:coverage

# Run E2E tests
npm run test:e2e

# Run security tests
npx jest tests/security

# Check lighthouse performance
npx @lhci/cli autorun --budget.path=./lighthouse/budgets.json
``` 