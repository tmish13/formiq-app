# Testing Mock Utilities

This directory contains a collection of shared mock utilities designed to make testing more consistent and efficient. These utilities provide mocks for various parts of the application, allowing tests to focus on behavior rather than implementation details.

## Available Mocks

### Service Mocks (`serviceMocks.ts`)

Mock utilities for services, particularly the PoseAnalysisService:

- `createMockKeypoints()`: Creates a set of mock keypoints for pose detection
- `createMockJointAngles()`: Creates mock joint angles for pose analysis
- `createMockAnalysisResult()`: Creates a complete mock analysis result with keypoints, angles, and feedback
- `createMockPoseAnalysisService()`: Creates a mock implementation of the PoseAnalysisService
- `setupMediaDevicesMock()`: Sets up mocks for the browser's mediaDevices API

### Form Check Mocks (`formCheckMocks.ts`)

Mock utilities for form check operations:

- `createMockFormCheck()`: Creates a single mock form check with default or overridden values
- `createMockFormChecks()`: Creates an array of mock form checks with optional customizations
- `createMockFeedbackItems()`: Creates mock feedback items for form checks
- `createMockFormCheckService()`: Creates a mock implementation of the FormCheckService

### Canvas Mocks (`canvasMocks.ts`)

Utilities for mocking the HTML canvas and file operations:

- `setupCanvasMock()`: Sets up mock for the canvas context, useful for visualization tests
- `createMockFile()`: Creates a mock File object for testing file uploads

### Axios Mocks (`axiosMocks.ts`)

Utilities for creating properly typed Axios errors:

- `createAxiosError()`: Creates a customizable Axios error with proper typing
- `createNetworkError()`: Creates a network error (e.g., no internet connection)
- `createTimeoutError()`: Creates a timeout error
- `createUnauthorizedError()`: Creates a 401 Unauthorized error
- `createForbiddenError()`: Creates a 403 Forbidden error
- `createNotFoundError()`: Creates a 404 Not Found error
- `createCsrfError()`: Creates a 419 CSRF Token Mismatch error
- `createValidationError()`: Creates a 422 Validation Error with customizable validation errors
- `createServerError()`: Creates a 500 Internal Server Error

## Usage Examples

### Using PoseAnalysisService Mock

```typescript
import { render, screen } from '@testing-library/react';
import { createMockPoseAnalysisService, createMockAnalysisResult } from '../tests/mocks';
import PoseAnalysis from './PoseAnalysis';

describe('PoseAnalysis', () => {
  it('shows feedback when analysis results are available', async () => {
    // Create a mock service
    const mockService = createMockPoseAnalysisService();
    
    // Render component with the mock service
    render(<PoseAnalysis service={mockService} />);
    
    // Emit a mock analysis result
    mockService._emitResult(createMockAnalysisResult({
      score: 85,
      feedback: [{ text: 'Good form detected', severity: 'low', type: 'form' }]
    }));
    
    // Check that feedback is displayed
    expect(await screen.findByText('Good form detected')).toBeInTheDocument();
  });
});
```

### Using Form Check Mocks

```typescript
import { render, screen } from '@testing-library/react';
import { createMockFormCheck } from '../tests/mocks';
import FormCheckDetails from './FormCheckDetails';

describe('FormCheckDetails', () => {
  it('displays form check details', () => {
    const mockFormCheck = createMockFormCheck({
      exercise_type: 'squat',
      status: FormCheckStatus.Completed
    });
    
    render(<FormCheckDetails formCheck={mockFormCheck} />);
    
    expect(screen.getByText('squat')).toBeInTheDocument();
    expect(screen.getByText('Completed')).toBeInTheDocument();
  });
});
```

### Using Axios Error Mocks

