/**
 * Script to check matrix status against actual test files
 * Checks for existence of test files and updates status flags in matrix
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

// Status indicators
const PENDING = 'Pending';
const COMPLETE = 'Complete';

interface TestFile {
  path: string;
  exists: boolean;
}

// Read the matrix file
const matrixContent = fs.readFileSync(MATRIX_FILE, 'utf8');

// Regular expression to match test file paths in the matrix
const testFileRegex = /\| `.+?` \|/g;

// Find all test files mentioned in the matrix
const testFilesInMatrix: TestFile[] = [];
let match;
const testFileMatches = matrixContent.match(/\| `([^`]+)` \|/g) || [];

for (const fileMatch of testFileMatches) {
  const fileName = fileMatch.replace(/\| `/, '').replace(/` \|/, '');
  
  // Check if the test file exists
  const exists = TEST_DIRS.some(dir => {
    const pattern = path.join(dir, `**/${fileName}`);
    return glob.sync(pattern).length > 0;
  });
  
  testFilesInMatrix.push({
    path: fileName,
    exists
  });
}

// Update the matrix content with the correct status
let updatedContent = matrixContent;

for (const testFile of testFilesInMatrix) {
  const status = testFile.exists ? COMPLETE : PENDING;
  
  // Replace the status for this file
  updatedContent = updatedContent.replace(
    new RegExp(`\\| \`${testFile.path.replace(/\./g, '\\.')}` + '` \\| [^|]+ \\|'),
    `| \`${testFile.path}\` | ${status} |`
  );
}

// Write the updated content back to the file
fs.writeFileSync(MATRIX_FILE, updatedContent, 'utf8');

console.log(`Matrix updated. Found ${testFilesInMatrix.length} test files.`);
console.log(`- Existing: ${testFilesInMatrix.filter(f => f.exists).length}`);
console.log(`- Missing: ${testFilesInMatrix.filter(f => !f.exists).length}`); 