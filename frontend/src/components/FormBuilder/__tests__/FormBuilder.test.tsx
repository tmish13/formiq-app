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
          type: 'min',
          value: 18,
          message: 'You must be at least 18 years old',
        },
        {
          type: 'max',
          value: 100,
          message: 'Age cannot be greater than 100',
        },
      ],
    },
  ];

  const mockOnSubmit = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
    (useFormBuilder as jest.Mock).mockReturnValue({
      values: {},
      errors: {},
      touched: {},
      handleChange: jest.fn(),
      handleBlur: jest.fn(),
      handleSubmit: jest.fn(),
      setFieldValue: jest.fn(),
      resetForm: jest.fn(),
      isSubmitting: false,
    });
  });

  it('renders all form fields correctly', () => {
    render(<FormBuilder fields={mockFields} onSubmit={mockOnSubmit} />);
    
    expect(screen.getByLabelText('Name')).toBeInTheDocument();
    expect(screen.getByLabelText('Email')).toBeInTheDocument();
    expect(screen.getByLabelText('Age')).toBeInTheDocument();
  });

  it('handles form submission with valid data', async () => {
    const mockHandleSubmit = jest.fn().mockImplementation((callback) => callback);
    (useFormBuilder as jest.Mock).mockReturnValue({
      values: {
        name: 'John Doe',
        email: 'john@example.com',
        age: 25,
      },
      errors: {},
      touched: {
        name: true,
        email: true,
        age: true,
      },
      handleChange: jest.fn(),
      handleBlur: jest.fn(),
      handleSubmit: mockHandleSubmit,
      setFieldValue: jest.fn(),
      resetForm: jest.fn(),
      isSubmitting: false,
    });

    render(<FormBuilder fields={mockFields} onSubmit={mockOnSubmit} />);
    
    const submitButton = screen.getByRole('button', { name: /submit/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(mockHandleSubmit).toHaveBeenCalled();
      expect(mockOnSubmit).toHaveBeenCalledWith({
        name: 'John Doe',
        email: 'john@example.com',
        age: 25,
      });
    });
  });

  it('displays validation errors for required fields', () => {
    (useFormBuilder as jest.Mock).mockReturnValue({
      values: {
        name: '',
        email: '',
        age: '',
      },
      errors: {
        name: 'Name is required',
        email: 'Email is required',
      },
      touched: {
        name: true,
        email: true,
        age: true,
      },
      handleChange: jest.fn(),
      handleBlur: jest.fn(),
      handleSubmit: jest.fn(),
      setFieldValue: jest.fn(),
      resetForm: jest.fn(),
      isSubmitting: false,
    });

    render(<FormBuilder fields={mockFields} onSubmit={mockOnSubmit} />);
    
    expect(screen.getByText('Name is required')).toBeInTheDocument();
    expect(screen.getByText('Email is required')).toBeInTheDocument();
  });

  it('displays validation errors for invalid email format', () => {
    (useFormBuilder as jest.Mock).mockReturnValue({
      values: {
        name: 'John Doe',
        email: 'invalid-email',
        age: 25,
      },
      errors: {
        email: 'Please enter a valid email',
      },
      touched: {
        name: true,
        email: true,
        age: true,
      },
      handleChange: jest.fn(),
      handleBlur: jest.fn(),
      handleSubmit: jest.fn(),
      setFieldValue: jest.fn(),
      resetForm: jest.fn(),
      isSubmitting: false,
    });

    render(<FormBuilder fields={mockFields} onSubmit={mockOnSubmit} />);
    
    expect(screen.getByText('Please enter a valid email')).toBeInTheDocument();
  });

  it('displays validation errors for age constraints', () => {
    (useFormBuilder as jest.Mock).mockReturnValue({
      values: {
        name: 'John Doe',
        email: 'john@example.com',
        age: 15,
      },
      errors: {
        age: 'You must be at least 18 years old',
      },
      touched: {
        name: true,
        email: true,
        age: true,
      },
      handleChange: jest.fn(),
      handleBlur: jest.fn(),
      handleSubmit: jest.fn(),
      setFieldValue: jest.fn(),
      resetForm: jest.fn(),
      isSubmitting: false,
    });

    render(<FormBuilder fields={mockFields} onSubmit={mockOnSubmit} />);
    
    expect(screen.getByText('You must be at least 18 years old')).toBeInTheDocument();
  });

  it('disables submit button while submitting', () => {
    (useFormBuilder as jest.Mock).mockReturnValue({
      values: {
        name: 'John Doe',
        email: 'john@example.com',
        age: 25,
      },
      errors: {},
      touched: {
        name: true,
        email: true,
        age: true,
      },
      handleChange: jest.fn(),
      handleBlur: jest.fn(),
      handleSubmit: jest.fn(),
      setFieldValue: jest.fn(),
      resetForm: jest.fn(),
      isSubmitting: true,
    });

    render(<FormBuilder fields={mockFields} onSubmit={mockOnSubmit} />);
    
    const submitButton = screen.getByRole('button', { name: /submit/i });
    expect(submitButton).toBeDisabled();
  });

  it('resets form when reset button is clicked', () => {
    const mockResetForm = jest.fn();
    (useFormBuilder as jest.Mock).mockReturnValue({
      values: {
        name: 'John Doe',
        email: 'john@example.com',
        age: 25,
      },
      errors: {},
      touched: {
        name: true,
        email: true,
        age: true,
      },
      handleChange: jest.fn(),
      handleBlur: jest.fn(),
      handleSubmit: jest.fn(),
      setFieldValue: jest.fn(),
      resetForm: mockResetForm,
      isSubmitting: false,
    });

    render(<FormBuilder fields={mockFields} onSubmit={mockOnSubmit} />);
    
    const resetButton = screen.getByRole('button', { name: /reset/i });
    fireEvent.click(resetButton);
    
    expect(mockResetForm).toHaveBeenCalled();
  });

  it('handles dynamic field updates', () => {
    const mockSetFieldValue = jest.fn();
    (useFormBuilder as jest.Mock).mockReturnValue({
      values: {
        name: 'John Doe',
        email: 'john@example.com',
        age: 25,
      },
      errors: {},
      touched: {
        name: true,
        email: true,
        age: true,
      },
      handleChange: jest.fn(),
      handleBlur: jest.fn(),
      handleSubmit: jest.fn(),
      setFieldValue: mockSetFieldValue,
      resetForm: jest.fn(),
      isSubmitting: false,
    });

    render(<FormBuilder fields={mockFields} onSubmit={mockOnSubmit} />);
    
    const ageInput = screen.getByLabelText('Age');
    fireEvent.change(ageInput, { target: { value: '30' } });
    
    expect(mockSetFieldValue).toHaveBeenCalledWith('age', 30);
  });
}); 