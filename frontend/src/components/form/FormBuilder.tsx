import React, { useState } from 'react';
import { Form, FormField, FieldType } from '../../types/form';
import { Button, Input, Select } from '../common';

interface FormBuilderProps {
  initialForm: Form;
  onSave: (form: Form) => void;
  onCancel: () => void;
}

export const FormBuilder: React.FC<FormBuilderProps> = ({
  initialForm,
  onSave,
  onCancel,
}) => {
  const [form, setForm] = useState<Form>(initialForm);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const validateForm = () => {
    const newErrors: Record<string, string> = {};
    
    if (!form.title) {
      newErrors.title = 'Title is required';
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSave = () => {
    if (validateForm()) {
      onSave(form);
    }
  };

  const addField = () => {
    const newField: FormField = {
      id: `field-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`,
      label: 'New Field',
      type: 'text',
      required: false,
      options: [],
      validation: {
        required: false,
        min: null,
        max: null,
        pattern: null,
      },
    };

    setForm({
      ...form,
      fields: [...form.fields, newField],
    });
  };

  const updateField = (fieldId: string, updates: Partial<FormField>) => {
    setForm({
      ...form,
      fields: form.fields.map(field =>
        field.id === fieldId ? { ...field, ...updates } : field
      ),
    });
  };

  return (
    <div className="form-builder">
      <div className="form-header">
        <Input
          label="Form Title"
          value={form.title}
          onChange={(e: React.ChangeEvent<HTMLInputElement>) => 
            setForm({ ...form, title: e.target.value })}
          error={errors.title}
        />
        <Input
          label="Description"
          value={form.description}
          onChange={(e: React.ChangeEvent<HTMLInputElement>) => 
            setForm({ ...form, description: e.target.value })}
          type="textarea"
        />
      </div>

      <div className="form-fields">
        {form.fields.map(field => (
          <div key={field.id} className="field-item">
            <Input
              label="Field Label"
              value={field.label}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => 
                updateField(field.id, { label: e.target.value })}
            />
            <Select
              label="Field Type"
              value={field.type}
              onChange={(e: React.ChangeEvent<HTMLSelectElement>) => 
                updateField(field.id, { type: e.target.value as FieldType })}
              options={[
                { value: 'text', label: 'Text' },
                { value: 'number', label: 'Number' },
                { value: 'email', label: 'Email' },
                { value: 'select', label: 'Select' },
              ]}
            />
            {field.type === 'select' && (
              <Button onClick={() => {/* Add option logic */}}>
                Add Option
              </Button>
            )}
          </div>
        ))}
      </div>

      <Button onClick={addField}>Add Field</Button>

      <div className="form-actions">
        <Button onClick={handleSave}>Save Form</Button>
        <Button variant="secondary" onClick={onCancel}>
          Cancel
        </Button>
      </div>
    </div>
  );
}; 