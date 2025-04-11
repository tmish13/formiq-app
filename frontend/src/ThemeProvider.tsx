import React from 'react';
import { ThemeProvider as StyledThemeProvider } from 'styled-components';
import { theme } from './theme';

// Create context for our custom theme for React components that need it
export const ThemeContext = React.createContext(theme);

// Custom hook to use the theme
export const useTheme = () => React.useContext(ThemeContext);

// Theme provider component
interface ThemeProviderProps {
  children: React.ReactNode;
}

export const ThemeProvider: React.FC<ThemeProviderProps> = ({ children }) => {
  return (
    <StyledThemeProvider theme={theme}>
      <ThemeContext.Provider value={theme}>
        {children}
      </ThemeContext.Provider>
    </StyledThemeProvider>
  );
}; 