```typescript
import { createNetworkError, createValidationError } from '../tests/mocks';
import { handleApiError } from '../utils/errorHandling';

describe('Error handling', () => {
  it('handles network errors', () => {
    const error = createNetworkError();
    const result = handleApiError(error);
    
    expect(result.isNetworkError).toBe(true);
    expect(result.message).toContain('network');
  });
  
  it('handles validation errors', () => {
    const validationErrors = {
      email: ['Email is required', 'Email must be valid']
    };
    
    const error = createValidationError(validationErrors);
    const result = handleApiError(error);
    
    expect(result.isValidationError).toBe(true);
    expect(result.validationErrors).toEqual(validationErrors);
  });
});
```

## Best Practices

1. **Prefer behavior-driven testing**: Focus on testing behavior rather than implementation details
2. **Use accessible queries**: Use `getByRole`, `getByLabelText`, etc. instead of direct DOM queries
3. **Clean up after tests**: Use `cleanup()` after tests that modify the DOM
4. **Avoid type assertions**: Create properly typed mocks to avoid type assertions
5. **Keep tests independent**: Each test should be independent and not rely on state from other tests

## Adding New Mocks

When adding new mock utilities:

1. Place them in the appropriate file based on their purpose
2. Document the utility with JSDoc comments
3. Add export to `index.ts`
4. Update this README with usage examples 

## Known Issues and Workarounds

### Styled Components in Tests

When testing components that use styled-components, there can be issues with the mock implementation. If you encounter errors like `styled.div is not a function`, consider these workarounds:

1. **Use direct component mocking**: Instead of trying to mock styled-components, mock the component you're testing and provide a simplified version without styled-components:

```typescript
// Mock the component directly
jest.mock('../ComponentWithStyledComponents', () => {
  const React = require('react');
  
  return {
    __esModule: true,
    default: ({ text, value }) => (
      <div data-testid="mocked-component">
        <div>{text}</div>
        <div>{value}</div>
      </div>
    )
  };
});
```

2. **Create simplified test components**: Create a new component specifically for testing that doesn't use styled-components:

```typescript
// Instead of importing the real component, create a test-only version
const TestFeedback = ({ feedback, score }) => (
  <div data-testid="form-check-feedback">
    <div>Form Check Score: {score}%</div>
    <div>{feedback}</div>
  </div>
);

// Use this in your tests
describe('FeedbackComponent', () => {
  it('displays the feedback', () => {
    render(<TestFeedback feedback="Good job" score={90} />);
    expect(screen.getByText('Good job')).toBeInTheDocument();
  });
});
```

3. **Use separate test files**: If you need to test a component that uses styled-components and can't easily mock it, consider creating a separate test file that uses a different approach (like above).

Remember that the test should focus on behavior and functionality, not implementation details. Using simple HTML elements instead of styled components in tests is often preferable anyway since it keeps tests simpler and more focused. 

## Example Tests

We've created several example tests to demonstrate how to use the mock utilities effectively:

### Using PoseAnalysisService Mock

Location: `frontend/src/tests/examples/UsingMocks.test.tsx`

This example demonstrates how to:
- Create a mock PoseAnalysisService
- Emit mock analysis results
- Test a component that consumes the service
- Verify user-visible feedback based on analysis results

### Axios Error Handling

Location: `frontend/src/tests/examples/AxiosErrorHandling.test.tsx`

This example demonstrates how to:
- Create various types of Axios errors (network, validation, server, auth)
- Test an error handling utility
- Verify error displays in a component based on different error types
- Create a component that properly handles API errors

### Form Check Mocks

Location: `frontend/src/tests/examples/FormCheckMocks.test.tsx`

This example demonstrates how to:
- Create mock form checks with customized properties
- Create and use a mock form check service
- Test CRUD operations on form checks
- Override mock service methods for specific test cases

These examples follow the behavior-driven testing approach, focusing on:
1. User interactions (clicking buttons, entering text)
2. Verifying visible outcomes (displayed text, UI elements)
3. Using accessible queries (getByRole, getByText)
4. Clean separation of concerns 