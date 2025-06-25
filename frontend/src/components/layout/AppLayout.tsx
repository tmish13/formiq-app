import React, { useState, useEffect, ReactNode } from 'react';
import { Link, useLocation } from 'react-router-dom';
import styled from 'styled-components';
import { useAuth } from '../../hooks/useAuth';
import { getThemeValue } from '../../utils/themeUtils';
import { Header, HeaderContent } from './Header';
import { errorHandlingService } from '../../services/errorHandlingService';
import { Snackbar, Alert } from '@mui/material';
import { MobileNavigation } from '../organisms/MobileNavigation';

// Commenting out these imports until they are properly implemented
// import { Footer } from './Footer';
// import { Sidebar } from './Sidebar';

const Container = styled.div<{ hasHeader: boolean }>`
  min-height: 100vh;
  display: flex;
  flex-direction: column;

  @media (min-width: ${({ theme }) => getThemeValue(theme, 'breakpoints.md', '769px')}) {
    padding-top: ${({ hasHeader }) => (hasHeader ? '64px' : '0')};
  }

  @media (max-width: ${({ theme }) => getThemeValue(theme, 'breakpoints.md', '768px')}) {
    padding-top: ${({ hasHeader }) => (hasHeader ? '56px' : '0')};
  }
`;

const Main = styled.main<{ hasHeader: boolean }>`
  flex: 1;
  display: flex;
  flex-direction: column;

  @media (min-width: ${({ theme }) => getThemeValue(theme, 'breakpoints.md', '769px')}) {
    min-height: calc(100vh - 64px);
  }

  @media (max-width: ${({ theme }) => getThemeValue(theme, 'breakpoints.md', '768px')}) {
    min-height: calc(100vh - 56px);
  }
`;

const ContentWrapper = styled.div<{ hasSidebar: boolean }>`
  display: flex;
  min-height: calc(100vh - 64px);
  
  @media (max-width: ${({ theme }) => getThemeValue(theme, 'breakpoints.sm', '576px')}) {
    min-height: calc(100vh - 56px);
    flex-direction: column;
  }
`;

const MainContent = styled.main<{ hasSidebar: boolean; hasFooter: boolean }>`
  flex: 1;
  background-color: ${({ theme }) => getThemeValue(theme, 'colors.background.main', '#F7FAFC')};
  padding: ${({ theme }) => getThemeValue(theme, 'spacing.lg', '1.5rem')};
  transition: padding ${({ theme }) => getThemeValue(theme, 'transitions.duration.medium', '0.3s')} ${({ theme }) => getThemeValue(theme, 'transitions.easing.easeInOut', 'cubic-bezier(0.4, 0, 0.2, 1)')};
  padding-bottom: ${({ hasFooter }) => (hasFooter ? '80px' : '1.5rem')};
  
  @media (max-width: ${({ theme }) => getThemeValue(theme, 'breakpoints.sm', '576px')}) {
    padding: ${({ theme }) => getThemeValue(theme, 'spacing.md', '1rem')};
    padding-bottom: ${({ hasFooter }) => (hasFooter ? '60px' : '1rem')};
  }
`;

const Logo = styled(Link)`
  display: flex;
  align-items: center;
  gap: ${({ theme }) => getThemeValue(theme, 'spacing.sm', '8px')};
  text-decoration: none;
  color: ${({ theme }) => getThemeValue(theme, 'colors.text.primary', '#000000')};
  font-weight: ${({ theme }) => getThemeValue(theme, 'typography.fontWeight.bold', '700')};
  font-size: ${({ theme }) => getThemeValue(theme, 'typography.fontSize.lg', '20px')};
`;

const Nav = styled.nav<{ isOpen: boolean }>`
  display: flex;
  gap: ${({ theme }) => getThemeValue(theme, 'spacing.md', '16px')};

  @media (max-width: ${({ theme }) => getThemeValue(theme, 'breakpoints.md', '768px')}) {
    display: ${({ isOpen }) => (isOpen ? 'flex' : 'none')};
    position: fixed;
    top: 56px;
    left: 0;
    right: 0;
    background-color: ${({ theme }) => getThemeValue(theme, 'colors.background.paper', '#FFFFFF')};
    flex-direction: column;
    padding: ${({ theme }) => getThemeValue(theme, 'spacing.md', '16px')};
    box-shadow: ${({ theme }) => getThemeValue(theme, 'shadows.medium', '0 4px 8px rgba(0, 0, 0, 0.1)')};
  }
`;

const NavLink = styled(Link)<{ active: boolean }>`
  color: ${({ theme, active }) =>
    active
      ? getThemeValue(theme, 'colors.primary.main', '#3f51b5')
      : getThemeValue(theme, 'colors.text.primary', '#000000')};
  text-decoration: none;
  font-weight: ${({ theme, active }) =>
    active
      ? getThemeValue(theme, 'typography.fontWeight.medium', '500')
      : getThemeValue(theme, 'typography.fontWeight.regular', '400')};
  padding: ${({ theme }) => getThemeValue(theme, 'spacing.sm', '8px')};
  border-radius: ${({ theme }) => getThemeValue(theme, 'borderRadius.sm', '4px')};
  transition: all ${({ theme }) => getThemeValue(theme, 'transitions.duration.short', '0.2s')} ${({ theme }) => getThemeValue(theme, 'transitions.easing.easeInOut', 'cubic-bezier(0.4, 0, 0.2, 1)')};

  &:hover {
    background-color: ${({ theme }) => getThemeValue(theme, 'colors.background.secondary', '#F2F2F7')};
  }
`;

