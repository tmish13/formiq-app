#!/usr/bin/env node

/**
 * Debug script to test authentication flow
 * Run this to clear all auth data and verify OAuth flow works
 */

console.log('🧪 FormIQ Authentication Flow Test');
console.log('====================================');

console.log('\n🧹 Step 1: Clear all authentication data');
console.log('Instructions:');
console.log('1. Open the app in browser or iOS simulator');
console.log('2. Open browser dev tools (F12)');
console.log('3. In console, run: clearAllAuthData()');
console.log('4. Refresh the page');
console.log('5. You should see the login page (not dashboard)');

console.log('\n🔐 Step 2: Test OAuth flow');
console.log('Instructions:');
console.log('1. Click "Continue with Google" button');
console.log('2. For web: Should open Google OAuth in new tab');
console.log('3. For mobile: Should open in-app browser with OAuth');
console.log('4. Complete OAuth flow');
console.log('5. Should redirect back to app and authenticate');

console.log('\n⚙️ Step 3: Backend OAuth endpoints needed');
console.log('Make sure backend has these endpoints:');
console.log('- GET /auth/social/google/mobile?redirect_uri=formiq://auth/callback');
console.log('- GET /auth/social/apple/mobile?redirect_uri=formiq://auth/callback');
console.log('- POST /auth/social/google (for web)');
console.log('- POST /auth/social/apple (for web)');

console.log('\n🏗️ Step 4: iOS build (if testing on device)');
console.log('After making changes, rebuild iOS app:');
console.log('cd frontend && npx cap build ios && npx cap open ios');

console.log('\n✅ Expected behavior:');
console.log('1. App opens to /auth page (not dashboard)');
console.log('2. OAuth buttons work without "Processing..." loop');
console.log('3. Successful OAuth redirects to dashboard');
console.log('4. Bottom navigation visible on all pages');

console.log('\n🐛 Debug utilities available in dev console:');
console.log('- clearAllAuthData() - Clear all auth data');
console.log('- isUserAuthenticated() - Check auth status');