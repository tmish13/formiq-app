import 'styled-components';
import { Theme } from './types/theme';

declare module 'styled-components' {
  export interface DefaultTheme extends Theme {
    colors: any;
    typography: any;
    spacing: any;
    borderRadius: any;
    shadows: any;
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
        easeInOut: string;
        easeOut: string;
        easeIn: string;
        sharp: string;
      };
    };
  }
} 