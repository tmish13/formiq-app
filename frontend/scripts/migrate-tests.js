#!/usr/bin/env node

/**
 * This script helps migrate existing tests to use the new testing utilities.
 * It finds and replaces common patterns in test files to update them.
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

// Search for test files
const testFiles = execSync('find src -name "*.test.tsx" -o -name "*.test.ts"', { encoding: 'utf-8' })
  .split('\n')
  .filter(Boolean);

console.log(`Found ${testFiles.length} test files to check.`);

let modifiedFiles = 0;

testFiles.forEach(file => {
  const filePath = path.resolve(file);
  let content = fs.readFileSync(filePath, 'utf-8');
  let modified = false;

  // Replace direct testing-library imports
  if (content.includes("import { render") && content.includes("@testing-library/react")) {
    content = content.replace(
      /import\s+{([^}]*)render([^}]*)}\s+from\s+['"]@testing-library\/react['"]/g,
      "import { $1$2 } from '../../tests/utils/testRender'"
    );
    modified = true;
  }

  // Replace standard render with our testRender
  if (content.includes("render(") && !content.includes("testRender(")) {
    content = content.replace(/import\s+{\s*([^}]*)\s*}\s+from\s+['"]\.\.\/\.\.\/tests\/utils\/testRender['"]/g, 
      "import { $1, render as testRender } from '../../tests/utils/testRender'");
    content = content.replace(/\brender\(/g, "testRender(");
    modified = true;
  }

  // Replace imports from server.js with testServer.ts
  if (content.includes("from '../../mocks/server'")) {
    content = content.replace(
      /import\s+{([^}]*)}\s+from\s+['"]\.\.\/\.\.\/mocks\/server['"]/g,
      "import { $1 } from '../../tests/utils/testServer'"
    );
    modified = true;
  }

  // Replace direct theme imports with mockTheme
  if (content.includes("import { theme }") && content.includes("from '../../theme'")) {
    content = content.replace(
      /import\s+{\s*theme\s*}\s+from\s+['"]\.\.\/\.\.\/theme['"]/g,
      "import { mockThemeWithFallbacks as theme } from '../../tests/__mocks__/mockTheme'"
    );
    modified = true;
  }

  // Simplify common provider wrapper patterns
  const providerWrapperPattern = /<Provider[^>]*>(\s*)<ThemeProvider[^>]*>(\s*)<(BrowserRouter|MemoryRouter)[^>]*>/g;
  if (content.match(providerWrapperPattern)) {
    content = content.replace(providerWrapperPattern, '');
    content = content.replace(/<\/(BrowserRouter|MemoryRouter)>(\s*)<\/ThemeProvider>(\s*)<\/Provider>/g, '');
    modified = true;
  }

  if (modified) {
    console.log(`Modified: ${file}`);
    fs.writeFileSync(filePath, content, 'utf-8');
    modifiedFiles++;
  }
});

console.log(`Done! Modified ${modifiedFiles} files.`);
console.log('\nSome manual checks may still be needed:');
console.log('1. Make sure import paths are correct');
console.log('2. Check for custom provider wrappers that weren\'t detected');
console.log('3. Review any MSW server reset/setup patterns'); 