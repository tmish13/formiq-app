import { StorageService } from './storageService';
import { MonitoringService } from './monitoringService';

export interface ErrorDetails {
  code: string;
  message: string;
  timestamp: number;
  context?: Record<string, any>;
  stack?: string;
  componentStack?: string;
  severity: 'error' | 'warning' | 'info';
  handled: boolean;
  source: 'client' | 'network' | 'server';
}

export interface ErrorReport {
  id: string;
  error: ErrorDetails;
  userAgent: string;
  deviceInfo: Record<string, any>;
  appVersion: string;
  url: string;
}

export class ErrorHandlingService {
  private static instance: ErrorHandlingService;
  private storage: StorageService;
  private monitoring: MonitoringService;
  private readonly MAX_STORED_ERRORS = 100;
  private errorListeners: Array<(error: ErrorDetails) => void> = [];

  private constructor() {
    this.storage = StorageService.getInstance();
    this.monitoring = MonitoringService.getInstance();
    this.initializeErrorHandlers();
  }

  public static getInstance(): ErrorHandlingService {
    if (!ErrorHandlingService.instance) {
      ErrorHandlingService.instance = new ErrorHandlingService();
    }
    return ErrorHandlingService.instance;
  }

  private initializeErrorHandlers(): void {
    // Handle uncaught errors
    window.onerror = (message, source, lineno, colno, error) => {
      this.handleError(error || new Error(message as string), {
        source: 'client',
        context: { source, lineno, colno }
      });
    };

    // Handle unhandled promise rejections
    window.onunhandledrejection = (event) => {
      this.handleError(event.reason, {
        source: 'client',
        context: { type: 'unhandled_promise' }
      });
    };
  }

  public handleError(
    error: Error | string,
    options: {
      severity?: ErrorDetails['severity'];
      source?: ErrorDetails['source'];
      context?: Record<string, any>;
      handled?: boolean;
    } = {}
  ): void {
    const errorDetails: ErrorDetails = {
      code: this.getErrorCode(error),
      message: typeof error === 'string' ? error : error.message,
      timestamp: Date.now(),
      stack: error instanceof Error ? error.stack : undefined,
      severity: options.severity || 'error',
      source: options.source || 'client',
      context: options.context,
      handled: options.handled || false
    };

    // Track error in monitoring (trackError accepts string | Error; pass message + context)
    this.monitoring.trackError(errorDetails.message, errorDetails.context);

    // Store error for later analysis
    this.storeError(errorDetails);

    // Notify error listeners
    this.notifyErrorListeners(errorDetails);

    // Log error for development
    if (process.env.NODE_ENV === 'development') {
      console.error('Error handled:', errorDetails);
    }

    // Handle critical errors
    if (this.isCriticalError(errorDetails)) {
      this.handleCriticalError(errorDetails);
    }
  }

  private getErrorCode(error: Error | string): string {
    if (error instanceof Error) {
      // Extract error code from known error types
      if ('code' in error) {
        return (error as any).code;
      }
      return error.name;
    }
    return 'UNKNOWN_ERROR';
  }

  private async storeError(error: ErrorDetails): Promise<void> {
    try {
      const storedErrors = JSON.parse(
        await this.storage.get('error_history') || '[]'
      );

      // Add new error and limit array size
      storedErrors.unshift(error);
      if (storedErrors.length > this.MAX_STORED_ERRORS) {
        storedErrors.pop();
      }

      await this.storage.set('error_history', JSON.stringify(storedErrors));
    } catch (storageError) {
      console.error('Failed to store error:', storageError);
    }
  }

  private notifyErrorListeners(error: ErrorDetails): void {
    this.errorListeners.forEach(listener => {
      try {
        listener(error);
      } catch (listenerError) {
        console.error('Error in error listener:', listenerError);
      }
    });
  }

  private isCriticalError(error: ErrorDetails): boolean {
    return (
      error.severity === 'error' &&
      (error.code.startsWith('FATAL_') ||
        error.message.includes('OutOfMemory') ||
        error.message.includes('QuotaExceeded'))
    );
  }

  private handleCriticalError(error: ErrorDetails): void {
    // Log critical error
    console.error('Critical error detected:', error);

    // Send immediate alert
    this.monitoring.sendAlert({
      type: 'critical_error',
      message: error.message,
      severity: 'error',
      details: { ...error },
    });

    // Attempt recovery
    this.attemptRecovery(error);
  }

  private async attemptRecovery(error: ErrorDetails): Promise<void> {
    try {
      // Clear problematic cache/storage if quota exceeded
      if (error.message.includes('QuotaExceeded')) {
        await this.clearNonEssentialStorage();
      }

      // Reload app if fatal error
      if (error.code.startsWith('FATAL_')) {
        window.location.reload();
      }
    } catch (recoveryError) {
      console.error('Recovery attempt failed:', recoveryError);
    }
  }

  private async clearNonEssentialStorage(): Promise<void> {
    try {
      const keysToPreserve = ['auth_token', 'user_settings'];
      const allKeys = await this.storage.keys();
      
      for (const key of allKeys) {
        if (!keysToPreserve.includes(key)) {
          await this.storage.remove(key);
        }
      }
    } catch (error) {
      console.error('Failed to clear storage:', error);
    }
  }

  public addErrorListener(listener: (error: ErrorDetails) => void): () => void {
    this.errorListeners.push(listener);
    return () => {
      this.errorListeners = this.errorListeners.filter(l => l !== listener);
    };
  }

  public async getErrorHistory(): Promise<ErrorDetails[]> {
    try {
      return JSON.parse(await this.storage.get('error_history') || '[]');
    } catch (error) {
      console.error('Failed to get error history:', error);
      return [];
    }
  }

  public async clearErrorHistory(): Promise<void> {
    try {
      await this.storage.remove('error_history');
    } catch (error) {
      console.error('Failed to clear error history:', error);
    }
  }

  public generateErrorReport(error: ErrorDetails): ErrorReport {
    return {
      id: crypto.randomUUID(),
      error,
      userAgent: navigator.userAgent,
      deviceInfo: {
        platform: navigator.platform,
        language: navigator.language,
        cookiesEnabled: navigator.cookieEnabled,
        onLine: navigator.onLine,
        screenSize: {
          width: window.screen.width,
          height: window.screen.height
        }
      },
      appVersion: process.env.REACT_APP_VERSION || 'unknown',
      url: window.location.href
    };
  }
}

export const errorHandlingService = ErrorHandlingService.getInstance(); 