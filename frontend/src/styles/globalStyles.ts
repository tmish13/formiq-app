import { createGlobalStyle } from 'styled-components';
import { Theme } from '../theme';
import { getThemeValue, fallbacks } from '../utils/themeUtils';

export const GlobalStyles = createGlobalStyle<{ theme?: Partial<Theme> }>`
  * {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
    -webkit-tap-highlight-color: transparent;
  }

  html, body {
    height: 100%;
    width: 100%;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    font-size: 16px;
    line-height: 1.5;
    color: ${({ theme }) => getThemeValue(theme, 'colors.text', fallbacks.colors.text)};
    background-color: ${({ theme }) => getThemeValue(theme, 'colors.background', fallbacks.colors.background)};
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
  }

  #root {
    height: 100%;
    width: 100%;
  }

  button {
    font-family: inherit;
    border: none;
    background: none;
    cursor: pointer;
    padding: 0;
    margin: 0;
    outline: none;
    -webkit-tap-highlight-color: transparent;
  }

  input, select, textarea {
    font-family: inherit;
    font-size: inherit;
    color: inherit;
    background: none;
    border: none;
    outline: none;
    -webkit-tap-highlight-color: transparent;
  }

  a {
    color: inherit;
    text-decoration: none;
    -webkit-tap-highlight-color: transparent;
  }

  ul, ol {
    list-style: none;
  }

  img {
    max-width: 100%;
    height: auto;
  }

  /* iOS-like scrolling */
  .scroll-container {
    -webkit-overflow-scrolling: touch;
    overflow-y: auto;
    scroll-behavior: smooth;
  }

  /* iOS-like button styles */
  .ios-button {
    background-color: ${({ theme }) => getThemeValue(theme, 'colors.primary', fallbacks.colors.primary)};
    color: ${({ theme }) => getThemeValue(theme, 'colors.white', fallbacks.colors.white)};
    padding: 12px 24px;
    border-radius: ${({ theme }) => getThemeValue(theme, 'borderRadius.medium', fallbacks.borderRadius.medium)};
    font-weight: ${({ theme }) => getThemeValue(theme, 'typography.fontWeight.medium', fallbacks.typography.fontWeight.medium)};
    transition: opacity ${({ theme }) => getThemeValue(theme, 'transitions.fast', fallbacks.transitions.fast)};

    &:active {
      opacity: 0.7;
    }

    &:disabled {
      background-color: ${({ theme }) => getThemeValue(theme, 'colors.disabled', fallbacks.colors.disabled)};
      cursor: not-allowed;
    }
  }

  /* iOS-like input styles */
  .ios-input {
    background-color: ${({ theme }) => getThemeValue(theme, 'colors.white', fallbacks.colors.white)};
    border: 1px solid ${({ theme }) => getThemeValue(theme, 'colors.secondaryLight', fallbacks.colors.secondaryLight)};
    padding: 12px 16px;
    border-radius: ${({ theme }) => getThemeValue(theme, 'borderRadius.medium', fallbacks.borderRadius.medium)};
    width: 100%;
    transition: border-color ${({ theme }) => getThemeValue(theme, 'transitions.fast', fallbacks.transitions.fast)};

    &:focus {
      border-color: ${({ theme }) => getThemeValue(theme, 'colors.primary', fallbacks.colors.primary)};
    }
  }

  /* iOS-like select styles */
  .ios-select {
    appearance: none;
    background-color: ${({ theme }) => getThemeValue(theme, 'colors.white', fallbacks.colors.white)};
    border: 1px solid ${({ theme }) => getThemeValue(theme, 'colors.secondaryLight', fallbacks.colors.secondaryLight)};
    padding: 12px 16px;
    padding-right: 40px;
    border-radius: ${({ theme }) => getThemeValue(theme, 'borderRadius.medium', fallbacks.borderRadius.medium)};
    width: 100%;
    background-image: url("data:image/svg+xml;charset=UTF-8,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3e%3cpolyline points='6 9 12 15 18 9'%3e%3c/polyline%3e%3c/svg%3e");
    background-repeat: no-repeat;
    background-position: right 12px center;
    background-size: 16px;
    transition: border-color ${({ theme }) => getThemeValue(theme, 'transitions.fast', fallbacks.transitions.fast)};

    &:focus {
      border-color: ${({ theme }) => getThemeValue(theme, 'colors.primary', fallbacks.colors.primary)};
    }
  }

  /* iOS-like card styles */
  .ios-card {
    background-color: ${({ theme }) => getThemeValue(theme, 'colors.white', fallbacks.colors.white)};
    border-radius: ${({ theme }) => getThemeValue(theme, 'borderRadius.medium', fallbacks.borderRadius.medium)};
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    padding: ${({ theme }) => getThemeValue(theme, 'spacing.lg', fallbacks.spacing.lg)};
  }

  /* iOS-like list styles */
  .ios-list {
    background-color: ${({ theme }) => getThemeValue(theme, 'colors.white', fallbacks.colors.white)};
    border-radius: ${({ theme }) => getThemeValue(theme, 'borderRadius.medium', fallbacks.borderRadius.medium)};
    overflow: hidden;
  }

  .ios-list-item {
    padding: ${({ theme }) => getThemeValue(theme, 'spacing.md', fallbacks.spacing.md)};
    border-bottom: 1px solid ${({ theme }) => getThemeValue(theme, 'colors.background', fallbacks.colors.background)};

    &:last-child {
      border-bottom: none;
    }
  }

  /* iOS-like scrollbar */
  ::-webkit-scrollbar {
    width: 8px;
    height: 8px;
  }

  ::-webkit-scrollbar-track {
    background: transparent;
  }

  ::-webkit-scrollbar-thumb {
    background: ${({ theme }) => getThemeValue(theme, 'colors.secondaryLight', fallbacks.colors.secondaryLight)};
    border-radius: 4px;
  }

  ::-webkit-scrollbar-thumb:hover {
    background: ${({ theme }) => getThemeValue(theme, 'colors.secondary', fallbacks.colors.secondary)};
  }

  /* iOS-like selection */
  ::selection {
    background: ${({ theme }) => getThemeValue(theme, 'colors.primaryLight', fallbacks.colors.primaryLight)};
    color: ${({ theme }) => getThemeValue(theme, 'colors.primary', fallbacks.colors.primary)};
  }
`; 