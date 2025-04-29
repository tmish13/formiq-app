export default {
  preset: 'ts-jest/presets/default-esm',
  testEnvironment: 'jsdom',
  setupFiles: ['<rootDir>/polyfills.js'],
  setupFilesAfterEnv: ['<rootDir>/frontend/src/setupTests.ts'],
  globalSetup: '<rootDir>/jest.globalSetup.js',
  transform: {
    '^.+\\.tsx?$': ['ts-jest', { 
      useESM: true,
      tsconfig: 'frontend/tsconfig.json'
    }]
  },
  moduleNameMapper: {
    '\\.(css|less|scss|sass)$': 'identity-obj-proxy',
    '\\.(jpg|jpeg|png|gif|webp|svg)$': '<rootDir>/frontend/tests/__mocks__/fileMock.js',
    '^@/(.*)$': '<rootDir>/frontend/src/$1',
    '^@capacitor/(.*)$': '<rootDir>/frontend/tests/__mocks__/@capacitor/$1',
    '^@tensorflow/tfjs$': '<rootDir>/frontend/tests/__mocks__/@tensorflow/tfjs/index.ts',
    '^@tensorflow/tfjs-backend-(.*)$': '<rootDir>/frontend/tests/__mocks__/@tensorflow/tfjs/backend.ts',
    '^@tensorflow/tfjs-converter$': '<rootDir>/frontend/tests/__mocks__/@tensorflow/tfjs/converter.ts',
    '^@tensorflow-models/(.*)$': '<rootDir>/frontend/tests/__mocks__/@tensorflow-models/$1',
    '^ioredis$': '<rootDir>/frontend/tests/__mocks__/ioredis.ts',
    '^@jest/globals$': '<rootDir>/node_modules/@jest/globals/build/index.js',
    '^(\\.{1,2}/.*)\\.js$': '$1',
    '^styled-components$': '<rootDir>/node_modules/styled-components',
    '^@mui/material$': '<rootDir>/frontend/tests/__mocks__/@mui/material.tsx'
  },
  testPathIgnorePatterns: [
    '/node_modules/',
    '/dist/',
    '/build/'
  ],
  globals: {
    'ts-jest': {
      tsconfig: 'frontend/tsconfig.json',
      useESM: true,
      isolatedModules: true
    }
  },
  moduleDirectories: ['node_modules', 'frontend/src'],
  transformIgnorePatterns: [
    'node_modules/(?!(@capacitor|react-router-dom|@jest|styled-components)/)'
  ],
  testMatch: [
    '<rootDir>/frontend/src/**/*.{spec,test}.{ts,tsx}',
    '<rootDir>/frontend/src/**/__tests__/**/*.{ts,tsx}'
  ],
  extensionsToTreatAsEsm: ['.ts', '.tsx'],
  testTimeout: 30000
} 