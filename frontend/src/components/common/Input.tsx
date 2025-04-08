import React, { useState } from 'react';
import styled from 'styled-components';

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helperText?: string;
  icon?: React.ReactNode;
  endIcon?: React.ReactNode;
  fullWidth?: boolean;
  variant?: 'outlined' | 'filled';
}

const InputWrapper = styled.div<{ fullWidth?: boolean }>`
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  width: ${({ fullWidth }) => (fullWidth ? '100%' : 'auto')};
  position: relative;
  text-align: left;
`;

const Label = styled.label`
  font-size: ${({ theme }) => theme.typography.fontSize.sm};
  font-weight: ${({ theme }) => theme.typography.fontWeight.medium};
  color: ${({ theme }) => theme.colors.text};
  transition: all 0.2s ease;
  margin-bottom: 4px;
`;

const IconWrapper = styled.div`
  position: absolute;
  top: 50%;
  left: 0.75rem;
  transform: translateY(-50%);
  color: ${({ theme }) => theme.colors.textSecondary};
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;
  z-index: 1;
`;

const EndIconWrapper = styled.div`
  position: absolute;
  top: 50%;
  right: 0.75rem;
  transform: translateY(-50%);
  color: ${({ theme }) => theme.colors.textSecondary};
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1;
`;

const InputContainer = styled.div`
  position: relative;
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
`;

const StyledInput = styled.input<{ 
  hasError?: boolean; 
  hasIcon?: boolean; 
  hasEndIcon?: boolean;
  variant?: 'outlined' | 'filled';
  isFocused?: boolean;
}>`
  padding: ${({ hasIcon, hasEndIcon }) => {
    if (hasIcon && hasEndIcon) return '0.75rem 2.5rem';
    if (hasIcon) return '0.75rem 0.75rem 0.75rem 2.5rem';
    if (hasEndIcon) return '0.75rem 2.5rem 0.75rem 0.75rem';
    return '0.75rem 1rem';
  }};
  border-radius: ${({ theme }) => theme.borderRadius.md};
  border: 1px solid ${({ theme, hasError, isFocused }) => 
    hasError 
      ? theme.colors.error 
      : isFocused 
        ? theme.colors.primary 
        : theme.colors.border};
  background-color: ${({ theme, variant }) => 
    variant === 'filled' ? `${theme.colors.border}40` : theme.colors.white};
  font-size: ${({ theme }) => theme.typography.fontSize.base};
  color: ${({ theme }) => theme.colors.text};
  transition: all 0.2s ease;
  width: 100%;
  height: 44px;
  text-align: left;
  
  &:focus {
    outline: none;
    border-color: ${({ theme, hasError }) => 
      hasError ? theme.colors.error : theme.colors.primary};
    box-shadow: 0 0 0 3px ${({ theme, hasError }) => 
      hasError 
        ? `${theme.colors.error}30` 
        : `${theme.colors.primary}30`};
    background-color: ${({ theme, variant }) => 
      variant === 'filled' ? `${theme.colors.border}20` : theme.colors.white};
  }
  
  &:hover:not(:disabled) {
    border-color: ${({ theme, hasError, isFocused }) => 
      hasError 
        ? theme.colors.error 
        : isFocused 
          ? theme.colors.primary 
          : theme.colors.textSecondary};
  }
  
  &:disabled {
    background-color: ${({ theme }) => theme.colors.disabled};
    cursor: not-allowed;
    opacity: 0.7;
  }
  
  &::placeholder {
    color: ${({ theme }) => theme.colors.textSecondary};
    opacity: 0.7;
  }
`;

const ErrorText = styled.span`
  color: ${({ theme }) => theme.colors.error};
  font-size: ${({ theme }) => theme.typography.fontSize.xs};
  margin-top: 0.25rem;
  text-align: left;
`;

const HelperText = styled.span`
  color: ${({ theme }) => theme.colors.textSecondary};
  font-size: ${({ theme }) => theme.typography.fontSize.xs};
  margin-top: 0.25rem;
  text-align: left;
`;

export const Input: React.FC<InputProps> = ({
  label,
  error,
  helperText,
  icon,
  endIcon,
  fullWidth = false,
  variant = 'outlined',
  ...props
}) => {
  const [isFocused, setIsFocused] = useState(false);
  
  const handleFocus = (e: React.FocusEvent<HTMLInputElement>) => {
    setIsFocused(true);
    if (props.onFocus) props.onFocus(e);
  };
  
  const handleBlur = (e: React.FocusEvent<HTMLInputElement>) => {
    setIsFocused(false);
    if (props.onBlur) props.onBlur(e);
  };
  
  return (
    <InputWrapper fullWidth={fullWidth}>
      {label && <Label>{label}</Label>}
      <InputContainer>
        {icon && <IconWrapper>{icon}</IconWrapper>}
        <StyledInput 
          hasError={!!error} 
          hasIcon={!!icon} 
          hasEndIcon={!!endIcon}
          variant={variant}
          isFocused={isFocused}
          onFocus={handleFocus}
          onBlur={handleBlur}
          {...props} 
        />
        {endIcon && <EndIconWrapper>{endIcon}</EndIconWrapper>}
      </InputContainer>
      {error && <ErrorText>{error}</ErrorText>}
      {helperText && !error && <HelperText>{helperText}</HelperText>}
    </InputWrapper>
  );
}; 