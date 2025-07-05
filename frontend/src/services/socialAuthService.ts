/**
 * Social Authentication Service
 * Handles Google and Apple sign-in integration
 */

export class SocialAuthService {
  private static instance: SocialAuthService;

  public static getInstance(): SocialAuthService {
    if (!SocialAuthService.instance) {
      SocialAuthService.instance = new SocialAuthService();
    }
    return SocialAuthService.instance;
  }

  /**
   * Initialize Google Sign-In
   */
  async initializeGoogleSignIn(): Promise<void> {
    return new Promise((resolve, reject) => {
      // Load Google Sign-In script if not already loaded
      if (!window.google) {
        const script = document.createElement('script');
        script.src = 'https://accounts.google.com/gsi/client';
        script.onload = () => {
          this.setupGoogleSignIn();
          resolve();
        };
        script.onerror = reject;
        document.head.appendChild(script);
      } else {
        this.setupGoogleSignIn();
        resolve();
      }
    });
  }

  private setupGoogleSignIn(): void {
    if (window.google) {
      window.google.accounts.id.initialize({
        client_id: process.env.REACT_APP_GOOGLE_CLIENT_ID || '',
        callback: this.handleGoogleCredentialResponse.bind(this),
      });
    }
  }

  /**
   * Handle Google sign-in response
   */
  private handleGoogleCredentialResponse(response: any): void {
    // This will be handled by the component that calls signInWithGoogle
    console.log('Google credential response:', response);
  }

  /**
   * Trigger Google Sign-In popup
   */
  async signInWithGoogle(): Promise<string> {
    return new Promise((resolve, reject) => {
      if (!window.google) {
        reject(new Error('Google Sign-In not initialized'));
        return;
      }

      window.google.accounts.id.prompt((notification: any) => {
        if (notification.isNotDisplayed() || notification.isSkippedMoment()) {
          // Fallback to one-tap or popup
          this.showGoogleOneTap(resolve, reject);
        }
      });
    });
  }

  private showGoogleOneTap(resolve: (token: string) => void, reject: (error: Error) => void): void {
    if (window.google) {
      window.google.accounts.id.renderButton(
        document.createElement('div'),
        {
          theme: 'outline',
          size: 'large',
          type: 'standard',
        }
      );

      // For now, we'll simulate the response
      // In a real implementation, you'd handle the actual Google response
      setTimeout(() => {
        // This is a placeholder - in real implementation, you'd get the actual credential
        resolve('google_mock_token');
      }, 1000);
    }
  }

  /**
   * Initialize Apple Sign-In
   */
  async initializeAppleSignIn(): Promise<void> {
    return new Promise((resolve, reject) => {
      // Load Apple Sign-In script if not already loaded
      if (!window.AppleID) {
        const script = document.createElement('script');
        script.src = 'https://appleid.cdn-apple.com/appleauth/static/jsapi/appleid/1/en_US/appleid.auth.js';
        script.onload = () => {
          this.setupAppleSignIn();
          resolve();
        };
        script.onerror = reject;
        document.head.appendChild(script);
      } else {
        this.setupAppleSignIn();
        resolve();
      }
    });
  }

  private setupAppleSignIn(): void {
    if (window.AppleID) {
      window.AppleID.auth.init({
        clientId: process.env.REACT_APP_APPLE_CLIENT_ID || '',
        scope: 'name email',
        redirectURI: window.location.origin + '/auth/apple/callback',
        state: 'apple_auth_state',
        usePopup: true,
      });
    }
  }

  /**
   * Trigger Apple Sign-In
   */
  async signInWithApple(): Promise<string> {
    return new Promise((resolve, reject) => {
      if (!window.AppleID) {
        reject(new Error('Apple Sign-In not initialized'));
        return;
      }

      window.AppleID.auth.signIn()
        .then((response: any) => {
          // Extract the ID token from the response
          resolve(response.authorization.id_token);
        })
        .catch((error: any) => {
          reject(new Error(`Apple Sign-In failed: ${error.error}`));
        });
    });
  }

  /**
   * Handle social login with redirect approach
   */
  redirectToSocialAuth(provider: 'google' | 'apple'): void {
    const baseUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000';
    
    if (provider === 'google') {
      window.location.href = `${baseUrl}/api/v1/auth/social/google/redirect`;
    } else if (provider === 'apple') {
      window.location.href = `${baseUrl}/api/v1/auth/social/apple/redirect`;
    }
  }
}

// Extend the Window interface to include Google and Apple APIs
declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: any) => void;
          prompt: (callback?: (notification: any) => void) => void;
          renderButton: (element: HTMLElement, config: any) => void;
        };
      };
    };
    AppleID?: {
      auth: {
        init: (config: any) => void;
        signIn: () => Promise<any>;
      };
    };
  }
}

export default SocialAuthService;