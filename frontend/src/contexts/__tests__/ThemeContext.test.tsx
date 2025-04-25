import React from 'react';
import { render, screen, fireEvent, act } from '@testing-library/react';
import { ThemeProvider, useTheme } from '../ThemeContext';
import { Theme } from '../../types/theme';

// Mock theme values
const mockLightTheme: Theme = {
  colors: {
    primary: {
      light: '#7986cb',
      main: '#3f51b5',
      dark: '#303f9f',
      contrastText: '#ffffff',
    },
    secondary: {
      light: '#ff4081',
      main: '#f50057',
      dark: '#c51162',
      contrastText: '#ffffff',
    },
    error: {
      light: '#e57373',
      main: '#f44336',
      dark: '#d32f2f',
      contrastText: '#ffffff',
    },
    warning: {
      light: '#ffb74d',
      main: '#ff9800',
      dark: '#f57c00',
      contrastText: '#ffffff',
    },
    success: {
      light: '#81c784',
      main: '#4caf50',
      dark: '#388e3c',
      contrastText: '#ffffff',
    },
    info: {
      light: '#64b5f6',
      main: '#2196f3',
      dark: '#1976d2',
      contrastText: '#ffffff',
    },
    gray: {
      light: '#f5f5f5',
      main: '#9e9e9e',
      dark: '#616161',
      contrastText: '#000000',
    },
    background: {
      main: '#ffffff',
      secondary: '#f5f5f5',
      paper: '#ffffff',
    },
    text: {
      primary: '#000000',
      secondary: '#666666',
      disabled: '#999999',
      inverse: '#ffffff',
    },
    border: {
      main: '#e0e0e0',
      light: '#f0f0f0',
    },
    disabled: '#e0e0e0',
  },
  typography: {
    fontFamily: {
      primary: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif",
      secondary: "'Poppins', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif",
      mono: "'SF Mono', SFMono-Regular, Consolas, 'Liberation Mono', Menlo, Courier, monospace",
    },
    fontSize: {
      xxs: '0.625rem',
      xs: '0.75rem',
      sm: '0.875rem',
      md: '1rem',
      lg: '1.125rem',
      xl: '1.25rem',
      xxl: '1.5rem',
    },
    fontWeight: {
      light: 300,
      regular: 400,
      medium: 500,
      semibold: 600,
      bold: 700,
    },
    lineHeight: {
      tight: '1.25',
      normal: '1.5',
      relaxed: '1.75',
    },
  },
  spacing: {
    xxs: '0.25rem',
    xs: '0.5rem',
    sm: '0.75rem',
    md: '1rem',
    lg: '1.5rem',
    xl: '2rem',
    xxl: '3rem',
  },
  borderRadius: {
    sm: '0.25rem',
    md: '0.5rem',
    lg: '1rem',
    full: '9999px',
  },
  shadows: {
    none: 'none',
    small: '0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)',
    medium: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
    large: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
  },
};

const mockDarkTheme: Theme = {
  ...mockLightTheme,
  colors: {
    primary: {
      light: '#9fa8da',
      main: '#5c6bc0',
      dark: '#3949ab',
      contrastText: '#ffffff',
    },
    secondary: {
      light: '#ff80ab',
      main: '#ec407a',
      dark: '#c2185b',
      contrastText: '#ffffff',
    },
    error: {
      light: '#ef9a9a',
      main: '#e57373',
      dark: '#d32f2f',
      contrastText: '#ffffff',
    },
    warning: {
      light: '#ffd180',
      main: '#ffb74d',
      dark: '#ff9800',
      contrastText: '#ffffff',
    },
    success: {
      light: '#a5d6a7',
      main: '#81c784',
      dark: '#4caf50',
      contrastText: '#ffffff',
    },
    info: {
      light: '#90caf9',
      main: '#64b5f6',
      dark: '#2196f3',
      contrastText: '#ffffff',
    },
    gray: {
      light: '#424242',
      main: '#757575',
      dark: '#212121',
      contrastText: '#ffffff',
    },
    background: {
      main: '#121212',
      secondary: '#1e1e1e',
      paper: '#242424',
    },
    text: {
      primary: '#ffffff',
      secondary: '#b0b0b0',
      disabled: '#666666',
      inverse: '#121212',
    },
    border: {
      main: '#333333',
      light: '#444444',
    },
    disabled: '#444444',
  },
};

// Mock localStorage
const mockLocalStorage = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  clear: jest.fn()
};
Object.defineProperty(window, 'localStorage', { value: mockLocalStorage });

// Mock matchMedia
Object.defineProperty(window, 'matchMedia', {
  value: jest.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(),
    removeListener: jest.fn(),
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  })),
});

// Test component that uses the theme context
const TestComponent = () => {
  const { isDarkMode, toggleDarkMode, theme } = useTheme();
  return (
    <div>
      <span data-testid="theme-mode">{isDarkMode ? 'dark' : 'light'}</span>
      <button data-testid="theme-toggle" onClick={toggleDarkMode}>
        Toggle Theme
      </button>
      <span data-testid="primary-color">{theme.colors.primary.main}</span>
      <span data-testid="font-size-md">{theme.typography.fontSize.md}</span>
      <span data-testid="spacing-md">{theme.spacing.md}</span>
      <span data-testid="shadow-medium">{theme.shadows.medium}</span>
    </div>
  );
};

