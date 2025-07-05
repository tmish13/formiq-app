/**
 * Playwright E2E Test Configuration for FormIQ
 * 
 * Comprehensive end-to-end testing configuration supporting:
 * - Cross-platform testing (desktop, mobile, tablet)
 * - Performance monitoring
 * - Visual regression testing
 * - Real user journey automation
 */

import { defineConfig, devices } from '@playwright/test';
import path from 'path';

// Environment configuration
const baseURL = process.env.E2E_BASE_URL || 'http://localhost:3000';
const isCI = !!process.env.CI;
const headless = process.env.E2E_HEADLESS !== 'false';

export default defineConfig({
  testDir: './tests/e2e',
  
  // Global test settings
  fullyParallel: true,
  forbidOnly: isCI,
  retries: isCI ? 2 : 0,
  workers: isCI ? 1 : undefined,
  
  // Test timeout settings
  timeout: 60000, // 1 minute per test
  expect: {
    timeout: 10000, // 10 seconds for assertions
  },
  
  // Reporter configuration
  reporter: [
    ['html', { outputFolder: 'test-results/e2e-report' }],
    ['json', { outputFile: 'test-results/e2e-results.json' }],
    ['junit', { outputFile: 'test-results/e2e-junit.xml' }],
    ...(isCI ? [['github']] : [['list']]),
  ],
  
  // Global test configuration
  use: {
    baseURL,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    
    // Browser context settings
    viewport: { width: 1280, height: 720 },
    ignoreHTTPSErrors: true,
    
    // Performance monitoring
    extraHTTPHeaders: {
      'Accept-Language': 'en-US,en;q=0.9',
    },
  },
  
  // Test output directories
  outputDir: 'test-results/e2e-artifacts',
  
  // Global setup and teardown
  globalSetup: path.join(__dirname, 'global-setup.ts'),
  globalTeardown: path.join(__dirname, 'global-teardown.ts'),
  
  // Project configurations for different platforms and browsers
  projects: [
    // Desktop browsers
    {
      name: 'chromium-desktop',
      use: { 
        ...devices['Desktop Chrome'],
        viewport: { width: 1920, height: 1080 },
      },
      testMatch: /.*\.(test|spec)\.ts/,
    },
    {
      name: 'firefox-desktop',
      use: { 
        ...devices['Desktop Firefox'],
        viewport: { width: 1920, height: 1080 },
      },
      testMatch: /.*\.(test|spec)\.ts/,
    },
    {
      name: 'webkit-desktop',
      use: { 
        ...devices['Desktop Safari'],
        viewport: { width: 1920, height: 1080 },
      },
      testMatch: /.*\.(test|spec)\.ts/,
    },
    
    // Mobile devices
    {
      name: 'mobile-chrome',
      use: { 
        ...devices['Pixel 5'],
      },
      testMatch: /.*mobile.*\.(test|spec)\.ts/,
    },
    {
      name: 'mobile-safari',
      use: { 
        ...devices['iPhone 13'],
      },
      testMatch: /.*mobile.*\.(test|spec)\.ts/,
    },
    
    // Tablet devices
    {
      name: 'tablet-chrome',
      use: { 
        ...devices['Galaxy Tab S4'],
      },
      testMatch: /.*tablet.*\.(test|spec)\.ts/,
    },
    {
      name: 'tablet-safari',
      use: { 
        ...devices['iPad Pro'],
      },
      testMatch: /.*tablet.*\.(test|spec)\.ts/,
    },
    
    // Performance testing project
    {
      name: 'performance',
      use: { 
        ...devices['Desktop Chrome'],
        viewport: { width: 1920, height: 1080 },
      },
      testMatch: /.*performance.*\.(test|spec)\.ts/,
      timeout: 120000, // 2 minutes for performance tests
    },
    
    // Visual regression testing
    {
      name: 'visual-regression',
      use: { 
        ...devices['Desktop Chrome'],
        viewport: { width: 1280, height: 720 },
      },
      testMatch: /.*visual.*\.(test|spec)\.ts/,
    },
  ],
  
  // Web server configuration for local testing
  webServer: process.env.E2E_SKIP_SERVER ? undefined : {
    command: 'npm start',
    url: baseURL,
    timeout: 120000,
    reuseExistingServer: !isCI,
    cwd: path.join(__dirname, '../..'),
  },
});