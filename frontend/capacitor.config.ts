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
      signingType: null
    }
  },
  plugins: {
    SplashScreen: {
      launchShowDuration: 3000,
      launchAutoHide: true,
      backgroundColor: '#4D7CFE',
      androidSplashResourceName: 'splash',
      androidScaleType: 'CENTER_CROP',
      showSpinner: true,
      spinnerColor: '#ffffff',
      splashFullScreen: true,
      splashImmersive: true
    },
    Camera: {
      promptLabelHeader: 'Access Camera',
      promptLabelCancel: 'Cancel',
      promptLabelPhoto: 'Take Photo',
      promptLabelPicture: 'Take Video'
    },
    CapacitorHttp: {
      enabled: true
    },
    Network: {
      displayOfflineBanner: false
    },
    Storage: {
      group: 'FormIQStorageGroup'
    },
    PWA: {
      enabled: true,
      autoUpdate: true,
      splashScreenEnabled: true,
      splashScreenIconSize: '128px',
      registerServiceWorker: true,
      showReloadPrompt: true
    },
  },
  ios: {
    contentInset: 'automatic',
    allowsLinkPreview: true,
    scrollEnabled: true,
    backgroundColor: '#F7FAFC',
    overrideUserAgent: 'FormIQ-iOS',
    appendUserAgent: 'FormIQ-iOS',
    limitsNavigationsToAppBoundDomains: true,
    preferredContentMode: 'mobile',
    usesFSKComponents: true
  },
  cordova: {},
  web: {
    allowFileAccess: true,
    useNativeNetwork: true
  }
};

export default config;
