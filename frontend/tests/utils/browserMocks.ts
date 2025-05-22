/**
 * Collection of browser API mocks for testing.
 * These utilities help avoid global mocks in setupTests.ts and allow
 * per-test control over mock behavior.
 */

// Create a mock BlobEvent if it doesn't exist in the test environment
if (typeof global.BlobEvent === 'undefined') {
  class MockBlobEvent extends Event {
    data: Blob;
    timecode: number;

    constructor(type: string, eventInitDict: { data: Blob; timecode: number }) {
      super(type);
      this.data = eventInitDict.data;
      this.timecode = eventInitDict.timecode;
    }
  }

  // Add to global
  Object.defineProperty(global, 'BlobEvent', {
    configurable: true,
    writable: true,
    value: MockBlobEvent
  });
}

// Mock MediaRecorder instance type
export interface MockMediaRecorderInstance {
  start: jest.Mock;
  stop: jest.Mock;
  pause: jest.Mock;
  resume: jest.Mock;
  requestData: jest.Mock;
  state: RecordingState;
  ondataavailable: null | ((event: any) => void);
  onstop: null | ((event: any) => void);
  onstart: null | ((event: any) => void);
  onerror: null | ((event: any) => void);
  onpause: null | ((event: any) => void);
  onresume: null | ((event: any) => void);
  addEventListener: jest.Mock;
  removeEventListener: jest.Mock;
  stream: MediaStream;
  mimeType: string;
}

// Mock MediaRecorder constructor type
export interface MockMediaRecorderConstructor {
  new(stream: MediaStream, options?: MediaRecorderOptions): MockMediaRecorderInstance;
  isTypeSupported: jest.Mock;
}

/**
 * Sets up media-related mocks like MediaRecorder
 * @returns Object containing mock implementations and cleanup function
 */
