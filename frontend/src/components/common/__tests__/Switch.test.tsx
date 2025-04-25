import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { ThemeProvider } from 'styled-components';
import { Switch } from '../../../../src/components/common/Switch';
import { theme } from '../../../../src/theme';
import { testRender } from '../../../utils/testRender';

describe('Switch', () => {
  it('renders properly', () => {
    testRender(<Switch checked={false} onChange={() => {}} />);
    expect(screen.getByRole('switch')).toBeInTheDocument();
  });

  it('can be toggled', () => {
    const handleChange = jest.fn();
    testRender(<Switch checked={false} onChange={handleChange} />);
    
    const switchElement = screen.getByRole('switch');
    
    // Default state should be unchecked
    expect(switchElement).toHaveAttribute('aria-checked', 'false');
    
    // Click to toggle
    fireEvent.click(switchElement);
    expect(handleChange).toHaveBeenCalled();
  });

  it('works with controlled components', () => {
    const handleChange = jest.fn();
    
    testRender(
      <Switch 
        checked={true} 
        onChange={handleChange} 
      />
    );
    
    const switchElement = screen.getByRole('switch');
    expect(switchElement).toHaveAttribute('aria-checked', 'true');
    
    fireEvent.click(switchElement);
    expect(handleChange).toHaveBeenCalled();
  });

  it('applies disabled styling when disabled', () => {
    testRender(<Switch checked={false} onChange={() => {}} disabled />);
    
    const switchElement = screen.getByRole('switch');
    expect(switchElement).toHaveClass('disabled');
    expect(switchElement).toHaveAttribute('aria-disabled', 'true');
  });
}); 