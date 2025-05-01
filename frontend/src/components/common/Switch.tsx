import React from 'react';
import styled from 'styled-components';
import { motion } from 'framer-motion';
import { getThemeValue, fallbacks } from '../../utils/themeUtils';

interface SwitchProps {
  checked: boolean;
  onChange: () => void;
  disabled?: boolean;
  'aria-label'?: string;
}

const SwitchContainer = styled.div<{ disabled?: boolean }>`
  position: relative;
  width: 50px;
  height: 24px;
  opacity: ${({ disabled }) => (disabled ? 0.5 : 1)};
  cursor: ${({ disabled }) => (disabled ? 'not-allowed' : 'pointer')};
`;

const SwitchTrack = styled(motion.div)<{ checked: boolean }>`
  position: absolute;
  width: 100%;
  height: 100%;
  border-radius: 12px;
  background-color: ${({ theme, checked }) =>
    checked
      ? getThemeValue(theme, 'colors.primary', fallbacks.color.primary)
      : getThemeValue(theme, 'colors.border', fallbacks.color.border)};
`;

const SwitchThumb = styled(motion.div)<{ checked: boolean }>`
  position: absolute;
  top: 2px;
  left: ${({ checked }) => (checked ? '26px' : '2px')};
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background-color: ${({ theme }) =>
    getThemeValue(theme, 'colors.white', fallbacks.color.white)};
  box-shadow: ${({ theme }) =>
    getThemeValue(theme, 'shadows.sm', fallbacks.shadows.sm)};
`;

export const Switch: React.FC<SwitchProps> = ({
  checked,
  onChange,
  disabled = false,
  'aria-label': ariaLabel,
}) => {
  const handleClick = () => {
    if (!disabled) {
      onChange();
    }
  };

  return (
    <SwitchContainer
      onClick={handleClick}
      disabled={disabled}
      role="switch"
      aria-checked={checked}
      aria-disabled={disabled}
      aria-label={ariaLabel}
    >
      <SwitchTrack
        checked={checked}
        initial={false}
        animate={{
          backgroundColor: checked
            ? getThemeValue({}, 'colors.primary', fallbacks.color.primary)
            : getThemeValue({}, 'colors.border', fallbacks.color.border),
        }}
        transition={{ duration: 0.2 }}
      />
      <SwitchThumb
        checked={checked}
        initial={false}
        animate={{
          x: checked ? 24 : 0,
        }}
        transition={{
          type: 'spring',
          stiffness: 500,
          damping: 30,
        }}
      />
    </SwitchContainer>
  );
}; 