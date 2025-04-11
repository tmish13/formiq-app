import React from 'react';
import { render, screen } from '@testing-library/react';
import { ThemeProvider } from 'styled-components';
import LoadingScreen from '../../../components/common/LoadingScreen';
import { theme } from '../../../theme';

describe('LoadingScreen', () => {
  const renderWithTheme = (component: React.ReactNode) => {
    return render(
      <ThemeProvider theme={theme}>
        {component}
      </ThemeProvider>
    );
  };

  it('renders with default props', () => {
    renderWithTheme(<LoadingScreen />);
    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });

  it('renders with custom message', () => {
    const message = 'Custom loading message';
    renderWithTheme(<LoadingScreen message={message} />);
    expect(screen.getByText(message)).toBeInTheDocument();
  });

  it('renders in full screen mode', () => {
    renderWithTheme(<LoadingScreen fullScreen />);
    const container = screen.getByText('Loading...').parentElement;
    expect(container).toHaveStyle({
      minHeight: '100vh',
      padding: '0'
    });
  });

  it('renders with default screen mode', () => {
    renderWithTheme(<LoadingScreen />);
    const container = screen.getByText('Loading...').parentElement;
    expect(container).toHaveStyle({
      minHeight: '200px',
      padding: '2rem'
    });
  });

  it('renders with custom aria-label', () => {
    const ariaLabel = 'Custom loading aria-label';
    renderWithTheme(<LoadingScreen ariaLabel={ariaLabel} />);
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-label', ariaLabel);
  });

  it('renders with custom background color', () => {
    const backgroundColor = '#f5f5f5';
    renderWithTheme(<LoadingScreen backgroundColor={backgroundColor} />);
    expect(screen.getByTestId('loading-screen')).toHaveStyle({
      backgroundColor
    });
  });

  it('renders with custom spinner color', () => {
    const spinnerColor = '#ff0000';
    renderWithTheme(<LoadingScreen spinnerColor={spinnerColor} />);
    const spinner = screen.getByRole('progressbar').querySelector('svg');
    expect(spinner).toHaveStyle({ color: spinnerColor });
  });
}); 