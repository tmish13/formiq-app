import React from 'react';
import { TextField, TextFieldProps } from '@mui/material';
import styled from 'styled-components';
import { getThemeValue } from '../../utils/themeUtils';

export interface InputProps extends Omit<TextFieldProps, 'variant'> {
  error?: boolean;
  helperText?: string;
  fullWidth?: boolean;
}

const StyledTextField = styled(TextField)<InputProps>`
  .MuiOutlinedInput-root {
    border-radius: ${({ theme }) => getThemeValue(theme, 'borderRadius.md', '8px')};
    
    &:hover .MuiOutlinedInput-notchedOutline {
      border-color: ${({ theme }) => getThemeValue(theme, 'colors.primary.main', '#3f51b5')};
    }
    
    &.Mui-focused .MuiOutlinedInput-notchedOutline {
      border-color: ${({ theme }) => getThemeValue(theme, 'colors.primary.main', '#3f51b5')};
    }

    &.Mui-error .MuiOutlinedInput-notchedOutline {
      border-color: ${({ theme }) => getThemeValue(theme, 'colors.error.main', '#f44336')};
    }
  }
  
  .MuiFormHelperText-root {
    margin-left: 0;
    margin-right: 0;
    color: ${({ theme, error }) => 
      error 
        ? getThemeValue(theme, 'colors.error.main', '#f44336')
        : getThemeValue(theme, 'colors.text.secondary', '#666666')
    };
  }

  .MuiInputLabel-root {
    color: ${({ theme }) => getThemeValue(theme, 'colors.text.secondary', '#666666')};
    &.Mui-focused {
      color: ${({ theme }) => getThemeValue(theme, 'colors.primary.main', '#3f51b5')};
    }
    &.Mui-error {
      color: ${({ theme }) => getThemeValue(theme, 'colors.error.main', '#f44336')};
    }
  }
`;

export const Input: React.FC<InputProps> = ({
  error,
  helperText,
  fullWidth = true,
  ...props
}) => {
  return (
    <StyledTextField
      variant="outlined"
      error={error}
      helperText={helperText}
      fullWidth={fullWidth}
      {...props}
    />
  );
}; 