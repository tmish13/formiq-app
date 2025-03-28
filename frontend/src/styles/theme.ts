import { DefaultTheme } from 'styled-components';

export const theme: DefaultTheme = {
  colors: {
    primary: '#007AFF',
    primaryDark: '#0056B3',
    primaryLight: '#E5F1FF',
    secondary: '#6C757D',
    secondaryDark: '#5A6268',
    secondaryLight: '#F8F9FA',
    success: '#28A745',
    successDark: '#218838',
    successLight: '#D4EDDA',
    error: '#DC3545',
    errorDark: '#C82333',
    errorLight: '#F8D7DA',
    warning: '#FFC107',
    warningDark: '#E0A800',
    warningLight: '#FFF3CD',
    info: '#17A2B8',
    infoDark: '#138496',
    infoLight: '#D1ECF1',
    text: '#212529',
    textSecondary: '#6C757D',
    background: '#F8F9FA',
    white: '#FFFFFF',
  },
  spacing: {
    xs: '0.25rem',
    sm: '0.5rem',
    md: '1rem',
    lg: '1.5rem',
    xl: '2rem',
    xxl: '3rem',
  },
  typography: {
    fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif",
    fontSize: {
      xs: '0.75rem',
      sm: '0.875rem',
      base: '1rem',
      lg: '1.125rem',
      xl: '1.25rem',
      xxl: '1.5rem',
    },
    fontWeight: {
      regular: 400,
      medium: 500,
      semibold: 600,
      bold: 700,
    },
  },
  borderRadius: {
    sm: '0.25rem',
    md: '0.375rem',
    lg: '0.5rem',
    xl: '1rem',
  },
  shadows: {
    sm: '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
    md: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
    lg: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
  },
  transitions: {
    fast: '150ms ease-in-out',
    normal: '250ms ease-in-out',
    slow: '350ms ease-in-out',
  },
  breakpoints: {
    xs: '320px',
    sm: '640px',
    md: '768px',
    lg: '1024px',
    xl: '1280px',
    xxl: '1536px',
  },
};

export type Theme = typeof theme; 