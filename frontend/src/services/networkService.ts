import { Network, NetworkStatus as CapacitorNetworkStatus } from '@capacitor/network';
import { createContext, useContext } from 'react';
import { Capacitor } from '@capacitor/core';

// Define network status interface
export interface NetworkStatus {
  connected: boolean;
  connectionType: string;
}

// Default status
export const defaultNetworkStatus: NetworkStatus = {
  connected: true,
  connectionType: 'wifi',
};

// Create context for network status
export const NetworkStatusContext = createContext<{
  status: NetworkStatus;
  isOnline: boolean;
}>({
  status: defaultNetworkStatus,
  isOnline: true,
});

// Custom hook to use network status
export const useNetworkStatus = () => useContext(NetworkStatusContext);

// Network service to handle online/offline detection
class NetworkService {
  private listeners: Array<(status: NetworkStatus) => void> = [];
  private currentStatus: NetworkStatus = defaultNetworkStatus;
  private initialized = false;
  private networkListener: any = null;
  private retryCount = 0;
  private maxRetries = 3;

  constructor() {
    this.initialize();
  }

  // Initialize network status detection with retry mechanism
  private async initialize() {
    if (this.initialized) {
      return;
    }

    try {
      // Get initial network status
      if (Capacitor.isNativePlatform()) {
        // Native implementation using Capacitor
        const status = await Network.getStatus();
        this.currentStatus = {
          connected: status.connected,
          connectionType: status.connectionType,
        };

        // Listen for network status changes
        this.networkListener = Network.addListener('networkStatusChange', (status: CapacitorNetworkStatus) => {
          this.currentStatus = {
            connected: status.connected,
            connectionType: status.connectionType,
          };
          this.notifyListeners();
        });
      } else {
        // Web implementation
        this.currentStatus = {
          connected: navigator.onLine,
          connectionType: navigator.onLine ? 'wifi' : 'none',
        };

        // Add browser event listeners for web
        window.addEventListener('online', this.handleOnline);
        window.addEventListener('offline', this.handleOffline);
      }

      this.initialized = true;
      this.retryCount = 0;
    } catch (error) {
      console.error('Error initializing network service:', error);
      
      // Retry initialization with exponential backoff
      if (this.retryCount < this.maxRetries) {
        this.retryCount++;
        const delay = Math.pow(2, this.retryCount) * 1000;
        console.log(`Retrying network service initialization in ${delay}ms (attempt ${this.retryCount}/${this.maxRetries})`);
        
        setTimeout(() => {
          this.initialize();
        }, delay);
      }
      
      // Fallback to browser API when all retries fail or immediately in web
      this.currentStatus = {
        connected: navigator.onLine,
        connectionType: navigator.onLine ? 'wifi' : 'none',
      };

      // Add browser event listeners as fallback
      window.addEventListener('online', this.handleOnline);
      window.addEventListener('offline', this.handleOffline);
    }
  }

  private handleOnline = () => {
    this.currentStatus = {
      connected: true,
      connectionType: 'wifi',
    };
    this.notifyListeners();
  };

  private handleOffline = () => {
    this.currentStatus = {
      connected: false,
      connectionType: 'none',
    };
    this.notifyListeners();
  };

  // Cleanup resources when service is destroyed
  public cleanup() {
    if (Capacitor.isNativePlatform() && this.networkListener) {
      this.networkListener.remove();
    } else {
      window.removeEventListener('online', this.handleOnline);
      window.removeEventListener('offline', this.handleOffline);
    }
  }

  // Get current network status
  async getStatus(): Promise<NetworkStatus> {
    if (!this.initialized) {
      await this.initialize();
    }
    
    // Recheck status for web implementation
    if (!Capacitor.isNativePlatform()) {
      this.currentStatus = {
        connected: navigator.onLine,
        connectionType: navigator.onLine ? 'wifi' : 'none',
      };
    }
    
    return this.currentStatus;
  }

  // Subscribe to network status changes
  subscribe(listener: (status: NetworkStatus) => void): () => void {
    this.listeners.push(listener);

    // Return unsubscribe function
    return () => {
      this.listeners = this.listeners.filter((l) => l !== listener);
    };
  }

  // Notify all listeners of status change
  private notifyListeners() {
    this.listeners.forEach((listener) => listener(this.currentStatus));
  }

  // Check if device is online
  async isOnline(): Promise<boolean> {
    const status = await this.getStatus();
    return status.connected;
  }
}

// Export singleton instance
export const networkService = new NetworkService();

export { Network }; 