import { useContext } from 'react';
import { ThemeContext, ThemeContextType } from '../contexts/ThemeContext';
import type { DefaultTheme } from 'styled-components';

export const useTheme = (): DefaultTheme => {
  const { theme } = useContext<ThemeContextType>(ThemeContext);
  if (!theme) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return theme;
}; 