import React, { useEffect } from 'react';
import styled from 'styled-components';
import { motion, AnimatePresence } from 'framer-motion';
import { getThemeValue, fallbacks } from '../../utils/themeUtils';
import { useTheme } from '../../contexts/ThemeContext';

const Container = styled(motion.div)`
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: ${({ theme }) => {
    const isDark = theme.colors.background === getThemeValue({}, 'colors.background', fallbacks.color.background) && 
                  theme.colors.background === '#111827';
    
    return isDark
      ? 'linear-gradient(135deg, #111827 0%, #1F2937 100%)'
      : 'linear-gradient(135deg, #4D7CFE 0%, #3D6CE8 100%)';
  }};
  z-index: 9999;
`;

const Logo = styled(motion.div)`
  width: 120px;
  height: 120px;
  margin-bottom: 24px;
  background-image: url('/logo.svg');
  background-size: contain;
  background-repeat: no-repeat;
  background-position: center;
`;

const LoadingBar = styled(motion.div)`
  width: 200px;
  height: 4px;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 2px;
  overflow: hidden;
`;

const LoadingProgress = styled(motion.div)`
  width: 100%;
  height: 100%;
  background: ${({ theme }) => getThemeValue(theme, 'colors.white', fallbacks.color.white)};
  border-radius: 2px;
`;

const LoadingText = styled(motion.p)`
  margin-top: 16px;
  color: ${({ theme }) => getThemeValue(theme, 'colors.white', fallbacks.color.white)};
  font-size: 14px;
  font-weight: ${({ theme }) => theme?.typography?.fontWeight?.medium || 500};
`;

interface SplashScreenProps {
  onComplete: () => void;
}

export const SplashScreen: React.FC<SplashScreenProps> = ({ onComplete }) => {
  const { theme } = useTheme();
  
  useEffect(() => {
    const timer = setTimeout(() => {
      onComplete();
    }, 2000);

    return () => clearTimeout(timer);
  }, [onComplete]);

  return (
    <AnimatePresence>
      <Container
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.5 }}
      >
        <Logo
          initial={{ scale: 0.5, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{
            type: 'spring',
            stiffness: 200,
            damping: 20,
            delay: 0.2,
          }}
        />
        <LoadingBar>
          <LoadingProgress
            initial={{ x: '-100%' }}
            animate={{ x: 0 }}
            transition={{
              duration: 1.5,
              ease: 'easeInOut',
            }}
          />
        </LoadingBar>
        <LoadingText
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
        >
          Loading FormIQ...
        </LoadingText>
      </Container>
    </AnimatePresence>
  );
}; 