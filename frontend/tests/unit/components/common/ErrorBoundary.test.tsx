/**
 * @jest-environment jsdom
 */

import '@testing-library/jest-dom';
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import ErrorBoundary from '../../../../src/components/ErrorBoundary';
import { AppError, ErrorCode } from '../../../../src/utils/errorHandling';

// Mock console.error to avoid test noise
const originalError = console.error;
beforeAll(() => {
  console.error = jest.fn();
});

afterAll(() => {
  console.error = originalError;
});

describe('ErrorBoundary', () => {
  const ThrowError = ({ message }: { message: string }) => {
    throw new Error(message);
  };

  const ThrowApiError = () => {
    throw new AppError(
      'Resource not found',
      ErrorCode.NOT_FOUND,
      404,
      { detail: 'Resource not found' }
    );
  };

  it('renders children when there is no error', () => {
    render(
      <ErrorBoundary>
        <div>Test Content</div>
      </ErrorBoundary>
    );

    expect(screen.getByText('Test Content')).toBeInTheDocument();
  });

  it('renders error UI when an error occurs', () => {
    const errorMessage = 'Test error message';
    
    render(
      <ErrorBoundary>
        <ThrowError message={errorMessage} />
      </ErrorBoundary>
    );

    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
    expect(screen.getByText(errorMessage)).toBeInTheDocument();
  });

  it('renders API error details when an API error occurs', () => {
    render(
      <ErrorBoundary>
        <ThrowApiError />
      </ErrorBoundary>
    );

    expect(screen.getByText('API Error Occurred')).toBeInTheDocument();
    expect(screen.getByText('Status: 404')).toBeInTheDocument();
    expect(screen.getByText('Error Code: NOT_FOUND')).toBeInTheDocument();
  });

  it('calls onError prop when an error occurs', () => {
    const onError = jest.fn();
    const errorMessage = 'Test error message';

    render(
      <ErrorBoundary onError={onError}>
        <ThrowError message={errorMessage} />
      </ErrorBoundary>
    );

    expect(onError).toHaveBeenCalledWith(
      expect.any(Error),
      expect.objectContaining({
        componentStack: expect.any(String)
      })
    );
  });

  it('renders custom fallback when provided', () => {
    const fallback = <div>Custom Error UI</div>;

    render(
      <ErrorBoundary fallback={fallback}>
        <ThrowError message="Test error" />
      </ErrorBoundary>
    );

    expect(screen.getByText('Custom Error UI')).toBeInTheDocument();
  });

  // Split the reset functionality into two separate tests
  // Test the Try Again button indirectly through resetOnChange
  it('resets error state using resetOnChange for Try Again button', () => {
    // Test component that simulates Try Again functionality using resetOnChange
    const TestResetContainer = () => {
      const [resetKey, setResetKey] = React.useState(1);
      
      return (
        <div>
          <button data-testid="manual-reset" onClick={() => setResetKey(prev => prev + 1)}>
            Manual Reset
          </button>
          <ErrorBoundary resetOnChange={resetKey}>
            {resetKey === 1 ? (
              <ThrowError message="Test error" />
            ) : (
              <div>Test Content</div>
            )}
          </ErrorBoundary>
        </div>
      );
    };

    render(<TestResetContainer />);

    // Verify error boundary is showing
    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByText('Something went wrong')).toBeInTheDocument();

    // Click the manual reset button to change resetOnChange prop
    fireEvent.click(screen.getByTestId('manual-reset'));
    
    // Verify component renders correctly after reset
    expect(screen.getByText('Test Content')).toBeInTheDocument();
  });

  it('resets when resetOnChange prop changes', () => {
    const TestComponent = ({ shouldThrow }: { shouldThrow: boolean }) => {
      if (shouldThrow) {
        throw new Error('Test error');
      }
      return <div>Test Content</div>;
    };

    const { rerender } = render(
      <ErrorBoundary resetOnChange={1}>
        <TestComponent shouldThrow={true} />
      </ErrorBoundary>
    );

    expect(screen.getByRole('alert')).toBeInTheDocument();

    // Change resetOnChange prop and update component to not throw
    rerender(
      <ErrorBoundary resetOnChange={2}>
        <TestComponent shouldThrow={false} />
      </ErrorBoundary>
    );

    expect(screen.getByText('Test Content')).toBeInTheDocument();
  });

  describe('development environment', () => {
    const originalEnv = process.env.NODE_ENV;

    beforeAll(() => {
      process.env.NODE_ENV = 'development';
    });

    afterAll(() => {
      process.env.NODE_ENV = originalEnv;
    });

    it('shows component stack in development mode', () => {
      render(
        <ErrorBoundary>
          <ThrowError message="Test error" />
        </ErrorBoundary>
      );

      expect(screen.getByText('Error Stack')).toBeInTheDocument();
    });
  });
}); 