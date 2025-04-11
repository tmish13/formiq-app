import React, { useState } from 'react';
import styled from 'styled-components';
import { motion, AnimatePresence } from 'framer-motion';
import { getThemeValue, fallbacks } from '../utils/themeUtils';

interface OnboardingWalkthroughProps {
  onComplete: () => void;
}

const Overlay = styled(motion.div)`
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
`;

const Modal = styled(motion.div)`
  background: ${({ theme }) => getThemeValue(theme, 'colors.white', fallbacks.colors.white)};
  border-radius: ${({ theme }) => theme.borderRadius.large};
  padding: ${({ theme }) => theme.spacing.large};
  max-width: 500px;
  width: 90%;
  position: relative;
`;

const SlideContainer = styled(motion.div)`
  text-align: center;
`;

const Title = styled.h2`
  font-size: ${({ theme }) => theme.typography.fontSize.xlarge};
  color: ${({ theme }) => getThemeValue(theme, 'colors.text', fallbacks.colors.text)};
  margin-bottom: ${({ theme }) => theme.spacing.large};
`;

const Description = styled.p`
  font-size: ${({ theme }) => theme.typography.fontSize.medium};
  color: ${({ theme }) => getThemeValue(theme, 'colors.textSecondary', fallbacks.colors.textSecondary)};
  margin-bottom: ${({ theme }) => theme.spacing.large};
  line-height: 1.6;
`;

const ButtonContainer = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: ${({ theme }) => theme.spacing.large};
`;

const Button = styled(motion.button)<{ variant?: 'primary' | 'secondary' }>`
  padding: ${({ theme }) => `${theme.spacing.small} ${theme.spacing.medium}`};
  border-radius: ${({ theme }) => theme.borderRadius.medium};
  font-size: ${({ theme }) => theme.typography.fontSize.medium};
  font-weight: ${({ theme }) => theme.typography.fontWeight.medium};
  border: none;
  cursor: pointer;
  background: ${({ theme, variant }) =>
    variant === 'primary'
      ? getThemeValue(theme, 'colors.primary', fallbacks.colors.primary)
      : 'transparent'};
  color: ${({ theme, variant }) =>
    variant === 'primary'
      ? getThemeValue(theme, 'colors.white', fallbacks.colors.white)
      : getThemeValue(theme, 'colors.textSecondary', fallbacks.colors.textSecondary)};

  &:hover {
    background: ${({ theme, variant }) =>
      variant === 'primary'
        ? getThemeValue(theme, 'colors.primaryDark', fallbacks.colors.primaryDark)
        : 'rgba(0, 0, 0, 0.05)'};
  }
`;

const ProgressDots = styled.div`
  display: flex;
  justify-content: center;
  gap: ${({ theme }) => theme.spacing.small};
  margin-top: ${({ theme }) => theme.spacing.large};
`;

const Dot = styled.div<{ active: boolean }>`
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: ${({ theme, active }) =>
    active
      ? getThemeValue(theme, 'colors.primary', fallbacks.colors.primary)
      : getThemeValue(theme, 'colors.border', fallbacks.colors.border)};
  transition: background 0.3s ease;
`;

const slides = [
  {
    title: 'Welcome to FormIQ: Your AI-Powered Coach',
    description: 'Get real-time feedback on your exercise form and technique from our advanced AI analysis system.',
  },
  {
    title: 'Track your Form. Prevent Injury. Train Smarter.',
    description: 'Our AI analyzes your movements in real-time to help you maintain proper form and prevent potential injuries.',
  },
  {
    title: 'Record and Review Your Movements. Get Instant Feedback.',
    description: 'Record your exercises and receive immediate, detailed feedback to help you improve your technique.',
  },
];

export const OnboardingWalkthrough: React.FC<OnboardingWalkthroughProps> = ({ onComplete }) => {
  const [currentSlide, setCurrentSlide] = useState(0);

  const handleNext = () => {
    if (currentSlide === slides.length - 1) {
      onComplete();
    } else {
      setCurrentSlide(currentSlide + 1);
    }
  };

  const handleSkip = () => {
    onComplete();
  };

  const slideVariants = {
    enter: {
      x: 300,
      opacity: 0
    },
    center: {
      zIndex: 1,
      x: 0,
      opacity: 1
    },
    exit: {
      zIndex: 0,
      x: -300,
      opacity: 0
    }
  };

  return (
    <Overlay
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
    >
      <Modal
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ type: 'spring', damping: 20, stiffness: 300 }}
      >
        <AnimatePresence mode="wait">
          <SlideContainer
            key={currentSlide}
            variants={slideVariants}
            initial="enter"
            animate="center"
            exit="exit"
            transition={{
              x: { type: "spring", stiffness: 300, damping: 30 },
              opacity: { duration: 0.2 }
            }}
          >
            <Title>{slides[currentSlide].title}</Title>
            <Description>{slides[currentSlide].description}</Description>
          </SlideContainer>
        </AnimatePresence>

        <ProgressDots>
          {slides.map((_, index) => (
            <Dot key={index} active={index === currentSlide} />
          ))}
        </ProgressDots>

        <ButtonContainer>
          <Button onClick={handleSkip}>Skip</Button>
          <Button
            variant="primary"
            onClick={handleNext}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
          >
            {currentSlide === slides.length - 1 ? 'Get Started' : 'Next'}
          </Button>
        </ButtonContainer>
      </Modal>
    </Overlay>
  );
}; 