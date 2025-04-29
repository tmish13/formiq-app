import React from 'react';
import { render, screen } from '@testing-library/react';
import { ThemeProvider } from 'styled-components';
import { LoadingSpinner } from '../LoadingSpinner';
import { theme } from '../../../theme';

describe('LoadingSpinner', () => {
  const renderWithTheme = (component: React.ReactNode) => {
    return render(
      <ThemeProvider theme={theme}>
        {component}
      </ThemeProvider>
    );
  };

  it('renders properly with default props', () => {
    renderWithTheme(<LoadingSpinner />);
    const spinner = screen.getByRole('progressbar');
    expect(spinner).toBeInTheDocument();
    expect(spinner).toHaveAttribute('aria-label', 'Loading');
  });

  it('renders with custom aria-label', () => {
    const ariaLabel = 'Custom aria label';
    renderWithTheme(<LoadingSpinner ariaLabel={ariaLabel} />);
    const spinner = screen.getByRole('progressbar');
    expect(spinner).toBeInTheDocument();
    expect(spinner).toHaveAttribute('aria-label', ariaLabel);
  });
}); 