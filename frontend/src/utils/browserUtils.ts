/**
 * Utilities for accessing and handling browser-specific APIs
 */

/**
 * Interface for browser media APIs
 */
export interface BrowserMediaAPIs {
  MediaRecorder?: typeof MediaRecorder;
  mediaDevices?: {
    getUserMedia?: (constraints: MediaStreamConstraints) => Promise<MediaStream>;
    enumerateDevices?: () => Promise<MediaDeviceInfo[]>;
  };
  URL?: {
    createObjectURL?: (object: any) => string;
    revokeObjectURL?: (url: string) => void;
  };
  navigator?: {
    mediaDevices?: {
      getUserMedia?: (constraints: MediaStreamConstraints) => Promise<MediaStream>;
      enumerateDevices?: () => Promise<MediaDeviceInfo[]>;
    };
  };
  getUserMedia?: (constraints: MediaStreamConstraints) => Promise<MediaStream>;
  createObjectURL?: (object: any) => string;
}

/**
 * Gets the browser APIs needed for media operations
 * @returns An object containing browser media APIs
 */
export function getBrowserAPIs(): BrowserMediaAPIs {
  if (typeof window === 'undefined') {
    return {};
  }

  const apis: BrowserMediaAPIs = {
    MediaRecorder: typeof MediaRecorder !== 'undefined' ? MediaRecorder : undefined,
    mediaDevices: typeof navigator !== 'undefined' && navigator.mediaDevices
      ? navigator.mediaDevices
      : undefined,
    URL: typeof URL !== 'undefined' ? URL : undefined,
    navigator: typeof navigator !== 'undefined' ? navigator : undefined
  };
  
  // Add direct access to getUserMedia for convenience
  if (apis.mediaDevices && apis.mediaDevices.getUserMedia) {
    apis.getUserMedia = apis.mediaDevices.getUserMedia.bind(apis.mediaDevices);
  }
  
  // Add direct access to createObjectURL for convenience
  if (apis.URL && apis.URL.createObjectURL) {
    apis.createObjectURL = apis.URL.createObjectURL.bind(apis.URL);
  }
  
  return apis;
}

/**
 * Checks if the device has camera capabilities
 * @returns Promise resolving to a boolean indicating camera availability
 */
export async function checkCameraAvailability(): Promise<boolean> {
  try {
    const mediaDevices = getBrowserAPIs().mediaDevices;
    
    if (!mediaDevices || !mediaDevices.enumerateDevices) {
      return false;
    }
    
    const devices = await mediaDevices.enumerateDevices();
    return devices.some(device => device.kind === 'videoinput');
  } catch (error) {
    console.error('Error checking camera availability:', error);
    return false;
  }
}

/**
 * Checks if the browser supports the MediaRecorder API
 * @returns Boolean indicating MediaRecorder support
 */
export function supportsMediaRecorder(): boolean {
  return typeof MediaRecorder !== 'undefined';
}

/**
 * Detects if the current environment is a mobile device
 * @returns Boolean indicating if user is on a mobile device
 */
export function isMobileDevice(): boolean {
  if (typeof navigator === 'undefined' || !navigator.userAgent) {
    return false;
  }
  
  const userAgent = navigator.userAgent.toLowerCase();
  return /android|webos|iphone|ipad|ipod|blackberry|windows phone/i.test(userAgent);
}

/**
 * Checks if the browser supports the required features for the application
 * @returns An object with support status for various features
 */
export function checkBrowserSupport(): Record<string, boolean> {
  return {
    mediaRecorder: supportsMediaRecorder(),
    mediaDevices: typeof navigator !== 'undefined' && 
                 !!navigator.mediaDevices &&
                 !!navigator.mediaDevices.getUserMedia,
    canvas: typeof document !== 'undefined' && 
           !!document.createElement('canvas').getContext('2d')
  };
}

/**
 * Checks if a specific media type is supported by the browser
 * @param mimeType The mime type to check
 */
export function isMediaTypeSupported(mimeType: string): boolean {
  const { MediaRecorder } = getBrowserAPIs();
  
  if (MediaRecorder && typeof MediaRecorder.isTypeSupported === 'function') {
    return MediaRecorder.isTypeSupported(mimeType);
  }
  
  return false;
}

/**
 * Checks if the device has camera capabilities
 */
export async function hasCameraSupport(): Promise<boolean> {
  const apis = getBrowserAPIs();
  
  if (!apis.getUserMedia) {
    return false;
  }
  
  try {
    const stream = await apis.getUserMedia({ video: true });
    const tracks = stream.getTracks();
    tracks.forEach((track: MediaStreamTrack) => track.stop());
    return tracks.length > 0;
  } catch (error) {
    return false;
  }
}

/**
 * Checks if the device has microphone capabilities
 */
export async function hasMicrophoneSupport(): Promise<boolean> {
  const apis = getBrowserAPIs();
  
  if (!apis.getUserMedia) {
    return false;
  }
  
  try {
    const stream = await apis.getUserMedia({ audio: true });
    const tracks = stream.getTracks();
    tracks.forEach((track: MediaStreamTrack) => track.stop());
    return tracks.length > 0;
  } catch (error) {
    return false;
  }
} 