import React from 'react';
import styled, { keyframes, DefaultTheme } from 'styled-components';
import { getThemeValue, fallbacks } from '../../utils/themeUtils';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost';
  size?: 'small' | 'medium' | 'large';
  isLoading?: boolean;
  fullWidth?: boolean;
  icon?: React.ReactNode;
  iconPosition?: 'left' | 'right';
}

const spin = keyframes`
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
`;

const StyledButton = styled.button<ButtonProps & { theme: DefaultTheme }>`
  padding: ${({ size }) => {
    switch (size) {
      case 'small': return '0.5rem 0.875rem';
      case 'large': return '0.75rem 1.5rem';
      default: return '0.625rem 1.125rem';
    }
  }};
  
  width: ${({ fullWidth }) => fullWidth ? '100%' : 'auto'};
  border-radius: ${({ theme }) => getThemeValue(theme, 'borderRadius.md', fallbacks.borderRadius.md)};
  font-weight: ${({ theme }) => getThemeValue(theme, 'typography.fontWeight.medium', String(fallbacks.typography.fontWeight.medium))};
  font-size: ${({ size, theme }) => {
    switch (size) {
      case 'small': return getThemeValue(theme, 'typography.fontSize.xs', fallbacks.typography.fontSize.xs);
      case 'large': return getThemeValue(theme, 'typography.fontSize.lg', fallbacks.typography.fontSize.lg);
      default: return getThemeValue(theme, 'typography.fontSize.md', fallbacks.typography.fontSize.md);
    }
  }};
  letter-spacing: 0.025em;
  cursor: pointer;
  transition: all 0.2s ease;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  position: relative;
  overflow: hidden;
  
  ${({ variant, theme }) => {
    switch (variant) {
      case 'secondary':
        return `
          background-color: ${getThemeValue(theme, 'colors.secondary', fallbacks.colors.secondary)};
          color: ${getThemeValue(theme, 'colors.white', fallbacks.colors.white)};
          border: none;
          box-shadow: ${getThemeValue(theme, 'shadows.sm', fallbacks.shadows.sm)};
          &:hover:not(:disabled) {
            background-color: ${getThemeValue(theme, 'colors.secondaryDark', fallbacks.colors.secondaryDark)};
            box-shadow: ${getThemeValue(theme, 'shadows.md', fallbacks.shadows.md)};
            transform: translateY(-1px);
          }
          &:active:not(:disabled) {
            background-color: ${getThemeValue(theme, 'colors.secondaryDark', fallbacks.colors.secondaryDark)};
            box-shadow: ${getThemeValue(theme, 'shadows.sm', fallbacks.shadows.sm)};
            transform: translateY(0);
          }
        `;
      case 'outline':
        return `
          background-color: transparent;
          color: ${getThemeValue(theme, 'colors.primary', fallbacks.colors.primary)};
          border: 2px solid ${getThemeValue(theme, 'colors.primary', fallbacks.colors.primary)};
          &:hover:not(:disabled) {
            background-color: ${getThemeValue(theme, 'colors.primaryLight', fallbacks.colors.primaryLight)}20;
            transform: translateY(-1px);
          }
          &:active:not(:disabled) {
            background-color: ${getThemeValue(theme, 'colors.primaryLight', fallbacks.colors.primaryLight)}30;
            transform: translateY(0);
          }
        `;
      case 'ghost':
        return `
          background-color: transparent;
          color: ${getThemeValue(theme, 'colors.primary', fallbacks.colors.primary)};
          border: none;
          &:hover:not(:disabled) {
            background-color: ${getThemeValue(theme, 'colors.primaryLight', fallbacks.colors.primaryLight)}20;
          }
          &:active:not(:disabled) {
            background-color: ${getThemeValue(theme, 'colors.primaryLight', fallbacks.colors.primaryLight)}30;
          }
        `;
      default:
        return `
          background-color: ${getThemeValue(theme, 'colors.primary', fallbacks.colors.primary)};
          color: ${getThemeValue(theme, 'colors.white', fallbacks.colors.white)};
          border: none;
          box-shadow: ${getThemeValue(theme, 'shadows.sm', fallbacks.shadows.sm)};
          &:hover:not(:disabled) {
            background-color: ${getThemeValue(theme, 'colors.primaryDark', fallbacks.colors.primaryDark)};
            box-shadow: ${getThemeValue(theme, 'shadows.md', fallbacks.shadows.md)};
            transform: translateY(-1px);
          }
          &:active:not(:disabled) {
            background-color: ${getThemeValue(theme, 'colors.primaryDark', fallbacks.colors.primaryDark)};
            box-shadow: ${getThemeValue(theme, 'shadows.sm', fallbacks.shadows.sm)};
            transform: translateY(0);
          }
        `;
    }
  }}
  
  &:disabled {
    opacity: 0.7;
    cursor: not-allowed;
    box-shadow: none;
  }
  
  &:focus {
    outline: none;
    box-shadow: 0 0 0 3px ${({ theme, variant }) => 
      variant === 'secondary' 
        ? `${getThemeValue(theme, 'colors.secondary', fallbacks.colors.secondary)}40` 
        : `${getThemeValue(theme, 'colors.primary', fallbacks.colors.primary)}40`};
  }
`;

const LoadingSpinner = styled.span`
  width: 1rem;
  height: 1rem;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-radius: 50%;
  border-top-color: white;
  animation: ${spin} 0.8s linear infinite;
  position: relative;
`;

export const Button: React.FC<ButtonProps> = ({
  children,
  variant = 'primary',
  size = 'medium',
  isLoading = false,
  disabled,
  fullWidth = false,
  icon,
  iconPosition = 'left',
  ...props
}) => {
  return (
    <StyledButton
      variant={variant}
      size={size}
      disabled={disabled || isLoading}
      fullWidth={fullWidth}
      {...props}
    >
      {isLoading ? (
        <LoadingSpinner />
      ) : (
        <>
          {icon && iconPosition === 'left' && icon}
          {children}
          {icon && iconPosition === 'right' && icon}
        </>
      )}
    </StyledButton>
  );
}; 