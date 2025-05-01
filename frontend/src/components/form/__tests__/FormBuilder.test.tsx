import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { FormBuilder } from '../FormBuilder';
import { FormField } from '../../../types/formBuilder';
import { ThemeProvider } from 'styled-components';
import { theme } from '../../../theme';

// Mock the useFormBuilder hook
const mockOnSubmit = jest.fn();

// Properly implement mockHandleSubmit to ensure it calls the callback with values
const mockHandleSubmit = jest.fn().mockImplementation(onSubmit => {
  return () => {
    // This simulates what the real handleSubmit does - it calls onSubmit with the values
    onSubmit({ test: 'value' });
    return true;
  };
});

jest.mock('../../../hooks/useFormBuilder', () => ({
  useFormBuilder: () => ({
    values: {},
    errors: {},
    touched: {},
    handleChange: jest.fn(),
    handleBlur: jest.fn(),
    handleSubmit: mockHandleSubmit,
    setFieldValue: jest.fn(),
    resetForm: jest.fn(),
    isSubmitting: false
  })
}));

describe('FormBuilder', () => {
  const mockFields: FormField[] = [
    {
      id: 'name',
      type: 'text',
      label: 'Name',
      placeholder: 'Enter your name',
      required: true
    },
    {
      id: 'email',
      type: 'email',
      label: 'Email',
      placeholder: 'Enter your email',
      required: true
    }
  ];

  const renderWithTheme = (ui: React.ReactElement) => {
    return render(
      <ThemeProvider theme={theme}>
        {ui}
      </ThemeProvider>
    );
  };
  
  beforeEach(() => {
    jest.clearAllMocks();
  });
  
  it('renders form builder', () => {
    renderWithTheme(<FormBuilder fields={mockFields} onSubmit={mockOnSubmit} />);
    expect(screen.getByTestId('form-builder')).toBeInTheDocument();
  });

  it('displays form fields', () => {
    renderWithTheme(<FormBuilder fields={mockFields} onSubmit={mockOnSubmit} />);
    mockFields.forEach(field => {
      expect(screen.getByTestId(`field-${field.id}`)).toBeInTheDocument();
      expect(screen.getByText(field.label)).toBeInTheDocument();
    });
  });

  it('has submit and reset buttons', () => {
    renderWithTheme(<FormBuilder fields={mockFields} onSubmit={mockOnSubmit} />);
    expect(screen.getByTestId('submit-button')).toBeInTheDocument();
    expect(screen.getByTestId('reset-button')).toBeInTheDocument();
  });

  it('submits form when submit button is clicked', () => {
    // Render the component
    renderWithTheme(<FormBuilder fields={mockFields} onSubmit={mockOnSubmit} />);
    
    // Get the form and submit it directly
    const form = screen.getByTestId('form-builder');
    fireEvent.submit(form);

    // The mockOnSubmit should have been called with the test value
    expect(mockOnSubmit).toHaveBeenCalledWith({ test: 'value' });
  });
}); 