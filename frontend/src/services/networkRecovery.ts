import { EventEmitter } from 'events';
import { storageService } from './storageService';

interface PendingRequest {
  id: string;
  url: string;
  method: string;
  body?: any;
  headers: Record<string, string>;
  timestamp: number;
  retryCount: number;
}

export class NetworkRecoveryService extends EventEmitter {
  private static instance: NetworkRecoveryService;
  private isOnline: boolean = navigator.onLine;
  private pendingRequests: PendingRequest[] = [];
  private readonly MAX_RETRIES = 3;
  private readonly RETRY_DELAY = 5000; // 5 seconds
  private readonly STORAGE_KEY = 'pending_requests';

  private constructor() {
    super();
    this.initialize();
  }

  public static getInstance(): NetworkRecoveryService {
    if (!NetworkRecoveryService.instance) {
      NetworkRecoveryService.instance = new NetworkRecoveryService();
    }
    return NetworkRecoveryService.instance;
  }

  private initialize(): void {
    window.addEventListener('online', this.handleOnline);
    window.addEventListener('offline', this.handleOffline);
    this.loadPendingRequests();
  }

  private handleOnline = async (): Promise<void> => {
    this.isOnline = true;
    this.emit('online');
    await this.processPendingRequests();
  };

  private handleOffline = (): void => {
    this.isOnline = false;
    this.emit('offline');
  };

  private async loadPendingRequests(): Promise<void> {
    try {
      const saved = await storageService.get(this.STORAGE_KEY);
      if (saved) {
        this.pendingRequests = JSON.parse(saved);
      }
    } catch (error) {
      console.error('Error loading pending requests:', error);
    }
  }

  private async savePendingRequests(): Promise<void> {
    try {
      await storageService.set(this.STORAGE_KEY, JSON.stringify(this.pendingRequests));
    } catch (error) {
      console.error('Error saving pending requests:', error);
    }
  }

  public async queueRequest(request: Omit<PendingRequest, 'id' | 'timestamp' | 'retryCount'>): Promise<void> {
    const pendingRequest: PendingRequest = {
      ...request,
      id: Math.random().toString(36).substring(7),
      timestamp: Date.now(),
      retryCount: 0
    };

    this.pendingRequests.push(pendingRequest);
    await this.savePendingRequests();
    this.emit('request-queued', pendingRequest);

    if (this.isOnline) {
      await this.processPendingRequests();
    }
  }

  private async processPendingRequests(): Promise<void> {
    if (!this.isOnline || this.pendingRequests.length === 0) return;

    const requests = [...this.pendingRequests];
    this.pendingRequests = [];
    await this.savePendingRequests();

    for (const request of requests) {
      try {
        await this.executeRequest(request);
      } catch (error) {
        if (request.retryCount < this.MAX_RETRIES) {
          request.retryCount++;
          this.pendingRequests.push(request);
          await this.savePendingRequests();
          await new Promise(resolve => setTimeout(resolve, this.RETRY_DELAY));
        } else {
          this.emit('request-failed', { request, error });
        }
      }
    }
  }

  private async executeRequest(request: PendingRequest): Promise<void> {
    const response = await fetch(request.url, {
      method: request.method,
      headers: request.headers,
      body: request.body ? JSON.stringify(request.body) : undefined
    });

    if (!response.ok) {
      throw new Error(`Request failed with status ${response.status}`);
    }

    this.emit('request-completed', request);
  }

  public getQueuedRequests(): PendingRequest[] {
    return [...this.pendingRequests];
  }

  public async clearQueue(): Promise<void> {
    this.pendingRequests = [];
    await this.savePendingRequests();
    this.emit('queue-cleared');
  }

  public isNetworkOnline(): boolean {
    return this.isOnline;
  }

  public destroy(): void {
    window.removeEventListener('online', this.handleOnline);
    window.removeEventListener('offline', this.handleOffline);
  }
}

export const networkRecoveryService = NetworkRecoveryService.getInstance(); 