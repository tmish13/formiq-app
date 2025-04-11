export type Theme = {
  colors: {
    primary: string;
    primaryDark: string;
    secondary: string;
    success: string;
    successLight: string;
    warning: string;
    warningLight: string;
    error: string;
    errorLight: string;
    background: string;
    surface: string;
    text: string;
    textSecondary: string;
    border: string;
    disabled: string;
  };
  spacing: {
    xs: string;
    sm: string;
    md: string;
    lg: string;
    xl: string;
  };
  typography: {
    fontFamily: string;
    fontSize: {
      xs: string;
      sm: string;
      md: string;
      lg: string;
      xl: string;
    };
    fontWeight: {
      regular: number;
      medium: number;
      bold: number;
    };
  };
  borderRadius: {
    sm: string;
    md: string;
    lg: string;
    round: string;
  };
  shadows: {
    sm: string;
    md: string;
    lg: string;
  };
  transitions: {
    fast: string;
    medium: string;
    slow: string;
  };
};

export const theme: Theme = {
  colors: {
    primary: '#007AFF',
    primaryDark: '#0056B3',
    secondary: '#5856D6',
    success: '#34C759',
    successLight: '#4CD964',
    warning: '#FF9500',
    warningLight: '#FFB340',
    error: '#FF3B30',
    errorLight: '#FF6961',
    background: '#F2F2F7',
    surface: '#FFFFFF',
    text: '#000000',
    textSecondary: '#8E8E93',
    border: '#C6C6C8',
    disabled: '#C7C7CC',
  },
  spacing: {
    xs: '4px',
    sm: '8px',
    md: '16px',
    lg: '24px',
    xl: '32px',
  },
  typography: {
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
    fontSize: {
      xs: '12px',
      sm: '14px',
      md: '16px',
      lg: '18px',
      xl: '20px',
    },
    fontWeight: {
      regular: 400,
      medium: 500,
      bold: 700,
    },
  },
  borderRadius: {
    sm: '4px',
    md: '8px',
    lg: '12px',
    round: '50%',
  },
  shadows: {
    sm: '0 1px 2px rgba(0, 0, 0, 0.05)',
    md: '0 2px 4px rgba(0, 0, 0, 0.1)',
    lg: '0 4px 6px rgba(0, 0, 0, 0.15)',
  },
  transitions: {
    fast: '150ms ease-in-out',
    medium: '300ms ease-in-out',
    slow: '500ms ease-in-out',
  },
}; 