import { DefaultTheme } from 'styled-components';
import { Theme } from './types';

export const mockTheme: Theme = {
  colors: {
    primary: { main: '#1976d2', light: '#42a5f5', dark: '#1565c0', contrastText: '#fff' },
    secondary: { main: '#9c27b0', light: '#ba68c8', dark: '#7b1fa2', contrastText: '#fff' },
    error: { main: '#d32f2f', light: '#ef5350', dark: '#c62828', contrastText: '#fff' },
    warning: { main: '#ed6c02', light: '#ff9800', dark: '#e65100', contrastText: '#fff' },
    info: { main: '#0288d1', light: '#03a9f4', dark: '#01579b', contrastText: '#fff' },
    success: { main: '#2e7d32', light: '#4caf50', dark: '#1b5e20', contrastText: '#fff' },
    background: { main: '#fff', secondary: '#f5f5f5', paper: '#fff' },
    text: { primary: '#000', secondary: '#666', disabled: '#999' },
    border: { default: '#e0e0e0', light: '#f0f0f0', dark: '#bdbdbd' },
    disabled: { background: '#e0e0e0', text: '#999' },
    gray: { light: '#f5f5f5', main: '#9e9e9e', dark: '#616161', contrastText: '#000' },
  },
  typography: {
    fontFamily: 'Roboto, Helvetica, Arial, sans-serif',
    fontSize: { xs: '0.75rem', sm: '0.875rem', md: '1rem', lg: '1.125rem', xl: '1.25rem' },
    fontWeight: { light: 300, regular: 400, medium: 500, bold: 700 },
  },
  spacing: { xs: '0.5rem', sm: '0.75rem', md: '1rem', lg: '1.5rem', xl: '2rem' },
  breakpoints: { xs: '0px', sm: '600px', md: '960px', lg: '1280px', xl: '1920px' },
  borderRadius: { sm: '0.25rem', md: '0.5rem', lg: '1rem', full: '9999px' },
  shadows: { sm: '0 1px 3px 0 rgba(0,0,0,0.1)', md: '0 4px 6px -1px rgba(0,0,0,0.1)', lg: '0 10px 15px -3px rgba(0,0,0,0.1)' },
  transitions: {
    fast: '150ms',
    normal: '300ms',
    slow: '500ms',
  },
}; 