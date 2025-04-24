import { StorageService } from './storageService';
import { EventEmitter } from 'events';

export interface PendingRequest {
  id: string;
  url: string;
  method?: string;
  body?: any;
  headers?: Record<string, string>;
  timestamp: number;
  retryCount: number;
}

export class NetworkRecoveryService {
  private static instance: NetworkRecoveryService;
  private eventEmitter: EventEmitter;
  private storageService: StorageService;
  private isOnline: boolean = true;
  private pendingRequests: PendingRequest[] = [];
  private processingQueue: boolean = false;
  private maxRetries: number = 5;
  private retryDelay: number = 5000;

  private constructor() {
    this.eventEmitter = new EventEmitter();
    this.storageService = StorageService.getInstance();
    this.initialize();
  }

  public static getInstance(): NetworkRecoveryService {
    if (!NetworkRecoveryService.instance) {
      NetworkRecoveryService.instance = new NetworkRecoveryService();
    }
    return NetworkRecoveryService.instance;
  }

  private initialize(): void {
    window.addEventListener('online', this.handleOnline.bind(this));
    window.addEventListener('offline', this.handleOffline.bind(this));
    this.loadPendingRequests();
  }

  public destroy(): void {
    window.removeEventListener('online', this.handleOnline.bind(this));
    window.removeEventListener('offline', this.handleOffline.bind(this));
    this.eventEmitter.removeAllListeners();
  }

  private async handleOnline(): Promise<void> {
    this.isOnline = true;
    this.eventEmitter.emit('online');
    await this.processQueue();
  }

  private handleOffline(): void {
    this.isOnline = false;
    this.eventEmitter.emit('offline');
  }

  public isNetworkOnline(): boolean {
    return this.isOnline;
  }

  private async loadPendingRequests(): Promise<void> {
    const storedRequests = await this.storageService.get('pending_requests');
    if (storedRequests) {
      try {
        this.pendingRequests = JSON.parse(storedRequests);
      } catch (error) {
        console.error('Error parsing stored requests:', error);
        this.pendingRequests = [];
      }
    }
  }

  public async queueRequest(request: PendingRequest | string, options: RequestInit = {}): Promise<void> {
    let pendingRequest: PendingRequest;
    
    if (typeof request === 'string') {
      pendingRequest = {
        id: Math.random().toString(36).substring(7),
        url: request,
        method: options.method || 'GET',
        body: options.body,
        headers: options.headers as Record<string, string>,
        timestamp: Date.now(),
        retryCount: 0
      };
    } else {
      pendingRequest = request;
    }

    this.pendingRequests.push(pendingRequest);
    await this.savePendingRequests();
    this.eventEmitter.emit('request-queued', pendingRequest);

    if (this.isNetworkOnline()) {
      await this.processQueue();
    }
  }

  private async processQueue(): Promise<void> {
    if (this.processingQueue || !this.isNetworkOnline() || this.pendingRequests.length === 0) {
      return;
    }

    this.processingQueue = true;

    while (this.pendingRequests.length > 0 && this.isNetworkOnline()) {
      const request = this.pendingRequests[0];
      
      try {
        const response = await fetch(request.url, {
          method: request.method,
          body: request.body ? JSON.stringify(request.body) : undefined,
          headers: request.headers
        });

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        this.pendingRequests.shift();
        this.eventEmitter.emit('request-completed', request);
      } catch (error) {
        request.retryCount++;
        
        if (request.retryCount >= this.maxRetries) {
          this.pendingRequests.shift();
          this.eventEmitter.emit('request-failed', request);
        } else {
          await new Promise(resolve => setTimeout(resolve, this.retryDelay));
        }
      }

      await this.savePendingRequests();
    }

    this.processingQueue = false;
  }

  private async savePendingRequests(): Promise<void> {
    await this.storageService.set('pending_requests', JSON.stringify(this.pendingRequests));
  }

  public async clearQueue(): Promise<void> {
    this.pendingRequests = [];
    await this.savePendingRequests();
  }

  public getQueuedRequests(): PendingRequest[] {
    return [...this.pendingRequests];
  }

  public on(event: string, listener: (...args: any[]) => void): void {
    this.eventEmitter.on(event, listener);
  }

  public off(event: string, listener: (...args: any[]) => void): void {
    this.eventEmitter.off(event, listener);
  }
}

export default NetworkRecoveryService.getInstance(); 