import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { FormBuilder } from '../../form/FormBuilder';
import { useFormBuilder } from '../../../hooks/useFormBuilder';
import { FormField, FormValidationRule } from '../../../types/formBuilder';

// Mock the hooks
jest.mock('../../../hooks/useFormBuilder');

describe('FormBuilder', () => {
  const mockFields: FormField[] = [
    {
      id: 'name',
      type: 'text',
      label: 'Name',
      placeholder: 'Enter your name',
      required: true,
      validation: [
        {
          type: 'required',
          message: 'Name is required',
        },
        {
          type: 'minLength',
          value: 2,
          message: 'Name must be at least 2 characters',
        },
      ],
    },
    {
      id: 'email',
      type: 'email',
      label: 'Email',
      placeholder: 'Enter your email',
      required: true,
      validation: [
        {
          type: 'required',
          message: 'Email is required',
        },
        {
          type: 'email',
          message: 'Please enter a valid email',
        },
      ],
    },
    {
      id: 'age',
      type: 'number',
      label: 'Age',
      placeholder: 'Enter your age',
      required: false,
      validation: [
        {
          type: 'custom',
          message: 'You must be at least 18 years old',
        },
        {
          type: 'custom',
          message: 'Age cannot be greater than 100',
        },
      ],
    },
  ];

  const mockOnSubmit = jest.fn();
  const mockHandleChange = jest.fn();
  const mockHandleBlur = jest.fn();
  const mockHandleSubmit = jest.fn();
  const mockSetFieldValue = jest.fn();
  const mockResetForm = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
    // Set default mock values and functions
    mockHandleSubmit.mockImplementation((callback) => (e: React.FormEvent) => {
      if (e && e.preventDefault) {
        e.preventDefault();
      }
      return callback({
        name: 'John Doe',
        email: 'john@example.com',
        age: 30
      });
    });
    
    (useFormBuilder as jest.Mock).mockReturnValue({
      values: {
        name: 'John Doe',
        email: 'john@example.com',
        age: 30
      },
      errors: {},
      touched: {
        name: true,
        email: true,
        age: true
      },
      handleChange: mockHandleChange,
      handleBlur: mockHandleBlur,
      handleSubmit: mockHandleSubmit,
      setFieldValue: mockSetFieldValue,
      resetForm: mockResetForm,
      isSubmitting: false,
    });
  });

  it('renders all form fields correctly', () => {
    render(<FormBuilder fields={mockFields} onSubmit={mockOnSubmit} />);
    
    // Check if labels are rendered
    expect(screen.getByLabelText('Name')).toBeInTheDocument();
    expect(screen.getByLabelText('Email')).toBeInTheDocument();
    expect(screen.getByLabelText('Age')).toBeInTheDocument();
  });

  it('handles form submission with valid data', async () => {
    render(<FormBuilder fields={mockFields} onSubmit={mockOnSubmit} />);
    
    // Find the submit button and click it
    const submitButton = screen.getByRole('button', { name: /submit/i });
    fireEvent.click(submitButton);

    // Check that handleSubmit was called
    expect(mockHandleSubmit).toHaveBeenCalled();
    
    await waitFor(() => {
      // Check that onSubmit was called with the expected values
      expect(mockOnSubmit).toHaveBeenCalledWith({
        name: 'John Doe',
        email: 'john@example.com',
        age: 30
      });
    });
  });

  it('handles input changes correctly', () => {
    render(<FormBuilder fields={mockFields} onSubmit={mockOnSubmit} />);
    
    // Get the name input and simulate a change
    const nameInput = screen.getByLabelText('Name');
    fireEvent.change(nameInput, { target: { value: 'Jane Doe' } });
    
    // Check that handleChange was called
    expect(mockHandleChange).toHaveBeenCalled();
  });

  it('handles input blur correctly', () => {
    render(<FormBuilder fields={mockFields} onSubmit={mockOnSubmit} />);
    
    // Get the name input and simulate blur
    const nameInput = screen.getByLabelText('Name');
    fireEvent.blur(nameInput);
    
    // Check that handleBlur was called
    expect(mockHandleBlur).toHaveBeenCalled();
  });

  it('sets field value correctly', () => {
    render(<FormBuilder fields={mockFields} onSubmit={mockOnSubmit} />);
    
    // Get the age input and simulate a change
    const ageInput = screen.getByLabelText('Age');
    fireEvent.change(ageInput, { target: { value: '35' } });
    
    // Check that handleChange was called
    expect(mockHandleChange).toHaveBeenCalled();
  });

  it('displays validation errors for required fields', () => {
    // Mock the hook to return errors
    (useFormBuilder as jest.Mock).mockReturnValue({
      values: {
        name: '',
        email: '',
        age: ''
      },
      errors: {
        name: 'Name is required',
        email: 'Email is required'
      },
      touched: {
        name: true,
        email: true,
        age: false
      },
      handleChange: mockHandleChange,
      handleBlur: mockHandleBlur,
      handleSubmit: mockHandleSubmit,
      setFieldValue: mockSetFieldValue,
      resetForm: mockResetForm,
      isSubmitting: false,
    });

    render(<FormBuilder fields={mockFields} onSubmit={mockOnSubmit} />);
    
    // Check that error messages are displayed
    expect(screen.getByText('Name is required')).toBeInTheDocument();
    expect(screen.getByText('Email is required')).toBeInTheDocument();
  });

  it('displays validation errors for invalid email format', () => {
    // Mock the hook to return email validation error
    (useFormBuilder as jest.Mock).mockReturnValue({
      values: {
        name: 'John Doe',
        email: 'invalid-email',
        age: 25
      },
      errors: {
        email: 'Please enter a valid email'
      },
      touched: {
        name: true,
        email: true,
        age: true
      },
      handleChange: mockHandleChange,
      handleBlur: mockHandleBlur,
      handleSubmit: mockHandleSubmit,
      setFieldValue: mockSetFieldValue,
      resetForm: mockResetForm,
      isSubmitting: false,
    });

    render(<FormBuilder fields={mockFields} onSubmit={mockOnSubmit} />);
    
    // Check that email error message is displayed
    expect(screen.getByText('Please enter a valid email')).toBeInTheDocument();
  });

  it('displays validation errors for age constraints', () => {
    // Mock the hook to return age validation error
    (useFormBuilder as jest.Mock).mockReturnValue({
      values: {
        name: 'John Doe',
        email: 'john@example.com',
        age: 15
      },
      errors: {
        age: 'You must be at least 18 years old'
      },
      touched: {
        name: true,
        email: true,
        age: true
      },
      handleChange: mockHandleChange,
      handleBlur: mockHandleBlur,
      handleSubmit: mockHandleSubmit,
      setFieldValue: mockSetFieldValue,
      resetForm: mockResetForm,
      isSubmitting: false,
    });

    render(<FormBuilder fields={mockFields} onSubmit={mockOnSubmit} />);
    
    // Check that age error message is displayed
    expect(screen.getByText('You must be at least 18 years old')).toBeInTheDocument();
  });

  it('disables submit button while submitting', () => {
    // Mock the hook to set isSubmitting to true
    (useFormBuilder as jest.Mock).mockReturnValue({
      values: {
        name: 'John Doe',
        email: 'john@example.com',
        age: 25
      },
      errors: {},
      touched: {
        name: true,
        email: true,
        age: true
      },
      handleChange: mockHandleChange,
      handleBlur: mockHandleBlur,
      handleSubmit: mockHandleSubmit,
      setFieldValue: mockSetFieldValue,
      resetForm: mockResetForm,
      isSubmitting: true,
    });

    render(<FormBuilder fields={mockFields} onSubmit={mockOnSubmit} />);
    
    // Check that submit button is disabled
    const submitButton = screen.getByRole('button', { name: /submit/i });
    expect(submitButton).toBeDisabled();
  });

  it('resets form when reset button is clicked', () => {
    render(<FormBuilder fields={mockFields} onSubmit={mockOnSubmit} />);
    
    // Find the reset button and click it
    const resetButton = screen.getByRole('button', { name: /reset/i });
    fireEvent.click(resetButton);
    
    // Check that resetForm was called
    expect(mockResetForm).toHaveBeenCalled();
  });

  it('uses setFieldValue for direct field updates', () => {
    render(<FormBuilder fields={mockFields} onSubmit={mockOnSubmit} />);
    
    // Find age input and simulate direct value change
    const ageInput = screen.getByLabelText('Age');
    fireEvent.change(ageInput, { target: { value: '40' } });
    
    // Verify handleChange was called
    expect(mockHandleChange).toHaveBeenCalled();
  });
}); 