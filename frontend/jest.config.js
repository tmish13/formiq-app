module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'jsdom',
  setupFiles: ['<rootDir>/polyfills.js'],
  setupFilesAfterEnv: ['<rootDir>/src/setupTests.ts'],
  moduleNameMapper: {
    '\\.(css|less|scss|sass)$': 'identity-obj-proxy',
    '\\.(gif|ttf|eot|svg|png|jpg|jpeg|webp)$': '<rootDir>/tests/__mocks__/fileMock.js',
    '^@/(.*)$': '<rootDir>/src/$1',
    '^@components/(.*)$': '<rootDir>/src/components/$1',
    '^@services/(.*)$': '<rootDir>/src/services/$1',
    '^@utils/(.*)$': '<rootDir>/src/utils/$1',
    '^@hooks/(.*)$': '<rootDir>/src/hooks/$1',
    '^@contexts/(.*)$': '<rootDir>/src/contexts/$1',
    '^@store/(.*)$': '<rootDir>/src/store/$1',
    '^@types/(.*)$': '<rootDir>/src/types/$1',
    '^styled-components$': '<rootDir>/tests/__mocks__/styled-components.js',
    '^react-router-dom$': '<rootDir>/tests/__mocks__/react-router-dom.tsx',
    '^ioredis$': '<rootDir>/tests/__mocks__/ioredis.ts',
    '^@theme$': '<rootDir>/tests/__mocks__/mockTheme.ts',
    '^../../mocks/server$': '<rootDir>/tests/utils/testServer.ts',
    '^../../../mocks/server$': '<rootDir>/tests/utils/testServer.ts',
    '^../formCheckService$': '<rootDir>/src/services/formAnalysisService.ts',
    '^../../services/formCheckService$': '<rootDir>/src/services/formAnalysisService.ts',
    '^@tensorflow-models/pose-detection$': '<rootDir>/tests/__mocks__/@tensorflow-models/pose-detection.ts',
    '^../Results$': '<rootDir>/src/pages/analysis/Results.tsx',
    '^../History$': '<rootDir>/src/pages/analysis/History.tsx',
    '^src/(.*)$': '<rootDir>/src/$1',
    '^tests/(.*)$': '<rootDir>/tests/$1',
    '^../index$': '<rootDir>/src/store/index.ts',
    '^../../../components/common/(.*)$': '<rootDir>/src/components/common/$1',
    '^../../../services/(.*)$': '<rootDir>/src/services/$1',
    '^../../services/(.*)$': '<rootDir>/src/services/$1',
    '^../../../store/(.*)$': '<rootDir>/src/store/$1',
    '^../../../utils/(.*)$': '<rootDir>/src/utils/$1'
  },
  moduleDirectories: ['node_modules', 'src', '<rootDir>'],
  moduleFileExtensions: ['ts', 'tsx', 'js', 'jsx', 'json', 'node'],
  transform: {
    '^.+\\.(ts|tsx)$': ['ts-jest', {
      tsconfig: '<rootDir>/tsconfig.json',
      diagnostics: {
        ignoreCodes: [151001]
      },
      isolatedModules: true
    }],
    '^.+\\.(js|jsx)$': ['babel-jest', {
      presets: ['@babel/preset-env', '@babel/preset-react'],
      plugins: [
        '@babel/plugin-transform-object-rest-spread', 
        'babel-plugin-styled-components',
        '@babel/plugin-transform-runtime'
      ]
    }]
  },
  transformIgnorePatterns: [
    '/node_modules/(?!(@formiq|react-native|@react-native|react-navigation|@react-navigation|react-router-dom|@tensorflow|@tensorflow-models)/)'
  ],
  collectCoverage: true,
  collectCoverageFrom: [
    'src/**/*.{ts,tsx,js,jsx}',
    '!src/**/*.d.ts',
    '!src/**/*.stories.{ts,tsx}',
    '!src/**/*.test.{ts,tsx}',
    '!src/**/index.{ts,tsx}',
    '!src/**/types.{ts,tsx}'
  ],
  coverageThreshold: {
    global: {
      branches: 85,
      functions: 85,
      lines: 85,
      statements: 85
    }
  },
  testMatch: [
    '<rootDir>/src/**/*.{spec,test}.{ts,tsx}',
    '<rootDir>/src/**/__tests__/**/*.{ts,tsx}'
  ],
  testPathIgnorePatterns: [
    '/node_modules/',
    '/dist/',
    '/coverage/',
    '/.next/',
    '/build/'
  ],
  verbose: true,
  testTimeout: 10000,
  maxWorkers: '50%'
}; 