export function setupMediaMocks() {
  // Save original values
  const originalMediaRecorder = global.MediaRecorder;
  const hasMediaRecorder = typeof originalMediaRecorder !== 'undefined';

  // Media Recorder Mock
  class MockMediaRecorder {
    static isTypeSupported = jest.fn().mockReturnValue(true);
    
    ondataavailable: ((ev: BlobEvent) => void) | null = null;
    onerror: ((ev: Event) => void) | null = null;
    onpause: ((ev: Event) => void) | null = null;
    onresume: ((ev: Event) => void) | null = null;
    onstart: ((ev: Event) => void) | null = null;
    onstop: ((ev: Event) => void) | null = null;
    
    state: RecordingState = 'inactive';
    stream: MediaStream;
    videoBitsPerSecond: number = 0;
    audioBitsPerSecond: number = 0;
    mimeType: string = 'video/webm';
    
    start = jest.fn().mockImplementation((timeslice?: number): void => {
      this.state = 'recording';
      if (this.onstart) this.onstart(new Event('start'));
      
      // Simulate data available event after a small delay
      setTimeout(() => {
        if (this.ondataavailable) {
          const mockBlob = new Blob(['mock-video-data'], { type: 'video/webm' });
          this.ondataavailable(new BlobEvent('dataavailable', { data: mockBlob, timecode: 0 }));
        }
      }, 50);
    });
    
    stop = jest.fn().mockImplementation((): void => {
      this.state = 'inactive';
      if (this.onstop) this.onstop(new Event('stop'));
    });
    
    pause = jest.fn().mockImplementation((): void => {
      this.state = 'paused';
      if (this.onpause) this.onpause(new Event('pause'));
    });
    
    resume = jest.fn().mockImplementation((): void => {
      this.state = 'recording';
      if (this.onresume) this.onresume(new Event('resume'));
    });
    
    requestData = jest.fn().mockImplementation((): void => {
      const mockBlob = new Blob(['mock-video-data'], { type: 'video/webm' });
      if (this.ondataavailable) {
        this.ondataavailable(new BlobEvent('dataavailable', { data: mockBlob, timecode: 0 }));
      }
    });
    
    addEventListener = jest.fn().mockImplementation((event: string, handler: any): void => {
      switch (event) {
        case 'dataavailable':
          this.ondataavailable = handler;
          break;
        case 'start':
          this.onstart = handler;
          break;
        case 'stop':
          this.onstop = handler;
          break;
        case 'pause':
          this.onpause = handler;
          break;
        case 'resume':
          this.onresume = handler;
          break;
        case 'error':
          this.onerror = handler;
          break;
      }
    });
    
    removeEventListener = jest.fn().mockImplementation((event: string): void => {
      switch (event) {
        case 'dataavailable':
          this.ondataavailable = null;
          break;
        case 'start':
          this.onstart = null;
          break;
        case 'stop':
          this.onstop = null;
          break;
        case 'pause':
          this.onpause = null;
          break;
        case 'resume':
          this.onresume = null;
          break;
        case 'error':
          this.onerror = null;
          break;
      }
    });
    
    constructor(stream: MediaStream, options?: MediaRecorderOptions) {
      this.stream = stream;
    }
  }

  // Mock MediaDevices implementation
  const mockMediaDevices = {
    getUserMedia: jest.fn().mockImplementation((constraints: MediaStreamConstraints) => {
      return Promise.resolve({
        getTracks: jest.fn().mockReturnValue([
          {
            stop: jest.fn(),
            kind: constraints.video ? 'video' : 'audio',
            enabled: true,
            readyState: 'live',
            label: 'Mock Track',
            id: 'mock-track-id',
            addEventListener: jest.fn(),
            removeEventListener: jest.fn(),
            applyConstraints: jest.fn().mockResolvedValue(undefined),
            getCapabilities: jest.fn().mockReturnValue({
              width: { min: 320, max: 1280 },
              height: { min: 240, max: 720 }
            }),
            getConstraints: jest.fn().mockReturnValue(constraints)
          }
        ]),
        getVideoTracks: jest.fn().mockReturnValue([]),
        getAudioTracks: jest.fn().mockReturnValue([]),
        addEventListener: jest.fn(),
        removeEventListener: jest.fn(),
        clone: jest.fn().mockImplementation(() => {
          // Return a copy of the same stream object structure
          return {
            getTracks: jest.fn().mockReturnValue([]),
            getVideoTracks: jest.fn().mockReturnValue([]),
            getAudioTracks: jest.fn().mockReturnValue([]),
            addEventListener: jest.fn(),
            removeEventListener: jest.fn()
          };
        })
      });
    }),
    enumerateDevices: jest.fn().mockResolvedValue([
      {
        deviceId: 'mock-camera-id',
        kind: 'videoinput',
        label: 'Mock Camera',
        groupId: 'mock-group-1'
      },
      {
        deviceId: 'mock-mic-id',
        kind: 'audioinput',
        label: 'Mock Microphone',
        groupId: 'mock-group-1'
      }
    ]),
    getDisplayMedia: jest.fn().mockImplementation(() => {
      return Promise.resolve({
        getTracks: jest.fn().mockReturnValue([
          {
            stop: jest.fn(),
            kind: 'video',
            enabled: true,
            readyState: 'live',
            label: 'Mock Display',
            id: 'mock-display-id',
            addEventListener: jest.fn(),
            removeEventListener: jest.fn()
          }
        ])
      });
    }),
    addEventListener: jest.fn(),
    removeEventListener: jest.fn()
  };
  
  // Create a mock instance for easy reference
  const mockMediaRecorderInstance = new MockMediaRecorder({} as MediaStream);
  
  // Store original values to restore later
  const originalMediaDevices = navigator.mediaDevices;
  const originalCreateObjectURL = URL.createObjectURL;
  const originalRevokeObjectURL = URL.revokeObjectURL;
  
  // Apply mocks
  if (!hasMediaRecorder) {
    Object.defineProperty(global, 'MediaRecorder', {
      configurable: true,
      writable: true,
      value: MockMediaRecorder
    });
  } else {
    // Keep original but mock the static method
    global.MediaRecorder.isTypeSupported = jest.fn().mockImplementation(() => true);
  }
  
  // Check if we can modify the mediaDevices property
  const navigatorDescriptor = Object.getOwnPropertyDescriptor(navigator, 'mediaDevices');
  const canMockMediaDevices = !navigatorDescriptor || navigatorDescriptor.configurable;
  
  // Apply mocks - only if properties are configurable
  if (canMockMediaDevices) {
    Object.defineProperty(navigator, 'mediaDevices', {
      configurable: true,
      writable: true,
      value: mockMediaDevices
    });
  } else {
    // Directly mock the getUserMedia method if we can't redefine the property
    if (navigator.mediaDevices) {
      navigator.mediaDevices.getUserMedia = mockMediaDevices.getUserMedia;
      navigator.mediaDevices.enumerateDevices = mockMediaDevices.enumerateDevices;
      if ('getDisplayMedia' in navigator.mediaDevices) {
        // @ts-ignore - TypeScript may not know about this API depending on lib settings
        navigator.mediaDevices.getDisplayMedia = mockMediaDevices.getDisplayMedia;
      }
    }
  }
  
  // Mock URL methods
  const mockCreateObjectURL = jest.fn().mockReturnValue('mock-object-url');
  const mockRevokeObjectURL = jest.fn();
  
  Object.defineProperty(URL, 'createObjectURL', {
    configurable: true,
    writable: true,
    value: mockCreateObjectURL
  });
  
  Object.defineProperty(URL, 'revokeObjectURL', {
    configurable: true,
    writable: true,
    value: mockRevokeObjectURL
  });
  
  // Helper functions to trigger MediaRecorder events
  function triggerDataAvailable(data = new Blob(['mock-data'], { type: 'video/webm' })) {
    if (mockMediaRecorderInstance.ondataavailable) {
      mockMediaRecorderInstance.ondataavailable(new BlobEvent('dataavailable', { 
        data, 
        timecode: 0 
      }));
    }
  }

  function triggerStop() {
    if (mockMediaRecorderInstance.onstop) {
      mockMediaRecorderInstance.onstop(new Event('stop'));
    }
  }
  
  // Return mocks and cleanup function
  return {
    mockMediaRecorder: MockMediaRecorder,
    mockMediaRecorderInstance,
    mockMediaDevices,
    mockGetUserMedia: mockMediaDevices.getUserMedia,
    mockCreateObjectURL,
    mockRevokeObjectURL,
    triggerDataAvailable,
    triggerStop,
    cleanup: () => {
      // Restore original values
      if (!hasMediaRecorder) {
        Object.defineProperty(global, 'MediaRecorder', {
          configurable: true,
          writable: true,
          value: undefined
        });
      } else {
        // If it originally existed, just restore the isTypeSupported method
        global.MediaRecorder.isTypeSupported = originalMediaRecorder.isTypeSupported;
      }
      
      // Only restore if we were able to mock
      if (canMockMediaDevices) {
        Object.defineProperty(navigator, 'mediaDevices', {
          configurable: true,
          writable: true,
          value: originalMediaDevices
        });
      } else if (navigator.mediaDevices && originalMediaDevices) {
        // Restore the original methods
        navigator.mediaDevices.getUserMedia = originalMediaDevices.getUserMedia;
        navigator.mediaDevices.enumerateDevices = originalMediaDevices.enumerateDevices;
        if ('getDisplayMedia' in originalMediaDevices) {
          // @ts-ignore
          navigator.mediaDevices.getDisplayMedia = originalMediaDevices.getDisplayMedia;
        }
      }
      
      Object.defineProperty(URL, 'createObjectURL', {
        configurable: true,
        writable: true,
        value: originalCreateObjectURL
      });
      
      Object.defineProperty(URL, 'revokeObjectURL', {
        configurable: true,
        writable: true,
        value: originalRevokeObjectURL
      });
    }
  };
}

