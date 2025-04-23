module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'jsdom',
  setupFiles: ['<rootDir>/polyfills.js'],
  setupFilesAfterEnv: ['<rootDir>/frontend/tests/setup.tsx'],
  globalSetup: '<rootDir>/jest.globalSetup.js',
  transform: {
    '^.+\\.(ts|tsx)$': 'ts-jest',
  },
  moduleNameMapper: {
    '\\.(css|less|scss|sass)$': 'identity-obj-proxy',
    '\\.(jpg|jpeg|png|gif|webp|svg)$': '<rootDir>/frontend/tests/__mocks__/fileMock.js'
  },
  testPathIgnorePatterns: [
    '/node_modules/',
    '/dist/',
    '/build/'
  ],
  globals: {
    'ts-jest': {
      tsconfig: '<rootDir>/frontend/tsconfig.json'
    }
  },
  moduleDirectories: ['node_modules', 'src'],
  transformIgnorePatterns: [
    'node_modules/(?!(react-router-dom)/)'
  ]
} 