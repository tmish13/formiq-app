import { Theme } from '../types/theme';

export const baseTheme = {
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
  breakpoints: {
    xs: '0px',
    sm: '600px',
    md: '960px',
    lg: '1280px',
    xl: '1920px',
  },
  transitions: {
    duration: {
      short: '150ms',
      medium: '300ms',
      long: '500ms',
    },
    easing: {
      easeIn: 'cubic-bezier(0.4, 0, 1, 1)',
      easeOut: 'cubic-bezier(0, 0, 0.2, 1)',
      easeInOut: 'cubic-bezier(0.4, 0, 0.2, 1)',
    },
  },
  zIndex: {
    modal: 1000,
    popover: 900,
    tooltip: 800,
    drawer: 700,
    appBar: 600,
  },
};

export const lightTheme: Theme = {
  ...baseTheme,
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
};

export const darkTheme: Theme = {
  ...baseTheme,
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

// Default theme
export const theme = lightTheme; 