import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { ThemeProvider } from 'styled-components';
import { Button } from '../../../../src/components/common/Button';

// Mocked theme with properties required for the Button component
const mockTheme = {
  colors: {
    primary: '#3f51b5',
    primaryDark: '#303f9f',
    primaryLight: '#7986cb',
    secondary: '#f50057',
    secondaryDark: '#c51162',
    secondaryLight: '#ff4081',
    white: '#ffffff',
    black: '#000000',
    text: '#000000',
    textSecondary: '#666666',
    error: '#f44336',
    errorLight: '#e57373',
    success: '#4caf50',
    successLight: '#81c784',
    warning: '#ff9800',
    warningLight: '#ffb74d',
    background: '#ffffff',
    surface: '#ffffff',
    border: '#e0e0e0',
    disabled: '#e0e0e0'
  },
  typography: {
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
    fontSize: {
      xs: '0.75rem',
      sm: '0.875rem',
      md: '1rem',
      lg: '1.125rem',
      xl: '1.25rem'
    },
    fontWeight: {
      regular: 400,
      medium: 500,
      bold: 700
    }
  },
  spacing: {
    xs: '4px',
    sm: '8px',
    md: '16px',
    lg: '24px',
    xl: '32px'
  },
  borderRadius: {
    sm: '4px',
    md: '8px',
    lg: '12px'
  },
  shadows: {
    sm: '0 1px 3px rgba(0, 0, 0, 0.1)',
    md: '0 4px 6px rgba(0, 0, 0, 0.1)',
    lg: '0 8px 16px rgba(0, 0, 0, 0.1)'
  },
  breakpoints: {
    mobile: '320px',
    tablet: '768px',
    desktop: '1024px',
    wide: '1440px'
  },
  transitions: {
    fast: '0.2s',
    medium: '0.3s',
    slow: '0.5s'
  },
  zIndex: {
    modal: 1000,
    overlay: 900,
    dropdown: 800,
    header: 700
  }
};

describe('Button', () => {
  const renderWithTheme = (component: React.ReactNode) => {
    return render(
      <ThemeProvider theme={mockTheme}>
        {component}
      </ThemeProvider>
    );
  };

  it('renders with default props', () => {
    renderWithTheme(<Button>Click me</Button>);
    const button = screen.getByRole('button', { name: 'Click me' });
    expect(button).toBeInTheDocument();
  });

  it('renders with secondary variant', () => {
    renderWithTheme(<Button variant="secondary">Secondary</Button>);
    const button = screen.getByRole('button', { name: 'Secondary' });
    expect(button).toBeInTheDocument();
  });

  it('renders with outline variant', () => {
    renderWithTheme(<Button variant="outline">Outline</Button>);
    const button = screen.getByRole('button', { name: 'Outline' });
    expect(button).toBeInTheDocument();
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
  });

  it('renders with custom size', () => {
    renderWithTheme(<Button size="large">Large</Button>);
    const button = screen.getByRole('button', { name: 'Large' });
    expect(button).toBeInTheDocument();
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
    renderWithTheme(<Button isLoading>Loading</Button>);
    const button = screen.getByRole('button', { name: '' });
    expect(button).toBeDisabled();
  });

  it('applies custom styles', () => {
    const customStyle = { backgroundColor: '#ff0000' };
    renderWithTheme(<Button style={customStyle}>Custom Style</Button>);
    const button = screen.getByRole('button', { name: 'Custom Style' });
    expect(button).toBeInTheDocument();
  });

  it('renders with full width', () => {
    renderWithTheme(<Button fullWidth>Full Width</Button>);
    const button = screen.getByRole('button', { name: 'Full Width' });
    expect(button).toBeInTheDocument();
  });
}); 