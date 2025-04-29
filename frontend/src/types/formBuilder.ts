export interface FormValidationRule {
  type: 'required' | 'minLength' | 'email' | 'custom';
  value?: number;
  message: string;
  validator?: (value: any) => boolean;
}

export interface FormField {
  id: string;
  type: 'text' | 'email' | 'number' | 'password' | 'select' | 'checkbox' | 'radio';
  label: string;
  placeholder?: string;
  required?: boolean;
  value?: any;
  options?: { label: string; value: any }[];
  validation?: FormValidationRule[];
  disabled?: boolean;
  hidden?: boolean;
  className?: string;
  style?: React.CSSProperties;
} 