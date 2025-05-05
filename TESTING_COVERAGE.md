## Running Tests

To run the full test suite:

```bash
cd frontend
npm test
```

To run only consolidated tests:

```bash
cd frontend
npm run test:consolidated
```

Or use the provided script to run consolidated tests and generate a coverage report:

```bash
./scripts/run-consolidated-tests.sh
```

To update snapshots:

```bash
./scripts/update-snapshots.sh
```

## Ensuring Proper Test Structure

To verify that all tests are properly structured and follow the consolidated pattern:

```bash
./scripts/verify-test-structure.sh
```

This will:
1. Count the number of tests in various locations
2. Verify that consolidated tests follow the proper naming pattern
3. Check for the existence of a snapshots directory
4. Provide a summary of the test structure

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

1. All tests are run including consolidated tests
2. A coverage audit is performed
3. Coverage results are attached as an artifact
4. A summary of the coverage report is added as a comment to the PR

This helps reviewers quickly understand the impact of changes on test coverage. 