import React, { useState, useEffect, ReactNode } from 'react';
import { NetworkStatusContext, defaultNetworkStatus, NetworkStatus, networkService } from '../services/networkService';

interface NetworkStatusProviderProps {
  children: ReactNode;
}

export const NetworkStatusProvider: React.FC<NetworkStatusProviderProps> = ({ children }) => {
  const [networkStatus, setNetworkStatus] = useState<NetworkStatus>(defaultNetworkStatus);
  const [isFirstConnect, setIsFirstConnect] = useState<boolean>(true);

  useEffect(() => {
    // Get initial network status
    const initNetworkStatus = async () => {
      try {
        const status = await networkService.getStatus();
        setNetworkStatus(status);
        setIsFirstConnect(!status.connected);
      } catch (error) {
        console.error('Failed to get initial network status', error);
      }
    };

    initNetworkStatus();

    // Subscribe to network status changes
    const unsubscribe = networkService.subscribe((status) => {
      setNetworkStatus(status);
      
      // Show reconnection notification when going from offline to online, 
      // but not on first load
      if (status.connected && !networkStatus.connected && !isFirstConnect) {
        // You could trigger a notification here or dispatch an action
        // Reconnected to network, syncing data...
      }
      
      // If we've connected once, mark first connect as done
      if (status.connected) {
        setIsFirstConnect(false);
      }
    });

    return () => {
      unsubscribe();
    };
  }, [networkStatus.connected, isFirstConnect]);

  return (
    <NetworkStatusContext.Provider value={{ status: networkStatus, isOnline: networkStatus.connected }}>
      {children}
    </NetworkStatusContext.Provider>
  );
}; 