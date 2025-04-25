import { Theme } from '../../types/theme';

export const mockThemeWithFallbacks: Theme = {
  colors: {
    primary: {
      main: '#007AFF',
      light: '#47A3FF',
      dark: '#0055B3',
      contrastText: '#FFFFFF'
    },
    secondary: {
      main: '#5856D6',
      light: '#7A79E0',
      dark: '#3E3D96',
      contrastText: '#FFFFFF'
    },
    error: {
      main: '#FF3B30',
      light: '#FF6B6B',
      dark: '#B32B24',
      contrastText: '#FFFFFF'
    },
    warning: {
      main: '#FF9500',
      light: '#FFB84D',
      dark: '#B36800',
      contrastText: '#FFFFFF'
    },
    success: {
      main: '#34C759',
      light: '#6EDB8A',
      dark: '#258B3F',
      contrastText: '#FFFFFF'
    },
    info: {
      main: '#5AC8FA',
      light: '#8DD9FB',
      dark: '#3F8CB0',
      contrastText: '#FFFFFF'
    },
    gray: {
      main: '#6B7280',
      light: '#9CA3AF',
      dark: '#374151',
      contrastText: '#FFFFFF'
    },
    background: {
      main: '#FFFFFF',
      secondary: '#F9FAFB',
      paper: '#F3F4F6'
    },
    text: {
      primary: '#111827',
      secondary: '#4B5563',
      disabled: '#9CA3AF',
      inverse: '#FFFFFF'
    },
    border: {
      main: '#E5E7EB',
      light: '#F3F4F6'
    },
    disabled: '#9CA3AF'
  },
  typography: {
    fontFamily: {
      primary: '"Inter", "Helvetica", "Arial", sans-serif',
      secondary: '"SF Pro Display", "Helvetica", "Arial", sans-serif',
      mono: '"SF Mono", "Menlo", "Monaco", "Courier New", monospace'
    },
    fontSize: {
      xxs: '0.75rem',
      xs: '0.875rem',
      sm: '1rem',
      md: '1.125rem',
      lg: '1.25rem',
      xl: '1.5rem',
      xxl: '2rem'
    },
    fontWeight: {
      light: 300,
      regular: 400,
      medium: 500,
      semibold: 600,
      bold: 700
    },
    lineHeight: {
      tight: '1.25',
      normal: '1.5',
      relaxed: '1.75'
    }
  },
  spacing: {
    xxs: '0.25rem',
    xs: '0.5rem',
    sm: '0.75rem',
    md: '1rem',
    lg: '1.5rem',
    xl: '2rem',
    xxl: '3rem'
  },
  borderRadius: {
    sm: '0.25rem',
    md: '0.5rem',
    lg: '1rem',
    full: '9999px'
  },
  shadows: {
    none: 'none',
    small: '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
    medium: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
    large: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)'
  }
}; 