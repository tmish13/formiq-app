# MSW Handlers and Shared Mocks for Behavior-Driven Testing

## Summary of Changes

We've successfully enhanced the `tests/utils/sharedMocks.ts` file to include a comprehensive set of MSW handlers and mock generators that support behavior-driven testing across the FormIQ application. These changes enable tests to focus on user behavior rather than implementation details, making tests more maintainable and resilient to refactoring.

## New Types Added

- `Subscription`: Models subscription data with fields for plan details, billing status, and renewal settings
- `SubscriptionPlan`: Defines subscription tier features, pricing, and metadata
- `Video`: Models video content with metadata, processing status, and playback configuration

## New Mock Generators Added

1. **Subscription Mocks**:
   - `createMockSubscription()`: Generates realistic subscription objects
   - `createMockSubscriptionPlan()`: Creates individual subscription plans
   - `createMockSubscriptionPlans()`: Returns an array of tiered plans (Basic, Premium, Annual)

2. **Video Mocks**:
   - `createMockVideo()`: Generates video metadata with playback configuration

## MSW API Handlers Added

### Auth Handlers
- `POST /api/login`: Handles user authentication
  - Returns a JWT token and user data for valid credentials
  - Returns 401 for invalid credentials
- `GET /api/session`: Retrieves current user session
  - Returns authenticated user if token present
  - Returns unauthenticated state otherwise

### Form Check Handlers
- `GET /api/form-checks`: Lists form checks with filtering support
  - Supports query parameters for userId, status, and limit
- `GET /api/form-checks/:id`: Retrieves individual form check details
- `POST /api/form-checks`: Creates new form check submissions
- `DELETE /api/form-checks/:id`: Handles deletion of form checks

### Subscription Handlers
- `GET /api/subscription`: Retrieves current subscription details
- `GET /api/subscription/plans`: Lists available subscription tiers
- `POST /api/subscription/upgrade`: Simulates subscription tier upgrades
- `POST /api/subscription/downgrade`: Handles subscription downgrades

### Video Handlers
- `POST /api/upload`: Processes video uploads
  - Returns processing status and video metadata
- `GET /api/video/:id`: Retrieves video details with playback configuration
  - Simulates different video states (processing, ready, error)

### Error Handling
- Added generic error handler for unmatched requests
  - Returns 500 error with descriptive message
  - Logs unhandled requests to console for debugging

## Enhanced Server Setup

- `setupMockServer()`: Simplified function to create server with provided handlers
- `createTestServer()`: Creates preconfigured server with common handler combinations
  - Added `includeSubscription` option to include subscription handlers
  - Always includes generic error handler for unmatched requests

## Service Mocks Added/Updated

- `mockSubscriptionService`: Mocks for subscription management functions
  - Includes upgrade, downgrade, and cancellation operations
- `mockVideoService`: Consolidated video service mocks
  - Handles upload, playback, and processing operations

## Benefits for Testing

1. **Standardized Testing Setup**: Consistent API mocking across all tests
2. **Reduced Duplication**: Centralized mock data generation eliminates redundant code
3. **Realistic Test Data**: Mock generators create consistent, realistic test fixtures
4. **Isolated Testing**: Tests can focus on UI interactions without backend dependencies
5. **Better Error Handling**: Unmatched requests are caught and reported for debugging

## Usage Examples

### Setting up a test with authentication and form check handlers:

```tsx
import { 
  setupMockServer, 
  setupServerLifecycle,
  authHandlers,
  formCheckHandlers
} from '../utils/sharedMocks';

// Create server with auth and form check handlers
const server = setupMockServer([...authHandlers, ...formCheckHandlers]);

// Set up server lifecycle hooks
setupServerLifecycle(server);
```

### Creating test data with mock generators:

```tsx
import {
  createMockUser,
  createMockFormCheck,
  createMockSubscription
} from '../utils/sharedMocks';

// Create test fixtures
const user = createMockUser({ name: 'Test User' });
const formCheck = createMockFormCheck({ exercise_type: 'squat', score: 95 });
const subscription = createMockSubscription({ status: 'active' });
```

### Using the pre-configured test server:

```tsx
import {
  createTestServer,
  setupServerLifecycle
} from '../utils/sharedMocks';

// Create server with common handlers
const server = createTestServer({
  includeAuth: true,
  includeFormCheck: true,
  includeUpload: true,
  includeSubscription: true
});

// Set up server lifecycle hooks
setupServerLifecycle(server);
```

## Next Steps

1. **Update Existing Tests**: Replace inline mocks and handlers with these centralized utilities
2. **Document Handler Usage**: Add examples to the testing documentation
3. **Expand Coverage**: Add handlers for additional API endpoints as needed
4. **Maintain Test Independence**: Ensure tests properly reset state between runs 