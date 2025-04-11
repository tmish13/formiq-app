import React from 'react';
import { ThemeProvider as StyledThemeProvider } from 'styled-components';
import { theme } from '../theme';
import { GlobalStyles } from '../styles/globalStyles';

interface ThemeProviderProps {
  children: React.ReactNode;
}

export const ThemeProvider: React.FC<ThemeProviderProps> = ({ children }) => {
  return (
    <StyledThemeProvider theme={theme}>
      <GlobalStyles />
      {children}
    </StyledThemeProvider>
  );
}; 