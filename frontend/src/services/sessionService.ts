import { AuthTokens } from '../types/auth';

interface SessionData {
  [key: string]: any;
}

class SessionService {
  private readonly TOKEN_KEY = 'auth_tokens';
  private readonly SESSION_KEY = 'session_data';
  private readonly EXPIRY_KEY = 'session_expiry';
  private readonly SESSION_DURATION = 24 * 60 * 60 * 1000; // 24 hours

  // Token Management
  public getTokens(): AuthTokens | null {
    const tokens = localStorage.getItem(this.TOKEN_KEY);
    return tokens ? JSON.parse(tokens) : null;
  }

  public setTokens(tokens: AuthTokens): void {
    localStorage.setItem(this.TOKEN_KEY, JSON.stringify(tokens));
    this.refreshSessionExpiry();
  }

  public clearTokens(): void {
    localStorage.removeItem(this.TOKEN_KEY);
  }

  // Session Data Management
  public getSessionData<T = SessionData>(): T | null {
    const data = localStorage.getItem(this.SESSION_KEY);
    return data ? JSON.parse(data) : null;
  }

  public setSessionData(data: SessionData): void {
    localStorage.setItem(this.SESSION_KEY, JSON.stringify(data));
    this.refreshSessionExpiry();
  }

  public updateSessionData(data: Partial<SessionData>): void {
    const currentData = this.getSessionData() || {};
    this.setSessionData({ ...currentData, ...data });
  }

  public clearSessionData(): void {
    localStorage.removeItem(this.SESSION_KEY);
  }

  // Session Expiry Management
  private refreshSessionExpiry(): void {
    const expiry = Date.now() + this.SESSION_DURATION;
    localStorage.setItem(this.EXPIRY_KEY, expiry.toString());
  }

  public isSessionExpired(): boolean {
    const expiry = localStorage.getItem(this.EXPIRY_KEY);
    if (!expiry) return true;
    return Date.now() > parseInt(expiry, 10);
  }

  // Session Cleanup
  public clearSession(): void {
    this.clearTokens();
    this.clearSessionData();
    localStorage.removeItem(this.EXPIRY_KEY);
  }

  // Session Validation
  public validateSession(): boolean {
    if (this.isSessionExpired()) {
      this.clearSession();
      return false;
    }

    const tokens = this.getTokens();
    if (!tokens) {
      this.clearSession();
      return false;
    }

    this.refreshSessionExpiry();
    return true;
  }

  // Activity Tracking
  private lastActivity: number = Date.now();
  private readonly INACTIVITY_THRESHOLD = 30 * 60 * 1000; // 30 minutes

  public updateLastActivity(): void {
    this.lastActivity = Date.now();
    this.refreshSessionExpiry();
  }

  public isInactive(): boolean {
    return Date.now() - this.lastActivity > this.INACTIVITY_THRESHOLD;
  }

  // Initialize activity tracking
  public initActivityTracking(): void {
    window.addEventListener('mousemove', () => this.updateLastActivity());
    window.addEventListener('keypress', () => this.updateLastActivity());
    window.addEventListener('click', () => this.updateLastActivity());
    window.addEventListener('scroll', () => this.updateLastActivity());

    // Check for inactivity every minute
    setInterval(() => {
      if (this.isInactive()) {
        this.clearSession();
        window.location.href = '/login';
      }
    }, 60 * 1000);
  }
}

export const sessionService = new SessionService(); 