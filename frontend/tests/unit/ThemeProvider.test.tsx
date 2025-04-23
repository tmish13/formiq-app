import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ThemeProvider } from 'styled-components';
import { mockThemeWithFallbacks as mockTheme } from '../__mocks__/mockTheme';
import styled from 'styled-components';

// Create styled component that uses theme
const StyledComponent = styled.div<{ customColor?: boolean }>`
  color: ${({ theme, customColor }) => 
    customColor 
      ? theme.colors.primary.main 
      : theme.colors.text.primary};
  background-color: ${({ theme }) => theme.colors.background.main};
  padding: ${({ theme }) => theme.spacing.md};
  font-family: ${({ theme }) => theme.typography.fontFamily.primary};
  border-radius: ${({ theme }) => theme.borderRadius.md};
`;

// Create component with conditional styling
const ConditionalStyledComponent = styled.button<{ isActive: boolean }>`
  background-color: ${({ theme, isActive }) => 
    isActive 
      ? theme.colors.primary.main 
      : theme.colors.secondary.main};
  color: ${({ theme }) => theme.colors.text.inverse};
  padding: ${({ theme }) => `${theme.spacing.sm} ${theme.spacing.md}`};
  border-radius: ${({ theme }) => theme.borderRadius.md};
  border: none;
  transition: all ${({ theme }) => theme.transitions.duration.medium} ${({ theme }) => theme.transitions.easing.easeInOut};
  
  &:hover {
    background-color: ${({ theme, isActive }) => 
      isActive 
        ? theme.colors.primary.dark 
        : theme.colors.secondary.dark};
  }
`;

// Create component that uses nested theme properties
const NestedThemeComponent = styled.div`
  box-shadow: ${({ theme }) => `0 2px 4px ${theme.colors.primary.main}40`};
  transition: transform ${({ theme }) => theme.transitions.duration.medium};
`;

// Create a component with dynamic theme values
function DynamicThemeComponent({ active }: { active: boolean }) {
  return (
    <div data-testid="dynamic-theme-container">
      <ConditionalStyledComponent 
        isActive={active} 
        data-testid="dynamic-button"
      >
        {active ? 'Active Button' : 'Inactive Button'}
      </ConditionalStyledComponent>
      <StyledComponent 
        customColor={active} 
        data-testid="dynamic-text"
      >
        This text uses dynamic theme colors
      </StyledComponent>
    </div>
  );
}

describe('ThemeProvider Tests', () => {
  it('renders styled components with theme correctly', () => {
    render(
      <ThemeProvider theme={mockTheme}>
        <StyledComponent data-testid="themed-component">
          Themed Content
        </StyledComponent>
      </ThemeProvider>
    );
    
    const themedComponent = screen.getByTestId('themed-component');
    expect(themedComponent).toBeInTheDocument();
    expect(themedComponent).toHaveTextContent('Themed Content');
  });
  
  it('handles conditional styling based on props', () => {
    render(
      <ThemeProvider theme={mockTheme}>
        <ConditionalStyledComponent 
          isActive={true} 
          data-testid="active-button"
        >
          Active Button
        </ConditionalStyledComponent>
        <ConditionalStyledComponent 
          isActive={false} 
          data-testid="inactive-button"
        >
          Inactive Button
        </ConditionalStyledComponent>
      </ThemeProvider>
    );
    
    const activeButton = screen.getByTestId('active-button');
    const inactiveButton = screen.getByTestId('inactive-button');
    
    expect(activeButton).toBeInTheDocument();
    expect(inactiveButton).toBeInTheDocument();
    expect(activeButton).toHaveTextContent('Active Button');
    expect(inactiveButton).toHaveTextContent('Inactive Button');
  });
  
  it('handles theme updates correctly', () => {
    const { rerender } = render(
      <ThemeProvider theme={mockTheme}>
        <DynamicThemeComponent active={false} />
      </ThemeProvider>
    );
    
    // Initial render with inactive state
    expect(screen.getByTestId('dynamic-button')).toHaveTextContent('Inactive Button');
    
    // Rerender with active state
    rerender(
      <ThemeProvider theme={mockTheme}>
        <DynamicThemeComponent active={true} />
      </ThemeProvider>
    );
    
    // Should update to active state
    expect(screen.getByTestId('dynamic-button')).toHaveTextContent('Active Button');
  });
  
  it('handles nested theme access without errors', () => {
    render(
      <ThemeProvider theme={mockTheme}>
        <NestedThemeComponent data-testid="nested-theme-component">
          Component with nested theme properties
        </NestedThemeComponent>
      </ThemeProvider>
    );
    
    const nestedComponent = screen.getByTestId('nested-theme-component');
    expect(nestedComponent).toBeInTheDocument();
    expect(nestedComponent).toHaveTextContent('Component with nested theme properties');
  });
  
  it('falls back gracefully when theme values are undefined', () => {
    // Create a theme with missing values
    const incompleteTheme = {
      colors: {
        primary: { 
          main: '#1976d2' 
          // missing dark, light
        },
        // missing other colors
      },
      // missing typography, spacing, etc.
    };
    
    render(
      // @ts-ignore - deliberately testing incomplete theme
      <ThemeProvider theme={incompleteTheme}>
        <StyledComponent data-testid="incomplete-theme-component">
          Component with incomplete theme
        </StyledComponent>
      </ThemeProvider>
    );
    
    const component = screen.getByTestId('incomplete-theme-component');
    expect(component).toBeInTheDocument();
    expect(component).toHaveTextContent('Component with incomplete theme');
    // No errors should be thrown
  });
}); 