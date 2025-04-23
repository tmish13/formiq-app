import 'styled-components';

interface ColorPalette {
  light: string;
  main: string;
  dark: string;
  contrastText?: string;
}

interface Colors {
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
}

interface Typography {
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
}

interface Spacing {
  xxs: string;
  xs: string;
  sm: string;
  md: string;
  lg: string;
  xl: string;
  xxl: string;
}

interface BorderRadius {
  sm: string;
  md: string;
  lg: string;
  full: string;
}

interface Shadows {
  none: string;
  small: string;
  medium: string;
  large: string;
}

export interface Theme {
  colors: Colors;
  typography: Typography;
  spacing: Spacing;
  borderRadius: BorderRadius;
  shadows: Shadows;
}

declare module 'styled-components' {
  export interface DefaultTheme extends Theme {}
}

// Re-export for convenience
export type { DefaultTheme } from 'styled-components'; 