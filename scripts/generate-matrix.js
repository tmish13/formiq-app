"use strict";
/**
 * Script to generate or update the test functionality matrix
 * Scans test files and organizes by functionality, component, and status
 */
exports.__esModule = true;
var fs_1 = require("fs");
var path_1 = require("path");
var glob_1 = require("glob");
var url_1 = require("url");
// Get __dirname equivalent in ES modules
var __filename = (0, url_1.fileURLToPath)(import.meta.url);
var __dirname = path_1["default"].dirname(__filename);
var MATRIX_FILE = path_1["default"].resolve(__dirname, '../frontend-test-functionality-matrix.md');
var TEST_DIRS = [
    'src/**/__tests__',
    'tests/**',
    'frontend/src/**/__tests__',
    'frontend/tests/**'
];
// Organizational categories
var CATEGORIES = {
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
function findTestFiles() {
    var allFiles = [];
    TEST_DIRS.forEach(function (dir) {
        var pattern = path_1["default"].join(dir, '**/*.{test,spec}.{ts,tsx}');
        var files = glob_1["default"].sync(pattern);
        allFiles.push.apply(allFiles, files);
    });
    return allFiles;
}
// Categorize test files
function categorizeTests(files) {
    var categorized = {};
    // Initialize categories
    Object.keys(CATEGORIES).forEach(function (category) {
        categorized[category] = [];
    });
    // Add uncategorized category
    categorized['Uncategorized'] = [];
    files.forEach(function (file) {
        // Read file content to check for keywords
        var content = fs_1["default"].readFileSync(file, 'utf8');
        var assigned = false;
        for (var _i = 0, _a = Object.entries(CATEGORIES); _i < _a.length; _i++) {
            var _b = _a[_i], category = _b[0], keywords = _b[1];
            var keywordList = keywords.split('|');
            if (keywordList.some(function (keyword) {
                return file.toLowerCase().includes(keyword.toLowerCase()) ||
                    content.toLowerCase().includes(keyword.toLowerCase());
            })) {
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
function generateCategoryTable(category, files) {
    var table = "### ".concat(category, "\n");
    table += '| Functionality | Status | Test File(s) |\n';
    table += '|---------------|--------|-------------|\n';
    // Group files by functionality
    var functionalityMap = {};
    files.forEach(function (file) {
        // Extract functionality from filename or category
        var filename = path_1["default"].basename(file);
        var functionalityMatch = filename.match(/^([A-Za-z]+)\./) || [null, category];
        var functionality = functionalityMatch[1] || category;
        if (!functionalityMap[functionality]) {
            functionalityMap[functionality] = [];
        }
        functionalityMap[functionality].push(file);
    });
    // Add rows for each functionality
    Object.entries(functionalityMap).forEach(function (_a) {
        var functionality = _a[0], testFiles = _a[1];
        var isConsolidated = testFiles.some(function (file) { return file.includes('.consolidated.'); });
        var status = isConsolidated ? 'Complete' : 'Pending';
        // Format filenames more nicely
        var fileNames = testFiles.map(function (file) {
            var baseName = path_1["default"].basename(file);
            if (baseName.includes('.consolidated.')) {
                return baseName;
            }
            else {
                return baseName;
            }
        });
        table += "| ".concat(functionality, " | ").concat(status, " | ").concat(fileNames.join(', '), " |\n");
    });
    return table;
}
// Generate the entire matrix
function generateMatrix(categorizedTests) {
    var markdown = '# Frontend Test Functionality Matrix\n\n';
    markdown += 'This document maps test files to the specific functionalities they test, helping identify coverage gaps and redundancies.\n\n';
    // Add each category section
    Object.entries(categorizedTests)
        .filter(function (_a) {
        var _ = _a[0], files = _a[1];
        return files.length > 0;
    }) // Skip empty categories
        .forEach(function (_a) {
        var category = _a[0], files = _a[1];
        markdown += generateCategoryTable(category, files);
        markdown += '\n';
    });
    // Add next steps section
    markdown += "## Next Steps\n\n1. **Validate this Matrix**:\n   - Confirm that all behaviors are correctly mapped\n   - Ensure no critical behaviors are missing\n   - Verify primary test locations make sense\n\n2. **Continue Consolidation**:\n   - Start with highest-priority areas\n   - Refactor primary test locations to be behavior-focused\n   - Migrate unique test coverage from other files\n   - Remove redundant tests\n\n3. **Track Progress**:\n   - Update the Status column as work progresses\n   - Document test file deletions\n   - Measure coverage to ensure no functionality is lost";
    return markdown;
}
// Main function
function main() {
    var args = process.argv.slice(2);
    var updateFlag = args.includes('--update');
    console.log('Finding test files...');
    var testFiles = findTestFiles();
    console.log("Found ".concat(testFiles.length, " test files"));
    console.log('Categorizing tests...');
    var categorizedTests = categorizeTests(testFiles);
    console.log('Generating markdown...');
    var markdown = generateMatrix(categorizedTests);
    if (updateFlag || !fs_1["default"].existsSync(MATRIX_FILE)) {
        fs_1["default"].writeFileSync(MATRIX_FILE, markdown, 'utf8');
        console.log("Matrix written to ".concat(MATRIX_FILE));
    }
    else {
        console.log('Matrix generated (use --update to write to file):');
        console.log(markdown);
    }
}
main();
