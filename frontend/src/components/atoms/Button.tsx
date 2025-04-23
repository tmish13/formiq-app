import React from 'react';
import { Button as MuiButton, ButtonProps as MuiButtonProps } from '@mui/material';
import styled from 'styled-components';
import { getThemeValue } from '../../utils/themeUtils';

type ButtonVariant = 'contained' | 'outlined' | 'text';
type ButtonSize = 'small' | 'medium' | 'large';

export interface ButtonProps extends Omit<MuiButtonProps, 'variant' | 'size'> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  fullWidth?: boolean;
}

const StyledButton = styled(MuiButton)<ButtonProps>`
  text-transform: none;
  font-weight: ${({ theme }) => getThemeValue(theme, 'typography.fontWeight.medium', '500')};
  border-radius: ${({ theme }) => getThemeValue(theme, 'borderRadius.md', '8px')};
  padding: ${({ size, theme }) => {
    switch (size) {
      case 'small': return getThemeValue(theme, 'spacing.xs', '6px') + ' ' + getThemeValue(theme, 'spacing.md', '16px');
      case 'large': return getThemeValue(theme, 'spacing.md', '12px') + ' ' + getThemeValue(theme, 'spacing.lg', '24px');
      default: return getThemeValue(theme, 'spacing.sm', '8px') + ' ' + getThemeValue(theme, 'spacing.md', '20px');
    }
  }};
  font-size: ${({ size, theme }) => {
    switch (size) {
      case 'small': return getThemeValue(theme, 'typography.fontSize.sm', '0.875rem');
      case 'large': return getThemeValue(theme, 'typography.fontSize.lg', '1.125rem');
      default: return getThemeValue(theme, 'typography.fontSize.md', '1rem');
    }
  }};

  &.MuiButton-contained {
    background-color: ${({ theme }) => getThemeValue(theme, 'colors.primary.main', '#3f51b5')};
    color: ${({ theme }) => getThemeValue(theme, 'colors.text.inverse', '#ffffff')};
    &:hover {
      background-color: ${({ theme }) => getThemeValue(theme, 'colors.primary.dark', '#303f9f')};
    }
  }

  &.MuiButton-outlined {
    border-color: ${({ theme }) => getThemeValue(theme, 'colors.primary.main', '#3f51b5')};
    color: ${({ theme }) => getThemeValue(theme, 'colors.primary.main', '#3f51b5')};
    &:hover {
      border-color: ${({ theme }) => getThemeValue(theme, 'colors.primary.dark', '#303f9f')};
      background-color: ${({ theme }) => getThemeValue(theme, 'colors.primary.light', '#7986cb')};
    }
  }

  &.MuiButton-text {
    color: ${({ theme }) => getThemeValue(theme, 'colors.primary.main', '#3f51b5')};
    &:hover {
      background-color: ${({ theme }) => getThemeValue(theme, 'colors.primary.light', '#7986cb')};
    }
  }

  &:disabled {
    background-color: ${({ theme }) => getThemeValue(theme, 'colors.disabled', '#e0e0e0')};
    color: ${({ theme }) => getThemeValue(theme, 'colors.text.disabled', '#999999')};
  }
`;

export const Button: React.FC<ButtonProps> = ({
  children,
  variant = 'contained',
  size = 'medium',
  fullWidth = false,
  ...props
}) => {
  return (
    <StyledButton
      variant={variant}
      size={size}
      fullWidth={fullWidth}
      {...props}
    >
      {children}
    </StyledButton>
  );
}; 