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
      signingType: null,
      javaVersion: '17'
    }
  },
  // ... existing code ...
}; 