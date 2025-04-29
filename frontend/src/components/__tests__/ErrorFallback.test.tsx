import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ErrorFallback } from '../common/ErrorFallback';

// Mock Material UI components
jest.mock('@mui/material', () => ({
  Box: (props: any) => <div data-testid="mui-box" {...props} />,
  Typography: (props: any) => (
    <div 
      data-testid={`mui-typography-${props.variant || 'default'}`} 
      {...props}
    >
      {props.children}
    </div>
  ),
  Button: (props: any) => (
    <button 
      data-testid="mui-button" 
      onClick={props.onClick}
      {...props}
    >
      {props.children}
    </button>
  ),
  Container: (props: any) => <div data-testid="mui-container" {...props} />
}));

describe('ErrorFallback Component', () => {
  const mockError = new Error('Test error message');
  const mockResetErrorBoundary = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders the error message correctly', () => {
    render(
      <ErrorFallback 
        error={mockError}
        resetErrorBoundary={mockResetErrorBoundary}
      />
    );

    // Check the title is rendered
    expect(screen.getByTestId('mui-typography-h4')).toHaveTextContent('Something went wrong');
    
    // Check the error message is rendered
    expect(screen.getByText('Test error message')).toBeInTheDocument();
    
    // Check the retry button is rendered
    expect(screen.getByText('Try again')).toBeInTheDocument();
  });

  it('calls resetErrorBoundary when clicking the retry button', () => {
    render(
      <ErrorFallback 
        error={mockError}
        resetErrorBoundary={mockResetErrorBoundary}
      />
    );

    // Click the retry button
    const retryButton = screen.getByText('Try again');
    fireEvent.click(retryButton);

    // Check if resetErrorBoundary was called
    expect(mockResetErrorBoundary).toHaveBeenCalledTimes(1);
  });

  it('handles error with stack trace', () => {
    // Create an error with a stack trace
    const errorWithStack = new Error('Error with stack');
    errorWithStack.stack = 'Error: Error with stack\n    at Component (component.tsx:10:10)';

    render(
      <ErrorFallback 
        error={errorWithStack}
        resetErrorBoundary={mockResetErrorBoundary}
      />
    );

    // Check the error message is rendered correctly
    expect(screen.getByText('Error with stack')).toBeInTheDocument();
  });

  it('renders within a container with proper styling', () => {
    render(
      <ErrorFallback 
        error={mockError}
        resetErrorBoundary={mockResetErrorBoundary}
      />
    );

    // Check container exists
    const container = screen.getByTestId('mui-container');
    expect(container).toBeInTheDocument();

    // Check box with flex styling exists
    const box = screen.getByTestId('mui-box');
    expect(box).toBeInTheDocument();
  });

  it('handles an error without a message', () => {
    // Create an error without a message
    const emptyError = new Error();

    render(
      <ErrorFallback 
        error={emptyError}
        resetErrorBoundary={mockResetErrorBoundary}
      />
    );

    // Even with an empty error message, component should still render
    expect(screen.getByTestId('mui-typography-h4')).toHaveTextContent('Something went wrong');
    expect(screen.getByText('Try again')).toBeInTheDocument();
  });
}); 