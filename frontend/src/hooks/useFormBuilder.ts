import { useState, useCallback } from 'react';
import { FormField, FormValidationRule } from '../types/formBuilder';

interface UseFormBuilderReturn {
  fields: FormField[];
  addField: (field: FormField) => void;
  removeField: (fieldId: string) => void;
  updateField: (fieldId: string, updates: Partial<FormField>) => void;
  validateField: (fieldId: string, value: any) => string[];
  validateForm: () => Record<string, string[]>;
}

export const useFormBuilder = (initialFields: FormField[] = []): UseFormBuilderReturn => {
  const [fields, setFields] = useState<FormField[]>(initialFields);

  const addField = useCallback((field: FormField) => {
    setFields(prev => [...prev, field]);
  }, []);

  const removeField = useCallback((fieldId: string) => {
    setFields(prev => prev.filter(field => field.id !== fieldId));
  }, []);

  const updateField = useCallback((fieldId: string, updates: Partial<FormField>) => {
    setFields(prev => prev.map(field => 
      field.id === fieldId ? { ...field, ...updates } : field
    ));
  }, []);

  const validateField = useCallback((fieldId: string, value: any): string[] => {
    const field = fields.find(f => f.id === fieldId);
    if (!field || !field.validation) return [];

    return field.validation.reduce<string[]>((errors: string[], rule: FormValidationRule) => {
      if (rule.type === 'required' && !value) {
        errors.push(rule.message);
      }
      if (rule.type === 'minLength' && value.length < rule.value) {
        errors.push(rule.message);
      }
      if (rule.type === 'email' && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) {
        errors.push(rule.message);
      }
      return errors;
    }, []);
  }, [fields]);

  const validateForm = useCallback((): Record<string, string[]> => {
    return fields.reduce<Record<string, string[]>>((errors, field) => {
      if (field.required) {
        errors[field.id] = validateField(field.id, field.value);
      }
      return errors;
    }, {});
  }, [fields, validateField]);

  return {
    fields,
    addField,
    removeField,
    updateField,
    validateField,
    validateForm,
  };
}; 