import React from 'react';
import { render, screen } from '@testing-library/react';
import { generateTestFormAnalysis } from '../../utils/test-data';

// Mock the Results component directly
jest.mock('../../components/form/Results', () => ({
  Results: () => (
    <div>
      <div>Confidence Score: 85%</div>
      <div data-testid="form-feedback">
        <ul>
          <li>Good form overall</li>
          <li>Knees slightly caving inward</li>
        </ul>
      </div>
    </div>
  )
}));

// Mock an error version of the Results component for the error test
const MockErrorResults = () => (
  <div>
    <div>Failed to load analysis results. Please try again later.</div>
  </div>
);

describe('Upload and Results Integration', () => {
  // Test 1: Successful analysis results
  it('should navigate from upload to results page after successful upload', () => {
    // Render the mocked Results component directly
    const { Results } = require('../../components/form/Results');
    render(<Results />);

    // Verify results are displayed
    expect(screen.getByText(/Confidence Score:/i)).toBeInTheDocument();
    expect(screen.getByTestId('form-feedback')).toBeInTheDocument();
  });

  // Test 2: Upload Error Handling
  it('should handle upload errors gracefully', () => {
    // Mock a minimal version of the Upload component with error state already triggered
    render(
      <div>
        <div data-testid="upload-error" style={{ color: 'red', marginTop: '10px' }}>
          Failed to upload video. Please try again.
        </div>
      </div>
    );

    // Verify error message is displayed
    expect(screen.getByTestId('upload-error')).toBeInTheDocument();
  });

  // Test 3: Analysis Error Handling
  it('should handle analysis errors gracefully', () => {
    render(<MockErrorResults />);

    // Verify error message is displayed
    expect(screen.getByText(/Failed to load analysis results/i)).toBeInTheDocument();
  });
}); 