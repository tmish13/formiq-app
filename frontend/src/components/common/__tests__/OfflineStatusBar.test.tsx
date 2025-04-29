import React from 'react';
import { render, screen } from '@testing-library/react';
import { ThemeProvider } from 'styled-components';
import { OfflineStatusBar } from '../OfflineStatusBar';
import { theme } from '../../../theme';
import { useNetworkStatus } from '../../../services/networkService';

// Mock the network service
jest.mock('../../../services/networkService');
const mockUseNetworkStatus = useNetworkStatus as jest.MockedFunction<typeof useNetworkStatus>;

describe('OfflineStatusBar', () => {
  const renderWithTheme = (component: React.ReactNode) => {
    return render(
      <ThemeProvider theme={theme}>
        {component}
      </ThemeProvider>
    );
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders when offline', () => {
    // Mock navigator.onLine to false for this test
    Object.defineProperty(navigator, 'onLine', { 
      configurable: true,
      value: false,
      writable: true
    });
    
    mockUseNetworkStatus.mockReturnValue({ 
      status: { connected: false, connectionType: 'none' },
      isOnline: false
    });
    renderWithTheme(<OfflineStatusBar />);
    expect(screen.getByText('You are offline')).toBeInTheDocument();
  });

  it('does not render when online', () => {
    // Mock navigator.onLine to true for this test
    Object.defineProperty(navigator, 'onLine', { 
      configurable: true,
      value: true,
      writable: true
    });
    
    // Ensure mock returns connected: true to make the component hide
    mockUseNetworkStatus.mockReturnValue({ 
      status: { connected: true, connectionType: 'wifi' },
      isOnline: true
    });
    
    renderWithTheme(<OfflineStatusBar />);
    
    // Just check that the text is not visible
    expect(screen.queryByText('You are offline')).not.toBeInTheDocument();
  });

  it('renders queue count when provided', () => {
    // Mock navigator.onLine to false for this test
    Object.defineProperty(navigator, 'onLine', { 
      configurable: true,
      value: false,
      writable: true
    });
    
    mockUseNetworkStatus.mockReturnValue({ 
      status: { connected: false, connectionType: 'none' },
      isOnline: false
    });
    renderWithTheme(<OfflineStatusBar queueCount={2} />);
    expect(screen.getByText('2 requests queued for when you\'re back online')).toBeInTheDocument();
  });

  it('renders singular queue count when count is 1', () => {
    // Mock navigator.onLine to false for this test
    Object.defineProperty(navigator, 'onLine', { 
      configurable: true,
      value: false,
      writable: true
    });
    
    mockUseNetworkStatus.mockReturnValue({ 
      status: { connected: false, connectionType: 'none' },
      isOnline: false
    });
    renderWithTheme(<OfflineStatusBar queueCount={1} />);
    expect(screen.getByText('1 request queued for when you\'re back online')).toBeInTheDocument();
  });

  it('does not render queue info when count is 0', () => {
    // Mock navigator.onLine to false for this test
    Object.defineProperty(navigator, 'onLine', { 
      configurable: true,
      value: false,
      writable: true
    });
    
    mockUseNetworkStatus.mockReturnValue({ 
      status: { connected: false, connectionType: 'none' },
      isOnline: false
    });
    renderWithTheme(<OfflineStatusBar queueCount={0} />);
    expect(screen.queryByText(/requests queued/)).not.toBeInTheDocument();
  });
}); 