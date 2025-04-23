import React from 'react';
import { Box, CircularProgress } from '@mui/material';
import styled from 'styled-components';

interface LoadingSpinnerProps {
  size?: 'small' | 'medium' | 'large';
  fullPage?: boolean;
}

const SpinnerContainer = styled(Box)<{ $fullPage: boolean }>`
  display: flex;
  justify-content: center;
  align-items: center;
  ${({ $fullPage }) => $fullPage && `
    min-height: 100vh;
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: rgba(255, 255, 255, 0.8);
    z-index: 9999;
  `}
`;

const getSpinnerSize = (size: LoadingSpinnerProps['size']) => {
  switch (size) {
    case 'small': return 24;
    case 'large': return 48;
    default: return 36;
  }
};

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  size = 'medium',
  fullPage = false
}) => {
  return (
    <SpinnerContainer $fullPage={fullPage}>
      <CircularProgress size={getSpinnerSize(size)} />
    </SpinnerContainer>
  );
}; 