// Offline mode simulation utilities
export function setupNetworkMocks() {
  const originalOnLine = navigator.onLine;
  
  function setOnline(isOnline: boolean) {
    Object.defineProperty(navigator, 'onLine', {
      configurable: true,
      get: () => isOnline,
      set: () => {} // Prevent direct setting
    });
    
    // Dispatch the appropriate event
    window.dispatchEvent(new Event(isOnline ? 'online' : 'offline'));
  }
  
  return {
    setOnline,
    setOffline: () => setOnline(false),
    restoreOnlineStatus: () => {
      Object.defineProperty(navigator, 'onLine', {
        configurable: true,
        get: () => originalOnLine,
        set: () => {}
      });
    }
  };
}

// Export a specific instance for global use if needed
export const globalMediaMocks = setupMediaMocks();

/**
 * Full mock of IntersectionObserver that can be used in tests
 */
export class MockIntersectionObserver implements Partial<IntersectionObserver> {
  root: Element | null = null;
  rootMargin: string = '0px';
  thresholds: ReadonlyArray<number> = [0];
  
  observe = jest.fn();
  disconnect = jest.fn();
  unobserve = jest.fn();
  takeRecords = jest.fn().mockReturnValue([]);
  
  // Internal property to store callback for testing
  private readonly _callback: IntersectionObserverCallback;
  
