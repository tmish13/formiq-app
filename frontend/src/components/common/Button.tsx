import React from 'react';
import styled, { keyframes } from 'styled-components';

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

const StyledButton = styled.button<ButtonProps>`
  padding: ${({ size }) => {
    switch (size) {
      case 'small': return '0.5rem 0.875rem';
      case 'large': return '0.75rem 1.5rem';
      default: return '0.625rem 1.125rem';
    }
  }};
  
  width: ${({ fullWidth }) => fullWidth ? '100%' : 'auto'};
  border-radius: ${({ theme }) => theme.borderRadius.md};
  font-weight: ${({ theme }) => theme.typography.fontWeight.semibold};
  font-size: ${({ size, theme }) => {
    switch (size) {
      case 'small': return theme.typography.fontSize.xs;
      case 'large': return theme.typography.fontSize.lg;
      default: return theme.typography.fontSize.base;
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
          background-color: ${theme.colors.secondary};
          color: ${theme.colors.white};
          border: none;
          box-shadow: ${theme.shadows.sm};
          &:hover:not(:disabled) {
            background-color: ${theme.colors.secondaryDark};
            box-shadow: ${theme.shadows.md};
            transform: translateY(-1px);
          }
          &:active:not(:disabled) {
            background-color: ${theme.colors.secondaryDark};
            box-shadow: ${theme.shadows.sm};
            transform: translateY(0);
          }
        `;
      case 'outline':
        return `
          background-color: transparent;
          color: ${theme.colors.primary};
          border: 2px solid ${theme.colors.primary};
          &:hover:not(:disabled) {
            background-color: ${theme.colors.primaryLight}20;
            transform: translateY(-1px);
          }
          &:active:not(:disabled) {
            background-color: ${theme.colors.primaryLight}30;
            transform: translateY(0);
          }
        `;
      case 'ghost':
        return `
          background-color: transparent;
          color: ${theme.colors.primary};
          border: none;
          &:hover:not(:disabled) {
            background-color: ${theme.colors.primaryLight}20;
          }
          &:active:not(:disabled) {
            background-color: ${theme.colors.primaryLight}30;
          }
        `;
      default:
        return `
          background-color: ${theme.colors.primary};
          color: ${theme.colors.white};
          border: none;
          box-shadow: ${theme.shadows.sm};
          &:hover:not(:disabled) {
            background-color: ${theme.colors.primaryDark};
            box-shadow: ${theme.shadows.md};
            transform: translateY(-1px);
          }
          &:active:not(:disabled) {
            background-color: ${theme.colors.primaryDark};
            box-shadow: ${theme.shadows.sm};
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
        ? `${theme.colors.secondary}40` 
        : `${theme.colors.primary}40`};
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