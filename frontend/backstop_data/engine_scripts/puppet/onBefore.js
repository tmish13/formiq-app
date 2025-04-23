/**
 * onBefore script for BackstopJS
 * This script will be executed before the page is opened
 */

module.exports = async (page, scenario) => {
  console.log('SCENARIO SETUP > ' + scenario.label);

  // Set a custom user agent to identify test runs
  await page.setUserAgent('BackstopJS Visual Testing');

  // Set device scale factor based on viewport
  let deviceScaleFactor = 1;
  if (scenario.viewport.width <= 414) {
    deviceScaleFactor = 2; // For mobile devices
  } else if (scenario.viewport.width <= 1024) {
    deviceScaleFactor = 1.5; // For tablets
  }

  // Configure viewport for the test
  await page.setViewport({
    width: scenario.viewport.width,
    height: scenario.viewport.height,
    deviceScaleFactor,
    isMobile: scenario.viewport.width < 768,
    hasTouch: scenario.viewport.width < 1024
  });

  // Override CSS media queries
  if (scenario.emulateMedia) {
    await page.emulateMediaFeatures([
      { name: 'prefers-color-scheme', value: scenario.emulateMedia }
    ]);
  }

  // Set default navigation timeout
  await page.setDefaultNavigationTimeout(60000);
  
  // Set default request timeout
  await page.setDefaultTimeout(30000);

  // Block analytics to prevent unnecessary traffic during testing
  if (scenario.blockRequests !== false) {
    await page.setRequestInterception(true);
    
    page.on('request', request => {
      // List of services to block during visual testing
      const blockedDomains = [
        'www.google-analytics.com',
        'analytics.google.com',
        'googletagmanager.com',
        'hotjar.com',
        'analytics.twitter.com',
        'facebook.net',
        'connect.facebook.net',
        'static.ads-twitter.com',
        'bat.bing.com',
        'stats.g.doubleclick.net',
        'analytics.tiktok.com',
      ];
      
      const url = request.url();
      const shouldBlock = blockedDomains.some(domain => url.includes(domain));
      
      if (shouldBlock) {
        request.abort();
      } else {
        request.continue();
      }
    });
  }

  // Define custom headers if needed
  if (scenario.headers) {
    await page.setExtraHTTPHeaders(scenario.headers);
  }

  // Set cookies if specified
  if (scenario.cookies && scenario.cookies.length > 0) {
    for (const cookie of scenario.cookies) {
      await page.setCookie(cookie);
    }
  }

  // Setup localStorage for test if specified
  if (scenario.localStorage) {
    const localStorageData = scenario.localStorage;
    
    await page.evaluateOnNewDocument((data) => {
      for (const [key, value] of Object.entries(data)) {
        window.localStorage.setItem(key, value);
      }
    }, localStorageData);
  }

  // Set a common cookie for all tests to prevent cookie banners
  await page.setCookie({
    name: 'cookieConsent',
    value: 'accepted',
    domain: new URL(scenario.url).hostname,
    path: '/',
    expires: Date.now() / 1000 + 24 * 60 * 60, // Expires in 1 day
  });

  // Inject custom CSS to disable animations for better visual testing
  if (scenario.disableAnimations !== false) {
    await page.evaluateOnNewDocument(() => {
      const disableAnimationsStyle = document.createElement('style');
      disableAnimationsStyle.type = 'text/css';
      disableAnimationsStyle.innerHTML = `
        *, *::before, *::after {
          animation-duration: 0s !important;
          transition-duration: 0s !important;
          animation-delay: 0s !important;
          transition-delay: 0s !important;
          animation-iteration-count: 1 !important;
        }
      `;
      
      document.head.appendChild(disableAnimationsStyle);
    });
  }

  console.log('SCENARIO SETUP COMPLETE > ' + scenario.label);
}; 