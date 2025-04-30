import React from 'react';
import { useFormBuilder } from '../../hooks/useFormBuilder';
import { FormField } from '../../types/formBuilder';

interface FormBuilderProps {
  fields: FormField[];
  onSubmit: (values: Record<string, any>) => void;
}

export const FormBuilder: React.FC<FormBuilderProps> = ({ fields = [], onSubmit }) => {
  const {
    values,
    errors,
    touched,
    handleChange,
    handleBlur,
    handleSubmit,
    setFieldValue,
    resetForm,
    isSubmitting
  } = useFormBuilder();

  const submitForm = (e: React.FormEvent) => {
    e.preventDefault();
    handleSubmit((formValues) => {
      onSubmit(formValues);
    })();
  };

  return (
    <form 
      data-testid="form-builder"
      onSubmit={submitForm}
    >
      {(fields || []).map((field) => (
        <div key={field.id} className="form-field">
          <label htmlFor={field.id}>{field.label}</label>
          <input
            id={field.id}
            name={field.id}
            type={field.type}
            placeholder={field.placeholder}
            value={values[field.id] || ''}
            onChange={handleChange}
            onBlur={handleBlur}
            data-testid={`field-${field.id}`}
            required={field.required}
          />
          {touched[field.id] && errors[field.id] && (
            <div className="error-message" data-testid={`error-${field.id}`}>
              {errors[field.id]}
            </div>
          )}
        </div>
      ))}

      <div className="form-actions">
        <button 
          type="submit"
          data-testid="submit-button"
          disabled={isSubmitting}
        >
          Submit
        </button>
        <button 
          type="button"
          data-testid="reset-button"
          onClick={resetForm}
        >
          Reset
        </button>
      </div>
    </form>
  );
}; 