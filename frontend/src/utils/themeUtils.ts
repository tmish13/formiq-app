import { DefaultTheme } from 'styled-components';
import { Theme } from '../types/theme';

type ThemePath = {
  [K in keyof Theme]: Theme[K] extends object
    ? {
        [P in keyof Theme[K]]: Theme[K][P] extends object
          ? {
              [Q in keyof Theme[K][P]]: `${K & string}.${P & string}.${Q & string}`;
            }[keyof Theme[K][P]]
          : `${K & string}.${P & string}`;
      }[keyof Theme[K]]
    : K;
}[keyof Theme];

/**
 * Safely access theme values with fallbacks
 * @param theme The theme object
 * @param path Path to the theme property (e.g., 'colors.primary' or 'typography.fontSize.md')
 * @param fallback Fallback value if the property doesn't exist
 */
export const getThemeValue = <T extends string>(
  theme: Partial<Theme> | undefined,
  path: ThemePath,
  fallback: string
): string => {
  if (!theme) return fallback;

  const parts = path.split('.');
  let current: any = theme;

  for (const part of parts) {
    if (current === undefined || current === null) return fallback;
    current = current[part];
  }

  return current ?? fallback;
};

/**
 * Common fallback values for theme properties
 */
export const fallbacks: Theme = {
  colors: {
    primary: '#6200ee',
    primaryLight: '#9b4dff',
    primaryDark: '#0000ba',
    secondary: '#03dac6',
    secondaryLight: '#66fff9',
    secondaryDark: '#00a895',
    background: '#ffffff',
    surface: '#ffffff',
    text: '#000000',
    textSecondary: '#666666',
    textLight: '#999999',
    error: '#b00020',
    errorLight: '#cf6679',
    errorDark: '#7f0000',
    success: '#00c853',
    successLight: '#5efc82',
    successDark: '#009624',
    warning: '#ffd600',
    warningLight: '#ffff52',
    warningDark: '#c7a500',
    info: '#2196f3',
    infoLight: '#6ec6ff',
    infoDark: '#0069c0',
    border: '#e0e0e0',
    white: '#ffffff',
    black: '#000000',
    disabled: '#cccccc'
  },
  typography: {
    fontFamily: 'Roboto, sans-serif',
    fontSize: {
      xs: '12px',
      sm: '14px',
      md: '16px',
      lg: '18px',
      xl: '20px',
      xxl: '24px',
      xlarge: '28px',
      medium: '16px',
      small: '14px'
    },
    fontWeight: {
      regular: 400,
      medium: 500,
      bold: 700
    },
    lineHeight: {
      small: 1.2,
      medium: 1.5,
      large: 1.8
    }
  },
  spacing: {
    xs: '8px',
    sm: '16px',
    md: '24px',
    lg: '32px',
    xl: '40px'
  },
  borderRadius: {
    sm: '4px',
    md: '8px',
    lg: '12px'
  },
  shadows: {
    sm: '0 2px 4px rgba(0, 0, 0, 0.1)',
    md: '0 4px 8px rgba(0, 0, 0, 0.1)',
    lg: '0 8px 16px rgba(0, 0, 0, 0.1)'
  },
  breakpoints: {
    mobile: '320px',
    tablet: '768px',
    desktop: '1024px',
    wide: '1440px'
  },
  transitions: {
    fast: '0.2s',
    medium: '0.3s',
    slow: '0.5s'
  },
  zIndex: {
    modal: 1000,
    overlay: 900,
    dropdown: 800,
    header: 700
  }
}; 