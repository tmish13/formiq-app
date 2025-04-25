import React from 'react';
import styled from 'styled-components';

interface LoadingSpinnerProps {
  size?: string;
  dataTestId?: string;
}

const SpinnerContainer = styled.div<{ size: string }>`
  display: flex;
  justify-content: center;
  align-items: center;
  width: ${props => props.size};
  height: ${props => props.size};
`;

const Spinner = styled.div`
  border: 4px solid ${props => props.theme.colors.gray.light};
  border-left-color: ${props => props.theme.colors.primary.main};
  border-radius: 50%;
  width: 100%;
  height: 100%;
  animation: spin 1s linear infinite;

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }
`;

const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({ size = '40px', dataTestId = 'loading-spinner' }) => {
  return (
    <SpinnerContainer size={size} data-testid={dataTestId} role="status">
      <Spinner />
    </SpinnerContainer>
  );
};

export default LoadingSpinner; 