describe('ThemeContext', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockLocalStorage.getItem.mockReturnValue(null);
    
    // Reset matchMedia mock to default (light mode)
    Object.defineProperty(window, 'matchMedia', {
      value: jest.fn().mockImplementation(query => ({
        matches: false,
        media: query,
        onchange: null,
        addListener: jest.fn(),
        removeListener: jest.fn(),
        addEventListener: jest.fn(),
        removeEventListener: jest.fn(),
        dispatchEvent: jest.fn(),
      })),
    });

    // Reset meta theme-color tag
    const existingMetaTag = document.querySelector('meta[name="theme-color"]');
    if (existingMetaTag) {
      existingMetaTag.remove();
    }
  });

  it('should provide light theme by default when no preference is saved', () => {
    render(
      <ThemeProvider>
        <TestComponent />
      </ThemeProvider>
    );

    expect(screen.getByTestId('theme-mode')).toHaveTextContent('light');
    expect(screen.getByTestId('primary-color')).toHaveTextContent(mockLightTheme.colors.primary.main);
  });

  it('should use dark theme when system prefers dark mode', () => {
    // Mock system dark mode preference
    Object.defineProperty(window, 'matchMedia', {
      value: jest.fn().mockImplementation(query => ({
        matches: query === '(prefers-color-scheme: dark)',
        media: query,
        onchange: null,
        addListener: jest.fn(),
        removeListener: jest.fn(),
        addEventListener: jest.fn(),
        removeEventListener: jest.fn(),
        dispatchEvent: jest.fn(),
      })),
    });

    render(
      <ThemeProvider>
        <TestComponent />
      </ThemeProvider>
    );

    expect(screen.getByTestId('theme-mode')).toHaveTextContent('dark');
    expect(screen.getByTestId('primary-color')).toHaveTextContent(mockDarkTheme.colors.primary.main);
  });

  it('should use saved theme preference over system preference', () => {
    // Mock saved dark mode preference
    mockLocalStorage.getItem.mockReturnValue('true');

    render(
      <ThemeProvider>
        <TestComponent />
      </ThemeProvider>
    );

    expect(screen.getByTestId('theme-mode')).toHaveTextContent('dark');
    expect(screen.getByTestId('primary-color')).toHaveTextContent(mockDarkTheme.colors.primary.main);
  });

  it('should toggle between light and dark themes', () => {
    render(
      <ThemeProvider>
        <TestComponent />
      </ThemeProvider>
    );

    // Initial state (light theme)
    expect(screen.getByTestId('theme-mode')).toHaveTextContent('light');
    expect(screen.getByTestId('primary-color')).toHaveTextContent(mockLightTheme.colors.primary.main);

    // Toggle to dark theme
    act(() => {
      fireEvent.click(screen.getByTestId('theme-toggle'));
    });

    expect(screen.getByTestId('theme-mode')).toHaveTextContent('dark');
    expect(screen.getByTestId('primary-color')).toHaveTextContent(mockDarkTheme.colors.primary.main);

    // Toggle back to light theme
    act(() => {
      fireEvent.click(screen.getByTestId('theme-toggle'));
    });

    expect(screen.getByTestId('theme-mode')).toHaveTextContent('light');
    expect(screen.getByTestId('primary-color')).toHaveTextContent(mockLightTheme.colors.primary.main);
  });

  it('should persist theme preference to localStorage', () => {
    render(
      <ThemeProvider>
        <TestComponent />
      </ThemeProvider>
    );

    // Toggle to dark theme
    act(() => {
      fireEvent.click(screen.getByTestId('theme-toggle'));
    });

    expect(mockLocalStorage.setItem).toHaveBeenCalledWith('formiq_dark_mode', 'true');

    // Toggle back to light theme
    act(() => {
      fireEvent.click(screen.getByTestId('theme-toggle'));
    });

    expect(mockLocalStorage.setItem).toHaveBeenCalledWith('formiq_dark_mode', 'false');
  });

  it('should update theme-color meta tag', () => {
    render(
      <ThemeProvider>
        <TestComponent />
      </ThemeProvider>
    );

    const metaThemeColor = document.querySelector('meta[name="theme-color"]');
    expect(metaThemeColor).toBeTruthy();
    expect(metaThemeColor?.getAttribute('content')).toBe('#F7FAFC');

    // Toggle to dark theme
    act(() => {
      fireEvent.click(screen.getByTestId('theme-toggle'));
    });

    expect(metaThemeColor?.getAttribute('content')).toBe('#111827');
  });

  it('should provide correct theme values', () => {
    render(
      <ThemeProvider>
        <TestComponent />
      </ThemeProvider>
    );

    expect(screen.getByTestId('font-size-md')).toHaveTextContent(mockLightTheme.typography.fontSize.md);
    expect(screen.getByTestId('spacing-md')).toHaveTextContent(mockLightTheme.spacing.md);
    expect(screen.getByTestId('shadow-medium')).toHaveTextContent(mockLightTheme.shadows.medium);
  });
}); 