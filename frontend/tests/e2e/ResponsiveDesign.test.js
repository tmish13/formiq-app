const { devices } = require('puppeteer');
const path = require('path');
const { configureToMatchImageSnapshot } = require('jest-image-snapshot');

// Configure image snapshot testing
const toMatchImageSnapshot = configureToMatchImageSnapshot({
  failureThreshold: 0.02, // 2% threshold to allow minor rendering differences across devices
  failureThresholdType: 'percent',
  customSnapshotsDir: path.join(__dirname, 'snapshots'),
  customDiffDir: path.join(__dirname, 'diffs'),
});

expect.extend({ toMatchImageSnapshot });

// Define devices to test
const deviceViewports = [
  {
    name: 'iPhone X',
    device: devices['iPhone X'],
    width: 375,
    height: 812,
  },
  {
    name: 'iPad Pro',
    device: devices['iPad Pro'],
    width: 1024,
    height: 1366,
  },
  {
    name: 'Desktop',
    width: 1920,
    height: 1080,
  },
];

// Test pages
const pages = [
  {
    name: 'Home Page',
    path: '/',
    selectors: ['.header', '.hero-section', '.features-grid', '.footer'],
  },
  {
    name: 'Exercise Form Analysis',
    path: '/form-analysis',
    selectors: ['.form-upload-container', '.exercise-selector', '.camera-container'],
  },
  {
    name: 'Results Dashboard',
    path: '/dashboard',
    selectors: ['.summary-cards', '.progress-chart', '.recent-workouts'],
  },
];

describe('Responsive Design Tests', () => {
  beforeAll(async () => {
    // Set up base URL for tests
    global.BASE_URL = process.env.TEST_URL || 'http://localhost:3000';
  });

  // Test each page on each device
  deviceViewports.forEach(device => {
    describe(`${device.name} viewport tests`, () => {
      beforeAll(async () => {
        // Set browser viewport to match device
        await page.setViewport({
          width: device.width,
          height: device.height,
          deviceScaleFactor: device.device ? device.device.deviceScaleFactor : 1,
          isMobile: device.device ? device.device.isMobile : false,
          hasTouch: device.device ? device.device.hasTouch : false,
        });

        // Emulate device if specified
        if (device.device) {
          await page.emulate(device.device);
        }
      });

      pages.forEach(testPage => {
        describe(`${testPage.name}`, () => {
          beforeAll(async () => {
            // Navigate to page and wait for full load
            await page.goto(`${global.BASE_URL}${testPage.path}`, {
              waitUntil: 'networkidle2',
            });
            
            // Wait an additional time for any animations to complete
            await page.waitForTimeout(1000);
          });

          it('should render the page correctly', async () => {
            // Take a full page screenshot
            const screenshot = await page.screenshot({ fullPage: true });
            
            // Compare with stored snapshot
            expect(screenshot).toMatchImageSnapshot({
              customSnapshotIdentifier: `${device.name.replace(/\s+/g, '-').toLowerCase()}-${testPage.name.replace(/\s+/g, '-').toLowerCase()}`,
            });
          });

          // Test specific components if selectors are provided
          if (testPage.selectors && testPage.selectors.length) {
            it('should render critical components correctly', async () => {
              for (const selector of testPage.selectors) {
                try {
                  // Wait for element to be visible
                  await page.waitForSelector(selector, { visible: true, timeout: 5000 });
                  
                  // Take a screenshot of the specific element
                  const element = await page.$(selector);
                  if (element) {
                    const elementScreenshot = await element.screenshot();
                    
                    // Compare with stored snapshot
                    expect(elementScreenshot).toMatchImageSnapshot({
                      customSnapshotIdentifier: `${device.name.replace(/\s+/g, '-').toLowerCase()}-${testPage.name.replace(/\s+/g, '-').toLowerCase()}-${selector.replace(/[^a-zA-Z0-9]/g, '-')}`,
                    });
                  }
                } catch (error) {
                  // Log error but continue with other selectors
                  console.error(`Error capturing ${selector} on ${testPage.name} for ${device.name}:`, error);
                }
              }
            });
          }

          // Test responsive behavior
          it('should adjust layout for viewport size', async () => {
            // Test menu/navigation behavior
            if (device.width < 768) { // Mobile breakpoint
              // Check if hamburger menu exists
              const hamburgerExists = await page.$('.hamburger-menu, .mobile-menu-toggle, [data-testid="mobile-menu-button"]');
              if (hamburgerExists) {
                // Open mobile menu
                await hamburgerExists.click();
                await page.waitForTimeout(500); // Wait for animation
                
                // Take screenshot of open menu
                const mobileMenuScreenshot = await page.screenshot();
                expect(mobileMenuScreenshot).toMatchImageSnapshot({
                  customSnapshotIdentifier: `${device.name.replace(/\s+/g, '-').toLowerCase()}-${testPage.name.replace(/\s+/g, '-').toLowerCase()}-mobile-menu-open`,
                });
              }
            } else {
              // For larger screens, check that desktop navigation is visible
              const navExists = await page.$('nav, .desktop-navigation, .main-navigation');
              expect(navExists).not.toBeNull();
            }
          });

          // Test for content overflow issues
          it('should not have horizontal overflow', async () => {
            // Measure the page width
            const pageWidth = await page.evaluate(() => {
              return document.documentElement.scrollWidth;
            });
            
            // Check if page width exceeds viewport width
            expect(pageWidth).toBeLessThanOrEqual(device.width);
          });
        });
      });
    });
  });

  // Test interactive elements across devices
  describe('Interactive Element Tests', () => {
    it('should handle touch/click interactions on all devices', async () => {
      for (const device of deviceViewports) {
        // Set viewport for current device
        await page.setViewport({
          width: device.width,
          height: device.height,
          deviceScaleFactor: device.device ? device.device.deviceScaleFactor : 1,
          isMobile: device.device ? device.device.isMobile : false,
          hasTouch: device.device ? device.device.hasTouch : false,
        });

        // Navigate to exercise form page
        await page.goto(`${global.BASE_URL}/form-analysis`, {
          waitUntil: 'networkidle2',
        });

        // Test interactive elements, like buttons
        const captureButtonSelector = '.capture-button, [data-testid="capture-button"]';
        await page.waitForSelector(captureButtonSelector, { visible: true, timeout: 5000 });
        
        // Take before screenshot
        const beforeInteraction = await page.screenshot();
        
        // Click the button
        await page.click(captureButtonSelector);
        await page.waitForTimeout(1000); // Wait for interaction effects
        
        // Take after screenshot
        const afterInteraction = await page.screenshot();
        
        // Verify visual difference after interaction
        expect(afterInteraction).not.toMatchImage(beforeInteraction);
      }
    });
  });
}); 