import React from 'react';
import { render, screen } from '@testing-library/react';
import { ThemeProvider } from 'styled-components';
import { LoadingSpinner } from '../../../components/common/LoadingSpinner';
import { theme } from '../../../theme';

describe('LoadingSpinner', () => {
  const renderWithTheme = (component: React.ReactNode) => {
    return render(
      <ThemeProvider theme={theme}>
        {component}
      </ThemeProvider>
    );
  };

  it('renders with default props', () => {
    renderWithTheme(<LoadingSpinner />);
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
    expect(screen.getByText('Loading your fitness journey...')).toBeInTheDocument();
  });

  it('renders with custom size', () => {
    renderWithTheme(<LoadingSpinner size="large" />);
    const spinner = screen.getByRole('progressbar').parentElement;
    expect(spinner).toHaveStyle({ width: '64px', height: '64px' });
  });

  it('renders with custom text', () => {
    const customText = 'Custom loading text';
    renderWithTheme(<LoadingSpinner text={customText} />);
    expect(screen.getByText(customText)).toBeInTheDocument();
  });

  it('renders with custom aria-label', () => {
    const ariaLabel = 'Custom aria label';
    renderWithTheme(<LoadingSpinner ariaLabel={ariaLabel} />);
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-label', ariaLabel);
  });

  it('renders in full page mode', () => {
    renderWithTheme(<LoadingSpinner isFullPage />);
    const fullPageLoader = screen.getByRole('progressbar').closest('div[style*="position: fixed"]');
    expect(fullPageLoader).toBeInTheDocument();
  });

  it('renders without text when text prop is empty', () => {
    renderWithTheme(<LoadingSpinner text="" />);
    expect(screen.queryByText('Loading your fitness journey...')).not.toBeInTheDocument();
  });

  it('applies custom color', () => {
    const customColor = '#ff0000';
    renderWithTheme(<LoadingSpinner color={customColor} />);
    const svg = screen.getByRole('progressbar').querySelector('svg');
    expect(svg).toHaveStyle({ color: customColor });
  });
}); 