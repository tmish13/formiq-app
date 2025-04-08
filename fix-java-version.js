#!/usr/bin/env node

/**
 * This script fixes the Java version in Capacitor generated Gradle files
 * to ensure compatibility with the installed JDK.
 */
const fs = require('fs');
const path = require('path');

const filesToFix = [
  'android/app/capacitor.build.gradle',
  'android/capacitor-cordova-android-plugins/build.gradle'
];

// The version we want to set
const TARGET_JAVA_VERSION = 'VERSION_17';

function fixJavaVersion(filePath) {
  try {
    if (!fs.existsSync(filePath)) {
      console.log(`File not found: ${filePath}`);
      return;
    }

    let content = fs.readFileSync(filePath, 'utf8');
    
    // Replace any Java version with our target version
    const updatedContent = content.replace(
      /VERSION_\d+/g, 
      TARGET_JAVA_VERSION
    );
    
    if (content !== updatedContent) {
      fs.writeFileSync(filePath, updatedContent, 'utf8');
      console.log(`✅ Updated Java version in ${filePath}`);
    } else {
      console.log(`ℹ️ No changes needed in ${filePath}`);
    }
  } catch (error) {
    console.error(`❌ Error fixing Java version in ${filePath}:`, error);
  }
}

// Fix all target files
console.log('🔧 Fixing Java version in Capacitor generated files...');
filesToFix.forEach(file => fixJavaVersion(file));
console.log('✅ Java version fix complete'); 