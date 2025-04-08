#!/bin/bash

for gradle_file in node_modules/@capacitor/*/android/build.gradle
do
  echo "Updating $gradle_file"
  sed -i "" "s/sourceCompatibility JavaVersion.VERSION_21/sourceCompatibility JavaVersion.VERSION_11/g" "$gradle_file"
  sed -i "" "s/targetCompatibility JavaVersion.VERSION_21/targetCompatibility JavaVersion.VERSION_11/g" "$gradle_file"
  sed -i "" "s/sourceCompatibility JavaVersion.VERSION_20/sourceCompatibility JavaVersion.VERSION_11/g" "$gradle_file"
  sed -i "" "s/targetCompatibility JavaVersion.VERSION_20/targetCompatibility JavaVersion.VERSION_11/g" "$gradle_file"
  sed -i "" "s/sourceCompatibility JavaVersion.VERSION_17/sourceCompatibility JavaVersion.VERSION_11/g" "$gradle_file"
  sed -i "" "s/targetCompatibility JavaVersion.VERSION_17/targetCompatibility JavaVersion.VERSION_11/g" "$gradle_file"
done 