import React, { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import styled from 'styled-components';
import { useAuth } from '../../hooks/useAuth';

const LayoutContainer = styled.div`
  min-height: 100vh;
  display: flex;
  flex-direction: column;
`;

const MainContent = styled.main<{ hasHeader: boolean }>`
  flex: 1;
  padding-top: ${({ hasHeader }) => (hasHeader ? '64px' : '0')}; // Height of the header
  
  @media (max-width: ${({ theme }) => theme.breakpoints.sm}) {
    padding-top: ${({ hasHeader }) => (hasHeader ? '56px' : '0')}; // Smaller header height on mobile
  }
`;

const Header = styled.header`
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 64px;
  background-color: ${({ theme }) => theme.colors.white};
  box-shadow: ${({ theme }) => theme.shadows.sm};
  display: flex;
  align-items: center;
  padding: 0 ${({ theme }) => theme.spacing.xl};
  z-index: 1000;
  
  @media (max-width: ${({ theme }) => theme.breakpoints.sm}) {
    height: 56px;
    padding: 0 ${({ theme }) => theme.spacing.md};
  }
`;

const Logo = styled(Link)`
  font-size: ${({ theme }) => theme.typography.fontSize.xl};
  font-weight: ${({ theme }) => theme.typography.fontWeight.bold};
  color: ${({ theme }) => theme.colors.primary};
  text-decoration: none;
  margin-right: ${({ theme }) => theme.spacing.xl};
  
  @media (max-width: ${({ theme }) => theme.breakpoints.sm}) {
    font-size: ${({ theme }) => theme.typography.fontSize.lg};
    margin-right: ${({ theme }) => theme.spacing.md};
  }
`;

const Nav = styled.nav<{ isOpen: boolean }>`
  display: flex;
  align-items: center;
  gap: ${({ theme }) => theme.spacing.md};
  flex: 1;
  
  @media (max-width: ${({ theme }) => theme.breakpoints.md}) {
    position: fixed;
    top: 56px;
    left: 0;
    right: 0;
    flex-direction: column;
    background-color: ${({ theme }) => theme.colors.white};
    box-shadow: ${({ theme }) => theme.shadows.md};
    padding: ${({ theme }) => theme.spacing.md};
    transform: translateY(${({ isOpen }) => (isOpen ? '0' : '-100%')});
    opacity: ${({ isOpen }) => (isOpen ? '1' : '0')};
    visibility: ${({ isOpen }) => (isOpen ? 'visible' : 'hidden')};
    transition: all ${({ theme }) => theme.transitions.medium};
    height: auto;
    align-items: flex-start;
    z-index: 999;
  }
`;

const NavLink = styled(Link)<{ active?: boolean }>`
  color: ${({ theme, active }) =>
    active ? theme.colors.primary : theme.colors.textSecondary};
  text-decoration: none;
  font-weight: ${({ theme, active }) =>
    active ? theme.typography.fontWeight.semibold : theme.typography.fontWeight.normal};
  padding: ${({ theme }) => theme.spacing.sm} ${({ theme }) => theme.spacing.md};
  border-radius: ${({ theme }) => theme.borderRadius.md};
  transition: all ${({ theme }) => theme.transitions.fast};

  &:hover {
    color: ${({ theme }) => theme.colors.primary};
    background-color: ${({ theme }) => theme.colors.primaryLight};
  }
  
  @media (max-width: ${({ theme }) => theme.breakpoints.md}) {
    width: 100%;
    padding: ${({ theme }) => theme.spacing.md};
    font-size: ${({ theme }) => theme.typography.fontSize.lg};
  }
`;

const UserMenu = styled.div`
  position: relative;
  
  @media (max-width: ${({ theme }) => theme.breakpoints.md}) {
    margin-left: auto;
  }
`;

const UserButton = styled.button`
  display: flex;
  align-items: center;
  gap: ${({ theme }) => theme.spacing.sm};
  background: none;
  border: none;
  padding: ${({ theme }) => theme.spacing.sm} ${({ theme }) => theme.spacing.md};
  cursor: pointer;
  color: ${({ theme }) => theme.colors.text};
  font-weight: ${({ theme }) => theme.typography.fontWeight.medium};
  min-width: 44px;
  min-height: 44px;
  
  @media (max-width: ${({ theme }) => theme.breakpoints.sm}) {
    padding: ${({ theme }) => theme.spacing.sm};
  }
`;

const DropdownMenu = styled.div<{ isOpen: boolean }>`
  position: absolute;
  top: 100%;
  right: 0;
  background-color: ${({ theme }) => theme.colors.white};
  border-radius: ${({ theme }) => theme.borderRadius.md};
  box-shadow: ${({ theme }) => theme.shadows.md};
  min-width: 200px;
  display: ${({ isOpen }) => (isOpen ? 'block' : 'none')};
  margin-top: ${({ theme }) => theme.spacing.xs};
  z-index: 1001;
  
  @media (max-width: ${({ theme }) => theme.breakpoints.sm}) {
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
  padding: ${({ theme }) => theme.spacing.sm} ${({ theme }) => theme.spacing.md};
  color: ${({ theme }) => theme.colors.text};
  text-decoration: none;
  transition: all ${({ theme }) => theme.transitions.fast};
  min-height: 44px;
  display: flex;
  align-items: center;

  &:hover {
    background-color: ${({ theme }) => theme.colors.primaryLight};
    color: ${({ theme }) => theme.colors.primary};
  }
  
  @media (max-width: ${({ theme }) => theme.breakpoints.sm}) {
    padding: ${({ theme }) => theme.spacing.md};
    font-size: ${({ theme }) => theme.typography.fontSize.base};
  }
`;

const LogoutButton = styled.button`
  display: block;
  width: 100%;
  padding: ${({ theme }) => theme.spacing.sm} ${({ theme }) => theme.spacing.md};
  background: none;
  border: none;
  color: ${({ theme }) => theme.colors.error};
  text-align: left;
  cursor: pointer;
  transition: all ${({ theme }) => theme.transitions.fast};
  min-height: 44px;

  &:hover {
    background-color: ${({ theme }) => theme.colors.error}10;
  }
  
  @media (max-width: ${({ theme }) => theme.breakpoints.sm}) {
    padding: ${({ theme }) => theme.spacing.md};
    font-size: ${({ theme }) => theme.typography.fontSize.base};
  }
`;

const HamburgerButton = styled.button`
  display: none;
  flex-direction: column;
  justify-content: space-between;
  width: 24px;
  height: 20px;
  background: transparent;
  border: none;
  cursor: pointer;
  padding: 0;
  margin-right: ${({ theme }) => theme.spacing.md};
  min-width: 44px;
  min-height: 44px;
  
  @media (max-width: ${({ theme }) => theme.breakpoints.md}) {
    display: flex;
  }
  
  div {
    width: 24px;
    height: 3px;
    background: ${({ theme }) => theme.colors.primary};
    border-radius: 10px;
    transition: all 0.3s linear;
    position: relative;
    transform-origin: 1px;
  }
`;

const Overlay = styled.div<{ show: boolean }>`
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  z-index: 998;
  display: ${({ show }) => (show ? 'block' : 'none')};
`;

interface AppLayoutProps {
  children: React.ReactNode;
}

export const AppLayout: React.FC<AppLayoutProps> = ({ children }) => {
  const location = useLocation();
  const { user, logout, isAuthenticated } = useAuth();
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [isMobileNavOpen, setIsMobileNavOpen] = useState(false);

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

  return (
    <LayoutContainer>
      {showHeader && (
        <>
          <Header>
            <HamburgerButton onClick={(e) => {
              e.stopPropagation();
              setIsMobileNavOpen(!isMobileNavOpen);
            }}>
              <div />
              <div />
              <div />
            </HamburgerButton>
            <Logo to="/">FormIQ</Logo>
            <Nav isOpen={isMobileNavOpen} onClick={handleMenuClick}>
              <NavLink to="/dashboard" active={location.pathname === '/dashboard'}>
                Dashboard
              </NavLink>
              <NavLink to="/workout" active={location.pathname === '/workout'}>
                Workout
              </NavLink>
              <NavLink to="/analysis" active={location.pathname === '/analysis'}>
                Analysis
              </NavLink>
            </Nav>
            <UserMenu>
              <UserButton onClick={(e) => {
                e.stopPropagation();
                setIsMenuOpen(!isMenuOpen);
              }}>
                {user?.name}
              </UserButton>
              <DropdownMenu isOpen={isMenuOpen} onClick={handleMenuClick}>
                <DropdownItem to="/profile">Profile</DropdownItem>
                <LogoutButton onClick={handleLogout}>Logout</LogoutButton>
              </DropdownMenu>
            </UserMenu>
          </Header>
          <Overlay show={isMobileNavOpen || isMenuOpen} onClick={() => {
            setIsMobileNavOpen(false);
            setIsMenuOpen(false);
          }} />
        </>
      )}
      <MainContent hasHeader={showHeader}>{children}</MainContent>
    </LayoutContainer>
  );
}; 