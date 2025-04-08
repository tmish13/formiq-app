import { createGlobalStyle } from 'styled-components';
// No need to import Theme as it's defined in the DefaultTheme from styled-components

export const GlobalStyles = createGlobalStyle`
  * {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
    -webkit-tap-highlight-color: transparent;
  }

  html {
    font-size: 16px;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    
    @media (max-width: ${({ theme }) => theme.breakpoints.sm}) {
      font-size: 14px;
    }
  }

  body {
    font-family: ${({ theme }) => theme.typography?.fontFamily?.base || "'Inter', sans-serif"};
    font-size: ${({ theme }) => theme.typography?.fontSize?.base || '16px'};
    line-height: 1.5;
    color: ${({ theme }) => theme.colors?.text || '#212529'};
    background-color: ${({ theme }) => theme.colors?.background || '#f8f9fa'};
    overflow-x: hidden;
    text-size-adjust: 100%;
    -webkit-text-size-adjust: 100%;
  }

  h1, h2, h3, h4, h5, h6 {
    font-weight: ${({ theme }) => theme.typography?.fontWeight?.bold || 700};
    line-height: 1.2;
    margin-bottom: ${({ theme }) => theme.spacing?.md || '1rem'};
  }

  h1 {
    font-size: ${({ theme }) => theme.typography?.fontSize?.xxl || '2.5rem'};
    
    @media (max-width: ${({ theme }) => theme.breakpoints.sm}) {
      font-size: 2rem;
    }
  }

  h2 {
    font-size: ${({ theme }) => theme.typography?.fontSize?.xl || '2rem'};
    
    @media (max-width: ${({ theme }) => theme.breakpoints.sm}) {
      font-size: 1.75rem;
    }
  }

  h3 {
    font-size: ${({ theme }) => theme.typography?.fontSize?.lg || '1.75rem'};
    
    @media (max-width: ${({ theme }) => theme.breakpoints.sm}) {
      font-size: 1.5rem;
    }
  }

  p {
    margin-bottom: ${({ theme }) => theme.spacing?.md || '1rem'};
  }

  a {
    color: ${({ theme }) => theme.colors?.primary || '#0d6efd'};
    text-decoration: none;
    transition: color ${({ theme }) => theme.transitions?.fast || '0.2s ease'};
    touch-action: manipulation;
    
    &:hover {
      color: ${({ theme }) => theme.colors?.primaryDark || '#0a58ca'};
    }
  }

  /* Improve touch targets on mobile */
  button, 
  input[type="button"], 
  input[type="submit"], 
  input[type="reset"],
  a {
    min-height: 44px;
    min-width: 44px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
  }
  
  /* Add safe areas for iPhone X and newer */
  @supports (padding: max(0px)) {
    body {
      padding-left: env(safe-area-inset-left);
      padding-right: env(safe-area-inset-right);
      padding-bottom: env(safe-area-inset-bottom);
    }
  }

  button {
    cursor: pointer;
    font-family: inherit;
    font-size: inherit;
    line-height: inherit;
    touch-action: manipulation;
  }

  img {
    max-width: 100%;
    height: auto;
  }

  input, 
  textarea, 
  select {
    font-family: inherit;
    font-size: inherit;
    
    @media (max-width: ${({ theme }) => theme.breakpoints.sm}) {
      font-size: 16px; /* Prevents iOS zoom on focus */
    }
  }

  ul, ol {
    margin-bottom: ${({ theme }) => theme.spacing?.md || '1rem'};
    padding-left: ${({ theme }) => theme.spacing?.md || '1rem'};
  }

  code {
    font-family: ${({ theme }) => theme.typography?.fontFamily?.mono || 'monospace'};
    font-size: ${({ theme }) => theme.typography?.fontSize?.sm || '0.875rem'};
    background-color: ${({ theme }) => theme.colors?.secondaryLight || '#e9ecef'};
    padding: ${({ theme }) => theme.spacing?.xs || '0.25rem'} ${({ theme }) => theme.spacing?.sm || '0.5rem'};
    border-radius: ${({ theme }) => theme.borderRadius?.sm || '0.25rem'};
  }

  pre {
    background-color: ${({ theme }) => theme.colors?.secondaryLight || '#e9ecef'};
    padding: ${({ theme }) => theme.spacing?.md || '1rem'};
    border-radius: ${({ theme }) => theme.borderRadius?.md || '0.5rem'};
    overflow-x: auto;
    margin-bottom: ${({ theme }) => theme.spacing?.md || '1rem'};
  }

  blockquote {
    border-left: 4px solid ${({ theme }) => theme.colors?.primary || '#0d6efd'};
    padding-left: ${({ theme }) => theme.spacing?.md || '1rem'};
    margin-bottom: ${({ theme }) => theme.spacing?.md || '1rem'};
    color: ${({ theme }) => theme.colors?.textSecondary || '#6c757d'};
  }

  table {
    width: 100%;
    border-collapse: collapse;
    margin-bottom: ${({ theme }) => theme.spacing?.md || '1rem'};
    overflow-x: auto;
    display: block;
    
    @media (min-width: ${({ theme }) => theme.breakpoints.md}) {
      display: table;
    }
  }

  th, td {
    padding: ${({ theme }) => theme.spacing?.sm || '0.5rem'};
    border: 1px solid ${({ theme }) => theme.colors?.border || '#dee2e6'};
    text-align: left;
  }

  th {
    background-color: ${({ theme }) => theme.colors?.secondaryLight || '#e9ecef'};
    font-weight: ${({ theme }) => theme.typography?.fontWeight?.semibold || 600};
  }

  tr:nth-child(even) {
    background-color: ${({ theme }) => theme.colors?.secondaryLight || '#e9ecef'};
  }

  .loading-spinner {
    display: inline-block;
    width: 20px;
    height: 20px;
    border: 2px solid ${({ theme }) => theme.colors?.white || '#ffffff'};
    border-radius: 50%;
    border-top-color: transparent;
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }
  
  /* Add swipe gesture support */
  * {
    touch-action: pan-x pan-y;
  }
  
  /* Disable pull-to-refresh browser behavior */
  html {
    overscroll-behavior-y: contain;
  }
`; 