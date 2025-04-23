import React from 'react';
import { render, screen } from '@testing-library/react';
import { ThemeProvider } from 'styled-components';
import { LoadingSpinner } from '../../../../src/components/common/LoadingSpinner';
import { theme } from '../../../../src/theme';

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
    const spinner = screen.getByRole('status');
    expect(spinner).toBeInTheDocument();
    expect(spinner).toHaveAttribute('aria-label', 'Loading');
  });

  it('renders with custom size', () => {
    renderWithTheme(<LoadingSpinner size="large" />);
    const spinner = screen.getByRole('status');
    expect(spinner).toBeInTheDocument();
  });

  it('renders with custom color', () => {
    renderWithTheme(<LoadingSpinner color="#ff0000" />);
    const spinner = screen.getByRole('status');
    expect(spinner).toBeInTheDocument();
  });

  it('renders with custom aria-label', () => {
    const ariaLabel = 'Custom aria label';
    renderWithTheme(<LoadingSpinner ariaLabel={ariaLabel} />);
    expect(screen.getByRole('status')).toHaveAttribute('aria-label', ariaLabel);
  });

  it('renders with custom test ID', () => {
    const testId = 'custom-spinner';
    renderWithTheme(<LoadingSpinner testId={testId} />);
    expect(screen.getByTestId(testId)).toBeInTheDocument();
  });
}); 