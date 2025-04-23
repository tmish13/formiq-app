import React from 'react';
import { Typography as MuiTypography, TypographyProps as MuiTypographyProps } from '@mui/material';
import styled from 'styled-components';

export interface TypographyProps extends Omit<MuiTypographyProps, 'variant'> {
  variant?: 'h1' | 'h2' | 'h3' | 'h4' | 'h5' | 'h6' | 'body1' | 'body2' | 'caption';
  weight?: 'light' | 'regular' | 'medium' | 'bold';
  color?: 'primary' | 'secondary' | 'text' | 'error' | 'success' | 'warning';
}

const StyledTypography = styled(MuiTypography)<TypographyProps>`
  font-weight: ${({ weight, theme }) => {
    switch (weight) {
      case 'light': return theme.typography.fontWeight.light;
      case 'medium': return theme.typography.fontWeight.medium;
      case 'bold': return theme.typography.fontWeight.bold;
      default: return theme.typography.fontWeight.regular;
    }
  }};
  color: ${({ color, theme }) => {
    switch (color) {
      case 'primary': return theme.colors.primary.main;
      case 'secondary': return theme.colors.secondary.main;
      case 'error': return theme.colors.error.main;
      case 'success': return theme.colors.success.main;
      case 'warning': return theme.colors.warning.main;
      default: return theme.colors.text.primary;
    }
  }};
`;

export const Typography: React.FC<TypographyProps> = ({
  children,
  variant = 'body1',
  weight = 'regular',
  color = 'text',
  ...props
}) => {
  return (
    <StyledTypography
      variant={variant}
      weight={weight}
      color={color}
      {...props}
    >
      {children}
    </StyledTypography>
  );
}; 