import { DefaultTheme } from 'styled-components';
import { Theme } from '../types/theme';

export type ThemePath = string;

/**
 * Fallback values for theme properties
 */
export const fallbacks = {
  color: {
    primary: '#3f51b5',
    secondary: '#f50057',
    error: '#f44336',
    warning: '#ff9800',
    success: '#4caf50',
    info: '#2196f3',
    black: '#000000',
    white: '#ffffff',
    text: '#333333',
    background: '#ffffff',
    disabled: '#e0e0e0',
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
  fontSize: {
    xxs: '0.625rem',
    xs: '0.75rem',
    sm: '0.875rem',
    md: '1rem',
    lg: '1.125rem',
    xl: '1.25rem',
    xxl: '1.5rem',
    xlarge: '2rem', // Added for backward compatibility
  },
  borderRadius: {
    sm: '0.25rem',
    md: '0.5rem',
    lg: '1rem',
    full: '9999px',
  },
};

/**
 * Gets a value from the theme using a path string
 * Handles nested properties and provides fallbacks if the value doesn't exist
 * 
 * @param theme The theme object
 * @param path The path to the value in dot notation (e.g. 'colors.primary')
 * @param fallback Optional fallback value
 * @returns The value from the theme or the fallback
 */
export function getThemeValue(theme: DefaultTheme, path: ThemePath, fallback?: string): string {
  // Common paths with direct access
  if (path === 'colors.primary') return theme.colors.primary.main;
  if (path === 'colors.secondary') return theme.colors.secondary.main;
  if (path === 'colors.error') return theme.colors.error.main;
  if (path === 'colors.background') return theme.colors.background.main;
  if (path === 'colors.text') return theme.colors.text.primary;
  if (path === 'colors.white') return '#ffffff';
  if (path === 'colors.secondaryLight') return theme.colors.secondary.light;

  // Handle more complex paths
  const parts = path.split('.');
  
  try {
    let value: any = theme;
    for (const part of parts) {
      value = value[part];
      if (value === undefined) {
        throw new Error(`Theme value not found at ${path}`);
      }
    }
    return value;
  } catch (error) {
    // If we have a fallback, use it
    if (fallback !== undefined) {
      return fallback;
    }
    
    // Try to get value from fallbacks
    try {
      if (parts[0] === 'colors') {
        return fallbacks.color[parts[1] as keyof typeof fallbacks.color];
      }
      if (parts[0] === 'typography' && parts[1] === 'fontSize') {
        return fallbacks.fontSize[parts[2] as keyof typeof fallbacks.fontSize];
      }
      if (parts[0] === 'spacing') {
        return fallbacks.spacing[parts[1] as keyof typeof fallbacks.spacing];
      }
      if (parts[0] === 'borderRadius') {
        return fallbacks.borderRadius[parts[1] as keyof typeof fallbacks.borderRadius];
      }
    } catch {
      // Fallback to sensible default if all else fails
      console.warn(`Theme value not found at ${path} and no fallback available`);
      return '#000000';
    }
    
    console.warn(`Theme value not found at ${path}`);
    return '#000000';
  }
} 