  constructor(callback: IntersectionObserverCallback, options?: IntersectionObserverInit) {
    this._callback = callback;
    
    if (options?.root) {
      // Check if the root is an Element (not a Document)
      if (options.root instanceof Element) {
        this.root = options.root;
      } else {
        // If it's a Document, ignore it (IntersectionObserver API would do the same)
        this.root = null;
      }
    }
    
    if (options?.rootMargin) {
      this.rootMargin = options.rootMargin;
    }
    
    if (options?.threshold) {
      this.thresholds = Array.isArray(options.threshold) 
        ? options.threshold 
        : [options.threshold];
    }
  }
  
  // Method to trigger the callback in tests
  public triggerCallback(entries: Partial<IntersectionObserverEntry>[]) {
    this._callback(
      entries.map(entry => ({
        isIntersecting: false,
        intersectionRatio: 0,
        boundingClientRect: {} as DOMRectReadOnly,
        intersectionRect: {} as DOMRectReadOnly,
        rootBounds: null,
        target: document.createElement('div'),
        time: Date.now(),
        ...entry
      })),
      this as IntersectionObserver
    );
  }
}

/**
 * Full mock of ResizeObserver that can be used in tests
 */
export class MockResizeObserver implements Partial<ResizeObserver> {
  observe = jest.fn();
  disconnect = jest.fn();
  unobserve = jest.fn();
  
  // Internal property to store callback for testing
  private readonly _callback: ResizeObserverCallback;
  
  constructor(callback: ResizeObserverCallback) {
    this._callback = callback;
  }
  
  // Method to trigger the callback in tests
  public triggerCallback(entries: Partial<ResizeObserverEntry>[]) {
    this._callback(
      entries.map(entry => ({
        target: document.createElement('div'),
        contentRect: {} as DOMRectReadOnly,
        borderBoxSize: [],
        contentBoxSize: [],
        devicePixelContentBoxSize: [],
        ...entry
      })),
      this as ResizeObserver
    );
  }
}

/**
 * Sets up mocks for IntersectionObserver and ResizeObserver.
 * @returns Object containing mock instances and a cleanup function
 */
