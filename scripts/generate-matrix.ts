/**
 * Script to generate or update the test functionality matrix
 * Scans test files and organizes by functionality, component, and status
 */

import fs from 'fs';
import path from 'path';
import glob from 'glob';
import { fileURLToPath } from 'url';

// Get __dirname equivalent in ES modules
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const MATRIX_FILE = path.resolve(__dirname, '../frontend-test-functionality-matrix.md');
const TEST_DIRS = [
  'src/**/__tests__',
  'tests/**',
  'frontend/src/**/__tests__',
  'frontend/tests/**'
];

// Organizational categories
const CATEGORIES = {
  'Upload Guidance & Flow': 'upload',
  'Form Analysis': 'form',
  'User Authentication': 'auth',
  'Profile Management': 'profile',
  'API Services': 'api|service',
  'Custom Hooks': 'hook',
  'Video Service': 'video',
  'Subscription Management': 'subscription',
  'Pose Analysis': 'pose',
  'Exercise Analysis': 'exercise',
  'Form Check Redux Flow': 'formCheck|form-check',
  'Component Testing': 'component',
  'End-to-End User Flows': 'e2e|flow',
  'Security & Performance': 'security|performance'
};

// Find all test files
function findTestFiles(): string[] {
  const allFiles: string[] = [];
  
  TEST_DIRS.forEach(dir => {
    const pattern = path.join(dir, '**/*.{test,spec}.{ts,tsx}');
    const files = glob.sync(pattern);
    allFiles.push(...files);
  });
  
  return allFiles;
}

// Categorize test files
function categorizeTests(files: string[]): Record<string, string[]> {
  const categorized: Record<string, string[]> = {};
  
  // Initialize categories
  Object.keys(CATEGORIES).forEach(category => {
    categorized[category] = [];
  });
  
  // Add uncategorized category
  categorized['Uncategorized'] = [];
  
  files.forEach(file => {
    // Read file content to check for keywords
    const content = fs.readFileSync(file, 'utf8');
    let assigned = false;
    
    for (const [category, keywords] of Object.entries(CATEGORIES)) {
      const keywordList = keywords.split('|');
      
      if (keywordList.some(keyword => 
          file.toLowerCase().includes(keyword.toLowerCase()) || 
          content.toLowerCase().includes(keyword.toLowerCase()))) {
        categorized[category].push(file);
        assigned = true;
        break;
      }
    }
    
    if (!assigned) {
      categorized['Uncategorized'].push(file);
    }
  });
  
  return categorized;
}

// Generate markdown table for a category
function generateCategoryTable(category: string, files: string[]): string {
  let table = `### ${category}\n`;
  table += '| Functionality | Status | Test File(s) |\n';
  table += '|---------------|--------|-------------|\n';
  
  // Group files by functionality
  const functionalityMap: Record<string, string[]> = {};
  
  files.forEach(file => {
    // Extract functionality from filename or category
    const filename = path.basename(file);
    const functionalityMatch = filename.match(/^([A-Za-z]+)\./) || [null, category];
    const functionality = functionalityMatch[1] || category;
    
    if (!functionalityMap[functionality]) {
      functionalityMap[functionality] = [];
    }
    
    functionalityMap[functionality].push(file);
  });
  
  // Add rows for each functionality
  Object.entries(functionalityMap).forEach(([functionality, testFiles]) => {
    const isConsolidated = testFiles.some(file => file.includes('.consolidated.'));
    const status = isConsolidated ? 'Complete' : 'Pending';
    
    // Format filenames more nicely
    const fileNames = testFiles.map(file => {
      const baseName = path.basename(file);
      if (baseName.includes('.consolidated.')) {
        return baseName;
      } else {
        return baseName;
      }
    });
    
    table += `| ${functionality} | ${status} | ${fileNames.join(', ')} |\n`;
  });
  
  return table;
}

// Generate the entire matrix
function generateMatrix(categorizedTests: Record<string, string[]>): string {
  let markdown = '# Frontend Test Functionality Matrix\n\n';
  markdown += 'This document maps test files to the specific functionalities they test, helping identify coverage gaps and redundancies.\n\n';
  
  // Add each category section
  Object.entries(categorizedTests)
    .filter(([_, files]) => files.length > 0) // Skip empty categories
    .forEach(([category, files]) => {
      markdown += generateCategoryTable(category, files);
      markdown += '\n';
    });
  
  // Add next steps section
  markdown += `## Next Steps

1. **Validate this Matrix**:
   - Confirm that all behaviors are correctly mapped
   - Ensure no critical behaviors are missing
   - Verify primary test locations make sense

2. **Continue Consolidation**:
   - Start with highest-priority areas
   - Refactor primary test locations to be behavior-focused
   - Migrate unique test coverage from other files
   - Remove redundant tests

3. **Track Progress**:
   - Update the Status column as work progresses
   - Document test file deletions
   - Measure coverage to ensure no functionality is lost`;
  
  return markdown;
}

// Main function
function main(): void {
  const args = process.argv.slice(2);
  const updateFlag = args.includes('--update');
  
  console.log('Finding test files...');
  const testFiles = findTestFiles();
  console.log(`Found ${testFiles.length} test files`);
  
  console.log('Categorizing tests...');
  const categorizedTests = categorizeTests(testFiles);
  
  console.log('Generating markdown...');
  const markdown = generateMatrix(categorizedTests);
  
  if (updateFlag || !fs.existsSync(MATRIX_FILE)) {
    fs.writeFileSync(MATRIX_FILE, markdown, 'utf8');
    console.log(`Matrix written to ${MATRIX_FILE}`);
  } else {
    console.log('Matrix generated (use --update to write to file):');
    console.log(markdown);
  }
}

main(); 