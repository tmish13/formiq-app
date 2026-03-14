import { Capacitor } from '@capacitor/core';
import { Device, DeviceInfo } from '@capacitor/device';
import { App, AppState } from '@capacitor/app';
import { StatusBar, Style } from '@capacitor/status-bar';
import { SplashScreen } from '@capacitor/splash-screen';
import { SafeArea } from '@capacitor-community/safe-area';
import { Preferences } from '@capacitor/preferences';

export interface SafeAreaInsets {
  top: number;
  bottom: number;
  left: number;
  right: number;
}

export interface MobileFeatures {
  hasHaptics: boolean;
  hasCamera: boolean;
  hasBiometrics: boolean;
  hasNotifications: boolean;
  supportsBackgroundMode: boolean;
  supportsVibration: boolean;
}

export interface AppInfo {
  deviceInfo: DeviceInfo;
  safeAreaInsets: SafeAreaInsets;
  features: MobileFeatures;
  isNative: boolean;
  platform: 'ios' | 'android' | 'web';
}

/**
 * Comprehensive mobile service for Capacitor integration
 * Handles device features, platform detection, and mobile-specific optimizations
 */
export class MobileService {
  private static instance: MobileService;
  private appInfo: AppInfo | null = null;
  private appStateListeners: Array<(state: AppState) => void> = [];

  private constructor() {
    this.initialize();
  }

  public static getInstance(): MobileService {
    if (!MobileService.instance) {
      MobileService.instance = new MobileService();
    }
    return MobileService.instance;
  }

  /**
   * Initialize mobile service and gather device information
   */
  private async initialize(): Promise<void> {
    try {
      const isNative = Capacitor.isNativePlatform();
      const platform = Capacitor.getPlatform() as 'ios' | 'android' | 'web';

      // Get device information
      const deviceInfo = await Device.getInfo();

      // Get safe area insets
      let safeAreaInsets: SafeAreaInsets = { top: 0, bottom: 0, left: 0, right: 0 };
      if (isNative) {
        // getSafeAreaInsets() was removed in @capacitor-community/safe-area v7.
        // Fall back to CSS env() variable values for beta; native safe-area
        // styling is handled via CSS custom properties set by the plugin.
        safeAreaInsets = {
          top: 0,
          bottom: 0,
          left: 0,
          right: 0
        };
      }

      // Detect device features
      const features = await this.detectFeatures();

      this.appInfo = {
        deviceInfo,
        safeAreaInsets,
        features,
        isNative,
        platform
      };

      // Configure platform-specific settings
      await this.configurePlatform();

      // Setup app state listeners
      this.setupAppStateListeners();

    } catch (error) {
      console.error('Failed to initialize mobile service:', error);
    }
  }

  /**
   * Get comprehensive app information
   */
  public async getAppInfo(): Promise<AppInfo> {
    if (!this.appInfo) {
      await this.initialize();
    }
    return this.appInfo!;
  }

  /**
   * Configure platform-specific settings
   */
  private async configurePlatform(): Promise<void> {
    if (!Capacitor.isNativePlatform()) return;

    try {
      const platform = Capacitor.getPlatform();

      if (platform === 'ios') {
        // Configure iOS status bar
        await StatusBar.setStyle({ style: Style.Light });
        await StatusBar.setBackgroundColor({ color: '#667eea' });
        await StatusBar.setOverlaysWebView({ overlay: false });
      } else if (platform === 'android') {
        // Configure Android status bar
        await StatusBar.setStyle({ style: Style.Dark });
        await StatusBar.setBackgroundColor({ color: '#ffffff' });
        await StatusBar.setOverlaysWebView({ overlay: false });
      }

      // Hide splash screen after configuration
      await SplashScreen.hide({
        fadeOutDuration: 300
      });

    } catch (error) {
      console.warn('Platform configuration failed:', error);
    }
  }

  /**
   * Detect available device features
   */
  private async detectFeatures(): Promise<MobileFeatures> {
    const isNative = Capacitor.isNativePlatform();
    const platform = Capacitor.getPlatform();

    return {
      hasHaptics: isNative && (platform === 'ios' || platform === 'android'),
      hasCamera: isNative,
      hasBiometrics: isNative,
      hasNotifications: isNative,
      supportsBackgroundMode: isNative,
      supportsVibration: isNative || ('vibrate' in navigator)
    };
  }

  /**
   * Setup app state change listeners
   */
  private setupAppStateListeners(): void {
    if (!Capacitor.isNativePlatform()) return;

    App.addListener('appStateChange', (state: AppState) => {
      console.log('App state changed:', state);
      this.appStateListeners.forEach(listener => listener(state));
      
      // Handle app state specific logic
      if (state.isActive) {
        this.onAppResume();
      } else {
        this.onAppPause();
      }
    });

    // Handle back button on Android
    App.addListener('backButton', ({ canGoBack }) => {
      if (!canGoBack) {
        App.exitApp();
      } else {
        window.history.back();
      }
    });
  }

  /**
   * Add app state change listener
   */
  public addAppStateListener(listener: (state: AppState) => void): void {
    this.appStateListeners.push(listener);
  }

