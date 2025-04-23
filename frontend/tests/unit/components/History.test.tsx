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
    score: 95,
    created_at: '2024-01-15T10:00:00Z',
    feedback: {
      overall: 'Good form overall',
      issues: ['Keep your back straight'],
      suggestions: ['Focus on depth']
    }
  },
  {
    id: '2',
    exercise_type: 'deadlift',
    score: 88,
    created_at: '2024-01-14T15:30:00Z',
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
    (formCheckService.getFormChecks as jest.Mock).mockImplementation(() => new Promise(() => {}));
    renderWithProviders(<History />);
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });
  
  it('displays form checks when data is loaded', async () => {
    (formCheckService.getFormChecks as jest.Mock).mockResolvedValue(mockFormChecks);
    renderWithProviders(<History />);
    
    await waitFor(() => {
      expect(screen.getByText('squat')).toBeInTheDocument();
      expect(screen.getByText('deadlift')).toBeInTheDocument();
      expect(screen.getByText('Good form overall')).toBeInTheDocument();
      expect(screen.getByText('Keep your back straight')).toBeInTheDocument();
    });
  });
  
  it('displays formatted dates', async () => {
    (formCheckService.getFormChecks as jest.Mock).mockResolvedValue(mockFormChecks);
    renderWithProviders(<History />);
    
    await waitFor(() => {
      const dateCells = screen.getAllByRole('cell').filter(cell => 
        cell.textContent?.match(/\d{1,2}\/\d{1,2}\/\d{4}/)
      );
      expect(dateCells).toHaveLength(2);
    });
  });
  
  it('displays error message when API call fails', async () => {
    const errorMessage = 'Error loading form checks';
    (formCheckService.getFormChecks as jest.Mock).mockRejectedValue(new Error(errorMessage));
    
    renderWithProviders(<History />);
    
    await waitFor(() => {
      expect(screen.getByText(/error loading form checks/i)).toBeInTheDocument();
    });
  });
  
  it('handles empty state when no form checks exist', async () => {
    (formCheckService.getFormChecks as jest.Mock).mockResolvedValue([]);
    renderWithProviders(<History />);
    
    await waitFor(() => {
      expect(screen.getByText('No form checks found')).toBeInTheDocument();
      expect(screen.getByText('Start by recording your first form check')).toBeInTheDocument();
    });
  });
}); 