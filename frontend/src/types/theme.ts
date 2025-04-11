import 'styled-components';

interface ColorShade {
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
}

interface Typography {
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
}

interface Spacing {
  xs: string;
  sm: string;
  md: string;
  lg: string;
  xl: string;
}

interface BorderRadius {
  sm: string;
  md: string;
  lg: string;
  round: string;
}

interface Shadows {
  sm: string;
  md: string;
  lg: string;
}

interface Transitions {
  fast: string;
  medium: string;
  slow: string;
}

export interface Theme {
  colors: ColorShade;
  typography: Typography;
  spacing: Spacing;
  borderRadius: BorderRadius;
  shadows: Shadows;
  transitions: Transitions;
}

declare module 'styled-components' {
  export interface DefaultTheme extends Theme {}
}

// Re-export for convenience
export type { DefaultTheme } from 'styled-components'; 