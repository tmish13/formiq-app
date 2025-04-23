import React from 'react';
import { Box } from '@mui/material';
import styled from 'styled-components';
import { Input, InputProps } from '../atoms/Input';
import { Typography } from '../atoms/Typography';

export interface FormFieldProps extends InputProps {
  label: string;
  required?: boolean;
  description?: string;
}

const FieldContainer = styled(Box)`
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 16px;
`;

const LabelContainer = styled(Box)`
  display: flex;
  align-items: center;
  gap: 4px;
`;

const RequiredAsterisk = styled(Typography)`
  color: ${({ theme }) => theme.colors.error.main};
`;

const Description = styled(Typography)`
  color: ${({ theme }) => theme.colors.text.secondary};
  font-size: 0.875rem;
`;

export const FormField: React.FC<FormFieldProps> = ({
  label,
  required = false,
  description,
  error,
  helperText,
  ...props
}) => {
  return (
    <FieldContainer>
      <LabelContainer>
        <Typography variant="body2" weight="medium">
          {label}
        </Typography>
        {required && <RequiredAsterisk>*</RequiredAsterisk>}
      </LabelContainer>
      {description && (
        <Description variant="caption">{description}</Description>
      )}
      <Input
        error={error}
        helperText={helperText}
        required={required}
        {...props}
      />
    </FieldContainer>
  );
}; 