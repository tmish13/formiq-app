import React from 'react';
import { testRender, screen, fireEvent, waitFor } from '../../../test-utils';
import { FormBuilder } from '../../form/FormBuilder';
import { createForm } from '../../../../tests/factories/form';

describe('FormBuilder', () => {
  const mockForm = createForm();
  const defaultProps = {
    initialForm: mockForm,
    onSave: jest.fn(),
    onCancel: jest.fn(),
  };
  
  it('renders form builder with initial form', () => {
    testRender(<FormBuilder {...defaultProps} />);
    expect(screen.getByTestId('form-builder')).toBeInTheDocument();
  });

  it('displays form title', () => {
    testRender(<FormBuilder {...defaultProps} />);
    expect(screen.getByTestId('form-title')).toHaveTextContent(mockForm.title);
  });

  it('displays form description', () => {
    testRender(<FormBuilder {...defaultProps} />);
    expect(screen.getByTestId('form-description')).toHaveTextContent(mockForm.description);
  });

  it('displays form fields', () => {
    testRender(<FormBuilder {...defaultProps} />);
    mockForm.fields.forEach(field => {
      expect(screen.getByTestId(`field-${field.id}`)).toBeInTheDocument();
    });
  });

  it('handles field reordering', async () => {
    testRender(<FormBuilder {...defaultProps} />);
    const firstField = screen.getByTestId(`field-${mockForm.fields[0].id}`);
    const secondField = screen.getByTestId(`field-${mockForm.fields[1].id}`);
    
    fireEvent.dragStart(firstField);
    fireEvent.dragOver(secondField);
    fireEvent.drop(secondField);
    
    await waitFor(() => {
      const fields = screen.getAllByTestId(/^field-/);
      expect(fields[0]).toHaveAttribute('data-testid', `field-${mockForm.fields[1].id}`);
      expect(fields[1]).toHaveAttribute('data-testid', `field-${mockForm.fields[0].id}`);
    });
  });

  it('handles field deletion', async () => {
    testRender(<FormBuilder {...defaultProps} />);
    const deleteButton = screen.getByTestId(`delete-field-${mockForm.fields[0].id}`);
    
    fireEvent.click(deleteButton);
    
    await waitFor(() => {
      expect(screen.queryByTestId(`field-${mockForm.fields[0].id}`)).not.toBeInTheDocument();
    });
  });
}); 