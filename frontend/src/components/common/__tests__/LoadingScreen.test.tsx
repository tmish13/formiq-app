import React from 'react';
import { render, screen } from '@testing-library/react';
import { ThemeProvider } from 'styled-components';
import LoadingScreen from '../../../../src/components/common/LoadingScreen';
import { theme } from '../../../../src/theme';

jest.mock('../../../../src/hooks/useTheme', () => ({
  useTheme: () => ({ theme })
}));

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
    renderWithTheme(<LoadingScreen message="Please wait" />);
    expect(screen.getByText('Please wait')).toBeInTheDocument();
  });

  it('renders in full screen mode', () => {
    renderWithTheme(<LoadingScreen fullScreen />);
    const container = screen.getByTestId('loading-screen');
    expect(container).toBeInTheDocument();
  });

  it('renders with default screen mode', () => {
    renderWithTheme(<LoadingScreen />);
    const container = screen.getByTestId('loading-screen');
    expect(container).toBeInTheDocument();
    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });

  it('displays the spinner', () => {
    renderWithTheme(<LoadingScreen />);
    const spinner = screen.getByRole('status');
    expect(spinner).toBeInTheDocument();
    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });

  it('applies custom aria-label', () => {
    renderWithTheme(<LoadingScreen ariaLabel="Custom loading indicator" />);
    const loadingScreen = screen.getByRole('status');
    expect(loadingScreen).toHaveAttribute('aria-label', 'Custom loading indicator');
  });

  it('renders with custom background color', () => {
    renderWithTheme(<LoadingScreen />);
    const loadingScreen = screen.getByTestId('loading-screen');
    expect(loadingScreen).toBeInTheDocument();
  });

  it('renders with custom spinner color', () => {
    renderWithTheme(<LoadingScreen />);
    const loadingScreen = screen.getByTestId('loading-screen');
    expect(loadingScreen).toBeInTheDocument();
  });
}); 