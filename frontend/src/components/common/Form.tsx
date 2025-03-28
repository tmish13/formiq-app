import React from 'react';
import { useForm, UseFormProps, UseFormReturn } from 'react-hook-form';
import { yupResolver } from '@hookform/resolvers/yup';
import * as yup from 'yup';
import styled from 'styled-components';

const FormContainer = styled.form`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.spacing.md};
  width: 100%;
`;

interface FormProps<T extends Record<string, any>> {
  onSubmit: (data: T) => Promise<void> | void;
  schema?: yup.ObjectSchema<any>;
  defaultValues?: Partial<T>;
  children: (methods: UseFormReturn<T>) => React.ReactNode;
  className?: string;
}

export function Form<T extends Record<string, any>>({
  onSubmit,
  schema,
  defaultValues,
  children,
  className,
}: FormProps<T>) {
  const methods = useForm<T>({
    resolver: schema ? yupResolver(schema) : undefined,
    defaultValues,
  } as UseFormProps<T>);

  const handleSubmit = async (data: T) => {
    try {
      await onSubmit(data);
    } catch (error) {
      console.error('Form submission error:', error);
    }
  };

  return (
    <FormContainer
      className={className}
      onSubmit={methods.handleSubmit(handleSubmit)}
    >
      {children(methods)}
    </FormContainer>
  );
} 