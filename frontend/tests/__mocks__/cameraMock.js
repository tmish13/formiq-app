// Mock for browser's camera API
const mockGetUserMedia = jest.fn().mockImplementation((constraints) => {
  return Promise.resolve({
    getTracks: () => [
      {
        stop: jest.fn(),
        addEventListener: jest.fn(),
        removeEventListener: jest.fn(),
      },
    ],
  });
});

// Mock for MediaRecorder
class MockMediaRecorder {
  constructor(stream, options) {
    this.stream = stream;
    this.options = options;
    this.state = 'inactive';
    this.ondataavailable = null;
    this.onstop = null;
    this.onstart = null;
    this.onerror = null;
  }

  start(timeslice) {
    this.state = 'recording';
    if (this.onstart) this.onstart();
    
    // Simulate data available events
    if (this.ondataavailable) {
      const mockBlob = new Blob(['mock-video-data'], { type: 'video/webm' });
      this.ondataavailable({ data: mockBlob });
    }
  }

  stop() {
    this.state = 'inactive';
    if (this.onstop) this.onstop();
  }

  requestData() {
    if (this.ondataavailable) {
      const mockBlob = new Blob(['mock-video-data'], { type: 'video/webm' });
      this.ondataavailable({ data: mockBlob });
    }
  }
}

// Add mocks to global object
Object.defineProperty(global.navigator, 'mediaDevices', {
  value: {
    getUserMedia: mockGetUserMedia,
  },
  writable: true,
});

Object.defineProperty(global, 'MediaRecorder', {
  value: MockMediaRecorder,
  writable: true,
});

module.exports = {
  mockGetUserMedia,
  MockMediaRecorder,
}; 