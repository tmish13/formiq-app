import React, { useState } from 'react';
import styled from 'styled-components';
import { motion, AnimatePresence } from 'framer-motion';
import { getThemeValue, fallbacks } from '../utils/themeUtils';

interface OnboardingWalkthroughProps {
  onComplete: () => void;
}

interface OnboardingSlide {
  title: string;
  description: string;
  icon: string;
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
  background: ${({ theme }) => getThemeValue(theme, 'colors.white', fallbacks.color.white)};
  border-radius: ${({ theme }) => theme.borderRadius.large};
  padding: ${({ theme }) => theme.spacing.large};
  max-width: 600px;
  width: 90%;
  position: relative;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
`;

const SlideContainer = styled(motion.div)`
  text-align: center;
  min-height: 280px;
  display: flex;
  flex-direction: column;
  justify-content: center;
`;

const IconContainer = styled.div`
  font-size: 48px;
  margin-bottom: ${({ theme }) => theme.spacing.medium};
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
`;

const Title = styled.h2`
  font-size: ${({ theme }) => theme.typography.fontSize.xl};
  color: ${({ theme }) => getThemeValue(theme, 'colors.text', fallbacks.color.text)};
  margin-bottom: ${({ theme }) => theme.spacing.medium};
  font-weight: ${({ theme }) => theme.typography.fontWeight.bold};
`;

const Description = styled.p`
  font-size: ${({ theme }) => theme.typography.fontSize.md};
  color: ${({ theme }) => getThemeValue(theme, 'colors.textSecondary', fallbacks.color.textSecondary)};
  margin-bottom: ${({ theme }) => theme.spacing.large};
  line-height: 1.6;
  max-width: 450px;
  margin-left: auto;
  margin-right: auto;
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
  font-size: ${({ theme }) => theme.typography.fontSize.md};
  font-weight: ${({ theme }) => theme.typography.fontWeight.medium};
  border: none;
  cursor: pointer;
  background: ${({ theme, variant }) =>
    variant === 'primary'
      ? getThemeValue(theme, 'colors.primary', fallbacks.color.primary)
      : 'transparent'};
  color: ${({ theme, variant }) =>
    variant === 'primary'
      ? getThemeValue(theme, 'colors.white', fallbacks.color.white)
      : getThemeValue(theme, 'colors.textSecondary', fallbacks.color.textSecondary)};

  &:hover {
    background: ${({ theme, variant }) =>
      variant === 'primary'
        ? getThemeValue(theme, 'colors.primaryDark', fallbacks.color.primaryDark)
        : 'rgba(0, 0, 0, 0.05)'};
  }
`;

const StepCounter = styled.div`
  position: absolute;
  top: ${({ theme }) => theme.spacing.medium};
  right: ${({ theme }) => theme.spacing.medium};
  background: ${({ theme }) => getThemeValue(theme, 'colors.primary', fallbacks.color.primary)};
  color: ${({ theme }) => getThemeValue(theme, 'colors.white', fallbacks.color.white)};
  padding: ${({ theme }) => `${theme.spacing.xs} ${theme.spacing.sm}`};
  border-radius: ${({ theme }) => theme.borderRadius.medium};
  font-size: ${({ theme }) => theme.typography.fontSize.sm};
  font-weight: ${({ theme }) => theme.typography.fontWeight.medium};
`;

const ProgressDots = styled.div`
  display: flex;
  justify-content: center;
  gap: ${({ theme }) => theme.spacing.small};
  margin-top: ${({ theme }) => theme.spacing.large};
`;

const Dot = styled.div<{ active: boolean }>`
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: ${({ theme, active }) =>
    active
      ? getThemeValue(theme, 'colors.primary', fallbacks.color.primary)
      : getThemeValue(theme, 'colors.border', fallbacks.color.border)};
  transition: background 0.3s ease;
  cursor: pointer;
  
  &:hover {
    background: ${({ theme, active }) =>
      active
        ? getThemeValue(theme, 'colors.primary', fallbacks.color.primary)
        : getThemeValue(theme, 'colors.text', fallbacks.color.text)};
  }
`;

const slides: OnboardingSlide[] = [
  {
    title: 'Welcome to FormIQ: Your AI-Powered Exercise Coach',
    description: 'FormIQ uses advanced AI with 33+ keypoint pose detection and machine learning to analyze your exercise form in real-time. Get personalized coaching that helps you train smarter, prevent injuries, and maximize your results.',
    icon: '🤖',
  },
  {
    title: 'Our 10-Step AI Analysis Pipeline',
    description: 'Upload your exercise video → AI processes frames → Detects body keypoints → Calculates joint angles → Analyzes movement patterns → Generates ML scores for posture, stability & depth → Provides personalized feedback.',
    icon: '⚙️',
  },
  {
    title: 'Choose Your Exercise & Record Smart',
    description: 'Select from our comprehensive exercise library including squats, deadlifts, and more. Our AI guides you on optimal camera positioning, lighting, and recording techniques for best analysis results.',
    icon: '📹',
  },
  {
    title: 'Get Detailed ML-Powered Scores',
    description: 'Receive precise scores for Posture (body alignment), Stability (balance & control), and Depth (range of motion). Each score is calculated using advanced machine learning trained on expert movement patterns.',
    icon: '📊',
  },
  {
    title: 'Track Progress & Improve Over Time',
    description: 'Monitor your form improvement with detailed analytics, trend charts, and achievement milestones. See exactly how your technique evolves and where to focus your training efforts.',
    icon: '📈',
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

  const handleDotClick = (index: number) => {
    setCurrentSlide(index);
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
        <StepCounter>
          {currentSlide + 1} of {slides.length}
        </StepCounter>
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
            <IconContainer>{slides[currentSlide].icon}</IconContainer>
            <Title>{slides[currentSlide].title}</Title>
            <Description>{slides[currentSlide].description}</Description>
          </SlideContainer>
        </AnimatePresence>

        <ProgressDots data-testid="progress-dots">
          {slides.map((_, index) => (
            <Dot 
              key={index} 
              active={index === currentSlide}
              onClick={() => handleDotClick(index)}
              data-testid={`progress-dot-${index}`}
            />
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