// Mock the styled-components module
jest.mock('styled-components', () => ({
  __esModule: true,
  default: {
    div: () => {
      const StyledDiv = ({ children, ...props }: { children: React.ReactNode; [key: string]: any }) => 
        <div {...props}>{children}</div>;
      return StyledDiv;
    }
  },
  ThemeProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>
}));

import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import styled from 'styled-components';

// Create a simplified styled component
const StyledComponent = styled.div`
  padding: 10px;
`;

// Create a component that uses the styled component
const SimpleStyledFeedback = ({ feedback }: { feedback: string }) => (
  <StyledComponent data-testid="styled-feedback">
    {feedback}
  </StyledComponent>
);

// Test suite
describe('SimpleStyledFeedback Component', () => {
  it('renders the feedback text', () => {
    render(<SimpleStyledFeedback feedback="Great job!" />);
    expect(screen.getByTestId('styled-feedback')).toHaveTextContent('Great job!');
  });
}); 