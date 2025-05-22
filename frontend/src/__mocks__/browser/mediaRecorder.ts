/**
 * Mock implementation of MediaRecorder for tests
 */
import { jest } from '@jest/globals';

export class MockMediaRecorder {
  static isTypeSupported = jest.fn().mockReturnValue(true);
  
  // Event handlers
  ondataavailable: ((event: any) => void) | null = null;
  onstop: ((event: any) => void) | null = null;
  
  // State
  state: string = 'inactive';
  
  // Mock functions
  start = jest.fn().mockImplementation(() => {
    this.state = 'recording';
    
    // Simulate data event after a small delay
    setTimeout(() => {
      if (this.ondataavailable) {
        const mockBlob = new Blob(['test data'], { type: 'video/webm' });
        this.ondataavailable({ data: mockBlob });
      }
    }, 100);
  });
  
  stop = jest.fn().mockImplementation(() => {
    this.state = 'inactive';
    
    // Trigger stop event
    if (this.onstop) {
      this.onstop({});
    }
  });
}

// Mock for createObjectURL in test environment
export const mockCreateObjectURL = jest.fn().mockReturnValue('test-video.mp4');

export default MockMediaRecorder; 