import React from 'react';
import { Box, Typography, Button, Container } from '@mui/material';

interface ErrorFallbackProps {
  error?: Error;
  resetErrorBoundary: () => void;
}

export const ErrorFallback: React.FC<ErrorFallbackProps> = ({ error, resetErrorBoundary }) => {
  return (
    <Container data-testid="mui-container">
      <Box data-testid="mui-box" display="flex" flexDirection="column" alignItems="center" justifyContent="center" minHeight={200}>
        <Typography variant="h4" gutterBottom data-testid="mui-typography-h4">
          Something went wrong
        </Typography>
        <Typography variant="body1" gutterBottom>
          {error?.message || 'An unexpected error occurred.'}
        </Typography>
        <Button variant="contained" color="primary" onClick={resetErrorBoundary}>
          Try again
        </Button>
        {error?.stack && (
          <Box mt={2}>
            <Typography variant="caption" component="pre">
              {error.stack}
            </Typography>
          </Box>
        )}
      </Box>
    </Container>
  );
}; 