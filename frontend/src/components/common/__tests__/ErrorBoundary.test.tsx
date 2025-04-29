/**
 * @jest-environment jsdom
 */

import '@testing-library/jest-dom';
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import ErrorBoundary from '../ErrorBoundary';

// Mock console.error to avoid test noise
const originalError = console.error;
beforeAll(() => {
  console.error = jest.fn();
});

afterAll(() => {
  console.error = originalError;
});

// Mock errorHandlingService
jest.mock('../../../services/errorHandlingService', () => ({
  errorHandlingService: {
    handleError: jest.fn()
  }
}));

// Mock store
jest.mock('../../../store', () => ({
  store: {
    dispatch: jest.fn()
  }
}));

// Mock setError action
jest.mock('../../../store/slices/authSlice', () => ({
  setError: jest.fn()
}));

// Simple component that doesn't throw an error
const SafeComponent = () => {
  return <div>Test Content</div>;
};

describe('ErrorBoundary', () => {
  it('renders children when there is no error', () => {
    render(
      <ErrorBoundary>
        <SafeComponent />
      </ErrorBoundary>
    );

    expect(screen.getByText('Test Content')).toBeInTheDocument();
  });

  it('has expected error handling methods', () => {
    // For prototype methods
    expect(typeof ErrorBoundary.prototype.componentDidCatch).toBe('function');
    expect(typeof ErrorBoundary.prototype.getUserFriendlyMessage).toBe('function');
    
    // For instance methods (arrow functions are not on the prototype)
    const errorBoundary = new ErrorBoundary({ children: null });
    expect(typeof errorBoundary.handleRetry).toBe('function');
    expect(typeof errorBoundary.handleReload).toBe('function');
  });

  // This test is just a validation that the static method exists
  it('has static getDerivedStateFromError method', () => {
    expect(typeof ErrorBoundary.getDerivedStateFromError).toBe('function');
  });

  it('has componentDidUpdate method for resetting on prop change', () => {
    expect(typeof ErrorBoundary.prototype.componentDidUpdate).toBe('function');
  });
  
  it('has proper render method to display error UI', () => {
    expect(typeof ErrorBoundary.prototype.render).toBe('function');
    
    // Let's validate the render method handles the error state correctly
    const errorBoundary = new ErrorBoundary({ children: null });
    // Manually set the state to simulate an error
    errorBoundary.state = {
      hasError: true,
      error: new Error('Test error'),
      errorInfo: null
    };
    
    // This is a simplified approach to test the logic without trying to render components that throw
    const result = errorBoundary.render();
    
    // Validate the result is a React element when there's an error
    expect(result).toBeTruthy();
  });
  
  it('returns a user-friendly message based on error type', () => {
    const errorBoundary = new ErrorBoundary({ children: null });
    
    // Test with different error types
    const defaultError = new Error('Generic error');
    expect(errorBoundary.getUserFriendlyMessage(defaultError)).toBe('An unexpected error occurred. Please try again.');
    
    const notFoundError = new Error('Not found');
    notFoundError.name = 'NotFoundError';
    expect(errorBoundary.getUserFriendlyMessage(notFoundError)).toBe('The requested resource could not be found.');
    
    const networkError = new Error('Network error');
    networkError.name = 'NetworkError';
    expect(errorBoundary.getUserFriendlyMessage(networkError)).toBe('Unable to connect to the server. Please check your internet connection.');
  });
  
  it('renders custom fallback when provided and an error occurs', () => {
    const errorBoundary = new ErrorBoundary({ 
      children: null,
      fallback: <div>Custom Error UI</div>
    });
    // Manually set the state to simulate an error
    errorBoundary.state = {
      hasError: true,
      error: new Error('Test error'),
      errorInfo: null
    };
    
    const result = errorBoundary.render();
    // With our fallback, the result should match the fallback
    expect(result).toEqual(<div>Custom Error UI</div>);
  });
  
  it('handles error state reset via handleRetry', () => {
    const errorBoundary = new ErrorBoundary({ children: null });
    errorBoundary.state = {
      hasError: true,
      error: new Error('Test error'),
      errorInfo: null
    };
    
    // Create a mock for setState
    errorBoundary.setState = jest.fn();
    
    // Call the retry method
    errorBoundary.handleRetry();
    
    // Verify setState was called with the correct parameters
    expect(errorBoundary.setState).toHaveBeenCalledWith({
      hasError: false,
      error: null,
      errorInfo: null
    });
  });
}); 