import React, { useState, useEffect } from 'react';
import styled from 'styled-components';
import { motion, AnimatePresence } from 'framer-motion';
import { useSwipeable } from 'react-swipeable';
import { Device } from '@capacitor/device';
import { StatusBar } from '@capacitor/status-bar';
import { SafeArea } from '@capacitor/safe-area';

interface MobileLayoutProps {
  children: React.ReactNode;
  title?: string;
  showBackButton?: boolean;
  onBack?: () => void;
  showMenu?: boolean;
}

const SafeAreaContainer = styled(motion.div)<{ topInset: number; bottomInset: number }>`
  padding-top: ${props => props.topInset}px;
  padding-bottom: ${props => props.bottomInset}px;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: ${({ theme }) => theme.colors.background};
`;

const Header = styled(motion.header)`
  position: sticky;
  top: 0;
  z-index: 100;
  background: ${({ theme }) => theme.colors.surface};
  padding: 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  touch-action: none;
`;

const Title = styled.h1`
  font-size: 20px;
  font-weight: 600;
  margin: 0;
  color: ${({ theme }) => theme.colors.text};
`;

const BackButton = styled(motion.button)`
  background: none;
  border: none;
  padding: 8px;
  margin: -8px;
  cursor: pointer;
  display: flex;
  align-items: center;
  color: ${({ theme }) => theme.colors.primary};
  font-size: 16px;
  
  &:active {
    opacity: 0.7;
  }
`;

const MenuButton = styled(motion.button)`
  background: none;
  border: none;
  padding: 8px;
  margin: -8px;
  cursor: pointer;
  display: flex;
  align-items: center;
  color: ${({ theme }) => theme.colors.text};
`;

const Content = styled(motion.main)`
  flex: 1;
  padding: 16px;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
`;

const Menu = styled(motion.div)`
  position: fixed;
  top: 0;
  right: 0;
  bottom: 0;
  width: 80%;
  max-width: 300px;
  background: ${({ theme }) => theme.colors.surface};
  box-shadow: -2px 0 8px rgba(0, 0, 0, 0.1);
  padding: 16px;
  z-index: 1000;
`;

const Overlay = styled(motion.div)`
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 999;
`;

export const MobileLayout: React.FC<MobileLayoutProps> = ({
  children,
  title,
  showBackButton,
  onBack,
  showMenu
}) => {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [safeAreaInsets, setSafeAreaInsets] = useState({ top: 0, bottom: 0 });
  const [deviceInfo, setDeviceInfo] = useState<any>(null);

  useEffect(() => {
    const initializeLayout = async () => {
      try {
        // Get device info
        const info = await Device.getInfo();
        setDeviceInfo(info);

        // Set status bar style based on platform
        if (info.platform === 'ios') {
          await StatusBar.setStyle({ style: 'dark' });
        }

        // Get safe area insets
        const insets = await SafeArea.getSafeAreaInsets();
        setSafeAreaInsets({
          top: insets.top,
          bottom: insets.bottom
        });
      } catch (error) {
        console.error('Failed to initialize mobile layout:', error);
      }
    };

    initializeLayout();
  }, []);

  const swipeHandlers = useSwipeable({
    onSwipedLeft: () => setIsMenuOpen(false),
    onSwipedRight: () => showMenu && setIsMenuOpen(true),
    trackMouse: true
  });

  const menuVariants = {
    open: {
      x: 0,
      transition: {
        type: 'spring',
        stiffness: 300,
        damping: 30
      }
    },
    closed: {
      x: '100%',
      transition: {
        type: 'spring',
        stiffness: 300,
        damping: 30
      }
    }
  };

  return (
    <SafeAreaContainer
      topInset={safeAreaInsets.top}
      bottomInset={safeAreaInsets.bottom}
      {...swipeHandlers}
    >
      <Header
        initial={false}
        animate={{ y: 0 }}
        transition={{ type: 'spring', stiffness: 300, damping: 30 }}
      >
        {showBackButton && (
          <BackButton
            onClick={onBack}
            whileTap={{ scale: 0.95 }}
            aria-label="Go back"
          >
            ←
          </BackButton>
        )}
        
        <Title>{title}</Title>
        
        {showMenu && (
          <MenuButton
            onClick={() => setIsMenuOpen(true)}
            whileTap={{ scale: 0.95 }}
            aria-label="Open menu"
          >
            ☰
          </MenuButton>
        )}
      </Header>

      <Content
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
      >
        {children}
      </Content>

      <AnimatePresence>
        {isMenuOpen && (
          <>
            <Overlay
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setIsMenuOpen(false)}
            />
            <Menu
              initial="closed"
              animate="open"
              exit="closed"
              variants={menuVariants}
            >
              {/* Menu content goes here */}
            </Menu>
          </>
        )}
      </AnimatePresence>
    </SafeAreaContainer>
  );
}; 