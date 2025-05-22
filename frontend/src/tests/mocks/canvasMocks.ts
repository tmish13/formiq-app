// Helper to setup canvas context mock
export const setupCanvasMock = () => {
  const mockCanvasContext = {
    clearRect: jest.fn(),
    beginPath: jest.fn(),
    arc: jest.fn(),
    fill: jest.fn(),
    stroke: jest.fn(),
    moveTo: jest.fn(),
    lineTo: jest.fn(),
    fillText: jest.fn(),
    strokeStyle: '',
    fillStyle: '',
    lineWidth: 0,
    font: '',
    textAlign: ''
  };

  const mockGetContext = jest.fn().mockReturnValue(mockCanvasContext);
  const originalGetContext = HTMLCanvasElement.prototype.getContext;

  // Mock the getContext method
  HTMLCanvasElement.prototype.getContext = mockGetContext;

  return {
    mockCanvasContext,
    mockGetContext,
    cleanup: () => {
      HTMLCanvasElement.prototype.getContext = originalGetContext;
    }
  };
};

// Helper to create a mock file
export const createMockFile = (
  name: string = 'test.mp4', 
  type: string = 'video/mp4', 
  size: number = 1024 * 1024
): File => {
  const blob = new Blob(['mock file content'], { type });
  return new File([blob], name, { type });
}; 