# Testing Coverage Documentation

## Test Organization

The test suite is organized as follows:

### Frontend Tests

- **Consolidated Tests**: Located in `tests/consolidated/` directory
  - Feature-focused tests covering complete components or features
  - Behavior-driven testing approach
  - Examples:
    - `tests/consolidated/CoreUserJourneys.consolidated.test.tsx` - Core user journeys through the application
    - `tests/consolidated/Authentication.consolidated.test.tsx` - Authentication functionality
    - `tests/consolidated/SecurityAndPerformance.consolidated.test.tsx` - Security and performance

### Backend Tests

The FormIQ application has fully transitioned to a consolidated testing approach. All tests are now organized as follows:

- **Frontend Consolidated Tests**: Located in `/tests/consolidated/*.consolidated.test.(ts|tsx)`. The application has 27 consolidated test files covering all major functionality.
- **Backend Tests**: Located in `backend/tests` with 56 Python test files organized by test type (unit, integration, e2e).

Legacy tests have been **completely removed** as part of the codebase cleanup. All test functionality has been migrated to the consolidated structure.

## Running Tests

To run the consolidated test suite:

```bash
cd frontend
npm run test:consolidated
```

Or use the provided script to run consolidated tests and generate a coverage report:

```bash
./scripts/run-consolidated-tests.sh
```

For test development purposes, you can run a specific test file:

```bash
cd frontend
npm run test:consolidated -- [TestFileName]
```

To generate a coverage report for consolidated tests:

```bash
cd frontend
npm run test:coverage:consolidated
```

## Setting Up the Test Environment

If you encounter dependency issues when running consolidated tests, you can set up the required dependencies:

```bash
cd frontend
npm run test:setup
```

This will install all required testing dependencies including supertest, TensorFlow.js, MSW, and Jest DOM.

## Coverage Audit

FormIQ maintains strict code coverage thresholds to ensure the codebase is adequately tested. We use a coverage budget system to enforce these thresholds.

To run a full coverage audit:

```bash
./scripts/coverage-audit.sh
```

This will:
1. Run all tests with coverage instrumentation
2. Generate detailed HTML, text, and JSON coverage reports
3. Compare coverage results with the thresholds defined in `coverage-budget.json`
4. Identify folders with low coverage
5. Find files that have no test coverage
6. Generate a comprehensive coverage report in Markdown format

### Coverage Thresholds

The coverage thresholds are defined in `coverage-budget.json` and vary by folder type:

| Folder Type | Statements | Branches | Functions | Lines |
|-------------|------------|----------|-----------|-------|
| Global      | 85%        | 75%      | 80%       | 85%   |
| Services    | 90%        | 80%      | 85%       | 90%   |
| Redux       | 90%        | 80%      | 85%       | 90%   |
| Components  | 85%        | 75%      | 80%       | 85%   |
| Hooks       | 90%        | 80%      | 90%       | 90%   |
| Utils       | 95%        | 85%      | 90%       | 95%   |

These thresholds ensure that the critical parts of the application, especially services, hooks, and utilities, have excellent test coverage.

## CI/CD Integration

The coverage audit is integrated into our CI/CD pipeline. For every pull request:

1. All consolidated tests are run
2. A coverage audit is performed
3. Coverage results are attached as an artifact
4. A summary of the coverage report is added as a comment to the PR

This helps reviewers quickly understand the impact of changes on test coverage.

## Known Issues with Consolidated Tests

There are some known issues with the consolidated test suite:

1. React version mismatches that cause "Cannot read properties of undefined (reading 'S')" errors
2. Path resolution problems with module imports
3. Missing dependencies in some test environments

We address these issues with the setupTests.ts configuration. If you encounter test failures, verify you're using the latest version of this file.

## Test Maintenance

As the application evolves, all new features should have corresponding tests added to the consolidated test structure. Follow these guidelines:

1. Create tests in the `tests/consolidated` directory
2. Name files using the `[Feature].consolidated.test.(ts|tsx)` pattern
3. Ensure tests are independent and can run in isolation
4. Mock external dependencies appropriately
5. Verify coverage meets or exceeds the thresholds

There is no longer any need to maintain legacy test files, as they have been removed from the codebase.

## Recent Improvements

* **Removed Legacy Tests**: All legacy tests have been removed from the codebase, reducing complexity and maintenance overhead.
* **Consolidated Test Structure**: The original 247 legacy test files have been consolidated into 27 comprehensive feature-based test files.
* **Enhanced Security Testing**: Created comprehensive security tests covering:
  * HTTP security headers
  * Authentication and authorization controls
  * Rate limiting prevention
  * XSS protection mechanisms
  * Component-level auth guards
* **Performance Testing Integration**: Implemented performance budget testing for:
  * Web Vitals metrics (FCP, LCP, TTI, CLS)
  * Resource size budgets
  * API response times

These improvements have significantly improved test maintainability and execution speed. 