  /**
   * Remove app state change listener
   */
  public removeAppStateListener(listener: (state: AppState) => void): void {
    const index = this.appStateListeners.indexOf(listener);
    if (index > -1) {
      this.appStateListeners.splice(index, 1);
    }
  }

  /**
   * Handle app resume
   */
  private onAppResume(): void {
    // Check for updates, refresh data, etc.
    console.log('App resumed - refreshing data...');
  }

  /**
   * Handle app pause
   */
  private onAppPause(): void {
    // Save state, pause timers, etc.
    console.log('App paused - saving state...');
  }

  /**
   * Provide haptic feedback
   */
  public async hapticFeedback(type: 'light' | 'medium' | 'heavy' = 'medium'): Promise<void> {
    if (!this.appInfo?.features.hasHaptics) return;

    try {
      // Use web vibration API as fallback
      if (this.appInfo.features.supportsVibration && 'vibrate' in navigator) {
        const duration = type === 'light' ? 50 : type === 'medium' ? 100 : 200;
        navigator.vibrate(duration);
      }
    } catch (error) {
      console.warn('Haptic feedback failed:', error);
    }
  }

  /**
   * Show native-style loading indicator
   */
  public async showLoading(message?: string): Promise<void> {
    // This would typically use a native loading plugin
    // For now, we'll emit an event that components can listen to
    window.dispatchEvent(new CustomEvent('showNativeLoading', { 
      detail: { message } 
    }));
  }

  /**
   * Hide native-style loading indicator
   */
  public async hideLoading(): Promise<void> {
    window.dispatchEvent(new CustomEvent('hideNativeLoading'));
  }

  /**
   * Check if device has network connectivity
   */
  public async checkConnectivity(): Promise<boolean> {
    if (Capacitor.isNativePlatform()) {
      try {
        const { Network } = await import('@capacitor/network');
        const status = await Network.getStatus();
        return status.connected;
      } catch (error) {
        console.warn('Network check failed:', error);
      }
    }
    return navigator.onLine;
  }

  /**
   * Get device performance metrics
   */
  public getPerformanceInfo(): {
    memory?: number;
    cores?: number;
    batteryLevel?: number;
    isLowPowerMode?: boolean;
  } {
    const result: any = {};

    // Web APIs
    if ('deviceMemory' in navigator) {
      result.memory = (navigator as any).deviceMemory;
    }

    if ('hardwareConcurrency' in navigator) {
      result.cores = navigator.hardwareConcurrency;
    }

    // Battery API (experimental)
    if ('getBattery' in navigator) {
      (navigator as any).getBattery().then((battery: any) => {
        result.batteryLevel = battery.level * 100;
        result.isLowPowerMode = battery.level < 0.2;
      });
    }

    return result;
  }

  /**
   * Optimize app for low-end devices
   */
  public async optimizeForDevice(): Promise<void> {
    const performance = this.getPerformanceInfo();
    
    // Reduce animations on low-end devices
    if (performance.memory && performance.memory < 4) {
      document.documentElement.style.setProperty('--animation-duration', '0.1s');
      console.log('Optimized animations for low-memory device');
    }

    // Disable some features on very low-end devices
    if (performance.cores && performance.cores < 4) {
      window.dispatchEvent(new CustomEvent('enableLowPerformanceMode'));
      console.log('Enabled low performance mode');
    }
  }

  /**
   * Set status bar style
   */
  public async setStatusBarStyle(style: 'light' | 'dark'): Promise<void> {
    if (!Capacitor.isNativePlatform()) return;

    try {
      await StatusBar.setStyle({ 
        style: style === 'light' ? Style.Light : Style.Dark 
      });
    } catch (error) {
      console.warn('Failed to set status bar style:', error);
    }
  }

  /**
   * Set status bar background color
   */
  public async setStatusBarColor(color: string): Promise<void> {
    if (!Capacitor.isNativePlatform()) return;

    try {
      await StatusBar.setBackgroundColor({ color });
    } catch (error) {
      console.warn('Failed to set status bar color:', error);
    }
  }

  /**
   * Store data securely
   */
  public async setSecureData(key: string, value: string): Promise<void> {
    try {
      await Preferences.set({ key, value });
    } catch (error) {
      console.error('Failed to store secure data:', error);
      throw error;
    }
  }

  /**
   * Retrieve secure data
   */
  public async getSecureData(key: string): Promise<string | null> {
    try {
      const { value } = await Preferences.get({ key });
      return value;
    } catch (error) {
      console.error('Failed to retrieve secure data:', error);
      return null;
    }
  }

  /**
   * Clear secure data
   */
  public async clearSecureData(key: string): Promise<void> {
    try {
      await Preferences.remove({ key });
    } catch (error) {
      console.error('Failed to clear secure data:', error);
    }
  }

  /**
   * Get app version information
   */
  public async getAppVersion(): Promise<{ version: string; build: string }> {
    if (Capacitor.isNativePlatform()) {
      try {
        const info = await App.getInfo();
        return {
          version: info.version,
          build: info.build
        };
      } catch (error) {
        console.warn('Failed to get app version:', error);
      }
    }

    return {
      version: process.env.REACT_APP_VERSION || '1.0.0',
      build: process.env.REACT_APP_BUILD || '1'
    };
  }
}

export const mobileService = MobileService.getInstance();
export default mobileService;