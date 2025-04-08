#!/bin/bash

# Script to fix Java version and run Android app

echo "🔧 Fixing Java version in Capacitor Gradle files..."
cd "$(dirname "$0")"

# Run fix-java-version.js script
node fix-java-version.js

# Navigate to Android directory
cd android

# Fix Java version in Gradle files directly as a fallback
sed -i "" "s/VERSION_21/VERSION_17/g" app/capacitor.build.gradle 
sed -i "" "s/VERSION_21/VERSION_17/g" capacitor-cordova-android-plugins/build.gradle

echo "✅ Java version fixed, building APK..."

# Build APK
./gradlew assembleDebug

echo "🚀 APK built successfully! You can now run the app in Android Studio."
echo "   APK location: android/app/build/outputs/apk/debug/app-debug.apk" 