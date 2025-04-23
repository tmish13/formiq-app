#!/usr/bin/env node

/**
 * Theme Audit Script
 * 
 * This script scans the frontend codebase for theme-related references
 * and identifies potential issues such as:
 * 
 * 1. Incorrect fallbacks references (fallbacks.colors instead of fallbacks.color)
 * 2. Missing theme paths or incorrect paths
 * 3. Inconsistencies in theme usage
 * 
 * Usage: node scripts/theme-audit.js [--fix]
 * The --fix flag will attempt to automatically fix common issues
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

// Configuration
const SRC_DIR = path.resolve(__dirname, '../src');
const EXTENSIONS = ['.tsx', '.ts', '.jsx', '.js'];
const IGNORE_DIRS = ['node_modules', 'dist', 'build', 'coverage'];

// Issues to look for
const ISSUES = {
  FALLBACKS_COLORS: {
    pattern: /fallbacks\.colors\./g,
    fix: (content) => content.replace(/fallbacks\.colors\./g, 'fallbacks.color.'),
    description: 'Incorrect fallbacks.colors reference (should be fallbacks.color)'
  },
  TYPOGRAPHY_SIZING: {
    pattern: /typography\.fontSize\.(small|medium|large|xlarge)/g,
    fix: (content) => content
      .replace(/typography\.fontSize\.small/g, 'typography.fontSize.sm')
      .replace(/typography\.fontSize\.medium/g, 'typography.fontSize.md')
      .replace(/typography\.fontSize\.large/g, 'typography.fontSize.lg')
      .replace(/typography\.fontSize\.xlarge/g, 'typography.fontSize.xl'),
    description: 'Incorrect typography size reference (should use sm/md/lg/xl format)'
  },
  DIRECT_THEME_COLOR: {
    pattern: /colors\.(primary|secondary|error|warning|success|info|text|background|border|disabled)(?!\.(main|light|dark|primary|secondary))/g,
    fix: null, // This requires manual review
    description: 'Direct theme color reference without specifying variant (main/light/dark)'
  },
  FALLBACKS_TYPOGRAPHY: {
    pattern: /fallbacks\.typography\./g,
    fix: null, // This requires manual review
    description: 'Reference to fallbacks.typography (should use separate specific fallbacks)'
  }
};

// Find all files to analyze
function findFiles(dir, fileList = []) {
  const files = fs.readdirSync(dir);
  
  files.forEach(file => {
    const filePath = path.join(dir, file);
    const stat = fs.statSync(filePath);
    
    if (stat.isDirectory() && !IGNORE_DIRS.includes(file)) {
      findFiles(filePath, fileList);
    } else if (stat.isFile() && EXTENSIONS.includes(path.extname(file))) {
      fileList.push(filePath);
    }
  });
  
  return fileList;
}

// Analyze a single file
function analyzeFile(filePath, shouldFix = false) {
  let content = fs.readFileSync(filePath, 'utf8');
  const originalContent = content;
  const issues = [];
  
  // Check for each issue
  Object.entries(ISSUES).forEach(([issueKey, issue]) => {
    const matches = content.match(issue.pattern);
    
    if (matches) {
      issues.push({
        issueKey,
        description: issue.description,
        count: matches.length,
        matches: matches
      });
      
      // Apply fix if requested and available
      if (shouldFix && issue.fix) {
        content = issue.fix(content);
      }
    }
  });
  
  // Save changes if fixes were applied
  if (shouldFix && content !== originalContent) {
    fs.writeFileSync(filePath, content, 'utf8');
    console.log(`  - Fixed issues in ${path.relative(SRC_DIR, filePath)}`);
  }
  
  return {
    filePath,
    issues,
    hasIssues: issues.length > 0
  };
}

// Main function
function main() {
  // Parse arguments
  const shouldFix = process.argv.includes('--fix');
  
  console.log('🔍 Scanning codebase for theme issues...');
  console.log(shouldFix ? '✅ Fix mode enabled' : '⚠️ Fix mode disabled (use --fix to auto-fix issues)');
  
  // Find and analyze files
  const files = findFiles(SRC_DIR);
  console.log(`Found ${files.length} files to analyze`);
  
  let issueCount = 0;
  let fixableIssueCount = 0;
  const issueFiles = [];
  
  files.forEach(filePath => {
    const result = analyzeFile(filePath, shouldFix);
    
    if (result.hasIssues) {
      issueFiles.push(result);
      
      result.issues.forEach(issue => {
        issueCount += issue.count;
        
        if (ISSUES[issue.issueKey].fix) {
          fixableIssueCount += issue.count;
        }
      });
    }
  });
  
  // Display results
  console.log('\n📊 Theme Audit Results');
  console.log(`Found ${issueCount} issues in ${issueFiles.length} files`);
  console.log(`${fixableIssueCount} issues are automatically fixable`);
  
  if (issueFiles.length > 0) {
    console.log('\n📄 Files with issues:');
    
    issueFiles.forEach(file => {
      console.log(`\n${path.relative(SRC_DIR, file.filePath)}`);
      
      file.issues.forEach(issue => {
        const fixable = ISSUES[issue.issueKey].fix ? 'fixable' : 'manual review required';
        console.log(`  - ${issue.description} (${issue.count} occurrences, ${fixable})`);
        
        if (issue.matches && issue.matches.length <= 5) {
          issue.matches.forEach(match => {
            console.log(`    - ${match}`);
          });
        }
      });
    });
    
    if (!shouldFix && fixableIssueCount > 0) {
      console.log('\n💡 Tip: Run with --fix to automatically fix issues');
    }
  } else {
    console.log('\n✅ No theme issues found!');
  }
}

// Run the script
main(); 