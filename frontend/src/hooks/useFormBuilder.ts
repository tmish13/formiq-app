import { useState, useCallback } from 'react';
import { FormField, FormValidationRule } from '../types/formBuilder';

interface UseFormBuilderReturn {
  values: Record<string, any>;
  errors: Record<string, string>;
  touched: Record<string, boolean>;
  handleChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  handleBlur: (e: React.FocusEvent<HTMLInputElement>) => void;
  handleSubmit: (onSubmit: (values: Record<string, any>) => void | Promise<void>) => () => void;
  setFieldValue: (field: string, value: any) => void;
  resetForm: () => void;
  isSubmitting: boolean;
}

export const useFormBuilder = (initialValues: Record<string, any> = {}): UseFormBuilderReturn => {
  const [values, setValues] = useState<Record<string, any>>(initialValues);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [touched, setTouched] = useState<Record<string, boolean>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value, type } = e.target;
    // Convert to number for number inputs
    const processedValue = type === 'number' && value ? Number(value) : value;
    setValues(prev => ({ ...prev, [name]: processedValue }));
  }, []);

  const handleBlur = useCallback((e: React.FocusEvent<HTMLInputElement>) => {
    const { name } = e.target;
    setTouched(prev => ({ ...prev, [name]: true }));
  }, []);

  const handleSubmit = useCallback((onSubmit: (values: Record<string, any>) => void | Promise<void>) => () => {
    // Mark all fields as touched
    Object.keys(values).forEach(key => {
      setTouched(prev => ({ ...prev, [key]: true }));
    });
    
    setIsSubmitting(true);
    
    try {
      // Make sure to actually pass the values to onSubmit
      onSubmit({ ...values });
    } finally {
      // Set isSubmitting to false immediately after onSubmit completes
      setIsSubmitting(false);
    }
  }, [values]);

  const setFieldValue = useCallback((field: string, value: any) => {
    setValues(prev => ({ ...prev, [field]: value }));
  }, []);

  const resetForm = useCallback(() => {
    setValues(initialValues);
    setErrors({});
    setTouched({});
    setIsSubmitting(false);
  }, [initialValues]);

  return {
    values,
    errors,
    touched,
    handleChange,
    handleBlur,
    handleSubmit,
    setFieldValue,
    resetForm,
    isSubmitting
  };
}; 