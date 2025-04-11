import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import styled from 'styled-components';
import { useAuth } from '../hooks/useAuth';
import { useTheme } from 'styled-components';
import { Theme } from '../theme';
import { motion } from 'framer-motion';
import { OnboardingWalkthrough } from '../components/OnboardingWalkthrough';

// Styled Components
const HomeContainer = styled(motion.div)`
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: calc(100vh - 64px);
  text-align: center;
  gap: ${({ theme }) => theme.spacing.xl};
  padding: ${({ theme }) => theme.spacing.xl};
  background: ${({ theme }) => theme.colors.background};
`;

const Title = styled(motion.h1)`
  font-size: ${({ theme }) => theme.typography.fontSize.xxl};
  color: ${({ theme }) => theme.colors.text};
  margin-bottom: ${({ theme }) => theme.spacing.md};
`;

const Subtitle = styled(motion.h2)`
  font-size: ${({ theme }) => theme.typography.fontSize.lg};
  color: ${({ theme }) => theme.colors.textSecondary};
  margin-bottom: ${({ theme }) => theme.spacing.xl};
`;

const Button = styled(motion.button)`
  background: ${({ theme }) => theme.colors.primary};
  color: ${({ theme }) => theme.colors.white};
  border: none;
  padding: ${({ theme }) => `${theme.spacing.md} ${theme.spacing.xl}`};
  border-radius: ${({ theme }) => theme.borderRadius.md};
  font-size: ${({ theme }) => theme.typography.fontSize.md};
  font-weight: ${({ theme }) => theme.typography.fontWeight.medium};
  cursor: pointer;
  transition: ${({ theme }) => theme.transitions.medium};
  box-shadow: ${({ theme }) => theme.shadows.md};

  &:hover {
    background: ${({ theme }) => theme.colors.primaryDark};
    transform: translateY(-2px);
  }

  &:active {
    transform: translateY(0);
  }
`;

const StatusBadge = styled(motion.div)<{ status: 'active' | 'inactive' }>`
  background: ${({ theme, status }) =>
    status === 'active' ? theme.colors.successLight : theme.colors.warningLight};
  color: ${({ theme, status }) =>
    status === 'active' ? theme.colors.success : theme.colors.warning};
  padding: ${({ theme }) => `${theme.spacing.xs} ${theme.spacing.md}`};
  border-radius: ${({ theme }) => theme.borderRadius.sm};
  font-size: ${({ theme }) => theme.typography.fontSize.sm};
  margin-bottom: ${({ theme }) => theme.spacing.md};
`;

const DeviceInfo = styled(motion.div)`
  position: absolute;
  top: ${({ theme }) => theme.spacing.md};
  right: ${({ theme }) => theme.spacing.md};
  background: ${({ theme }) => theme.colors.white};
  padding: ${({ theme }) => theme.spacing.sm};
  border-radius: ${({ theme }) => theme.borderRadius.sm};
  box-shadow: ${({ theme }) => theme.shadows.sm};
  font-size: ${({ theme }) => theme.typography.fontSize.sm};
  color: ${({ theme }) => theme.colors.textSecondary};
`;

export function Home() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const theme = useTheme() as Theme;
  const [deviceType, setDeviceType] = useState<'ios' | 'android' | 'web'>('web');
  const [isSessionActive, setIsSessionActive] = useState(false);
  const [showOnboarding, setShowOnboarding] = useState(false);

  useEffect(() => {
    // Detect device type
    const detectDevice = () => {
      const userAgent = navigator.userAgent.toLowerCase();
      if (/iphone|ipad|ipod/.test(userAgent)) {
        setDeviceType('ios');
      } else if (/android/.test(userAgent)) {
        setDeviceType('android');
      } else {
        setDeviceType('web');
      }
    };

    detectDevice();

    // Check for active session
    const checkSession = () => {
      const activeSession = localStorage.getItem('activeSession');
      setIsSessionActive(!!activeSession);
    };

    // Check if onboarding has been shown
    const checkOnboarding = () => {
      const hasSeenOnboarding = localStorage.getItem('hasSeenOnboarding');
      if (!hasSeenOnboarding) {
        setShowOnboarding(true);
      }
    };

    checkSession();
    checkOnboarding();
  }, []);

  const handleOnboardingComplete = () => {
    setShowOnboarding(false);
    localStorage.setItem('hasSeenOnboarding', 'true');
  };

  const containerVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: {
      opacity: 1,
      y: 0,
      transition: {
        duration: 0.6,
        ease: 'easeOut',
      },
    },
  };

  const buttonVariants = {
    hover: { scale: 1.05 },
    tap: { scale: 0.95 },
  };

  return (
    <>
      <HomeContainer
        initial="hidden"
        animate="visible"
        variants={containerVariants}
      >
        <DeviceInfo>
          {deviceType.toUpperCase()} Device
        </DeviceInfo>

        {isSessionActive && (
          <StatusBadge
            status="active"
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
          >
            Active Session
          </StatusBadge>
        )}

        <Title>Welcome to FormIQ</Title>
        <Subtitle>AI-powered fitness form analysis</Subtitle>

        {user ? (
          <Button
            onClick={() => navigate('/form-check')}
            variants={buttonVariants}
            whileHover="hover"
            whileTap="tap"
          >
            Start Form Check
          </Button>
        ) : (
          <Button
            onClick={() => navigate('/login')}
            variants={buttonVariants}
            whileHover="hover"
            whileTap="tap"
          >
            Login to Start
          </Button>
        )}
      </HomeContainer>

      {showOnboarding && (
        <OnboardingWalkthrough onComplete={handleOnboardingComplete} />
      )}
    </>
  );
} 