import { useState, useEffect, useCallback } from 'react';
import { Capacitor } from '@capacitor/core';
import { Camera, CameraPermissionState } from '@capacitor/camera';

interface CameraPermissionResult {
  granted: boolean;
  denied: boolean;
  requested: boolean;
  error: string | null;
  isLoading: boolean;
  requestPermission: () => Promise<boolean>;
}

/**
 * Custom hook for managing camera permissions across platforms
 * Handles web and native permissions differently, with proper fallbacks
 */
export const useCameraPermissions = (): CameraPermissionResult => {
  const [granted, setGranted] = useState(false);
  const [denied, setDenied] = useState(false);
  const [requested, setRequested] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const isNative = Capacitor.isNativePlatform();

  // Check for camera permissions on component mount
  useEffect(() => {
    const checkPermissions = async () => {
      try {
        setIsLoading(true);
        const permissionState = await Camera.checkPermissions();
        
        if (permissionState.camera === 'granted') {
          setGranted(true);
          setDenied(false);
        } else if (permissionState.camera === 'denied') {
          setGranted(false);
          setDenied(true);
        } else {
          setGranted(false);
          setDenied(false);
        }
        
        setRequested(permissionState.camera !== 'prompt');
        setError(null);
      } catch (err) {
        console.error('Error checking camera permissions:', err);
        setError('Failed to check camera permissions');
        setGranted(false);
        setDenied(true);
      } finally {
        setIsLoading(false);
      }
    };

    checkPermissions();
  }, []);

  // Function to request camera permissions
  const requestPermission = useCallback(async (): Promise<boolean> => {
    try {
      setIsLoading(true);
      setRequested(true);
      
      const permissionState = await Camera.requestPermissions({
        permissions: ['camera'],
      });
      
      const isGranted = permissionState.camera === 'granted';
      setGranted(isGranted);
      setDenied(!isGranted);
      setError(null);
      
      return isGranted;
    } catch (err) {
      console.error('Error requesting camera permissions:', err);
      setError('Failed to request camera permissions');
      setGranted(false);
      setDenied(true);
      return false;
    } finally {
      setIsLoading(false);
    }
  }, []);

  return {
    granted,
    denied,
    requested,
    error,
    isLoading,
    requestPermission,
  };
}; 