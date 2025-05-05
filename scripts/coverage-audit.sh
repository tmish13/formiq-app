#!/bin/bash

# Set colors for output
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Starting test coverage audit...${NC}"

# Create the coverage directory if it doesn't exist
mkdir -p coverage

# Run Jest with coverage and use the coverage budget
echo -e "${YELLOW}Running Jest tests with coverage...${NC}"
cd frontend && npm test -- --coverage --coverageReporters="text" --coverageReporters="html" --coverageReporters="json-summary" --collectCoverageFrom="src/**/*.{ts,tsx}" --coverageDirectory="../coverage" --json --outputFile="../coverage/test-results.json"

# Check the exit code
if [ $? -ne 0 ]; then
  echo -e "${RED}Tests failed or coverage thresholds not met.${NC}"
  echo -e "${YELLOW}See detailed coverage report at:${NC} file://$(pwd)/../coverage/index.html"
  exit 1
fi

# Generate a coverage summary report
echo -e "${GREEN}Generating coverage summary report...${NC}"
cd ..
node -e "
const fs = require('fs');
const path = require('path');

const coverageSummary = JSON.parse(fs.readFileSync('./coverage/coverage-summary.json', 'utf8'));
const budget = JSON.parse(fs.readFileSync('./coverage-budget.json', 'utf8'));

// Check if coverage meets the budget
let budgetExceeded = false;
const report = [];

// Check global coverage
const total = coverageSummary.total;
const globalBudget = budget.global;

report.push('# Coverage Audit Report');
report.push('');
report.push('## Global Coverage');
report.push('');

const coverageTable = [
  '| Metric | Coverage | Budget | Status |',
  '| ------ | -------- | ------ | ------ |',
];

const getCoverageStatus = (actual, threshold) => {
  if (actual < threshold) {
    budgetExceeded = true;
    return '❌ FAIL';
  }
  return '✅ PASS';
};

coverageTable.push(\`| Statements | \${total.statements.pct.toFixed(2)}% | \${globalBudget.statements}% | \${getCoverageStatus(total.statements.pct, globalBudget.statements)} |\`);
coverageTable.push(\`| Branches | \${total.branches.pct.toFixed(2)}% | \${globalBudget.branches}% | \${getCoverageStatus(total.branches.pct, globalBudget.branches)} |\`);
coverageTable.push(\`| Functions | \${total.functions.pct.toFixed(2)}% | \${globalBudget.functions}% | \${getCoverageStatus(total.functions.pct, globalBudget.functions)} |\`);
coverageTable.push(\`| Lines | \${total.lines.pct.toFixed(2)}% | \${globalBudget.lines}% | \${getCoverageStatus(total.lines.pct, globalBudget.lines)} |\`);

report.push(...coverageTable);
report.push('');

// Add folders with low coverage
report.push('## Folders with Low Coverage');
report.push('');
report.push('| Folder | Statements | Branches | Functions | Lines |');
report.push('| ------ | ---------- | -------- | --------- | ----- |');

const lowCoverage = [];

for (const [key, value] of Object.entries(coverageSummary)) {
  if (key !== 'total') {
    const folderPath = key.replace(/^\//, '');
    
    // Skip if coverage is good
    if (
      value.statements.pct >= globalBudget.statements &&
      value.branches.pct >= globalBudget.branches &&
      value.functions.pct >= globalBudget.functions &&
      value.lines.pct >= globalBudget.lines
    ) {
      continue;
    }
    
    lowCoverage.push({
      folder: folderPath,
      metrics: {
        statements: value.statements.pct.toFixed(2),
        branches: value.branches.pct.toFixed(2),
        functions: value.functions.pct.toFixed(2),
        lines: value.lines.pct.toFixed(2)
      }
    });
  }
}

// Sort by statement coverage (ascending)
lowCoverage.sort((a, b) => parseFloat(a.metrics.statements) - parseFloat(b.metrics.statements));

if (lowCoverage.length === 0) {
  report.push('No folders with coverage below thresholds! 🎉');
} else {
  for (const item of lowCoverage) {
    report.push(\`| \${item.folder} | \${item.metrics.statements}% | \${item.metrics.branches}% | \${item.metrics.functions}% | \${item.metrics.lines}% |\`);
  }
}

report.push('');
report.push('## Files with Missing Coverage');
report.push('');

const missingCoverage = [];

// Scan for files with missing coverage
const scanFiles = (dir) => {
  const files = fs.readdirSync(dir);
  
  for (const file of files) {
    const filePath = path.join(dir, file);
    const stat = fs.statSync(filePath);
    
    if (stat.isDirectory()) {
      scanFiles(filePath);
    } else if (file.match(/\.(ts|tsx)$/)) {
      // Skip test files
      if (file.includes('.test.') || file.includes('.spec.')) continue;
      
      // Check if file has coverage data
      const relativePath = filePath.replace(/\\\\/g, '/');
      if (!Object.keys(coverageSummary).some(key => key.includes(relativePath))) {
        missingCoverage.push(relativePath);
      }
    }
  }
};

try {
  scanFiles('./frontend/src');
} catch (error) {
  report.push('Error scanning files: ' + error.message);
}

if (missingCoverage.length === 0) {
  report.push('No files missing coverage! 🎉');
} else {
  report.push('The following files have no tests:');
  report.push('');
  for (const file of missingCoverage) {
    report.push(\`- \${file}\`);
  }
}

// Write report to markdown file
fs.writeFileSync('./coverage/COVERAGE_REPORT.md', report.join('\\n'));

// Output summary to console
console.log('Coverage summary:');
console.log(\`Statements: \${total.statements.pct.toFixed(2)}% (\${globalBudget.statements}% required)\`);
console.log(\`Branches: \${total.branches.pct.toFixed(2)}% (\${globalBudget.branches}% required)\`);
console.log(\`Functions: \${total.functions.pct.toFixed(2)}% (\${globalBudget.functions}% required)\`);
console.log(\`Lines: \${total.lines.pct.toFixed(2)}% (\${globalBudget.lines}% required)\`);
console.log(\`\\nSee detailed report at: ./coverage/COVERAGE_REPORT.md\`);

process.exit(budgetExceeded ? 1 : 0);
"

# Check if the audit failed
if [ $? -ne 0 ]; then
  echo -e "${RED}Coverage audit failed. See coverage report for details.${NC}"
  echo -e "${YELLOW}Coverage report:${NC} file://$(pwd)/coverage/index.html"
  echo -e "${YELLOW}Coverage summary:${NC} file://$(pwd)/coverage/COVERAGE_REPORT.md"
  exit 1
else
  echo -e "${GREEN}Coverage audit passed successfully!${NC}"
  echo -e "${YELLOW}Coverage report:${NC} file://$(pwd)/coverage/index.html"
  echo -e "${YELLOW}Coverage summary:${NC} file://$(pwd)/coverage/COVERAGE_REPORT.md"
  exit 0
fi 