export function setupObserverMocks() {
  // Store original values
  const originalIntersectionObserver = global.IntersectionObserver;
  const originalResizeObserver = global.ResizeObserver;
  
  // Apply mocks
  Object.defineProperty(global, 'IntersectionObserver', {
    configurable: true,
    writable: true,
    value: MockIntersectionObserver
  });
  
  Object.defineProperty(global, 'ResizeObserver', {
    configurable: true,
    writable: true,
    value: MockResizeObserver
  });
  
  // Return mocks and cleanup function
  return {
    MockIntersectionObserver,
    MockResizeObserver,
    cleanup: () => {
      // Restore original values
      Object.defineProperty(global, 'IntersectionObserver', {
        configurable: true,
        writable: true,
        value: originalIntersectionObserver
      });
      
      Object.defineProperty(global, 'ResizeObserver', {
        configurable: true,
        writable: true,
        value: originalResizeObserver
      });
    }
  };
}

/**
 * Sets up mocks for HTML5 canvas operations.
 * @returns Object containing mock implementations and a cleanup function
 */
export function setupCanvasMocks() {
  // Store original method
  const originalGetContext = HTMLCanvasElement.prototype.getContext;
  
  // Create mock canvas context
  const mockCanvasRenderingContext2D = {
    drawImage: jest.fn(),
    getImageData: jest.fn().mockReturnValue({
      data: new Uint8ClampedArray(400), // 100 pixels (RGBA)
      width: 10,
      height: 10
    }),
    putImageData: jest.fn(),
    createImageData: jest.fn(),
    setTransform: jest.fn(),
    getTransform: jest.fn(),
    resetTransform: jest.fn(),
    scale: jest.fn(),
    translate: jest.fn(),
    transform: jest.fn(),
    beginPath: jest.fn(),
    closePath: jest.fn(),
    moveTo: jest.fn(),
    lineTo: jest.fn(),
    arc: jest.fn(),
    stroke: jest.fn(),
    fill: jest.fn(),
    clearRect: jest.fn(),
    fillRect: jest.fn(),
    strokeRect: jest.fn(),
    save: jest.fn(),
    restore: jest.fn(),
    fillText: jest.fn(),
    strokeText: jest.fn(),
    measureText: jest.fn().mockReturnValue({ width: 100 }),
  };
  
  // Mock getContext
  HTMLCanvasElement.prototype.getContext = jest.fn().mockImplementation(
    (contextType) => {
      if (contextType === '2d') {
        return mockCanvasRenderingContext2D;
      }
      return null;
    }
  );
  
  // Return mock and cleanup
  return {
    mockCanvasContext: mockCanvasRenderingContext2D,
    cleanup: () => {
      // Restore original method
      HTMLCanvasElement.prototype.getContext = originalGetContext;
    }
  };
}

/**
 * Sets up mocks for window.matchMedia and window.screen.
 * @returns Object containing mock instances and a cleanup function
 */
export function setupScreenMocks(matches = false) {
  // Store original methods
  const originalMatchMedia = window.matchMedia;
  const originalScreen = window.screen;
  
  // Create mock implementations
  const mockMatchMedia = jest.fn().mockImplementation(query => ({
    matches,
    media: query,
    onchange: null,
    addListener: jest.fn(),
    removeListener: jest.fn(),
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  }));
  
  // Apply mocks
  Object.defineProperty(window, 'matchMedia', {
    configurable: true,
    writable: true,
    value: mockMatchMedia,
  });
  
  // Mock screen properties
  Object.defineProperty(window, 'screen', {
    configurable: true,
    writable: true,
    value: {
      ...originalScreen,
      orientation: {
        type: 'portrait-primary',
        angle: 0,
        addEventListener: jest.fn(),
        removeEventListener: jest.fn(),
        dispatchEvent: jest.fn(),
        lock: jest.fn().mockResolvedValue(undefined),
        unlock: jest.fn(),
      },
    },
  });
  
  // Return mocks and cleanup function
  return {
    mockMatchMedia,
    cleanup: () => {
      // Restore original methods
      Object.defineProperty(window, 'matchMedia', {
        configurable: true,
        writable: true,
        value: originalMatchMedia,
      });
      
      Object.defineProperty(window, 'screen', {
        configurable: true,
        writable: true,
        value: originalScreen,
      });
    }
  };
} 