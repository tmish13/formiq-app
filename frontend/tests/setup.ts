import '@testing-library/jest-dom';
import { expect } from '@jest/globals';

declare global {
  namespace jest {
    interface Matchers<R> {
      toBeInTheDocument(): R;
      toHaveAttribute(attr: string, value?: string): R;
      toHaveStyle(style: Record<string, any>): R;
      toHaveClass(className: string): R;
      toBeVisible(): R;
      toBeDisabled(): R;
    }
  }
} 