const UserMenu = styled.div`
  position: relative;
  
  @media (max-width: ${({ theme }) => getThemeValue(theme, 'breakpoints.md', '768px')}) {
    margin-left: auto;
  }
`;

const UserButton = styled.button`
  display: flex;
  align-items: center;
  gap: ${({ theme }) => getThemeValue(theme, 'spacing.sm', '0.75rem')};
  background: none;
  border: none;
  padding: ${({ theme }) => getThemeValue(theme, 'spacing.sm', '0.75rem')} ${({ theme }) => getThemeValue(theme, 'spacing.md', '1rem')};
  cursor: pointer;
  color: ${({ theme }) => getThemeValue(theme, 'colors.text.primary', '#2D3748')};
  font-weight: ${({ theme }) => getThemeValue(theme, 'typography.fontWeight.medium', '500')};
  min-width: 44px;
  min-height: 44px;
  
  @media (max-width: ${({ theme }) => getThemeValue(theme, 'breakpoints.sm', '576px')}) {
    padding: ${({ theme }) => getThemeValue(theme, 'spacing.sm', '0.75rem')};
  }
`;

const DropdownMenu = styled.div<{ isOpen: boolean }>`
  position: absolute;
  top: 100%;
  right: 0;
  background-color: ${({ theme }) => getThemeValue(theme, 'colors.background.paper', '#FFFFFF')};
  border-radius: ${({ theme }) => getThemeValue(theme, 'borderRadius.md', '0.5rem')};
  box-shadow: ${({ theme }) => getThemeValue(theme, 'shadows.medium', '0 4px 6px rgba(0,0,0,0.1)')};
  min-width: 200px;
  display: ${({ isOpen }) => (isOpen ? 'block' : 'none')};
  margin-top: ${({ theme }) => getThemeValue(theme, 'spacing.xs', '0.5rem')};
  z-index: ${({ theme }) => getThemeValue(theme, 'zIndex.dropdown', '1001')};
  
  @media (max-width: ${({ theme }) => getThemeValue(theme, 'breakpoints.sm', '576px')}) {
    position: fixed;
    top: 56px;
    right: 0;
    width: 100%;
    border-radius: 0;
    margin-top: 0;
  }
`;

const DropdownItem = styled(Link)`
  display: block;
  padding: ${({ theme }) => getThemeValue(theme, 'spacing.sm', '0.75rem')} ${({ theme }) => getThemeValue(theme, 'spacing.md', '1rem')};
  color: ${({ theme }) => getThemeValue(theme, 'colors.text.primary', '#2D3748')};
  text-decoration: none;
  transition: all ${({ theme }) => getThemeValue(theme, 'transitions.duration.short', '0.2s')} ${({ theme }) => getThemeValue(theme, 'transitions.easing.easeInOut', 'cubic-bezier(0.4, 0, 0.2, 1)')};
  min-height: 44px;
  display: flex;
  align-items: center;

  &:hover {
    background-color: ${({ theme }) => getThemeValue(theme, 'colors.primary.light', '#7986cb')}20;
    color: ${({ theme }) => getThemeValue(theme, 'colors.primary.main', '#3f51b5')};
  }
  
  @media (max-width: ${({ theme }) => getThemeValue(theme, 'breakpoints.sm', '576px')}) {
    padding: ${({ theme }) => getThemeValue(theme, 'spacing.md', '1rem')};
    font-size: ${({ theme }) => getThemeValue(theme, 'typography.fontSize.md', '1rem')};
  }
`;

const LogoutButton = styled.button`
  display: block;
  width: 100%;
  padding: ${({ theme }) => getThemeValue(theme, 'spacing.sm', '0.75rem')} ${({ theme }) => getThemeValue(theme, 'spacing.md', '1rem')};
  background: none;
  border: none;
  color: ${({ theme }) => getThemeValue(theme, 'colors.error.main', '#f44336')};
  text-align: left;
  cursor: pointer;
  transition: all ${({ theme }) => getThemeValue(theme, 'transitions.duration.short', '0.2s')} ${({ theme }) => getThemeValue(theme, 'transitions.easing.easeInOut', 'cubic-bezier(0.4, 0, 0.2, 1)')};
  min-height: 44px;
  font-weight: ${({ theme }) => getThemeValue(theme, 'typography.fontWeight.regular', '400')};

  &:hover {
    background-color: ${({ theme }) => getThemeValue(theme, 'colors.error.light', '#e57373')}10;
  }
  
  @media (max-width: ${({ theme }) => getThemeValue(theme, 'breakpoints.sm', '576px')}) {
    padding: ${({ theme }) => getThemeValue(theme, 'spacing.md', '1rem')};
    font-size: ${({ theme }) => getThemeValue(theme, 'typography.fontSize.md', '1rem')};
  }
`;

