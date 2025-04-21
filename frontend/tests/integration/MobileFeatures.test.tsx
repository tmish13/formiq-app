import React from 'react';
import { screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Camera } from '@capacitor/camera';
import { Preferences } from '@capacitor/preferences';
import { Network } from '@capacitor/network';
import { App } from '../../src/App';
import { render } from '../../src/test-utils';
import { act } from 'react-dom/test-utils';

// Mock components to avoid real UI rendering issues
jest.mock('../../src/components/FormCheck', () => ({
  __esModule: true,
  default: () => (
    <div data-testid="form-check-component">
      <button>Take Photo</button>
      <div>Camera Component</div>
      <img alt="preview" />
    </div>
  )
}));

jest.mock('../../src/components/Settings', () => ({
  __esModule: true,
  default: () => (
    <div data-testid="settings-component">
      <label>
        Dark Mode
        <input type="checkbox" role="switch" aria-label="dark mode" />
      </label>
      <button aria-label="clear preferences">Clear Preferences</button>
    </div>
  )
}));

jest.mock('../../src/components/Nav', () => ({
  __esModule: true,
  default: () => (
    <nav data-testid="nav-component">
      <a href="/form-check">Form Check</a>
      <a href="/settings">Settings</a>
    </nav>
  )
}));

// Mock Capacitor Camera plugin
const mockCameraGetPhoto = jest.fn().mockResolvedValue({
  path: 'path/to/photo.jpg',
  webPath: 'blob:photo.jpg',
  format: 'jpeg'
});

const mockCameraCheckPermissions = jest.fn().mockResolvedValue({ camera: 'granted' });
const mockCameraRequestPermissions = jest.fn().mockResolvedValue({ camera: 'granted' });

jest.mock('@capacitor/camera', () => ({
  Camera: {
    getPhoto: (...args: any[]) => mockCameraGetPhoto(...args),
    checkPermissions: (...args: any[]) => mockCameraCheckPermissions(...args),
    requestPermissions: (...args: any[]) => mockCameraRequestPermissions(...args)
  }
}));

// Mock Capacitor Preferences plugin
const mockPreferencesGet = jest.fn().mockResolvedValue({ value: 'test-token' });
const mockPreferencesSet = jest.fn().mockResolvedValue(undefined);
const mockPreferencesRemove = jest.fn().mockResolvedValue(undefined);
const mockPreferencesClear = jest.fn().mockResolvedValue(undefined);
const mockPreferencesKeys = jest.fn().mockResolvedValue({ keys: ['auth-token', 'user-settings'] });

jest.mock('@capacitor/preferences', () => ({
  Preferences: {
    get: (...args: any[]) => mockPreferencesGet(...args),
    set: (...args: any[]) => mockPreferencesSet(...args),
    remove: (...args: any[]) => mockPreferencesRemove(...args),
    clear: (...args: any[]) => mockPreferencesClear(...args),
    keys: (...args: any[]) => mockPreferencesKeys(...args)
  }
}));

// Mock Capacitor Network plugin
const mockNetworkGetStatus = jest.fn().mockResolvedValue({ connected: true, connectionType: 'wifi' });
const mockNetworkAddListener = jest.fn();
const mockNetworkRemoveListener = jest.fn();

jest.mock('@capacitor/network', () => {
  const listeners = new Set();
  return {
    Network: {
      getStatus: (...args: any[]) => mockNetworkGetStatus(...args),
      addListener: (event: string, callback: (status: any) => void) => {
        mockNetworkAddListener(event, callback);
        listeners.add(callback);
        return { remove: () => { 
          mockNetworkRemoveListener(); 
          listeners.delete(callback);
        }};
      },
      // Method to simulate network status change for tests
      _simulateStatusChange: (status: any) => {
        listeners.forEach((callback: any) => callback(status));
      }
    }
  };
});

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: jest.fn((key: string) => store[key] || null),
    setItem: jest.fn((key: string, value: string) => {
      store[key] = value;
    }),
    removeItem: jest.fn((key: string) => {
      delete store[key];
    }),
    clear: jest.fn(() => {
      store = {};
    }),
  };
})();

Object.defineProperty(window, 'localStorage', { value: localStorageMock });

// Create a mock router with navigation utilities
const mockNavigate = jest.fn();
jest.mock('react-router-dom', () => {
  const originalModule = jest.requireActual('react-router-dom');
  return {
    ...originalModule,
    useNavigate: () => mockNavigate,
    useLocation: jest.fn().mockReturnValue({
      pathname: '/',
      search: '',
      hash: '',
      state: null,
      key: 'default',
    }),
  };
});

