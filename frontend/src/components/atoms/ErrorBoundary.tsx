import React, { Component, ErrorInfo } from 'react';
import { Box, Typography, Button, Stack } from '@mui/material';
import { store } from '../../store';
import { setError } from '../../store/slices/authSlice';

interface Props {
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
  errorInfo?: ErrorInfo;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught error:', error, errorInfo);
    
    // Report to error tracking service
    this.reportError(error, errorInfo);
    
    // Update global error state
    store.dispatch(setError(error.message));
  }

  private reportError = (error: Error, errorInfo: ErrorInfo) => {
    // TODO: Implement error reporting service (e.g., Sentry)
    console.error('Error details:', {
      name: error.name,
      message: error.message,
      stack: error.stack,
      componentStack: errorInfo.componentStack,
    });
  };

  private handleReload = () => {
    window.location.reload();
  };

  private handleReset = () => {
    this.setState({ hasError: false, error: undefined, errorInfo: undefined });
  };

  public render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <Box
          sx={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            minHeight: '100vh',
            p: 3,
            textAlign: 'center',
          }}
        >
          <Typography variant="h4" gutterBottom color="error">
            Oops! Something went wrong
          </Typography>
          
          <Typography variant="body1" color="text.secondary" sx={{ mb: 3, maxWidth: 600 }}>
            We apologize for the inconvenience. An unexpected error has occurred.
            {this.state.error && (
              <Box component="pre" sx={{ mt: 2, p: 2, bgcolor: 'grey.100', borderRadius: 1 }}>
                {this.state.error.message}
              </Box>
            )}
          </Typography>

          <Stack direction="row" spacing={2}>
            <Button
              variant="contained"
              color="primary"
              onClick={this.handleReset}
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
        </Box>
      );
    }

    return this.props.children;
  }
} 