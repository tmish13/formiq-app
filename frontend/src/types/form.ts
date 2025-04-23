export type FormType = 'standard' | 'survey' | 'quiz';
export type FormStatus = 'draft' | 'published' | 'archived';
export type FieldType = 'text' | 'number' | 'email' | 'select' | 'checkbox' | 'radio' | 'textarea';

export interface FieldValidation {
  required: boolean;
  min: number | null;
  max: number | null;
  pattern: string | null;
}

export interface FormField {
  id: string;
  label: string;
  type: FieldType;
  required: boolean;
  options: string[];
  validation: FieldValidation;
}

export interface FormSubmission {
  id: string;
  formId: string;
  submittedBy: string;
  submittedAt: string;
  answers: Record<string, any>;
}

export interface Form {
  id: string;
  title: string;
  description: string;
  type: FormType;
  status: FormStatus;
  createdBy: string;
  createdAt: string;
  updatedAt: string;
  fields: FormField[];
  submissions: FormSubmission[];
  isPublished: boolean;
} 