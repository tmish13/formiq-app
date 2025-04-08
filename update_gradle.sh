#!/bin/bash

# Set source compatibility to Java 17 in all build.gradle files
echo "Updating Gradle files to use Java 17..."

# Set environment variables for Java 17
export JAVA_HOME=$(/usr/libexec/java_home -v 17)
export PATH="/opt/homebrew/opt/openjdk@17/bin:$PATH"
echo "Using Java version: $(java -version 2>&1 | head -n 1)"

# Update Capacitor plugins
for gradle_file in node_modules/@capacitor/*/android/build.gradle
do
  echo "Updating $gradle_file"
  sed -i "" "s/sourceCompatibility JavaVersion.VERSION_21/sourceCompatibility JavaVersion.VERSION_17/g" "$gradle_file"
  sed -i "" "s/targetCompatibility JavaVersion.VERSION_21/targetCompatibility JavaVersion.VERSION_17/g" "$gradle_file"
  sed -i "" "s/sourceCompatibility JavaVersion.VERSION_20/sourceCompatibility JavaVersion.VERSION_17/g" "$gradle_file"
  sed -i "" "s/targetCompatibility JavaVersion.VERSION_20/targetCompatibility JavaVersion.VERSION_17/g" "$gradle_file"
  sed -i "" "s/sourceCompatibility JavaVersion.VERSION_1_8/sourceCompatibility JavaVersion.VERSION_17/g" "$gradle_file"
  sed -i "" "s/targetCompatibility JavaVersion.VERSION_1_8/targetCompatibility JavaVersion.VERSION_17/g" "$gradle_file"
done

# Update Android app
for gradle_file in android/app/capacitor.build.gradle android/capacitor-cordova-android-plugins/build.gradle android/app/build.gradle
do
  echo "Updating $gradle_file"
  sed -i "" "s/sourceCompatibility JavaVersion.VERSION_21/sourceCompatibility JavaVersion.VERSION_17/g" "$gradle_file"
  sed -i "" "s/targetCompatibility JavaVersion.VERSION_21/targetCompatibility JavaVersion.VERSION_17/g" "$gradle_file"
  sed -i "" "s/sourceCompatibility JavaVersion.VERSION_20/sourceCompatibility JavaVersion.VERSION_17/g" "$gradle_file"
  sed -i "" "s/targetCompatibility JavaVersion.VERSION_20/targetCompatibility JavaVersion.VERSION_17/g" "$gradle_file"
  sed -i "" "s/sourceCompatibility JavaVersion.VERSION_1_8/sourceCompatibility JavaVersion.VERSION_17/g" "$gradle_file"
  sed -i "" "s/targetCompatibility JavaVersion.VERSION_1_8/targetCompatibility JavaVersion.VERSION_17/g" "$gradle_file"
done

# Update or add compileOptions section to app/build.gradle if it doesn't exist
if ! grep -q "compileOptions" android/app/build.gradle; then
  echo "Adding compileOptions section to android/app/build.gradle"
  sed -i "" '/android {/a\\n    compileOptions {\n        sourceCompatibility JavaVersion.VERSION_17\n        targetCompatibility JavaVersion.VERSION_17\n    }\n' android/app/build.gradle
fi

# Update variables.gradle file to use compatible versions
echo "Updating SDK and library versions in variables.gradle..."
sed -i "" "s/compileSdkVersion = 35/compileSdkVersion = 34/g" android/variables.gradle
sed -i "" "s/targetSdkVersion = 35/targetSdkVersion = 34/g" android/variables.gradle
sed -i "" "s/androidxActivityVersion = '1.9.2'/androidxActivityVersion = '1.8.0'/g" android/variables.gradle
sed -i "" "s/androidxAppCompatVersion = '1.7.0'/androidxAppCompatVersion = '1.6.1'/g" android/variables.gradle
sed -i "" "s/androidxCoreVersion = '1.15.0'/androidxCoreVersion = '1.12.0'/g" android/variables.gradle
sed -i "" "s/androidxFragmentVersion = '1.8.4'/androidxFragmentVersion = '1.6.1'/g" android/variables.gradle
sed -i "" "s/androidxWebkitVersion = '1.12.1'/androidxWebkitVersion = '1.8.0'/g" android/variables.gradle
sed -i "" "s/androidxJunitVersion = '1.2.1'/androidxJunitVersion = '1.1.5'/g" android/variables.gradle
sed -i "" "s/androidxEspressoCoreVersion = '3.6.1'/androidxEspressoCoreVersion = '3.5.1'/g" android/variables.gradle

# Update gradle.properties for Android compatibility
echo "Updating gradle.properties for compatibility..."
if ! grep -q "android.javaCompile.suppressSourceTargetDeprecationWarning=true" android/gradle.properties; then
  echo "android.javaCompile.suppressSourceTargetDeprecationWarning=true" >> android/gradle.properties
fi
if ! grep -q "android.enableJetifier=true" android/gradle.properties; then
  echo "android.enableJetifier=true" >> android/gradle.properties
fi
if ! grep -q "android.defaults.buildfeatures.buildconfig=true" android/gradle.properties; then
  echo "android.defaults.buildfeatures.buildconfig=true" >> android/gradle.properties
fi
if ! grep -q "android.nonTransitiveRClass=false" android/gradle.properties; then
  echo "android.nonTransitiveRClass=false" >> android/gradle.properties
fi
if ! grep -q "android.nonFinalResIds=false" android/gradle.properties; then
  echo "android.nonFinalResIds=false" >> android/gradle.properties
fi

# Fix CapacitorWebView.java to avoid VANILLA_ICE_CREAM reference or Java 21 features
WEBVIEW_PATH="node_modules/@capacitor/android/capacitor/src/main/java/com/getcapacitor/CapacitorWebView.java"
if [ -f "$WEBVIEW_PATH" ]; then
  echo "Fixing CapacitorWebView.java for Java 17 compatibility..."
  cp src/main/java/com/getcapacitor/CapacitorWebView.java "$WEBVIEW_PATH" 2>/dev/null || echo "No custom CapacitorWebView.java found, skipping..."
fi

# Update root build.gradle to set Java version for all projects
echo "Updating root build.gradle with Java 17 configuration..."
# Check if the file already has Java sourceCompatibility settings
if ! grep -q "sourceCompatibility = JavaVersion.VERSION_17" android/build.gradle; then
  # Add to allprojects if it exists, else add the block
  if grep -q "allprojects {" android/build.gradle; then
    sed -i "" '/allprojects {/,/}/s/}/    \/\/ Set Java version for all projects\n    tasks.withType(JavaCompile) {\n        sourceCompatibility = JavaVersion.VERSION_17\n        targetCompatibility = JavaVersion.VERSION_17\n    }\n}/' android/build.gradle
  else
    # Add allprojects block if it doesn't exist
    cat >> android/build.gradle << 'EOL'

allprojects {
    repositories {
        google()
        mavenCentral()
    }
    
    // Set Java version for all projects
    tasks.withType(JavaCompile) {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}
EOL
  fi
fi

echo "Gradle updates completed!"

# Now run a clean build with Java 17
echo "Running clean build with Java 17..."
cd android && ./gradlew clean build --info 