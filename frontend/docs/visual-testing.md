# Visual Regression Testing Guide

This guide explains how to run and maintain visual regression tests using BackstopJS for the FormIQ frontend.

## Prerequisites

1. Install BackstopJS globally:
   ```bash
   npm install -g backstopjs
   ```

2. Ensure your development server is running:
   ```bash
   npm run dev
   ```

## Running Visual Tests

Run the following commands from the `frontend` directory:

### 1. Run Tests Against Reference Images

```bash
npm run test:backstop
```

This will:
- Launch browsers to capture screenshots of the app
- Compare them against previously approved reference images
- Generate a visual report of differences

### 2. Approve Changes

After verifying that the visual changes are expected and correct:

```bash
npm run test:backstop:approve
```

This will update the reference images with the current state of the app.

### 3. Create New Reference Images

When adding new components or pages:

```bash
npm run test:backstop:reference
```

## Viewport Configurations

Our visual tests run against these viewport sizes:

1. iPhone 13 Pro (390 × 844)
2. Pixel 6 (393 × 851)
3. iPad Pro (1024 × 1366)
4. Desktop (1280 × 800)

## Test Coverage

The following screens are covered by visual regression tests:

1. Login screen
2. Dashboard
3. Workout tracking flow
4. Form analysis results
5. Progress visualization
6. Settings pages

## After Theme Changes

When making theme-related changes:

1. Run the normal visual test:
   ```bash
   npm run test:backstop
   ```

2. Review the differences in the generated report (opens automatically in your browser)

3. Check for:
   - Spacing consistency
   - Color application
   - Typography changes
   - Component sizing
   - Cross-device rendering

4. If all changes are approved, update the reference:
   ```bash
   npm run test:backstop:approve
   ```

5. Commit the updated reference images:
   ```bash
   git add test/backstop/reference
   git commit -m "test(backstop): update visual baselines after theme improvements"
   ```

## Handling Failures

If visual tests are failing but the differences are expected:

1. Review the report in detail
2. Validate that the new visuals match the design requirements
3. Update references with the approve command
4. Document why the visual change was necessary

If the changes are unexpected:

1. Check your theme-related changes
2. Look for unintended style overrides
3. Verify theme token usage
4. Fix issues and rerun tests

## Integration with CI

The GitHub Actions workflow checks visual regression on PRs. If your visual changes are intentional:

1. Run approve locally
2. Commit the new reference images
3. Push to your branch

This will ensure CI passes with your intended visual changes. 