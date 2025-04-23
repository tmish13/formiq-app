import React from 'react';
import { render, screen } from '@testing-library/react';
import { ThemeProvider } from 'styled-components';
import { OfflineStatusBar } from '../../../../src/components/common/OfflineStatusBar';
import { theme } from '../../../../src/theme';
import { useNetworkStatus } from '../../../../src/services/networkService';

// Mock the network service
jest.mock('../../../../src/services/networkService');
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
    mockUseNetworkStatus.mockReturnValue({ 
      status: { connected: false, connectionType: 'none' },
      isOnline: false
    });
    renderWithTheme(<OfflineStatusBar />);
    expect(screen.getByText('You are offline')).toBeInTheDocument();
  });

  it('does not render when online', () => {
    mockUseNetworkStatus.mockReturnValue({ 
      status: { connected: true, connectionType: 'wifi' },
      isOnline: true
    });
    renderWithTheme(<OfflineStatusBar />);
    expect(screen.queryByText('You are offline')).not.toBeInTheDocument();
  });

  it('renders queue count when provided', () => {
    mockUseNetworkStatus.mockReturnValue({ 
      status: { connected: false, connectionType: 'none' },
      isOnline: false
    });
    renderWithTheme(<OfflineStatusBar queueCount={2} />);
    expect(screen.getByText('2 requests queued for when you\'re back online')).toBeInTheDocument();
  });

  it('renders singular queue count when count is 1', () => {
    mockUseNetworkStatus.mockReturnValue({ 
      status: { connected: false, connectionType: 'none' },
      isOnline: false
    });
    renderWithTheme(<OfflineStatusBar queueCount={1} />);
    expect(screen.getByText('1 request queued for when you\'re back online')).toBeInTheDocument();
  });

  it('does not render queue info when count is 0', () => {
    mockUseNetworkStatus.mockReturnValue({ 
      status: { connected: false, connectionType: 'none' },
      isOnline: false
    });
    renderWithTheme(<OfflineStatusBar queueCount={0} />);
    expect(screen.queryByText(/requests queued/)).not.toBeInTheDocument();
  });
}); 