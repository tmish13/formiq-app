import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'io.formiq.app',
  appName: 'FormIQ',
  webDir: 'build',
  server: {
    hostname: 'app',
    androidScheme: 'file',
    iosScheme: 'file',
    allowNavigation: ['*']
  },
  android: {
    allowMixedContent: true,
    captureInput: true,
    webContentsDebuggingEnabled: true,
    backgroundColor: '#F7FAFC',
    overrideUserAgent: 'FormIQ-Android',
    appendUserAgent: 'FormIQ-Android',
    initialFocus: false,
    buildOptions: {
      keystorePath: undefined,
      keystorePassword: undefined,
      keystoreAlias: undefined,
      keystoreAliasPassword: undefined,
      releaseType: undefined,
      signingType: undefined
    }
  },
  plugins: {
    SplashScreen: {
      launchShowDuration: 3000,
      launchAutoHide: true,
      backgroundColor: "#4D7CFE",
      androidSplashResourceName: "splash",
      androidScaleType: "CENTER_CROP",
      showSpinner: true,
      spinnerColor: "#ffffff",
      splashFullScreen: true,
      splashImmersive: true
    },
    StatusBar: {
      style: "DARK",
      backgroundColor: "#FFFFFF",
      overlaysWebView: false
    },
    Camera: {
      promptLabelHeader: 'Camera Access',
      promptLabelCancel: 'Cancel',
      promptLabelPhoto: 'Record Exercise',
      promptLabelPicture: 'Record Video'
    },
    CapacitorHttp: {
      enabled: true
    },
    Network: {
      displayOfflineBanner: true
    },
    Preferences: {
      group: 'FormIQStorageGroup'
    }
  },
  ios: {
    scheme: 'App',
    limitsNavigationsToAppBoundDomains: true,
    contentInset: 'never',
    backgroundColor: '#ffffff',
    preferredContentMode: 'mobile',
    allowsLinkPreview: false,
    scrollEnabled: true,
    overrideUserAgent: 'FormIQ-iOS',
    appendUserAgent: 'FormIQ-iOS',
    buildOptions: {
      signingStyle: "automatic",
      exportMethod: "app-store",
      signingCertificate: undefined,
      provisioningProfile: undefined
    }
  }
};

export default config;
