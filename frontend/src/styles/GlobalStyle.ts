import { createGlobalStyle } from 'styled-components';
import { Theme } from '../theme';

export const GlobalStyle = createGlobalStyle<{ theme?: Theme }>`
  * {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
  }

  html {
    font-size: 16px;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen,
      Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
  }

  body {
    background-color: ${({ theme }) => theme?.colors?.background || '#F7FAFC'};
    color: ${({ theme }) => theme?.colors?.text || '#1F2937'};
    line-height: 1.5;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
  }

  button {
    font-family: inherit;
    border: none;
    background: none;
    cursor: pointer;
    padding: 0;
  }

  a {
    color: inherit;
    text-decoration: none;
  }

  img {
    max-width: 100%;
    height: auto;
  }

  input, textarea, select {
    font-family: inherit;
    font-size: inherit;
  }

  /* Scrollbar styling */
  ::-webkit-scrollbar {
    width: 8px;
    height: 8px;
  }

  ::-webkit-scrollbar-track {
    background: ${({ theme }) => theme?.colors?.background || '#F7FAFC'};
  }

  ::-webkit-scrollbar-thumb {
    background: ${({ theme }) => theme?.colors?.secondary || '#6B7280'};
    border-radius: 4px;
  }

  ::-webkit-scrollbar-thumb:hover {
    background: ${({ theme }) => theme?.colors?.secondaryDark || '#4B5563'};
  }

  /* Selection styling */
  ::selection {
    background: ${({ theme }) => theme?.colors?.primaryLight || '#6B93FE'};
    color: ${({ theme }) => theme?.colors?.white || '#FFFFFF'};
  }

  /* Focus outline */
  :focus {
    outline: 2px solid ${({ theme }) => theme?.colors?.primary || '#4D7CFE'};
    outline-offset: 2px;
  }

  /* Disable focus outline for mouse users */
  :focus:not(:focus-visible) {
    outline: none;
  }

  /* Enable focus outline for keyboard users */
  :focus-visible {
    outline: 2px solid ${({ theme }) => theme?.colors?.primary || '#4D7CFE'};
    outline-offset: 2px;
  }
`; 