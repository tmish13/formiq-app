import { ThemeOptions, createTheme } from '@mui/material/styles';

const themeOptions: ThemeOptions = {
  palette: {
    primary: {
      main: '#2196f3',
      light: '#64b5f6',
      dark: '#1976d2',
    },
    secondary: {
      main: '#f50057',
      light: '#ff4081',
      dark: '#c51162',
    },
    success: {
      main: '#4caf50',
      light: '#81c784',
      dark: '#388e3c',
    },
    error: {
      main: '#f44336',
      light: '#e57373',
      dark: '#d32f2f',
    },
    warning: {
      main: '#ff9800',
      light: '#ffb74d',
      dark: '#f57c00',
    },
    info: {
      main: '#2196f3',
      light: '#64b5f6',
      dark: '#1976d2',
    },
    text: {
      primary: '#212529',
      secondary: '#6c757d',
    },
    background: {
      default: '#f8f9fa',
      paper: '#ffffff',
    },
  },
  typography: {
    fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif",
    fontSize: 16,
    fontWeightLight: 300,
    fontWeightRegular: 400,
    fontWeightMedium: 500,
    fontWeightBold: 700,
    h1: {
      fontSize: '2.5rem',
      fontWeight: 700,
    },
    h2: {
      fontSize: '2rem',
      fontWeight: 700,
    },
    h3: {
      fontSize: '1.75rem',
      fontWeight: 600,
    },
    h4: {
      fontSize: '1.5rem',
      fontWeight: 600,
    },
    h5: {
      fontSize: '1.25rem',
      fontWeight: 600,
    },
    h6: {
      fontSize: '1rem',
      fontWeight: 600,
    },
    body1: {
      fontSize: '1rem',
      fontWeight: 400,
    },
    body2: {
      fontSize: '0.875rem',
      fontWeight: 400,
    },
  },
  spacing: (factor: number) => `${0.25 * factor}rem`,
  shape: {
    borderRadius: 4,
  },
  shadows: [
    'none',
    '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
    '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
    '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
    '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
    '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
    '0 30px 60px -12px rgba(0, 0, 0, 0.25)',
    '0 35px 70px -12px rgba(0, 0, 0, 0.25)',
    '0 40px 80px -12px rgba(0, 0, 0, 0.25)',
    '0 45px 90px -12px rgba(0, 0, 0, 0.25)',
    '0 50px 100px -12px rgba(0, 0, 0, 0.25)',
    '0 55px 110px -12px rgba(0, 0, 0, 0.25)',
    '0 60px 120px -12px rgba(0, 0, 0, 0.25)',
    '0 65px 130px -12px rgba(0, 0, 0, 0.25)',
    '0 70px 140px -12px rgba(0, 0, 0, 0.25)',
    '0 75px 150px -12px rgba(0, 0, 0, 0.25)',
    '0 80px 160px -12px rgba(0, 0, 0, 0.25)',
    '0 85px 170px -12px rgba(0, 0, 0, 0.25)',
    '0 90px 180px -12px rgba(0, 0, 0, 0.25)',
    '0 95px 190px -12px rgba(0, 0, 0, 0.25)',
    '0 100px 200px -12px rgba(0, 0, 0, 0.25)',
    '0 105px 210px -12px rgba(0, 0, 0, 0.25)',
    '0 110px 220px -12px rgba(0, 0, 0, 0.25)',
    '0 115px 230px -12px rgba(0, 0, 0, 0.25)',
    '0 120px 240px -12px rgba(0, 0, 0, 0.25)',
  ],
  transitions: {
    duration: {
      shortest: 150,
      shorter: 200,
      short: 250,
      standard: 300,
      complex: 375,
      enteringScreen: 225,
      leavingScreen: 195,
    },
    easing: {
      easeInOut: 'cubic-bezier(0.4, 0, 0.2, 1)',
      easeOut: 'cubic-bezier(0.0, 0, 0.2, 1)',
      easeIn: 'cubic-bezier(0.4, 0, 1, 1)',
      sharp: 'cubic-bezier(0.4, 0, 0.6, 1)',
    },
  },
  breakpoints: {
    values: {
      xs: 320,
      sm: 640,
      md: 768,
      lg: 1024,
      xl: 1280,
    },
  },
};

export const theme = createTheme(themeOptions); 