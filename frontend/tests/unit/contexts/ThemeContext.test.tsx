import React from 'react';
import { render, screen, fireEvent, act } from '@testing-library/react';
import { ThemeProvider, useTheme } from '../../../src/contexts/ThemeContext';
import { Theme } from '../../../src/types/theme';

// Mock theme values
const mockLightTheme: Theme = {
  colors: {
    primary: '#0ea5e9',
    primaryDark: '#0369a1',
    secondary: '#64748b',
    success: '#22c55e',
    successLight: '#4ade80',
    warning: '#f59e0b',
    warningLight: '#fbbf24',
    error: '#ef4444',
    errorLight: '#f87171',
    background: '#ffffff',
    surface: '#f5f5f5',
    text: '#1f2937',
    textSecondary: '#4b5563',
    border: '#e5e7eb',
    disabled: '#9ca3af'
  },
  spacing: {
    xs: '0.25rem',
    sm: '0.5rem',
    md: '1rem',
    lg: '1.5rem',
    xl: '2rem',
  },
  typography: {
    fontFamily: 'Roboto, sans-serif',
    fontSize: {
      xs: '0.75rem',
      sm: '0.875rem',
      md: '1rem',
      lg: '1.125rem',
      xl: '1.25rem',
    },
    fontWeight: {
      regular: 400,
      medium: 500,
      bold: 700,
    }
  },
  borderRadius: {
    sm: '0.125rem',
    md: '0.25rem',
    lg: '0.5rem',
    round: '9999px',
  },
  shadows: {
    sm: '0 1px 2px 0 rgb(0 0 0 / 0.05)',
    md: '0 4px 6px -1px rgb(0 0 0 / 0.1)',
    lg: '0 10px 15px -3px rgb(0 0 0 / 0.1)',
  },
  transitions: {
    fast: '150ms',
    medium: '300ms',
    slow: '500ms'
  }
};

const mockDarkTheme: Theme = {
  ...mockLightTheme,
  colors: {
    ...mockLightTheme.colors,
    primary: '#0369a1',
    primaryDark: '#075985',
    background: '#111827',
    surface: '#1f2937',
    text: '#f9fafb',
    textSecondary: '#d1d5db',
    border: '#374151',
    disabled: '#6b7280'
  }
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
      <span data-testid="primary-color">{theme.colors.primary}</span>
      <span data-testid="transition-fast">{theme.transitions.fast}</span>
      <span data-testid="transition-medium">{theme.transitions.medium}</span>
      <span data-testid="transition-slow">{theme.transitions.slow}</span>
    </div>
  );
};

describe('ThemeContext', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockLocalStorage.getItem.mockReturnValue(null);
  });

  it('should provide light theme by default when no preference is saved', () => {
    render(
      <ThemeProvider>
        <TestComponent />
      </ThemeProvider>
    );

    expect(screen.getByTestId('theme-mode')).toHaveTextContent('light');
    expect(screen.getByTestId('primary-color')).toHaveTextContent(mockLightTheme.colors.primary);
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
    expect(screen.getByTestId('primary-color')).toHaveTextContent(mockDarkTheme.colors.primary);
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
    expect(screen.getByTestId('primary-color')).toHaveTextContent(mockDarkTheme.colors.primary);
  });

  it('should toggle between light and dark themes', () => {
    render(
      <ThemeProvider>
        <TestComponent />
      </ThemeProvider>
    );

    // Initial state (light theme)
    expect(screen.getByTestId('theme-mode')).toHaveTextContent('light');
    expect(screen.getByTestId('primary-color')).toHaveTextContent(mockLightTheme.colors.primary);

    // Toggle to dark theme
    act(() => {
      fireEvent.click(screen.getByTestId('theme-toggle'));
    });

    expect(screen.getByTestId('theme-mode')).toHaveTextContent('dark');
    expect(screen.getByTestId('primary-color')).toHaveTextContent(mockDarkTheme.colors.primary);

    // Toggle back to light theme
    act(() => {
      fireEvent.click(screen.getByTestId('theme-toggle'));
    });

    expect(screen.getByTestId('theme-mode')).toHaveTextContent('light');
    expect(screen.getByTestId('primary-color')).toHaveTextContent(mockLightTheme.colors.primary);
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
    expect(metaThemeColor?.getAttribute('content')).toBe(mockLightTheme.colors.background);

    // Toggle to dark theme
    act(() => {
      fireEvent.click(screen.getByTestId('theme-toggle'));
    });

    expect(metaThemeColor?.getAttribute('content')).toBe(mockDarkTheme.colors.background);
  });

  it('should provide correct transition values', () => {
    render(
      <ThemeProvider>
        <TestComponent />
      </ThemeProvider>
    );

    expect(screen.getByTestId('transition-fast')).toHaveTextContent(mockLightTheme.transitions.fast);
    expect(screen.getByTestId('transition-medium')).toHaveTextContent(mockLightTheme.transitions.medium);
    expect(screen.getByTestId('transition-slow')).toHaveTextContent(mockLightTheme.transitions.slow);
  });
}); 