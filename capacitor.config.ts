import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'io.formiq.app',
  appName: 'FormIQ',
  webDir: 'build',
  bundledWebRuntime: false,
  server: {
    hostname: 'localhost',
    androidScheme: 'http',
    iosScheme: 'http',
    cleartext: true
  },
  splashScreen: {
    launchShowDuration: 2000,
    launchAutoHide: true,
    backgroundColor: '#4D7CFE',
    androidSplashResourceName: 'splash',
    androidScaleType: 'CENTER_CROP',
    showSpinner: false,
    splashFullScreen: true,
    splashImmersive: true,
    layoutName: 'launch_screen',
    iosSplashResourceName: 'Splash'
  },
  android: {
    allowMixedContent: true,
    captureInput: true,
    webContentsDebuggingEnabled: true,
    backgroundColor: '#F7FAFC',
    overrideUserAgent: 'FormIQ-Android',
    appendUserAgent: 'FormIQ-Android',
    permissions: [
      "android.permission.CAMERA",
      "android.permission.READ_EXTERNAL_STORAGE",
      "android.permission.WRITE_EXTERNAL_STORAGE",
      "android.permission.INTERNET",
      "android.permission.ACCESS_NETWORK_STATE"
    ],
    initialFocus: false,
    buildOptions: {
      keystorePath: null,
      keystorePassword: null,
      keystoreAlias: null,
      keystoreAliasPassword: null,
      releaseType: null,
      signingType: null,
      javaVersion: '17'
    }
  },
  ios: {
    contentInset: 'always',
    allowsLinkPreview: true,
    scrollEnabled: true,
    backgroundColor: '#F7FAFC',
    overrideUserAgent: 'FormIQ-iOS',
    appendUserAgent: 'FormIQ-iOS',
    limitsNavigationsToAppBoundDomains: true,
    handleApplicationNotifications: true,
    preferredContentMode: 'mobile'
  }
};

export default config; 