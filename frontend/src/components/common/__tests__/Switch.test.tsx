import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { ThemeProvider } from 'styled-components';
import { Switch } from '../Switch';
import { mockTheme } from '../../../theme/mockTheme';

// Mock the fallbacks object that is used in Switch.tsx
jest.mock('../../../utils/themeUtils', () => ({
  getThemeValue: (theme: any, path: string, fallback?: string) => {
    // For tests, just return the fallback
    return fallback || '#000';
  },
  fallbacks: {
    color: {
      primary: '#3f51b5',
      border: '#e0e0e0',
      white: '#ffffff',
    },
    shadows: {
      sm: '0 1px 3px rgba(0, 0, 0, 0.12), 0 1px 2px rgba(0, 0, 0, 0.24)',
    }
  }
}));

// Custom render function with theme provider
const renderWithTheme = (ui: React.ReactElement) => {
  return render(
    <ThemeProvider theme={mockTheme as any}>
      {ui}
    </ThemeProvider>
  );
};

describe('Switch', () => {
  it('renders properly', () => {
    renderWithTheme(<Switch checked={false} onChange={() => {}} />);
    expect(screen.getByRole('switch')).toBeInTheDocument();
  });

  it('can be toggled', () => {
    const handleChange = jest.fn();
    renderWithTheme(<Switch checked={false} onChange={handleChange} />);
    
    const switchElement = screen.getByRole('switch');
    
    // Default state should be unchecked
    expect(switchElement).toHaveAttribute('aria-checked', 'false');
    
    // Click to toggle
    fireEvent.click(switchElement);
    expect(handleChange).toHaveBeenCalled();
  });

  it('works with controlled components', () => {
    const handleChange = jest.fn();
    
    renderWithTheme(
      <Switch 
        checked={true} 
        onChange={handleChange} 
      />
    );
    
    const switchElement = screen.getByRole('switch');
    expect(switchElement).toHaveAttribute('aria-checked', 'true');
    
    fireEvent.click(switchElement);
    expect(handleChange).toHaveBeenCalled();
  });

  it('applies disabled styling when disabled', () => {
    renderWithTheme(<Switch checked={false} onChange={() => {}} disabled />);
    
    const switchElement = screen.getByRole('switch');
    expect(switchElement).toHaveAttribute('aria-disabled', 'true');
  });
}); 