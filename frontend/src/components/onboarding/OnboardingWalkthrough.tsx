import React, { useEffect, useState } from 'react';
import styled from 'styled-components';
import { motion, AnimatePresence } from 'framer-motion';
import { getThemeValue, fallbacks } from '../../utils/themeUtils';

const Overlay = styled(motion.div)`
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.8);
  backdrop-filter: blur(8px);
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
`;

const SlideContainer = styled(motion.div)`
  position: relative;
  width: 90%;
  max-width: 400px;
  background: ${({ theme }) => getThemeValue(theme, 'colors.white', fallbacks.colors.white)};
  border-radius: 16px;
  padding: 32px;
  box-shadow: ${({ theme }) => getThemeValue(theme, 'shadows.lg', fallbacks.shadows.lg)};
`;

const SlideContent = styled.div`
  text-align: center;
`;

const Title = styled(motion.h2)`
  font-size: 24px;
  font-weight: ${({ theme }) => theme?.typography?.fontWeight?.bold || 700};
  margin-bottom: 16px;
  color: ${({ theme }) => getThemeValue(theme, 'colors.text', fallbacks.colors.text)};
`;

const Description = styled(motion.p)`
  font-size: 16px;
  line-height: 1.5;
  color: ${({ theme }) => getThemeValue(theme, 'colors.textSecondary', fallbacks.colors.textSecondary)};
  margin-bottom: 24px;
`;

const ButtonContainer = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 24px;
`;

const Button = styled(motion.button)<{ variant?: 'primary' | 'secondary' }>`
  padding: 12px 24px;
  border-radius: 8px;
  font-weight: ${({ theme }) => theme?.typography?.fontWeight?.medium || 500};
  cursor: pointer;
  border: none;
  background: ${({ theme, variant }) => 
    variant === 'primary' 
      ? getThemeValue(theme, 'colors.primary', fallbacks.colors.primary)
      : 'transparent'};
  color: ${({ theme, variant }) => 
    variant === 'primary'
      ? getThemeValue(theme, 'colors.white', fallbacks.colors.white)
      : getThemeValue(theme, 'colors.textSecondary', fallbacks.colors.textSecondary)};
  
  &:hover {
    opacity: 0.9;
  }
`;

const DotsContainer = styled.div`
  display: flex;
  justify-content: center;
  gap: 8px;
  margin-top: 24px;
`;

const Dot = styled(motion.div)<{ active: boolean }>`
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: ${({ theme, active }) => 
    active 
      ? getThemeValue(theme, 'colors.primary', fallbacks.colors.primary)
      : getThemeValue(theme, 'colors.border', fallbacks.colors.border)};
`;

const slides = [
  {
    id: 1,
    title: "Welcome to FormIQ",
    description: "Your AI-Powered Coach for perfect exercise form and injury prevention.",
  },
  {
    id: 2,
    title: "Track your Form",
    description: "Get real-time feedback on your exercise form and prevent injuries before they happen.",
  },
  {
    id: 3,
    title: "Train Smarter",
    description: "Record and review your movements with instant AI-powered feedback and tips.",
  },
];

interface OnboardingWalkthroughProps {
  onComplete: () => void;
}

export const OnboardingWalkthrough: React.FC<OnboardingWalkthroughProps> = ({ onComplete }) => {
  const [currentSlide, setCurrentSlide] = useState(0);
  const [isVisible, setIsVisible] = useState(true);

  useEffect(() => {
    const hasSeenOnboarding = localStorage.getItem('formiq_onboarding_complete');
    if (hasSeenOnboarding) {
      setIsVisible(false);
    }
  }, []);

  const handleNext = () => {
    if (currentSlide < slides.length - 1) {
      setCurrentSlide(prev => prev + 1);
    } else {
      localStorage.setItem('formiq_onboarding_complete', 'true');
      setIsVisible(false);
      onComplete();
    }
  };

  const handleSkip = () => {
    localStorage.setItem('formiq_onboarding_complete', 'true');
    setIsVisible(false);
    onComplete();
  };

  if (!isVisible) return null;

  return (
    <AnimatePresence>
      <Overlay
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
      >
        <SlideContainer
          initial={{ scale: 0.9, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.9, opacity: 0 }}
          transition={{ type: "spring", damping: 20 }}
        >
          <SlideContent>
            <Title
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.2 }}
            >
              {slides[currentSlide].title}
            </Title>
            <Description
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.3 }}
            >
              {slides[currentSlide].description}
            </Description>
            
            <DotsContainer>
              {slides.map((_, index) => (
                <Dot
                  key={index}
                  active={index === currentSlide}
                  initial={{ scale: 0.8 }}
                  animate={{ scale: index === currentSlide ? 1 : 0.8 }}
                  transition={{ type: "spring", damping: 10 }}
                />
              ))}
            </DotsContainer>

            <ButtonContainer>
              <Button
                variant="secondary"
                onClick={handleSkip}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
              >
                Skip
              </Button>
              <Button
                variant="primary"
                onClick={handleNext}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
              >
                {currentSlide === slides.length - 1 ? 'Get Started' : 'Next'}
              </Button>
            </ButtonContainer>
          </SlideContent>
        </SlideContainer>
      </Overlay>
    </AnimatePresence>
  );
}; 