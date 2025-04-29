export const mockStorageService = {
  get: jest.fn().mockImplementation((key: string) => Promise.resolve(null)),
  set: jest.fn().mockImplementation((key: string, value: any) => Promise.resolve()),
  remove: jest.fn().mockImplementation((key: string) => Promise.resolve()),
  clear: jest.fn().mockImplementation(() => Promise.resolve()),
};

export default mockStorageService; 