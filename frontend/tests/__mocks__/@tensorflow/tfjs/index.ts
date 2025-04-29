import { jest } from '@jest/globals';

const ready = jest.fn<() => Promise<void>>().mockResolvedValue(undefined);
const setBackend = jest.fn<(backend: string) => Promise<void>>().mockResolvedValue(undefined);
const getBackend = jest.fn<() => string>().mockReturnValue('cpu');
const env = {
  set: jest.fn<(key: string, value: unknown) => void>(),
  get: jest.fn<(key: string) => unknown>()
};

const gpgpu = {
  gl: {
    getExtension: jest.fn<(extension: string) => unknown>().mockReturnValue(true)
  }
};

const backendInstance = {
  gpgpu,
  dispose: jest.fn<() => void>()
};

const backend = jest.fn<() => typeof backendInstance>().mockReturnValue(backendInstance);

export {
  ready,
  setBackend,
  getBackend,
  env,
  backend
}; 