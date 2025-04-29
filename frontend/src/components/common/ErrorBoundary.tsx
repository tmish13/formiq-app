import React, { Component, ErrorInfo } from 'react';
import styled from 'styled-components';
import { Box, Typography, Button, Stack } from '@mui/material';
import { store } from '../../store';
import { setError } from '../../store/slices/authSlice';
import { errorHandlingService } from '../../services/errorHandlingService';
import { getThemeValue } from '../../utils/themeUtils';

const ErrorContainer = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 400px;
  padding: 2rem;
  text-align: center;
`;

const ErrorTitle = styled.h2`
  color: ${({ theme }) => getThemeValue(theme, 'colors.error.main', '#dc3545')};
  margin-bottom: 1rem;
`;

const ErrorMessage = styled.p`
  color: ${({ theme }) => getThemeValue(theme, 'colors.text.secondary', '#666')};
  margin-bottom: 2rem;
  max-width: 600px;
`;

interface ErrorBoundaryProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void;
  resetOnChange?: number;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null
    };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return {
      hasError: true,
      error,
      errorInfo: null
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    // Call onError prop if provided
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }

    // Log error to error handling service
    errorHandlingService.handleError(error, {
      severity: 'error',
      source: 'client',
      context: {
        component: 'ErrorBoundary',
        componentStack: errorInfo.componentStack
      }
    });

    // Update global error state
    store.dispatch(setError(error.message));

    // Update state with error info
    this.setState({
      errorInfo
    });
  }

  componentDidUpdate(prevProps: ErrorBoundaryProps) {
    // Reset error state when resetOnChange prop changes
    if (this.props.resetOnChange !== prevProps.resetOnChange) {
      this.setState({
        hasError: false,
        error: null,
        errorInfo: null
      });
    }
  }

  handleRetry = (): void => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null
    });
  };

  handleReload = (): void => {
    window.location.reload();
  };

  getUserFriendlyMessage(error: Error | null): string {
    if (!error) return 'An unexpected error occurred.';

    // Map technical errors to user-friendly messages
    const errorMessages: Record<string, string> = {
      NetworkError: 'Unable to connect to the server. Please check your internet connection.',
      TypeError: 'Something went wrong while processing your request.',
      AuthenticationError: 'Your session has expired. Please log in again.',
      ValidationError: 'Please check your input and try again.',
      NotFoundError: 'The requested resource could not be found.',
      default: 'An unexpected error occurred. Please try again.'
    };

    // Check for specific error types
    const errorType = error.name || error.constructor.name;
    return errorMessages[errorType] || errorMessages.default;
  }

  render(): React.ReactNode {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <ErrorContainer>
          <ErrorTitle>Oops! Something went wrong</ErrorTitle>
          <ErrorMessage>
            {this.getUserFriendlyMessage(this.state.error)}
          </ErrorMessage>
          <Stack direction="row" spacing={2}>
            <Button
              variant="contained"
              color="primary"
              onClick={this.handleRetry}
            >
              Try Again
            </Button>
            <Button
              variant="outlined"
              color="primary"
              onClick={this.handleReload}
            >
              Reload Page
            </Button>
          </Stack>
          {process.env.NODE_ENV === 'development' && this.state.error && (
            <Box component="pre" sx={{ mt: 2, p: 2, bgcolor: 'grey.100', borderRadius: 1 }}>
              {this.state.error.message}
            </Box>
          )}
        </ErrorContainer>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary; 