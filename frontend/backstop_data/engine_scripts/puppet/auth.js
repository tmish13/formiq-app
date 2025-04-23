/**
 * Authentication script for BackstopJS
 * This script will handle authenticating for routes that require login
 */

module.exports = async (page, scenario) => {
  console.log('SCENARIO > ' + scenario.label);
  
  const requiresAuth = [
    '/dashboard',
    '/profile',
    '/form-analysis',
    '/exercises/favorites',
    '/settings'
  ];
  
  // Check if the current scenario URL requires authentication
  const needsAuth = requiresAuth.some(route => scenario.url.includes(route));
  
  if (needsAuth) {
    console.log('AUTH > This scenario requires authentication');
    
    // Navigate to the login page
    await page.goto('http://localhost:3000/login');
    
    // Wait for the login form to be visible
    await page.waitForSelector('.login-form, form[action*="login"]', { visible: true, timeout: 5000 });
    
    // Fill in credentials
    await page.type('input[name="email"], input[type="email"]', 'test@example.com');
    await page.type('input[name="password"], input[type="password"]', 'password123');
    
    // Click login button
    await page.click('button[type="submit"], button:contains("Login"), input[type="submit"]');
    
    // Wait for redirect or dashboard to load
    await page.waitForNavigation({ waitUntil: 'networkidle0' });
    
    console.log('AUTH > Successfully logged in');
    
    // Now navigate to the actual scenario URL
    await page.goto(scenario.url);
    
    // Extra wait to ensure page is fully loaded
    await page.waitForTimeout(1000);
  }
  
  // Additional common setup for all scenarios
  await page.setViewport({
    width: scenario.viewport.width,
    height: scenario.viewport.height
  });
  
  // Handle cookies banner if present (common in many sites)
  try {
    const cookieBanner = await page.$('[data-testid="cookie-banner"], .cookie-banner, .cookies-notice');
    if (cookieBanner) {
      const acceptButton = await page.$('[data-testid="accept-cookies"], .accept-cookies, button:contains("Accept")');
      if (acceptButton) {
        await acceptButton.click();
        await page.waitForTimeout(500); // Wait for banner animation
      }
    }
  } catch (e) {
    console.log('No cookie banner found or error handling it');
  }
  
  // Hide any notification or toast messages that could be transient
  await page.evaluate(() => {
    const notifications = document.querySelectorAll('.notification, .toast, .alert, .snackbar');
    notifications.forEach(notification => {
      notification.style.display = 'none';
    });
  });
  
  // Wait for specified delay
  if (scenario.delay) {
    await page.waitForTimeout(scenario.delay);
  }
}; 