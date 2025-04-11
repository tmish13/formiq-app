import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { ThemeProvider } from 'styled-components';
import { Input } from '../../../components/common/Input';
import { theme } from '../../../theme';

describe('Input', () => {
  const renderWithTheme = (component: React.ReactNode) => {
    return render(
      <ThemeProvider theme={theme}>
        {component}
      </ThemeProvider>
    );
  };

  it('renders with default props', () => {
    renderWithTheme(<Input name="test" />);
    const input = screen.getByRole('textbox');
    expect(input).toBeInTheDocument();
    expect(input).toHaveAttribute('name', 'test');
  });

  it('renders with label', () => {
    const label = 'Test Label';
    renderWithTheme(<Input name="test" label={label} />);
    expect(screen.getByLabelText(label)).toBeInTheDocument();
  });

  it('renders with placeholder', () => {
    const placeholder = 'Enter text...';
    renderWithTheme(<Input name="test" placeholder={placeholder} />);
    expect(screen.getByPlaceholderText(placeholder)).toBeInTheDocument();
  });

  it('handles value changes', () => {
    const handleChange = jest.fn();
    renderWithTheme(<Input name="test" onChange={handleChange} />);
    const input = screen.getByRole('textbox');
    fireEvent.change(input, { target: { value: 'test value' } });
    expect(handleChange).toHaveBeenCalled();
  });

  it('renders with error message', () => {
    const errorMessage = 'This field is required';
    renderWithTheme(<Input name="test" error={errorMessage} />);
    expect(screen.getByText(errorMessage)).toBeInTheDocument();
    expect(screen.getByRole('textbox')).toHaveAttribute('aria-invalid', 'true');
  });

  it('renders with helper text', () => {
    const helperText = 'Helper text';
    renderWithTheme(<Input name="test" helperText={helperText} />);
    expect(screen.getByText(helperText)).toBeInTheDocument();
  });

  it('renders as required', () => {
    renderWithTheme(<Input name="test" required />);
    expect(screen.getByRole('textbox')).toBeRequired();
  });

  it('renders as disabled', () => {
    renderWithTheme(<Input name="test" disabled />);
    expect(screen.getByRole('textbox')).toBeDisabled();
  });

  it('renders with custom type', () => {
    renderWithTheme(<Input name="test" type="password" />);
    expect(screen.getByRole('textbox')).toHaveAttribute('type', 'password');
  });

  it('renders with custom className', () => {
    const className = 'custom-input';
    renderWithTheme(<Input name="test" className={className} />);
    expect(screen.getByRole('textbox')).toHaveClass(className);
  });

  it('renders with full width', () => {
    renderWithTheme(<Input name="test" fullWidth />);
    expect(screen.getByRole('textbox').parentElement?.parentElement).toHaveStyle({ width: '100%' });
  });

  it('renders with icon', () => {
    const icon = <span data-testid="test-icon">★</span>;
    renderWithTheme(<Input name="test" icon={icon} />);
    expect(screen.getByTestId('test-icon')).toBeInTheDocument();
  });

  it('renders with end icon', () => {
    const endIcon = <span data-testid="test-end-icon">★</span>;
    renderWithTheme(<Input name="test" endIcon={endIcon} />);
    expect(screen.getByTestId('test-end-icon')).toBeInTheDocument();
  });

  it('renders with filled variant', () => {
    renderWithTheme(<Input name="test" variant="filled" />);
    const input = screen.getByRole('textbox');
    expect(input).toHaveStyle({
      backgroundColor: `${theme.colors.border}40`
    });
  });

  it('handles focus and blur events', () => {
    const handleFocus = jest.fn();
    const handleBlur = jest.fn();
    renderWithTheme(
      <Input 
        name="test" 
        onFocus={handleFocus}
        onBlur={handleBlur}
      />
    );
    const input = screen.getByRole('textbox');
    fireEvent.focus(input);
    expect(handleFocus).toHaveBeenCalled();
    fireEvent.blur(input);
    expect(handleBlur).toHaveBeenCalled();
  });
}); 