// Mock camera error component
jest.mock('../../src/components/CameraError', () => ({
  __esModule: true,
  default: () => (
    <div data-testid="camera-error">Camera Permission Required</div>
  )
}));

// Mock network status indicator component
jest.mock('../../src/components/NetworkStatus', () => ({
  __esModule: true,
  default: ({ isOnline }: { isOnline: boolean }) => (
    <div data-testid="network-status">
      {isOnline ? 'Online Mode' : 'Offline Mode'}
      {!isOnline && <div>Cached Workouts</div>}
      {isOnline && <div>Syncing Data</div>}
    </div>
  )
}));

describe('Mobile Features Integration Tests', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorageMock.clear();
  });

  test('Camera functionality for form check', async () => {
    render(<App />);

    // Force app to render initially
    await waitFor(() => {
      expect(screen.getByTestId('nav-component')).toBeInTheDocument();
    });

    // Navigate to form check
    const formCheckLink = screen.getByText('Form Check');
    fireEvent.click(formCheckLink);

    // Verify navigation was called
    expect(mockNavigate).toHaveBeenCalledWith('/form-check', expect.anything());

    // Verify form check component is shown (mocked)
    await waitFor(() => {
      expect(screen.getByTestId('form-check-component')).toBeInTheDocument();
    });

    // Trigger camera
    const cameraButton = screen.getByRole('button', { name: /take photo/i });
    fireEvent.click(cameraButton);

    // Verify camera was called
    await waitFor(() => {
      expect(mockCameraGetPhoto).toHaveBeenCalled();
    });
  });

  test('Local storage and preferences', async () => {
    render(<App />);

    // Wait for app to render initially
    await waitFor(() => {
      expect(screen.getByTestId('nav-component')).toBeInTheDocument();
    });

    // Navigate to settings
    const settingsLink = screen.getByText('Settings');
    fireEvent.click(settingsLink);

    // Verify navigation was called
    expect(mockNavigate).toHaveBeenCalledWith('/settings', expect.anything());

    // Wait for settings component to appear
    await waitFor(() => {
      expect(screen.getByTestId('settings-component')).toBeInTheDocument();
    });

    // Change theme preference
    const darkModeSwitch = screen.getByRole('switch', { name: /dark mode/i });
    fireEvent.click(darkModeSwitch);

    // Verify preferences were set
    await waitFor(() => {
      expect(mockPreferencesSet).toHaveBeenCalled();
    });

    // Test clearing preferences
    const clearButton = screen.getByRole('button', { name: /clear preferences/i });
    fireEvent.click(clearButton);

    // Verify preferences were cleared
    await waitFor(() => {
      expect(mockPreferencesClear).toHaveBeenCalled();
    });
  });

  test('Network state changes', async () => {
    render(<App />);

    // Wait for app to render initially
    await waitFor(() => {
      expect(screen.getByTestId('nav-component')).toBeInTheDocument();
    });

    // Trigger offline state through the network plugin
    act(() => {
      (Network as any)._simulateStatusChange({ connected: false, connectionType: 'none' });
    });

    // Verify offline state is shown
    await waitFor(() => {
      expect(screen.getByText(/offline mode/i)).toBeInTheDocument();
    });

    // Trigger online state through the network plugin
    act(() => {
      (Network as any)._simulateStatusChange({ connected: true, connectionType: 'wifi' });
    });

    // Verify online state is shown
    await waitFor(() => {
      expect(screen.getByText(/online mode/i)).toBeInTheDocument();
      expect(screen.getByText(/syncing data/i)).toBeInTheDocument();
    });
  });

  test('Camera permissions handling', async () => {
    // Mock denied camera permissions
    mockCameraCheckPermissions.mockResolvedValueOnce({ camera: 'denied' });
    mockCameraRequestPermissions.mockResolvedValueOnce({ camera: 'denied' });

    render(<App />);

    // Wait for app to render initially
    await waitFor(() => {
      expect(screen.getByTestId('nav-component')).toBeInTheDocument();
    });

    // Navigate to form check
    const formCheckLink = screen.getByText('Form Check');
    fireEvent.click(formCheckLink);

    // Verify navigation was called
    expect(mockNavigate).toHaveBeenCalledWith('/form-check', expect.anything());

    // Wait for form check component to appear
    await waitFor(() => {
      expect(screen.getByTestId('form-check-component')).toBeInTheDocument();
    });

    // Trigger camera
    const cameraButton = screen.getByRole('button', { name: /take photo/i });
    fireEvent.click(cameraButton);

    // Verify permissions request
    await waitFor(() => {
      expect(mockCameraCheckPermissions).toHaveBeenCalled();
      expect(mockCameraRequestPermissions).toHaveBeenCalled();
    });
  });
}); 