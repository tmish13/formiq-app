import React from 'react';
import styled, { keyframes } from 'styled-components';

interface LoadingSpinnerProps {
  size?: 'small' | 'medium' | 'large';
  color?: string;
  isFullPage?: boolean;
  text?: string;
  ariaLabel?: string;
}

const spin = keyframes`
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
`;

const LoadingText = styled.div`
  margin-top: 1rem;
  color: ${({ theme }) => theme.colors.text};
  font-size: 1rem;
  text-align: center;
`;

const Container = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
`;

const FullPageLoader = styled.div`
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: ${({ theme }) => theme.colors.background};
  z-index: 9999;
`;

const SpinnerWrapper = styled.div<{ size: LoadingSpinnerProps['size'] }>`
  width: ${({ size }) => {
    switch (size) {
      case 'small': return '24px';
      case 'large': return '48px';
      default: return '32px';
    }
  }};
  height: ${({ size }) => {
    switch (size) {
      case 'small': return '24px';
      case 'large': return '48px';
      default: return '32px';
    }
  }};
  position: relative;
`;

const Spinner = styled.div<{ $color?: string }>`
  width: 100%;
  height: 100%;
  border: 3px solid ${({ theme }) => theme.colors.background};
  border-top: 3px solid ${({ $color, theme }) => $color || theme.colors.primary};
  border-radius: 50%;
  animation: ${spin} 1s linear infinite;
`;

const LoadingSpinner: React.FC<LoadingSpinnerProps> = React.memo(({
  size = 'medium',
  color,
  isFullPage = false,
  text,
  ariaLabel = 'Loading...'
}) => {
  const spinner = (
    <Container>
      <SpinnerWrapper size={size}>
        <Spinner $color={color} role="progressbar" aria-label={ariaLabel} />
      </SpinnerWrapper>
      {text && <LoadingText>{text}</LoadingText>}
    </Container>
  );

  if (isFullPage) {
    return <FullPageLoader>{spinner}</FullPageLoader>;
  }

  return spinner;
});

LoadingSpinner.displayName = 'LoadingSpinner';

export { LoadingSpinner }; 