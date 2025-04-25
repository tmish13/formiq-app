import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import History from '../../../src/pages/analysis/History';
import { ThemeProvider } from 'styled-components';
import { theme } from '../../../src/theme';
import { BrowserRouter } from 'react-router-dom';
import formCheckReducer from '../../../src/store/slices/formCheckSlice';
import { formCheckService } from '../../../src/services/formCheckService';
import { renderWithProviders } from '../../utils/test-utils';

// Mock formCheckService
jest.mock('../../../src/services/formCheckService', () => ({
  formCheckService: {
    getFormChecks: jest.fn()
  }
}));

// Mock data
const mockFormChecks = [
  {
    id: '1',
    exercise_type: 'squat',
    status: 'completed',
    score: 95,
    created_at: '2024-01-15T10:00:00Z',
    overall_feedback: 'Good form overall',
    feedback: {
      overall: 'Good form overall',
      issues: ['Keep your back straight'],
      suggestions: ['Focus on depth']
    }
  },
  {
    id: '2',
    exercise_type: 'deadlift',
    status: 'completed',
    score: 88,
    created_at: '2024-01-14T15:30:00Z',
    overall_feedback: 'Good form overall',
    feedback: {
      overall: 'Good form overall',
      issues: ['Slight rounding in lower back'],
      suggestions: ['Engage core before lifting']
    }
  }
];

describe('History Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('displays loading state initially', () => {
    renderWithProviders(<History />, {
      initialState: {
        formCheck: {
          formChecks: [],
          currentFormCheck: null,
          isLoading: true,
          error: null
        }
      }
    });
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
    expect(screen.getByLabelText('Loading form checks')).toBeInTheDocument();
  });
  
  it('displays form checks when data is loaded', async () => {
    renderWithProviders(<History />, {
      initialState: {
        formCheck: {
          formChecks: mockFormChecks,
          currentFormCheck: null,
          isLoading: false,
          error: null
        }
      }
    });
    
    // Check for table headers
    expect(screen.getByText('Date')).toBeInTheDocument();
    expect(screen.getByText('Exercise Type')).toBeInTheDocument();
    expect(screen.getByText('Status')).toBeInTheDocument();
    expect(screen.getByText('Feedback')).toBeInTheDocument();

    // Check for exercise types
    expect(screen.getByText('squat')).toBeInTheDocument();
    expect(screen.getByText('deadlift')).toBeInTheDocument();

    // Check for status
    expect(screen.getAllByText('completed')).toHaveLength(2);

    // Check for feedback
    expect(screen.getAllByText('Good form overall')).toHaveLength(2);
  });
  
  it('displays formatted dates', async () => {
    renderWithProviders(<History />, {
      initialState: {
        formCheck: {
          formChecks: mockFormChecks,
          currentFormCheck: null,
          isLoading: false,
          error: null
        }
      }
    });
    
    // Get all cells and filter for date cells
    const cells = screen.getAllByRole('cell');
    const dateCells = cells.filter(cell => 
      cell.textContent?.match(/\d{1,2}\/\d{1,2}\/\d{4}/)
    );
    expect(dateCells).toHaveLength(2);
  });
  
  it('displays error message when API call fails', async () => {
    const errorMessage = 'Failed to load form checks';
    renderWithProviders(<History />, {
      initialState: {
        formCheck: {
          formChecks: [],
          currentFormCheck: null,
          isLoading: false,
          error: errorMessage
        }
      }
    });
    
    expect(screen.getByRole('alert')).toHaveTextContent(errorMessage);
  });
  
  it('handles empty state when no form checks exist', async () => {
    renderWithProviders(<History />, {
      initialState: {
        formCheck: {
          formChecks: [],
          currentFormCheck: null,
          isLoading: false,
          error: null
        }
      }
    });
    
    expect(screen.getByText('No form checks found')).toBeInTheDocument();
    expect(screen.getByText('Start by recording your first form check')).toBeInTheDocument();
  });

  it('displays dash for missing feedback', async () => {
    const formChecksWithMissingFeedback = [
      {
        ...mockFormChecks[0],
        overall_feedback: null
      }
    ];
    renderWithProviders(<History />, {
      initialState: {
        formCheck: {
          formChecks: formChecksWithMissingFeedback,
          currentFormCheck: null,
          isLoading: false,
          error: null
        }
      }
    });
    
    expect(screen.getByText('-')).toBeInTheDocument();
  });
}); 