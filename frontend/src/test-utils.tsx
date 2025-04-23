// This file is kept for backward compatibility with existing tests
// It now re-exports the centralized testing utilities
import { render, testRender } from '../tests/utils/testRender';

// Re-export everything
export * from '@testing-library/react';
export { render, testRender }; 