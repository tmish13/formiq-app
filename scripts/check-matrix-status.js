"use strict";
/**
 * Script to check matrix status against actual test files
 * Checks for existence of test files and updates status flags in matrix
 */
exports.__esModule = true;
var fs = require("fs");
var path = require("path");
var glob = require("glob");
var MATRIX_FILE = path.resolve(__dirname, '../frontend-test-functionality-matrix.md');
var TEST_DIRS = [
    'src/**/__tests__',
    'tests/**',
    'frontend/src/**/__tests__',
    'frontend/tests/**'
];
// Status indicators
var PENDING = 'Pending';
var COMPLETE = 'Complete';
// Read the matrix file
var matrixContent = fs.readFileSync(MATRIX_FILE, 'utf8');
// Regular expression to match test file paths in the matrix
var testFileRegex = /\| `.+?` \|/g;
// Find all test files mentioned in the matrix
var testFilesInMatrix = [];
var match;
var testFileMatches = matrixContent.match(/\| `([^`]+)` \|/g) || [];
var _loop_1 = function (fileMatch) {
    var fileName = fileMatch.replace(/\| `/, '').replace(/` \|/, '');
    // Check if the test file exists
    var exists = TEST_DIRS.some(function (dir) {
        var pattern = path.join(dir, "**/".concat(fileName));
        return glob.sync(pattern).length > 0;
    });
    testFilesInMatrix.push({
        path: fileName,
        exists: exists
    });
};
for (var _i = 0, testFileMatches_1 = testFileMatches; _i < testFileMatches_1.length; _i++) {
    var fileMatch = testFileMatches_1[_i];
    _loop_1(fileMatch);
}
// Update the matrix content with the correct status
var updatedContent = matrixContent;
for (var _a = 0, testFilesInMatrix_1 = testFilesInMatrix; _a < testFilesInMatrix_1.length; _a++) {
    var testFile = testFilesInMatrix_1[_a];
    var status_1 = testFile.exists ? COMPLETE : PENDING;
    // Replace the status for this file
    updatedContent = updatedContent.replace(new RegExp("\\| `".concat(testFile.path.replace(/\./g, '\\.')) + '` \\| [^|]+ \\|'), "| `".concat(testFile.path, "` | ").concat(status_1, " |"));
}
// Write the updated content back to the file
fs.writeFileSync(MATRIX_FILE, updatedContent, 'utf8');
console.log("Matrix updated. Found ".concat(testFilesInMatrix.length, " test files."));
console.log("- Existing: ".concat(testFilesInMatrix.filter(function (f) { return f.exists; }).length));
console.log("- Missing: ".concat(testFilesInMatrix.filter(function (f) { return !f.exists; }).length));
