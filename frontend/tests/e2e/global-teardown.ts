/**
 * Playwright Global Teardown for FormIQ E2E Tests
 * 
 * Handles cleanup, test result processing, and environment teardown
 * after all end-to-end tests have completed.
 */

import { FullConfig } from '@playwright/test';
import fs from 'fs';
import path from 'path';

async function globalTeardown(config: FullConfig) {
  console.log('🧹 Starting FormIQ E2E Test Global Teardown...');
  
  try {
    // Clean up temporary test files
    await cleanupTestFiles();
    
    // Process test results
    await processTestResults();
    
    // Generate performance report
    await generatePerformanceReport();
    
    // Cleanup auth files
    await cleanupAuthFiles();
    
    console.log('✅ FormIQ E2E Test Global Teardown completed successfully');
  } catch (error) {
    console.error('❌ FormIQ E2E Test Global Teardown failed:', error);
    // Don't throw error as this shouldn't fail the test run
  }
}

/**
 * Clean up temporary test files
 */
async function cleanupTestFiles() {
  console.log('🗑️ Cleaning up temporary test files...');
  
  const tempDirs = [
    path.join(__dirname, '../fixtures/temp'),
    path.join(__dirname, '../test-results/artifacts'),
  ];
  
  for (const dir of tempDirs) {
    if (fs.existsSync(dir)) {
      try {
        fs.rmSync(dir, { recursive: true, force: true });
        console.log(`Cleaned up: ${dir}`);
      } catch (error) {
        console.warn(`Warning: Could not clean up ${dir}:`, error);
      }
    }
  }
}

/**
 * Process and aggregate test results
 */
async function processTestResults() {
  console.log('📊 Processing test results...');
  
  const resultsFile = path.join(__dirname, '../test-results/e2e-results.json');
  
  if (!fs.existsSync(resultsFile)) {
    console.log('No test results file found, skipping processing');
    return;
  }
  
  try {
    const rawResults = fs.readFileSync(resultsFile, 'utf8');
    const results = JSON.parse(rawResults);
    
    // Calculate test statistics
    const stats = {
      total: 0,
      passed: 0,
      failed: 0,
      skipped: 0,
      flaky: 0,
      duration: 0,
      byProject: {} as Record<string, any>,
    };
    
    // Process each test suite
    if (results.suites) {
      for (const suite of results.suites) {
        processTestSuite(suite, stats);
      }
    }
    
    // Generate summary report
    const summaryReport = {
      timestamp: new Date().toISOString(),
      environment: {
        nodeVersion: process.version,
        platform: process.platform,
        ci: !!process.env.CI,
      },
      statistics: stats,
      performance: {
        averageTestDuration: stats.total > 0 ? stats.duration / stats.total : 0,
        slowestTests: [], // Could be populated from detailed results
        fastestTests: [], // Could be populated from detailed results
      },
    };
    
    // Save summary report
    const summaryPath = path.join(__dirname, '../test-results/e2e-summary.json');
    fs.writeFileSync(summaryPath, JSON.stringify(summaryReport, null, 2));
    
    // Log summary to console
    console.log('📈 Test Results Summary:');
    console.log(`  Total: ${stats.total}`);
    console.log(`  Passed: ${stats.passed} (${((stats.passed / stats.total) * 100).toFixed(1)}%)`);
    console.log(`  Failed: ${stats.failed} (${((stats.failed / stats.total) * 100).toFixed(1)}%)`);
    console.log(`  Skipped: ${stats.skipped}`);
    console.log(`  Total Duration: ${(stats.duration / 1000).toFixed(2)}s`);
    
  } catch (error) {
    console.error('Error processing test results:', error);
  }
}

/**
 * Process individual test suite
 */
function processTestSuite(suite: any, stats: any) {
  if (suite.tests) {
    for (const test of suite.tests) {
      stats.total++;
      
      // Determine test status
      const lastResult = test.results?.[test.results.length - 1];
      if (lastResult) {
        switch (lastResult.status) {
          case 'passed':
            stats.passed++;
            break;
          case 'failed':
            stats.failed++;
            break;
          case 'skipped':
            stats.skipped++;
            break;
          case 'timedOut':
            stats.failed++;
            break;
        }
        
        if (lastResult.duration) {
          stats.duration += lastResult.duration;
        }
        
        // Check if test is flaky (multiple attempts)
        if (test.results.length > 1) {
          stats.flaky++;
        }
      }
    }
  }
  
  // Process nested suites
  if (suite.suites) {
    for (const nestedSuite of suite.suites) {
      processTestSuite(nestedSuite, stats);
    }
  }
}

