/**
 * Authentication utilities for clearing state and debugging
 */

import { store } from '../store';
import { logout } from '../store/slices/authSlice';

/**
 * Clear all authentication data from all storage mechanisms
 * Use this for debugging or when you need a complete reset
 */
export async function clearAllAuthData(): Promise<void> {
  console.log('🧹 Clearing all authentication data...');
  
  try {
    // Clear localStorage
    const authKeys = [
      'formiq_auth_token',
      'formiq_refresh_token',
      'formiq_user_data',
      'formiq_onboarding_complete',
      'formiq_user_progress',
      'persist:root', // Redux persist key
    ];
    
    authKeys.forEach(key => {
      localStorage.removeItem(key);
      console.log(`🗑️ Removed localStorage key: ${key}`);
    });
    
    // Clear sessionStorage
    sessionStorage.clear();
    
    // Clear Capacitor Preferences (for mobile)
    try {
      const { Preferences } = await import('@capacitor/preferences');
      
      for (const key of authKeys) {
        await Preferences.remove({ key });
        console.log(`🗑️ Removed Capacitor preference: ${key}`);
      }
    } catch (e) {
      console.log('📱 Capacitor Preferences not available (web environment)');
    }
    
    // Clear Redux store
    store.dispatch(logout());
    console.log('🔄 Redux auth state cleared');
    
    console.log('✅ All authentication data cleared successfully');
    
  } catch (error) {
    console.error('❌ Error clearing auth data:', error);
  }
}

/**
 * Check if user is truly authenticated by validating token
 */
export async function isUserAuthenticated(): Promise<boolean> {
  try {
    // Check localStorage first
    const token = localStorage.getItem('formiq_auth_token');
    
    if (!token) {
      console.log('🔍 No token found in localStorage');
      return false;
    }
    
    // Validate token format and expiration
    try {
      const tokenPayload = JSON.parse(atob(token.split('.')[1]));
      const now = Date.now() / 1000;
      
      if (tokenPayload.exp && tokenPayload.exp < now) {
        console.log('⏰ Token expired, clearing auth');
        await clearAllAuthData();
        return false;
      }
      
      console.log('✅ Valid token found');
      return true;
      
    } catch (e) {
      console.log('❌ Invalid token format, clearing auth');
      await clearAllAuthData();
      return false;
    }
    
  } catch (error) {
    console.error('🔍 Error checking authentication:', error);
    return false;
  }
}

/**
 * Development utility: Add to window for debugging
 */
if (process.env.NODE_ENV === 'development') {
  (window as any).clearAllAuthData = clearAllAuthData;
  (window as any).isUserAuthenticated = isUserAuthenticated;
  console.log('🛠️ Auth debug utilities added to window: clearAllAuthData(), isUserAuthenticated()');
}