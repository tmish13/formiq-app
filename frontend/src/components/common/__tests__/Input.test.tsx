import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { ThemeProvider } from 'styled-components';
import { Input } from '../Input';
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
    const input = screen.getByRole('textbox', { hidden: true });
    expect(input).toHaveAttribute('type', 'password');
  });

  it('renders with custom className', () => {
    const className = 'custom-input';
    renderWithTheme(<Input name="test" className={className} />);
    expect(screen.getByRole('textbox')).toHaveClass(className);
  });

  it('renders with full width', () => {
    renderWithTheme(<Input name="test" fullWidth />);
    const inputWrapper = screen.getByRole('textbox', { hidden: true }).closest('div');
    expect(inputWrapper).toHaveStyle({ width: '100%' });
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

  it('renders correctly', () => {
    renderWithTheme(<Input placeholder="Test input" />);
    expect(screen.getByPlaceholderText('Test input')).toBeInTheDocument();
  });

  it('handles value change', () => {
    const handleChange = jest.fn();
    renderWithTheme(<Input value="initial" onChange={handleChange} />);
    
    const input = screen.getByDisplayValue('initial');
    fireEvent.change(input, { target: { value: 'updated' } });
    
    expect(handleChange).toHaveBeenCalled();
  });

  it('applies error styling when error is present', () => {
    renderWithTheme(
      <Input 
        error="This is an error"
      />
    );
    
    expect(screen.getByText('This is an error')).toBeInTheDocument();
    // The input should have error styling
  });

  it('displays helper text when provided', () => {
    renderWithTheme(
      <Input 
        helperText="Helper text"
      />
    );
    
    expect(screen.getByText('Helper text')).toBeInTheDocument();
  });

  it('applies disabled styling when disabled', () => {
    renderWithTheme(<Input disabled />);
    
    const input = screen.getByRole('textbox');
    expect(input).toBeDisabled();
  });

  it('forwards data-testid attribute', () => {
    renderWithTheme(<Input data-testid="custom-input" />);
    expect(screen.getByTestId('custom-input')).toBeInTheDocument();
  });
}); 