/**
 * Generate performance report from test results
 */
async function generatePerformanceReport() {
  console.log('⚡ Generating performance report...');
  
  const performanceDataFile = path.join(__dirname, '../test-results/performance-data.json');
  
  if (!fs.existsSync(performanceDataFile)) {
    console.log('No performance data found, skipping performance report');
    return;
  }
  
  try {
    const performanceData = JSON.parse(fs.readFileSync(performanceDataFile, 'utf8'));
    
    const performanceReport = {
      timestamp: new Date().toISOString(),
      summary: {
        averageLoadTime: calculateAverage(performanceData.loadTimes || []),
        averageUploadTime: calculateAverage(performanceData.uploadTimes || []),
        averageAnalysisTime: calculateAverage(performanceData.analysisTimes || []),
      },
      thresholds: {
        loadTime: 3000, // 3 seconds
        uploadTime: 60000, // 1 minute
        analysisTime: 30000, // 30 seconds
      },
      violations: [] as any[],
    };
    
    // Check for threshold violations
    if (performanceReport.summary.averageLoadTime > performanceReport.thresholds.loadTime) {
      performanceReport.violations.push({
        metric: 'loadTime',
        average: performanceReport.summary.averageLoadTime,
        threshold: performanceReport.thresholds.loadTime,
      });
    }
    
    if (performanceReport.summary.averageUploadTime > performanceReport.thresholds.uploadTime) {
      performanceReport.violations.push({
        metric: 'uploadTime',
        average: performanceReport.summary.averageUploadTime,
        threshold: performanceReport.thresholds.uploadTime,
      });
    }
    
    if (performanceReport.summary.averageAnalysisTime > performanceReport.thresholds.analysisTime) {
      performanceReport.violations.push({
        metric: 'analysisTime',
        average: performanceReport.summary.averageAnalysisTime,
        threshold: performanceReport.thresholds.analysisTime,
      });
    }
    
    // Save performance report
    const performanceReportPath = path.join(__dirname, '../test-results/performance-report.json');
    fs.writeFileSync(performanceReportPath, JSON.stringify(performanceReport, null, 2));
    
    // Log performance summary
    console.log('⚡ Performance Summary:');
    console.log(`  Average Load Time: ${performanceReport.summary.averageLoadTime}ms`);
    console.log(`  Average Upload Time: ${performanceReport.summary.averageUploadTime}ms`);
    console.log(`  Average Analysis Time: ${performanceReport.summary.averageAnalysisTime}ms`);
    
    if (performanceReport.violations.length > 0) {
      console.warn('⚠️ Performance threshold violations detected:');
      performanceReport.violations.forEach(violation => {
        console.warn(`  ${violation.metric}: ${violation.average}ms > ${violation.threshold}ms`);
      });
    }
    
  } catch (error) {
    console.error('Error generating performance report:', error);
  }
}

/**
 * Calculate average from array of numbers
 */
function calculateAverage(numbers: number[]): number {
  if (numbers.length === 0) return 0;
  return numbers.reduce((sum, num) => sum + num, 0) / numbers.length;
}

/**
 * Clean up authentication files
 */
async function cleanupAuthFiles() {
  console.log('🔐 Cleaning up authentication files...');
  
  const authFiles = [
    path.join(__dirname, '../fixtures/auth.json'),
    path.join(__dirname, '../fixtures/.auth-state'),
  ];
  
  for (const authFile of authFiles) {
    if (fs.existsSync(authFile)) {
      try {
        fs.unlinkSync(authFile);
        console.log(`Cleaned up auth file: ${authFile}`);
      } catch (error) {
        console.warn(`Warning: Could not clean up auth file ${authFile}:`, error);
      }
    }
  }
}

export default globalTeardown;