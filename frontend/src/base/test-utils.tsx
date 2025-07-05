import React from 'react';
import { render, RenderOptions } from '@testing-library/react';
import { ModernThemeProvider } from '../contexts/ModernThemeContext';

const AllTheProviders: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <ModernThemeProvider>
      {children}
    </ModernThemeProvider>
  );
};

const customRender = (
  ui: React.ReactElement,
  options?: Omit<RenderOptions, 'wrapper'>
) => render(ui, { wrapper: AllTheProviders, ...options });

export * from '@testing-library/react';
export { customRender as render, customRender as testRender }; 