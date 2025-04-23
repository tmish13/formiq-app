export interface Theme {
  colors: {
    primary: ColorShade;
    secondary: ColorShade;
    error: ColorShade;
    warning: ColorShade;
    success: ColorShade;
    info: ColorShade;
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
      short: string;
      medium: string;
      long: string;
    };
    easing: {
      easeIn: string;
      easeOut: string;
      easeInOut: string;
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

export interface ColorShade {
  light: string;
  main: string;
  dark: string;
}

// Extend styled-components theme interface
declare module 'styled-components' {
  export interface DefaultTheme extends Theme {}
} 