import React from 'react';
import { render, screen, fireEvent, waitFor } from '../../../base/test-utils';
import { FormBuilder } from '../../../../src/components/form/FormBuilder';
import { createForm } from '../../../factories/form';

describe('FormBuilder Component', () => {
  const defaultProps = {
    initialForm: createForm(),
    onSave: jest.fn(),
    onCancel: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders with initial form data', () => {
    const form = createForm({
      title: 'Test Form',
      description: 'Test Description',
    });

    render(<FormBuilder {...defaultProps} initialForm={form} />);

    expect(screen.getByDisplayValue('Test Form')).toBeInTheDocument();
    expect(screen.getByDisplayValue('Test Description')).toBeInTheDocument();
  });

  it('allows adding new fields', () => {
    render(<FormBuilder {...defaultProps} />);
    
    // Find and click the Add Field button
    const addButton = screen.getByText('Add Field');
    fireEvent.click(addButton);
    
    // Look for the new field input with value "New Field"
    expect(screen.getByDisplayValue('New Field')).toBeInTheDocument();
  });

  it('handles field type changes', () => {
    render(<FormBuilder {...defaultProps} />);
    
    // Add a new field first
    const addButton = screen.getByText('Add Field');
    fireEvent.click(addButton);
    
    // Find all select elements
    const selects = screen.getAllByRole('combobox');
    
    // Get the last select (since we just added it)
    const fieldTypeSelect = selects[selects.length - 1];
    
    // Change the selection to 'select'
    fireEvent.change(fieldTypeSelect, { target: { value: 'select' } });
    
    // The new field should be the last field in the form
    const fieldItems = document.querySelectorAll('.field-item');
    const lastField = fieldItems[fieldItems.length - 1];
    
    // Now check that the last field has an "Add Option" button
    expect(lastField.textContent).toContain('Add Option');
  });

  it('validates required fields before saving', async () => {
    const onSave = jest.fn();
    // Create a form with an empty title to trigger validation
    const emptyForm = createForm({ title: '' });
    
    render(<FormBuilder {...defaultProps} initialForm={emptyForm} onSave={onSave} />);
    
    // Click the Save Form button
    const saveButton = screen.getByText('Save Form');
    fireEvent.click(saveButton);
    
    // Wait for error message to appear
    await waitFor(() => {
      const errorElement = screen.getByText('Title is required');
      expect(errorElement).toBeInTheDocument();
    });
    
    expect(onSave).not.toHaveBeenCalled();
  });

  it('calls onSave with updated form data', () => {
    const onSave = jest.fn();
    const form = createForm({
      title: 'Initial Title',
      description: 'Initial Description',
    });

    render(<FormBuilder {...defaultProps} initialForm={form} onSave={onSave} />);
    
    const titleInput = screen.getByDisplayValue('Initial Title');
    fireEvent.change(titleInput, { target: { value: 'Updated Title' } });
    
    const saveButton = screen.getByText('Save Form');
    fireEvent.click(saveButton);
    
    expect(onSave).toHaveBeenCalledWith(expect.objectContaining({
      title: 'Updated Title',
      description: 'Initial Description',
    }));
  });

  it('calls onCancel when cancel button is clicked', () => {
    const onCancel = jest.fn();
    render(<FormBuilder {...defaultProps} onCancel={onCancel} />);
    
    const cancelButton = screen.getByText('Cancel');
    fireEvent.click(cancelButton);
    
    expect(onCancel).toHaveBeenCalled();
  });
}); 