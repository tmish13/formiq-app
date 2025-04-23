const baseUrl = 'http://localhost:3000';

/**
 * BackstopJS configuration for visual regression testing
 * Captures key user flows and responsive layouts for testing
 */
module.exports = {
  id: 'formiq_visual_regression',
  viewports: [
    {
      name: 'phone',
      width: 375,
      height: 667
    },
    {
      name: 'tablet',
      width: 768,
      height: 1024
    },
    {
      name: 'desktop',
      width: 1280,
      height: 800
    }
  ],
  onBeforeScript: 'puppet/onBefore.js',
  onReadyScript: 'puppet/onReady.js',
  scenarios: [
    {
      label: 'Login Page',
      url: `${baseUrl}/login`,
      delay: 500,
      hideSelectors: ['.timestamp', '[data-variable]'],
      removeSelectors: ['.cookie-banner'],
      selectors: ['body'],
      readyEvent: null,
      readySelector: '#login-form',
      misMatchThreshold: 0.2
    },
    {
      label: 'Register Page',
      url: `${baseUrl}/register`,
      delay: 500,
      hideSelectors: ['.timestamp', '[data-variable]'],
      selectors: ['body'],
      readyEvent: null,
      readySelector: '#register-form',
      misMatchThreshold: 0.2
    },
    {
      label: 'Dashboard',
      url: `${baseUrl}/dashboard`,
      cookiePath: 'backstop_data/engine_scripts/cookies.json',
      delay: 500,
      hideSelectors: ['.timestamp', '[data-variable]', '.user-specific-data'],
      selectors: ['body'],
      readyEvent: null,
      readySelector: '.dashboard-container',
      misMatchThreshold: 0.2
    },
    {
      label: 'Form Check Upload',
      url: `${baseUrl}/workout/form-check/upload`,
      cookiePath: 'backstop_data/engine_scripts/cookies.json',
      delay: 500,
      hideSelectors: ['.timestamp', '[data-variable]', '.camera-feed'],
      selectors: ['body'],
      readyEvent: null,
      readySelector: '.upload-container',
      misMatchThreshold: 0.2
    },
    {
      label: 'Form Analysis',
      url: `${baseUrl}/form-analysis`,
      cookiePath: 'backstop_data/engine_scripts/cookies.json',
      delay: 500,
      hideSelectors: ['.timestamp', '[data-variable]', '.analysis-result-data'],
      selectors: ['body'],
      readyEvent: null,
      readySelector: '.analysis-container',
      misMatchThreshold: 0.2
    },
    {
      label: 'Progress Tracking',
      url: `${baseUrl}/progress`,
      cookiePath: 'backstop_data/engine_scripts/cookies.json',
      delay: 500,
      hideSelectors: ['.timestamp', '[data-variable]', '.chart-data'],
      selectors: ['body'],
      readyEvent: null,
      readySelector: '.progress-container',
      misMatchThreshold: 0.2
    },
    {
      label: 'User Profile',
      url: `${baseUrl}/profile`,
      cookiePath: 'backstop_data/engine_scripts/cookies.json',
      delay: 500,
      hideSelectors: ['.timestamp', '[data-variable]', '.user-specific-data'],
      selectors: ['body'],
      readyEvent: null,
      readySelector: '.profile-container',
      misMatchThreshold: 0.2
    }
  ],
  paths: {
    bitmaps_reference: 'backstop_data/bitmaps_reference',
    bitmaps_test: 'backstop_data/bitmaps_test',
    engine_scripts: 'backstop_data/engine_scripts',
    html_report: 'backstop_data/html_report',
    ci_report: 'backstop_data/ci_report'
  },
  report: ['browser'],
  engine: 'puppeteer',
  engineOptions: {
    args: ['--no-sandbox']
  },
  asyncCaptureLimit: 5,
  asyncCompareLimit: 50,
  debug: false,
  debugWindow: false
}; 