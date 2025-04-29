import { DefaultTheme } from 'styled-components';

export interface ColorPalette {
  light: string;
  main: string;
  dark: string;
  contrastText?: string;
}

export interface Theme extends DefaultTheme {
  colors: {
    primary: ColorPalette;
    secondary: ColorPalette;
    error: ColorPalette;
    warning: ColorPalette;
    success: ColorPalette;
    info: ColorPalette;
    gray: ColorPalette;
    background: {
      main: string;
      secondary: string;
      paper: string;
    };
    text: {
      primary: string;
      secondary: string;
      disabled: string;
      inverse: string;
    };
    border: {
      main: string;
      light: string;
    };
    disabled: string;
  };
  typography: {
    fontFamily: {
      primary: string;
      secondary: string;
      mono: string;
    };
    fontSize: {
      xxs: string;
      xs: string;
      sm: string;
      md: string;
      lg: string;
      xl: string;
      xxl: string;
    };
    fontWeight: {
      light: number;
      regular: number;
      medium: number;
      semibold: number;
      bold: number;
    };
    lineHeight: {
      tight: string;
      normal: string;
      relaxed: string;
    };
  };
  spacing: {
    xxs: string;
    xs: string;
    sm: string;
    md: string;
    lg: string;
    xl: string;
    xxl: string;
  };
  borderRadius: {
    sm: string;
    md: string;
    lg: string;
    full: string;
  };
  shadows: {
    none: string;
    small: string;
    medium: string;
    large: string;
  };
  breakpoints: {
    xs: string;
    sm: string;
    md: string;
    lg: string;
    xl: string;
  };
  transitions: {
    duration: {
      shortest: string;
      shorter: string;
      short: string;
      standard: string;
      complex: string;
      enteringScreen: string;
      leavingScreen: string;
      medium: string;
    };
    easing: {
      easeIn: string;
      easeOut: string;
      easeInOut: string;
      sharp: string;
    };
  };
  zIndex: {
    modal: number;
    popover: number;
    tooltip: number;
    drawer: number;
    appBar: number;
  };
}

export const theme: Theme = {
  colors: {
    primary: {
      light: '#38bdf8',
      main: '#0ea5e9',
      dark: '#0369a1',
      contrastText: '#ffffff',
    },
    secondary: {
      light: '#94a3b8',
      main: '#64748b',
      dark: '#334155',
      contrastText: '#ffffff',
    },
    error: {
      light: '#f87171',
      main: '#ef4444',
      dark: '#b91c1c',
      contrastText: '#ffffff',
    },
    warning: {
      light: '#fbbf24',
      main: '#f59e0b',
      dark: '#b45309',
      contrastText: '#ffffff',
    },
    info: {
      light: '#38bdf8',
      main: '#0ea5e9',
      dark: '#0369a1',
      contrastText: '#ffffff',
    },
    success: {
      light: '#4ade80',
      main: '#22c55e',
      dark: '#15803d',
      contrastText: '#ffffff',
    },
    gray: {
      light: '#e5e7eb',
      main: '#6b7280',
      dark: '#374151',
      contrastText: '#ffffff',
    },
    background: {
      main: '#ffffff',
      secondary: '#f3f4f6',
      paper: '#ffffff',
    },
    text: {
      primary: '#111827',
      secondary: '#6b7280',
      disabled: '#9ca3af',
      inverse: '#ffffff',
    },
    border: {
      main: '#e5e7eb',
      light: '#f3f4f6',
    },
    disabled: '#9ca3af',
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
    small: '0 1px 3px rgba(0, 0, 0, 0.1)',
    medium: '0 4px 6px rgba(0, 0, 0, 0.1)',
    large: '0 10px 15px rgba(0, 0, 0, 0.1)',
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
      shortest: '150ms',
      shorter: '300ms',
      short: '500ms',
      standard: '300ms',
      complex: '500ms',
      enteringScreen: '250ms',
      leavingScreen: '200ms',
      medium: '300ms',
    },
    easing: {
      easeIn: 'cubic-bezier(0.4, 0, 1, 1)',
      easeOut: 'cubic-bezier(0, 0, 0.2, 1)',
      easeInOut: 'cubic-bezier(0.4, 0, 0.2, 1)',
      sharp: 'cubic-bezier(0.4, 0, 0.6, 1)',
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