/**
 * Utility file for mocking HTML Canvas and its rendering context in tests
 */

/**
 * Creates a mock canvas context with all required methods and properties
 */
export function createMockCanvasContext() {
  const mockContext = {
    clearRect: jest.fn(),
    beginPath: jest.fn(),
    arc: jest.fn(),
    fill: jest.fn(),
    moveTo: jest.fn(),
    lineTo: jest.fn(),
    stroke: jest.fn(),
    strokeStyle: '',
    fillStyle: '',
    lineWidth: 1,
    canvas: {
      width: 640,
      height: 360,
    },
    save: jest.fn(),
    restore: jest.fn(),
    translate: jest.fn(),
    rotate: jest.fn(),
    scale: jest.fn(),
    setLineDash: jest.fn(),
    font: '',
    textAlign: 'center',
    textBaseline: 'middle',
    fillText: jest.fn(),
    strokeText: jest.fn(),
    createLinearGradient: jest.fn().mockReturnValue({
      addColorStop: jest.fn()
    }),
    measureText: jest.fn().mockReturnValue({ width: 50 })
  };

  return mockContext;
}

/**
 * Sets up a mock for canvas context
 * Instead of mocking the prototype, this returns a mock element that
 * you can use in your tests directly
 */
export function setupCanvasMock() {
  const mockContext = createMockCanvasContext();
  
  // Create a mock canvas element with a mocked getContext method
  const mockCanvas = {
    getContext: jest.fn().mockReturnValue(mockContext),
    width: 640,
    height: 360
  };
  
  return { mockCanvas, mockContext };
}

/**
 * Alternative method: Mock HTMLCanvasElement for all tests
 * Use this in a beforeAll/beforeEach block
 * This approach works but may cause type issues in TypeScript
 */
export function mockCanvasGlobally() {
  const mockContext = createMockCanvasContext();
  
  // Use any to bypass type checking for the mock
  HTMLCanvasElement.prototype.getContext = jest.fn(() => mockContext) as any;
  
  return mockContext;
}

/**
 * Cleans up canvas mocks after tests
 * Call this in afterAll or afterEach if you used mockCanvasGlobally
 */
export function cleanupCanvasMock() {
  jest.restoreAllMocks();
} 