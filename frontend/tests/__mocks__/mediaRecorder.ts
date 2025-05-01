// Define mock MediaRecorder class
class MockMediaRecorder {
  stream: MediaStream;
  state: string;
  ondataavailable: ((e: any) => void) | null;
  onstop: (() => void) | null;

  constructor(stream: MediaStream) {
    this.stream = stream;
    this.state = 'inactive';
    this.ondataavailable = null;
    this.onstop = null;
  }

  start() {
    this.state = 'recording';
    if (this.ondataavailable) {
      this.ondataavailable({ data: new Blob(['test'], { type: 'video/mp4' }) });
    }
  }

  stop() {
    this.state = 'inactive';
    if (this.onstop) this.onstop();
  }

  // Add the required static method
  static isTypeSupported(type: string): boolean {
    return type.includes('video');
  }
}

// Export the mock class
export default MockMediaRecorder; 