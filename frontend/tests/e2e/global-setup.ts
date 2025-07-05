/**
 * Playwright Global Setup for FormIQ E2E Tests
 * 
 * Handles authentication, test data preparation, and environment setup
 * for end-to-end testing scenarios.
 */

import { chromium, FullConfig } from '@playwright/test';
import fs from 'fs';
import path from 'path';

async function globalSetup(config: FullConfig) {
  console.log('🚀 Starting FormIQ E2E Test Global Setup...');
  
  const { baseURL } = config.projects[0].use;
  const authFile = path.join(__dirname, '../fixtures/auth.json');
  
  try {
    // Create test fixtures directory
    const fixturesDir = path.join(__dirname, '../fixtures');
    if (!fs.existsSync(fixturesDir)) {
      fs.mkdirSync(fixturesDir, { recursive: true });
    }
    
    // Setup authentication if needed
    if (process.env.E2E_ENABLE_AUTH !== 'false') {
      await setupAuthentication(baseURL!, authFile);
    }
    
    // Setup test data
    await setupTestData();
    
    // Verify application health
    await verifyApplicationHealth(baseURL!);
    
    console.log('✅ FormIQ E2E Test Global Setup completed successfully');
  } catch (error) {
    console.error('❌ FormIQ E2E Test Global Setup failed:', error);
    throw error;
  }
}

/**
 * Setup authentication for E2E tests
 */
async function setupAuthentication(baseURL: string, authFile: string) {
  console.log('🔐 Setting up authentication...');
  
  const browser = await chromium.launch();
  const page = await browser.newPage();
  
  try {
    // Navigate to login page
    await page.goto(`${baseURL}/auth/login`);
    
    // Fill login form
    const testEmail = process.env.E2E_TEST_EMAIL || 'test@formiq.com';
    const testPassword = process.env.E2E_TEST_PASSWORD || 'TestPassword123!';
    
    await page.fill('[data-testid="email-input"]', testEmail);
    await page.fill('[data-testid="password-input"]', testPassword);
    
    // Submit login form
    await page.click('[data-testid="login-button"]');
    
    // Wait for successful login (redirect to dashboard)
    await page.waitForURL(`${baseURL}/dashboard`, { timeout: 10000 });
    
    // Save authentication state
    await page.context().storageState({ path: authFile });
    
    console.log('✅ Authentication setup completed');
  } catch (error) {
    console.warn('⚠️ Authentication setup failed, tests will run without auth:', error);
    
    // Create empty auth file for tests that don't require auth
    fs.writeFileSync(authFile, JSON.stringify({
      cookies: [],
      origins: []
    }));
  } finally {
    await browser.close();
  }
}

/**
 * Setup test data and fixtures
 */
async function setupTestData() {
  console.log('📄 Setting up test data...');
  
  const fixturesDir = path.join(__dirname, '../fixtures');
  
  // Create sample video file for upload tests
  const sampleVideoPath = path.join(fixturesDir, 'sample-video.mp4');
  if (!fs.existsSync(sampleVideoPath)) {
    // Create a minimal MP4 file for testing
    const minimalMp4Buffer = Buffer.from([
      0x00, 0x00, 0x00, 0x20, 0x66, 0x74, 0x79, 0x70, // ftyp box header
      0x6D, 0x70, 0x34, 0x31, 0x00, 0x00, 0x00, 0x00, // mp41 brand
      0x6D, 0x70, 0x34, 0x31, 0x69, 0x73, 0x6F, 0x6D, // compatible brands
      0x00, 0x00, 0x00, 0x08, 0x66, 0x72, 0x65, 0x65, // free box
    ]);
    
    fs.writeFileSync(sampleVideoPath, minimalMp4Buffer);
  }
  
  // Create test user profiles
  const testProfiles = {
    testUser: {
      id: 'test-user-1',
      email: 'test@formiq.com',
      firstName: 'Test',
      lastName: 'User',
      subscription: 'premium',
    },
    basicUser: {
      id: 'basic-user-1',
      email: 'basic@formiq.com',
      firstName: 'Basic',
      lastName: 'User',
      subscription: 'basic',
    },
  };
  
  fs.writeFileSync(
    path.join(fixturesDir, 'test-profiles.json'),
    JSON.stringify(testProfiles, null, 2)
  );
  
  // Create mock analysis results
  const mockAnalysisResults = {
    squat: {
      analysisId: 'mock-squat-analysis-1',
      exercise: 'squat',
      scores: {
        posture: 85,
        stability: 78,
        depth: 92,
        overall: 85,
      },
      feedback: {
        summary: 'Good squat form overall. Focus on knee tracking.',
        improvements: [
          'Keep knees aligned with toes',
          'Maintain neutral spine',
          'Control the descent speed',
        ],
      },
      timestamp: new Date().toISOString(),
    },
    deadlift: {
      analysisId: 'mock-deadlift-analysis-1',
      exercise: 'deadlift',
      scores: {
        posture: 78,
        stability: 85,
        depth: 88,
        overall: 84,
      },
      feedback: {
        summary: 'Strong deadlift technique. Watch bar path.',
        improvements: [
          'Keep bar closer to body',
          'Engage lats throughout lift',
          'Full hip extension at top',
        ],
      },
      timestamp: new Date().toISOString(),
    },
  };
  
  fs.writeFileSync(
    path.join(fixturesDir, 'mock-analysis-results.json'),
    JSON.stringify(mockAnalysisResults, null, 2)
  );
  
  console.log('✅ Test data setup completed');
}

/**
 * Verify application health before running tests
 */
async function verifyApplicationHealth(baseURL: string) {
  console.log('🏥 Verifying application health...');
  
  const browser = await chromium.launch();
  const page = await browser.newPage();
  
  try {
    // Check if app loads
    await page.goto(baseURL, { timeout: 30000 });
    
    // Wait for React app to be ready
    await page.waitForSelector('[data-testid="app-root"]', { timeout: 15000 });
    
    // Check for any JavaScript errors
    const jsErrors: string[] = [];
    page.on('pageerror', (error) => {
      jsErrors.push(error.message);
    });
    
    // Navigate through key pages to verify they load
    const pagesToCheck = [
      '/',
      '/dashboard',
      '/form-analysis',
      '/progress',
    ];
    
    for (const pagePath of pagesToCheck) {
      try {
        await page.goto(`${baseURL}${pagePath}`, { timeout: 10000 });
        await page.waitForLoadState('networkidle', { timeout: 5000 });
      } catch (error) {
        console.warn(`⚠️ Warning: Page ${pagePath} may not be fully functional:`, error);
      }
    }
    
    if (jsErrors.length > 0) {
      console.warn('⚠️ JavaScript errors detected:', jsErrors);
    }
    
    console.log('✅ Application health verification completed');
  } catch (error) {
    console.error('❌ Application health check failed:', error);
    throw new Error(`Application is not ready for testing: ${error}`);
  } finally {
    await browser.close();
  }
}

export default globalSetup;