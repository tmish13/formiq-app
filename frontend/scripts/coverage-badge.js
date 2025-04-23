const fs = require('fs');
const path = require('path');

// Read the coverage summary
const coverageSummary = JSON.parse(
  fs.readFileSync(path.join(__dirname, '../coverage/coverage-summary.json'), 'utf8')
);

// Calculate overall coverage
const total = coverageSummary.total;
const coverage = Math.round((total.lines.pct + total.statements.pct + total.functions.pct + total.branches.pct) / 4);

// Generate badge color based on coverage
let color = 'red';
if (coverage >= 85) {
  color = 'green';
} else if (coverage >= 70) {
  color = 'yellow';
}

// Generate badge URL
const badgeUrl = `https://img.shields.io/badge/coverage-${coverage}%25-${color}`;

// Update README.md
const readmePath = path.join(__dirname, '../README.md');
let readme = fs.readFileSync(readmePath, 'utf8');

// Check if badge already exists
const badgeRegex = /!\[coverage\]\(https:\/\/img\.shields\.io\/badge\/coverage-\d+%25-\w+\)/;
if (badgeRegex.test(readme)) {
  // Replace existing badge
  readme = readme.replace(badgeRegex, `![coverage](${badgeUrl})`);
} else {
  // Add badge after the first heading
  readme = readme.replace(/^#.*$/m, `$&\n\n![coverage](${badgeUrl})`);
}

fs.writeFileSync(readmePath, readme);

console.log(`Coverage badge updated: ${coverage}%`); 