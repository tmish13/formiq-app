import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { ThemeProvider } from 'styled-components';
import { Switch } from '../../../components/common/Switch';
import { theme } from '../../../theme';

describe('Switch', () => {
  const renderWithTheme = (component: React.ReactNode) => {
    return render(
      <ThemeProvider theme={theme}>
        {component}
      </ThemeProvider>
    );
  };

  it('renders with default props', () => {
    const handleChange = jest.fn();
    renderWithTheme(<Switch checked={false} onChange={handleChange} />);
    const switchElement = screen.getByRole('switch');
    expect(switchElement).toBeInTheDocument();
    expect(switchElement).toHaveAttribute('aria-checked', 'false');
  });

  it('renders with label', () => {
    const label = 'Test Label';
    renderWithTheme(<Switch label={label} />);
    expect(screen.getByText(label)).toBeInTheDocument();
  });

  it('handles checked state', () => {
    const handleChange = jest.fn();
    renderWithTheme(<Switch checked={true} onChange={handleChange} />);
    expect(screen.getByRole('switch')).toHaveAttribute('aria-checked', 'true');
  });

  it('handles change events', () => {
    const handleChange = jest.fn();
    renderWithTheme(<Switch checked={false} onChange={handleChange} />);
    const switchElement = screen.getByRole('switch');
    fireEvent.click(switchElement);
    expect(handleChange).toHaveBeenCalled();
  });

  it('renders as disabled', () => {
    const handleChange = jest.fn();
    renderWithTheme(<Switch checked={false} onChange={handleChange} disabled />);
    const switchElement = screen.getByRole('switch');
    expect(switchElement).toHaveStyle({ opacity: '0.5', cursor: 'not-allowed' });
    fireEvent.click(switchElement);
    expect(handleChange).not.toHaveBeenCalled();
  });

  it('renders with custom className', () => {
    const className = 'custom-switch';
    renderWithTheme(<Switch className={className} />);
    expect(screen.getByRole('switch')).toHaveClass(className);
  });

  it('renders with custom size', () => {
    renderWithTheme(<Switch size="large" />);
    const switchElement = screen.getByRole('switch');
    expect(switchElement).toHaveStyle({
      width: '48px',
      height: '24px'
    });
  });

  it('renders with custom color', () => {
    const color = '#ff0000';
    renderWithTheme(<Switch color={color} />);
    const switchElement = screen.getByRole('switch');
    expect(switchElement).toHaveStyle({
      backgroundColor: color
    });
  });

  it('renders with custom name', () => {
    const name = 'test-switch';
    renderWithTheme(<Switch name={name} />);
    expect(screen.getByRole('switch')).toHaveAttribute('name', name);
  });

  it('renders with custom value', () => {
    const value = 'test-value';
    renderWithTheme(<Switch value={value} />);
    expect(screen.getByRole('switch')).toHaveAttribute('value', value);
  });

  it('renders with aria-label', () => {
    const handleChange = jest.fn();
    const ariaLabel = 'Toggle feature';
    renderWithTheme(
      <Switch 
        checked={false} 
        onChange={handleChange} 
        aria-label={ariaLabel} 
      />
    );
    expect(screen.getByRole('switch')).toHaveAttribute('aria-label', ariaLabel);
  });
}); 