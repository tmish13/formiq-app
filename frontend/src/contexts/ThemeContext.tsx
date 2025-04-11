import React, { createContext, useContext, useState, useEffect } from 'react';
import { ThemeProvider as StyledThemeProvider } from 'styled-components';
import { lightTheme, darkTheme, Theme } from '../theme';

export interface ThemeContextType {
  isDarkMode: boolean;
  toggleDarkMode: () => void;
  theme: Theme;
}

export const ThemeContext = createContext<ThemeContextType>({
  isDarkMode: false,
  toggleDarkMode: () => {},
  theme: lightTheme,
});

export const useTheme = () => useContext(ThemeContext);

interface ThemeProviderProps {
  children: React.ReactNode;
}

export const ThemeProvider: React.FC<ThemeProviderProps> = ({ children }) => {
  const [isDarkMode, setIsDarkMode] = useState(() => {
    // Check for system preference first
    const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    const saved = localStorage.getItem('formiq_dark_mode');
    
    // If user has explicitly set a preference, use that
    if (saved !== null) {
      return JSON.parse(saved);
    }
    
    // Otherwise use system preference
    return prefersDark;
  });

  useEffect(() => {
    localStorage.setItem('formiq_dark_mode', JSON.stringify(isDarkMode));
    document.documentElement.setAttribute('data-theme', isDarkMode ? 'dark' : 'light');
    
    // Update meta theme-color for mobile browsers
    const metaThemeColor = document.querySelector('meta[name="theme-color"]');
    if (metaThemeColor) {
      metaThemeColor.setAttribute('content', isDarkMode ? '#111827' : '#F7FAFC');
    } else {
      const meta = document.createElement('meta');
      meta.name = 'theme-color';
      meta.content = isDarkMode ? '#111827' : '#F7FAFC';
      document.head.appendChild(meta);
    }
  }, [isDarkMode]);

  const toggleDarkMode = () => {
    setIsDarkMode((prev: boolean) => !prev);
  };

  const theme: Theme = isDarkMode ? darkTheme : lightTheme;

  return (
    <ThemeContext.Provider value={{ isDarkMode, toggleDarkMode, theme }}>
      <StyledThemeProvider theme={theme}>
        {children}
      </StyledThemeProvider>
    </ThemeContext.Provider>
  );
}; 