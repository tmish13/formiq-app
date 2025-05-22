import React from 'react';
import { testRender, fireEvent } from '../../test-utils';
import { UploadGuidance } from '../UploadGuidance';
import { screen, waitFor } from '@testing-library/react';

describe('UploadGuidance Component', () => {
  const mockProps = {
    onChange: jest.fn(),
    exerciseType: 'squat'
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  /**
   * Tests for basic rendering and structure
   */
  describe('Basic Component Rendering', () => {
    it('renders without crashing', () => {
      testRender(<UploadGuidance {...mockProps} />);
      expect(screen.getByTestId('upload-guidance')).toBeInTheDocument();
    });

    it('displays upload guidance text', () => {
      testRender(<UploadGuidance {...mockProps} />);
      expect(screen.getByText(/Drag & drop your video here/i)).toBeInTheDocument();
    });

    it('displays supported file formats', () => {
      testRender(<UploadGuidance {...mockProps} />);
      expect(screen.getByText(/Supported formats: MP4, WebM, MOV/i)).toBeInTheDocument();
    });
  });

  /**
   * Tests for guidance content
   */
  describe('Guidance Content', () => {
    it('displays all common guidance items', () => {
      testRender(<UploadGuidance {...mockProps} />);
      expect(screen.getByText(/Position your camera/i)).toBeInTheDocument();
      expect(screen.getByText(/Ensure good lighting/i)).toBeInTheDocument();
      expect(screen.getByText(/Record from the side angle/i)).toBeInTheDocument();
      expect(screen.getByText(/Keep the camera stable/i)).toBeInTheDocument();
      expect(screen.getByText(/Wear clothing/i)).toBeInTheDocument();
    });

    it('displays squat-specific guidance when exerciseType is squat', () => {
      testRender(<UploadGuidance {...mockProps} />);
      expect(screen.getByText(/Keep your feet shoulder-width apart/i)).toBeInTheDocument();
      expect(screen.getByText(/Lower your body until your thighs are parallel/i)).toBeInTheDocument();
    });
    
    it('displays deadlift-specific guidance when exerciseType is deadlift', () => {
      testRender(<UploadGuidance {...{ ...mockProps, exerciseType: 'deadlift' }} />);
      expect(screen.getByText(/Position the bar over mid-foot/i)).toBeInTheDocument();
      expect(screen.getByText(/Maintain a neutral spine/i)).toBeInTheDocument();
    });
    
    it('displays bench press-specific guidance when exerciseType is bench_press', () => {
      testRender(<UploadGuidance {...{ ...mockProps, exerciseType: 'bench_press' }} />);
      expect(screen.getByText(/Lie flat on the bench/i)).toBeInTheDocument();
      expect(screen.getByText(/Keep your feet flat on the ground/i)).toBeInTheDocument();
    });
  });

  /**
   * Tests for tooltips and help text
   */
  describe('Tooltips & Help Text', () => {
    it('displays tooltip on hover', async () => {
      testRender(<UploadGuidance {...mockProps} />);
      
      // Find tooltip trigger element
      const tooltipTrigger = screen.getByTestId('tooltip-trigger');
      
      // Simulate hover
      fireEvent.mouseOver(tooltipTrigger);
      
      // Wait for tooltip to appear
      await waitFor(() => {
        expect(screen.getByTestId('tooltip-content')).toBeInTheDocument();
        expect(screen.getByText(/Position yourself from the side/i)).toBeInTheDocument();
      });
    });
    
    it('closes tooltip on mouse out', async () => {
      testRender(<UploadGuidance {...mockProps} />);
      
      const tooltipTrigger = screen.getByTestId('tooltip-trigger');
      
      // Show tooltip
      fireEvent.mouseOver(tooltipTrigger);
      
      // Verify tooltip is shown
      await waitFor(() => {
        expect(screen.getByTestId('tooltip-content')).toBeInTheDocument();
      });
      
      // Hide tooltip
      fireEvent.mouseOut(tooltipTrigger);
      
      // Verify tooltip is hidden
      await waitFor(() => {
        expect(screen.queryByTestId('tooltip-content')).not.toBeInTheDocument();
      });
    });
    
    it('shows help icon next to each guidance item', () => {
      testRender(<UploadGuidance {...mockProps} />);
      
      // There should be multiple help icons, at least one for each guidance item
      const helpIcons = screen.getAllByTestId('help-icon');
      expect(helpIcons.length).toBeGreaterThan(3); // Multiple guidance items with help
    });
  });

  /**
   * Tests for file input interaction
   */
  describe('File Input Interaction', () => {
    it('calls onChange when file is selected', () => {
      testRender(<UploadGuidance {...mockProps} />);
      const fileInput = screen.getByTestId('file-input');
      
      // Create a mock file
      const file = new File(['test'], 'test.mp4', { type: 'video/mp4' });
      
      // Mock the files property
      Object.defineProperty(fileInput, 'files', {
        value: [file]
      });
      
      // Trigger the change event
      fireEvent.change(fileInput);
      
      expect(mockProps.onChange).toHaveBeenCalled();
    });
    
    it('shows error when invalid file format is selected', () => {
      testRender(<UploadGuidance {...mockProps} />);
      const fileInput = screen.getByTestId('file-input');
      
      // Create a mock invalid file
      const file = new File(['test'], 'test.txt', { type: 'text/plain' });
      
      // Mock the files property
      Object.defineProperty(fileInput, 'files', {
        value: [file]
      });
      
      // Trigger the change event
      fireEvent.change(fileInput);
      
      // Verify error is shown
      expect(screen.getByText(/Unsupported file format/i)).toBeInTheDocument();
      
      // Verify onChange was not called
      expect(mockProps.onChange).not.toHaveBeenCalled();
    });
  });

  /**
   * Tests for responsive design
   */
  describe('Responsive Design', () => {
    it('adapts to mobile layout', () => {
      // Mock window.matchMedia
      window.matchMedia = jest.fn().mockImplementation(query => {
        return {
          matches: query.includes('max-width: 768px'),
          media: query,
          onchange: null,
          addListener: jest.fn(),
          removeListener: jest.fn(),
        };
      });
      
      testRender(<UploadGuidance {...mockProps} />);
      
      // Verify mobile-specific elements are present
      expect(screen.getByTestId('mobile-guidance')).toBeInTheDocument();
      expect(screen.getByTestId('mobile-upload-button')).toBeInTheDocument();
    });
    
    it('adapts to desktop layout', () => {
      // Mock window.matchMedia
      window.matchMedia = jest.fn().mockImplementation(query => {
        return {
          matches: !query.includes('max-width: 768px'),
          media: query,
          onchange: null,
          addListener: jest.fn(),
          removeListener: jest.fn(),
        };
      });
      
      testRender(<UploadGuidance {...mockProps} />);
      
      // Verify desktop-specific elements are present
      expect(screen.getByTestId('desktop-guidance')).toBeInTheDocument();
      expect(screen.getByTestId('desktop-upload-area')).toBeInTheDocument();
    });
  });

  /**
   * Tests for exercise-specific guidance
   */
  describe('Exercise-Specific Guidance', () => {
    it('updates guidance content when exercise type changes', () => {
      const { rerender } = testRender(<UploadGuidance {...mockProps} />);
      
      // Verify squat guidance is shown
      expect(screen.getByText(/Keep your feet shoulder-width apart/i)).toBeInTheDocument();
      
      // Update exercise type
      rerender(<UploadGuidance {...{ ...mockProps, exerciseType: 'deadlift' }} />);
      
      // Verify deadlift guidance is shown
      expect(screen.getByText(/Position the bar over mid-foot/i)).toBeInTheDocument();
      
      // Update to bench press
      rerender(<UploadGuidance {...{ ...mockProps, exerciseType: 'bench_press' }} />);
      
      // Verify bench press guidance is shown
      expect(screen.getByText(/Lie flat on the bench/i)).toBeInTheDocument();
    });
    
    it('shows correct video example for each exercise type', () => {
      const { rerender } = testRender(<UploadGuidance {...mockProps} />);
      
      // Verify squat example video is shown
      expect(screen.getByTestId('example-video')).toHaveAttribute('src', expect.stringContaining('squat-example'));
      
      // Update exercise type
      rerender(<UploadGuidance {...{ ...mockProps, exerciseType: 'deadlift' }} />);
      
      // Verify deadlift example video is shown
      expect(screen.getByTestId('example-video')).toHaveAttribute('src', expect.stringContaining('deadlift-example'));
    });
  });
}); 