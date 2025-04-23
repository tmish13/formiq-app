/**
 * onReady script for BackstopJS
 * This script will be executed when the page has loaded
 */

module.exports = async (page, scenario) => {
  console.log('SCENARIO READY > ' + scenario.label);
  
  // Wait for specified selectors to be ready
  if (scenario.readySelector) {
    await page.waitForSelector(scenario.readySelector, { visible: true, timeout: 10000 });
  }
  
  // Perform specified interactions if any are defined
  if (scenario.clickSelectors && scenario.clickSelectors.length > 0) {
    for (const selector of scenario.clickSelectors) {
      try {
        await page.waitForSelector(selector, { visible: true, timeout: 5000 });
        await page.click(selector);
        
        // Wait after clicking to allow any resulting animations to complete
        if (scenario.postInteractionWait) {
          await page.waitForTimeout(scenario.postInteractionWait);
        } else {
          await page.waitForTimeout(500); // Default wait
        }
      } catch (error) {
        console.error(`Error clicking selector "${selector}": ${error}`);
      }
    }
  }
  
  // Execute hover interactions if specified
  if (scenario.hoverSelectors && scenario.hoverSelectors.length > 0) {
    for (const selector of scenario.hoverSelectors) {
      try {
        await page.waitForSelector(selector, { visible: true, timeout: 5000 });
        await page.hover(selector);
        
        // Wait for hover effects
        await page.waitForTimeout(scenario.postInteractionWait || 500);
      } catch (error) {
        console.error(`Error hovering over selector "${selector}": ${error}`);
      }
    }
  }
  
  // Test any form interactions
  if (scenario.formSelectors) {
    for (const form of scenario.formSelectors) {
      try {
        // Input text in form fields
        if (form.inputSelector && form.inputValue) {
          await page.waitForSelector(form.inputSelector, { visible: true, timeout: 5000 });
          await page.type(form.inputSelector, form.inputValue);
        }
        
        // Select from dropdown
        if (form.selectSelector && form.selectValue) {
          await page.waitForSelector(form.selectSelector, { visible: true, timeout: 5000 });
          await page.select(form.selectSelector, form.selectValue);
        }
        
        // Click submit button if specified
        if (form.submitSelector) {
          await page.waitForSelector(form.submitSelector, { visible: true, timeout: 5000 });
          await page.click(form.submitSelector);
          
          // Wait for form submission
          await page.waitForTimeout(form.postSubmitWait || 1000);
        }
      } catch (error) {
        console.error(`Error with form interaction: ${error}`);
      }
    }
  }
  
  // Handle responsive testing for different viewports
  if (scenario.viewportWidthBreakpoints) {
    // Get current viewport size
    const currentViewport = {
      width: scenario.viewport.width,
      height: scenario.viewport.height
    };
    
    // Only run if we're testing the desktop viewport
    if (currentViewport.width >= 1024) {
      console.log('Testing responsive behavior at different breakpoints');
      
      // Test each defined breakpoint
      for (const breakpoint of scenario.viewportWidthBreakpoints) {
        await page.setViewport({
          width: breakpoint,
          height: currentViewport.height
        });
        
        // Wait for responsive adjustments
        await page.waitForTimeout(1000);
        
        // Take additional screenshot for this breakpoint
        await require('./onReady.js')(page, {
          ...scenario,
          viewport: {
            width: breakpoint,
            height: currentViewport.height
          },
          label: scenario.label + '-breakpoint-' + breakpoint
        });
      }
      
      // Restore original viewport
      await page.setViewport(currentViewport);
    }
  }
  
  // Remove known dynamic elements that would cause false positives
  await page.evaluate(() => {
    // List of selectors to hide
    const selectorsToHide = [
      '.date-time', // Dynamic date/time displays
      '.user-avatar', // User avatars that might change
      '.user-specific-content', // User-specific content
      '.analytics-counter', // Analytics counters
      '.random-content', // Random content
      '.advertisement', // Ads
      '.live-data', // Live data widgets
      '[data-dynamic=true]', // Elements marked as dynamic
      '.timestamp', // Timestamps
      '.carousel-active-slide', // Active carousel slides
    ];
    
    // Hide each selector
    selectorsToHide.forEach(selector => {
      const elements = document.querySelectorAll(selector);
      elements.forEach(element => {
        if (element) {
          element.style.visibility = 'hidden';
        }
      });
    });
  });
  
  // Additional wait to ensure page is stable
  await page.waitForTimeout(scenario.finalWait || 500);
}; 