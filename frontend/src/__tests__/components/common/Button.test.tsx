import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { ThemeProvider } from 'styled-components';
import { Button } from '../../../components/common/Button';
import { theme } from '../../../theme';

describe('Button', () => {
  const renderWithTheme = (component: React.ReactNode) => {
    return render(
      <ThemeProvider theme={theme}>
        {component}
      </ThemeProvider>
    );
  };

  it('renders with default props', () => {
    renderWithTheme(<Button>Click me</Button>);
    const button = screen.getByRole('button', { name: 'Click me' });
    expect(button).toBeInTheDocument();
    expect(button).toHaveStyle({
      backgroundColor: theme.colors.primary,
      color: theme.colors.white
    });
  });

  it('renders with secondary variant', () => {
    renderWithTheme(<Button variant="secondary">Secondary</Button>);
    const button = screen.getByRole('button', { name: 'Secondary' });
    expect(button).toHaveStyle({
      backgroundColor: theme.colors.secondary,
      color: theme.colors.black
    });
  });

  it('renders with outline variant', () => {
    renderWithTheme(<Button variant="outline">Outline</Button>);
    const button = screen.getByRole('button', { name: 'Outline' });
    expect(button).toHaveStyle({
      backgroundColor: 'transparent',
      borderColor: theme.colors.primary,
      color: theme.colors.primary
    });
  });

  it('handles click events', () => {
    const handleClick = jest.fn();
    renderWithTheme(<Button onClick={handleClick}>Click me</Button>);
    const button = screen.getByRole('button', { name: 'Click me' });
    fireEvent.click(button);
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it('renders in disabled state', () => {
    renderWithTheme(<Button disabled>Disabled</Button>);
    const button = screen.getByRole('button', { name: 'Disabled' });
    expect(button).toBeDisabled();
    expect(button).toHaveStyle({
      opacity: '0.5',
      cursor: 'not-allowed'
    });
  });

  it('renders with custom size', () => {
    renderWithTheme(<Button size="large">Large</Button>);
    const button = screen.getByRole('button', { name: 'Large' });
    expect(button).toHaveStyle({
      padding: `${theme.spacing.md} ${theme.spacing.lg}`,
      fontSize: theme.typography.fontSize.lg
    });
  });

  it('renders with icon', () => {
    renderWithTheme(
      <Button icon={<span data-testid="test-icon">★</span>}>
        With Icon
      </Button>
    );
    expect(screen.getByTestId('test-icon')).toBeInTheDocument();
  });

  it('renders with loading state', () => {
    renderWithTheme(<Button loading>Loading</Button>);
    const button = screen.getByRole('button', { name: 'Loading' });
    expect(button).toBeDisabled();
    expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();
  });

  it('applies custom styles', () => {
    const customStyle = { backgroundColor: '#ff0000' };
    renderWithTheme(<Button style={customStyle}>Custom Style</Button>);
    const button = screen.getByRole('button', { name: 'Custom Style' });
    expect(button).toHaveStyle(customStyle);
  });

  it('renders with full width', () => {
    renderWithTheme(<Button fullWidth>Full Width</Button>);
    const button = screen.getByRole('button', { name: 'Full Width' });
    expect(button).toHaveStyle({ width: '100%' });
  });
}); 