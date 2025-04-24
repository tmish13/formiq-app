import React from 'react';
import { CircularProgress, Box } from '@mui/material';

interface LoadingSpinnerProps {
  ariaLabel?: string;
}

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({ ariaLabel = 'Loading' }) => {
  return (
    <Box display="flex" justifyContent="center" alignItems="center">
      <CircularProgress role="progressbar" aria-label={ariaLabel} />
    </Box>
  );
}; 