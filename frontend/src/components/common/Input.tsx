import React, { useState } from 'react';
import styled from 'styled-components';
import { getThemeValue, fallbacks } from '../../utils/themeUtils';

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helperText?: string;
  icon?: React.ReactNode;
  endIcon?: React.ReactNode;
  fullWidth?: boolean;
  variant?: 'outlined' | 'filled';
}

const InputWrapper = styled.div<{ $fullWidth?: boolean }>`
  display: flex;
  flex-direction: column;
  margin-bottom: 1rem;
  width: ${({ $fullWidth }) => ($fullWidth ? '100%' : 'auto')};
`;

const Label = styled.label`
  font-size: ${({ theme }) => getThemeValue(theme, 'typography.fontSize.sm', '0.875rem')};
  color: ${({ theme }) => getThemeValue(theme, 'colors.text.primary', fallbacks.colors.text)};
  margin-bottom: 0.5rem;
  font-weight: ${({ theme }) => getThemeValue(theme, 'typography.fontWeight.medium', '500')};
`;

const InputContainer = styled.div`
  position: relative;
  display: flex;
  align-items: center;
  width: 100%;
`;

const IconWrapper = styled.div`
  position: absolute;
  left: 0.75rem;
  top: 50%;
  transform: translateY(-50%);
  color: ${({ theme }) => getThemeValue(theme, 'colors.text.secondary', fallbacks.colors.textSecondary)};
  display: flex;
  align-items: center;
  justify-content: center;
`;

const EndIconWrapper = styled.div`
  position: absolute;
  right: 0.75rem;
  top: 50%;
  transform: translateY(-50%);
  color: ${({ theme }) => getThemeValue(theme, 'colors.text.secondary', fallbacks.colors.textSecondary)};
  display: flex;
  align-items: center;
  justify-content: center;
`;

const StyledInput = styled.input<{
  $hasError?: boolean;
  $hasIcon?: boolean;
  $hasEndIcon?: boolean;
  $variant?: 'outlined' | 'filled';
  $isFocused?: boolean;
}>`
  padding: ${({ $hasIcon, $hasEndIcon }) => {
    if ($hasIcon && $hasEndIcon) return '0.75rem 2.5rem';
    if ($hasIcon) return '0.75rem 0.75rem 0.75rem 2.5rem';
    if ($hasEndIcon) return '0.75rem 2.5rem 0.75rem 0.75rem';
    return '0.75rem 1rem';
  }};
  border-radius: ${({ theme }) => getThemeValue(theme, 'borderRadius.md', '0.5rem')};
  border: 1px solid ${({ theme, $hasError, $isFocused }) => 
    $hasError 
      ? getThemeValue(theme, 'colors.error.main', fallbacks.colors.error) 
      : $isFocused 
        ? getThemeValue(theme, 'colors.primary.main', fallbacks.colors.primary) 
        : getThemeValue(theme, 'colors.border.main', fallbacks.colors.border)};
  background-color: ${({ theme, $variant }) => 
    $variant === 'filled' 
      ? `${getThemeValue(theme, 'colors.border.main', fallbacks.colors.border)}40` 
      : getThemeValue(theme, 'colors.background.main', fallbacks.colors.background)};
  font-size: ${({ theme }) => getThemeValue(theme, 'typography.fontSize.md', '1rem')};
  color: ${({ theme }) => getThemeValue(theme, 'colors.text.primary', fallbacks.colors.text)};
  transition: all 0.2s ease;
  width: 100%;
  height: 44px;
  text-align: left;
  
  &:focus {
    outline: none;
    border-color: ${({ theme, $hasError }) => 
      $hasError 
        ? getThemeValue(theme, 'colors.error.main', fallbacks.colors.error) 
        : getThemeValue(theme, 'colors.primary.main', fallbacks.colors.primary)};
    box-shadow: 0 0 0 3px ${({ theme, $hasError }) => 
      $hasError 
        ? `${getThemeValue(theme, 'colors.error.main', fallbacks.colors.error)}30` 
        : `${getThemeValue(theme, 'colors.primary.main', fallbacks.colors.primary)}30`};
    background-color: ${({ theme, $variant }) => 
      $variant === 'filled' 
        ? `${getThemeValue(theme, 'colors.border.main', fallbacks.colors.border)}20` 
        : getThemeValue(theme, 'colors.background.main', fallbacks.colors.background)};
  }
  
  &:hover:not(:disabled) {
    border-color: ${({ theme, $hasError, $isFocused }) => 
      $hasError 
        ? getThemeValue(theme, 'colors.error.main', fallbacks.colors.error) 
        : $isFocused 
          ? getThemeValue(theme, 'colors.primary.main', fallbacks.colors.primary) 
          : getThemeValue(theme, 'colors.text.secondary', fallbacks.colors.textSecondary)};
  }
  
  &:disabled {
    background-color: ${({ theme }) => getThemeValue(theme, 'colors.disabled', fallbacks.colors.disabled)};
    cursor: not-allowed;
    opacity: 0.7;
  }
  
  &::placeholder {
    color: ${({ theme }) => getThemeValue(theme, 'colors.text.secondary', fallbacks.colors.textSecondary)};
    opacity: 0.7;
  }
`;

const ErrorText = styled.span`
  color: ${({ theme }) => getThemeValue(theme, 'colors.error.main', fallbacks.colors.error)};
  font-size: ${({ theme }) => getThemeValue(theme, 'typography.fontSize.sm', '0.875rem')};
  margin-top: 0.25rem;
  text-align: left;
`;

const HelperText = styled.span`
  color: ${({ theme }) => getThemeValue(theme, 'colors.text.secondary', fallbacks.colors.textSecondary)};
  font-size: ${({ theme }) => getThemeValue(theme, 'typography.fontSize.sm', '0.875rem')};
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
  id,
  type,
  ...props
}) => {
  const [isFocused, setIsFocused] = useState(false);
  const inputId = id || `input-${props.name || Math.random().toString(36).substring(2, 9)}`;
  
  const handleFocus = (e: React.FocusEvent<HTMLInputElement>) => {
    setIsFocused(true);
    if (props.onFocus) props.onFocus(e);
  };
  
  const handleBlur = (e: React.FocusEvent<HTMLInputElement>) => {
    setIsFocused(false);
    if (props.onBlur) props.onBlur(e);
  };
  
  // Create a label text for password fields to help with ARIA roles
  const inputLabel = type === 'password' && !label ? 'Password' : label;
  
  return (
    <InputWrapper $fullWidth={fullWidth}>
      {inputLabel && <Label htmlFor={inputId}>{inputLabel}</Label>}
      <InputContainer>
        {icon && <IconWrapper>{icon}</IconWrapper>}
        <StyledInput 
          $hasError={!!error} 
          $hasIcon={!!icon} 
          $hasEndIcon={!!endIcon}
          $variant={variant}
          $isFocused={isFocused}
          onFocus={handleFocus}
          onBlur={handleBlur}
          id={inputId}
          aria-invalid={!!error ? 'true' : undefined}
          type={type}
          {...props} 
        />
        {endIcon && <EndIconWrapper>{endIcon}</EndIconWrapper>}
      </InputContainer>
      {error && <ErrorText>{error}</ErrorText>}
      {helperText && !error && <HelperText>{helperText}</HelperText>}
    </InputWrapper>
  );
};