import React from 'react';
import styled from 'styled-components';
import { motion } from 'framer-motion';
import { useTheme } from '../../hooks/useTheme';
import { getThemeValue } from '../../utils/themeUtils';

interface LoadingScreenProps {
  message?: string;
  fullScreen?: boolean;
  ariaLabel?: string;
}

const Container = styled(motion.div)<{ fullScreen: boolean }>`
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: ${({ fullScreen }) => (fullScreen ? '0' : '2rem')};
  min-height: ${({ fullScreen }) => (fullScreen ? '100vh' : '200px')};
  background: ${({ theme, fullScreen }) =>
    fullScreen ? getThemeValue(theme, 'colors.background', '#ffffff') : 'transparent'};
`;

const Spinner = styled(motion.div)`
  width: 40px;
  height: 40px;
  border: 3px solid ${({ theme }) => getThemeValue(theme, 'colors.primary.light', '#e3f2fd')};
  border-top: 3px solid ${({ theme }) => getThemeValue(theme, 'colors.primary.main', '#3f51b5')};
  border-radius: 50%;
  margin-bottom: 1rem;
`;

const Message = styled(motion.p)`
  color: ${({ theme }) => getThemeValue(theme, 'colors.text', '#000000')};
  font-size: 1rem;
  text-align: center;
  max-width: 80%;
`;

const LoadingScreen: React.FC<LoadingScreenProps> = ({
  message = 'Loading...',
  fullScreen = false,
  ariaLabel = 'Loading screen'
}) => {
  return (
    <Container
      fullScreen={fullScreen}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      role="status"
      aria-label={ariaLabel}
      data-testid="loading-screen"
    >
      <Spinner
        animate={{ rotate: 360 }}
        transition={{
          duration: 1,
          repeat: Infinity,
          ease: 'linear',
        }}
        aria-hidden="true"
      />
      <Message
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
      >
        {message}
      </Message>
    </Container>
  );
};

export default LoadingScreen; 