const HamburgerButton = styled.button`
  display: none;
  background: none;
  border: none;
  padding: ${({ theme }) => getThemeValue(theme, 'spacing.sm', '8px')};
  cursor: pointer;

  @media (max-width: ${({ theme }) => getThemeValue(theme, 'breakpoints.md', '768px')}) {
    display: block;
  }

  svg {
    width: 24px;
    height: 24px;
    stroke: ${({ theme }) => getThemeValue(theme, 'colors.text.primary', '#000000')};
  }
`;

const Overlay = styled.div<{ show: boolean }>`
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: ${({ theme }) => getThemeValue(theme, 'colors.background.overlay', 'rgba(0, 0, 0, 0.5)')};
  z-index: ${({ theme }) => getThemeValue(theme, 'zIndex.overlay', '998')};
  display: ${({ show }) => (show ? 'block' : 'none')};
`;

interface ErrorToast {
  message: string;
  severity: 'error' | 'warning' | 'info';
}

interface AppLayoutProps {
  children: ReactNode;
  hasHeader?: boolean;
  hasFooter?: boolean;
  hasSidebar?: boolean;
}

export const AppLayout: React.FC<AppLayoutProps> = ({ children, hasHeader = true, hasFooter = true, hasSidebar = false }) => {
  const location = useLocation();
  const { user, logout, isAuthenticated } = useAuth();
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [isMobileNavOpen, setIsMobileNavOpen] = useState(false);
  const [errorToast, setErrorToast] = useState<ErrorToast | null>(null);

  // Check if we're on an auth page (login or register)
  const isAuthPage = location.pathname === '/login' || location.pathname === '/register';
  
  // Only show header if authenticated and not on auth pages
  const showHeader = isAuthenticated && !isAuthPage;

  const handleLogout = async () => {
    await logout();
    setIsMenuOpen(false);
  };
  
  // Close mobile nav when changing routes
  useEffect(() => {
    setIsMobileNavOpen(false);
    setIsMenuOpen(false);
  }, [location.pathname]);
  
  // Close menus when clicking outside
  useEffect(() => {
    const handleClickOutside = () => {
      setIsMenuOpen(false);
      setIsMobileNavOpen(false);
    };
    
    if (isMenuOpen || isMobileNavOpen) {
      document.addEventListener('click', handleClickOutside);
    }
    
    return () => {
      document.removeEventListener('click', handleClickOutside);
    };
  }, [isMenuOpen, isMobileNavOpen]);
  
  // Stop propagation to prevent immediate closing when clicking the menu
  const handleMenuClick = (e: React.MouseEvent) => {
    e.stopPropagation();
  };

  useEffect(() => {
    // Add global error listener
    const removeListener = errorHandlingService.addErrorListener((error) => {
      setErrorToast({
        message: error.message,
        severity: error.severity
      });
    });

    return () => removeListener();
  }, []);

  const handleCloseToast = () => {
    setErrorToast(null);
  };

  return (
    <Container hasHeader={showHeader}>
      {showHeader && (
        <Header>
          <HeaderContent>
            <Logo to="/">
              <svg
                width="24"
                height="24"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z" />
                <line x1="4" y1="22" x2="4" y2="15" />
              </svg>
              FormIQ
            </Logo>

            <HamburgerButton onClick={() => setIsMobileNavOpen(!isMobileNavOpen)}>
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                {isMobileNavOpen ? (
                  <path d="M18 6L6 18M6 6l12 12" />
                ) : (
                  <path d="M3 12h18M3 6h18M3 18h18" />
                )}
              </svg>
            </HamburgerButton>

            <Nav isOpen={isMobileNavOpen}>
              <NavLink to="/" active={location.pathname === '/'}>
                Dashboard
              </NavLink>
              <NavLink to="/analysis" active={location.pathname === '/analysis'}>
                Analysis
              </NavLink>
              <NavLink to="/profile" active={location.pathname === '/profile'}>
                Profile
              </NavLink>
              <NavLink to="/auth/login" onClick={handleLogout} active={false}>
                Logout
              </NavLink>
            </Nav>
          </HeaderContent>
        </Header>
      )}
      <Overlay show={isMobileNavOpen || isMenuOpen} onClick={() => {
        setIsMobileNavOpen(false);
        setIsMenuOpen(false);
      }} />
      <Main hasHeader={showHeader}>
        <ContentWrapper hasSidebar={hasSidebar}>
          <MainContent hasSidebar={hasSidebar} hasFooter={hasFooter}>{children}</MainContent>
        </ContentWrapper>
      </Main>
      {isAuthenticated && (
        <MobileNavigation />
      )}
      
      {errorToast && (
        <Snackbar
          open={true}
          autoHideDuration={6000}
          onClose={handleCloseToast}
          anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
        >
          <Alert
            onClose={handleCloseToast}
            severity={errorToast.severity}
            variant="filled"
            sx={{ width: '100%' }}
          >
            {errorToast.message}
          </Alert>
        </Snackbar>
      )}
    </Container>
  );
}; 