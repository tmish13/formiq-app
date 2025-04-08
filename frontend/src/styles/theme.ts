import { ThemeOptions, createTheme } from '@mui/material/styles';
import 'styled-components';

// Extend the DefaultTheme interface from styled-components
declare module 'styled-components' {
  export interface DefaultTheme {
    colors: {
      primary: string;
      primaryLight: string;
      primaryDark: string;
      secondary: string;
      secondaryLight: string;
      secondaryDark: string;
      success: string;
      successLight: string;
      successDark: string;
      error: string;
      errorLight: string;
      errorDark: string;
      warning: string;
      warningLight: string;
      warningDark: string;
      info: string;
      infoLight: string;
      infoDark: string;
      text: string;
      textSecondary: string;
      background: string;
      white: string;
      border: string;
      disabled: string;
    };
    typography: {
      fontFamily: {
        base: string;
        mono: string;
      };
      fontSize: {
        xs: string;
        sm: string;
        base: string;
        lg: string;
        xl: string;
        xxl: string;
      };
      fontWeight: {
        light: number;
        normal: number;
        medium: number;
        semibold: number;
        bold: number;
      };
    };
    spacing: {
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
      sm: string;
      md: string;
      lg: string;
    };
    transitions: {
      fast: string;
      medium: string;
      slow: string;
    };
    breakpoints: {
      xs: string;
      sm: string;
      md: string;
      lg: string;
      xl: string;
    };
  }
}

// Define our theme object type
export interface Theme {
  colors: {
    primary: string;
    primaryLight: string;
    primaryDark: string;
    secondary: string;
    secondaryLight: string;
    secondaryDark: string;
    success: string;
    successLight: string;
    successDark: string;
    error: string;
    errorLight: string;
    errorDark: string;
    warning: string;
    warningLight: string;
    warningDark: string;
    info: string;
    infoLight: string;
    infoDark: string;
    text: string;
    textSecondary: string;
    background: string;
    white: string;
    border: string;
    disabled: string;
  };
  typography: {
    fontFamily: {
      base: string;
      mono: string;
    };
    fontSize: {
      xs: string;
      sm: string;
      base: string;
      lg: string;
      xl: string;
      xxl: string;
    };
    fontWeight: {
      light: number;
      normal: number;
      medium: number;
      semibold: number;
      bold: number;
    };
  };
  spacing: {
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
    sm: string;
    md: string;
    lg: string;
  };
  transitions: {
    fast: string;
    medium: string;
    slow: string;
  };
}

const themeOptions: ThemeOptions = {
  palette: {
    primary: {
      main: '#4D7CFE',
      light: '#83A9FF',
      dark: '#2E5BFF',
    },
    secondary: {
      main: '#6C5CE7',
      light: '#A29BFE',
      dark: '#5341D6',
    },
    success: {
      main: '#00C67F',
      light: '#46EDB0',
      dark: '#00A366',
    },
    error: {
      main: '#FF6B6B',
      light: '#FF9B9B',
      dark: '#E64C4C',
    },
    warning: {
      main: '#FFA502',
      light: '#FFCE82',
      dark: '#E08700',
    },
    info: {
      main: '#45AAF2',
      light: '#75C4F7',
      dark: '#2D8ED6',
    },
    text: {
      primary: '#2D3748',
      secondary: '#718096',
    },
    background: {
      default: '#F7FAFC',
      paper: '#FFFFFF',
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
      letterSpacing: '-0.025em',
    },
    h2: {
      fontSize: '2rem',
      fontWeight: 700,
      letterSpacing: '-0.025em',
    },
    h3: {
      fontSize: '1.75rem',
      fontWeight: 600,
      letterSpacing: '-0.025em',
    },
    h4: {
      fontSize: '1.5rem',
      fontWeight: 600,
      letterSpacing: '-0.025em',
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
      lineHeight: 1.6,
    },
    body2: {
      fontSize: '0.875rem',
      fontWeight: 400,
      lineHeight: 1.6,
    },
  },
  spacing: (factor: number) => `${0.25 * factor}rem`,
  shape: {
    borderRadius: 10,
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

// Our custom theme object
export const customTheme = {
  colors: {
    primary: '#4D7CFE',
    primaryLight: '#83A9FF',
    primaryDark: '#2E5BFF',
    secondary: '#6C5CE7',
    secondaryLight: '#A29BFE',
    secondaryDark: '#5341D6',
    success: '#00C67F',
    successLight: '#46EDB0',
    successDark: '#00A366',
    error: '#FF6B6B',
    errorLight: '#FF9B9B',
    errorDark: '#E64C4C',
    warning: '#FFA502',
    warningLight: '#FFCE82',
    warningDark: '#E08700',
    info: '#45AAF2',
    infoLight: '#75C4F7',
    infoDark: '#2D8ED6',
    text: '#2D3748',
    textSecondary: '#718096',
    background: '#F7FAFC',
    white: '#FFFFFF',
    border: '#E2E8F0',
    disabled: '#A0AEC0',
  },
  typography: {
    fontFamily: {
      base: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif",
      mono: "SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace",
    },
    fontSize: {
      xs: '0.75rem',
      sm: '0.875rem',
      base: '1rem',
      lg: '1.125rem',
      xl: '1.25rem',
      xxl: '1.5rem',
    },
    fontWeight: {
      light: 300,
      normal: 400,
      medium: 500,
      semibold: 600,
      bold: 700,
    },
  },
  spacing: {
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
    sm: '0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)',
    md: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
    lg: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
  },
  transitions: {
    fast: '150ms ease-in-out',
    medium: '300ms ease-in-out',
    slow: '500ms ease-in-out',
  },
  breakpoints: {
    xs: '0px',
    sm: '600px',
    md: '960px',
    lg: '1280px',
    xl: '1920px',
  },
}; 