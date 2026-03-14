import { storageService } from './storageService';
import networkRecoveryService from './networkRecovery';
import { FormAnalysisResult } from '../types/formAnalysis';

interface SyncQueueItem {
  id: string;
  type: 'form_analysis' | 'workout' | 'profile_update';
  data: any;
  timestamp: number;
  retryCount: number;
}

export class SyncService {
  private static instance: SyncService;
  private storage = storageService;
  private networkRecovery = networkRecoveryService;
  private syncQueue: SyncQueueItem[] = [];
  private isSyncing = false;
  private readonly MAX_RETRIES = 3;
  private readonly SYNC_INTERVAL = 5000; // 5 seconds

  private constructor() {
    this.initialize();
  }

  public static getInstance(): SyncService {
    if (!SyncService.instance) {
      SyncService.instance = new SyncService();
    }
    return SyncService.instance;
  }

  private async initialize(): Promise<void> {
    // Load pending items from storage
    const storedQueue = await this.storage.get('sync_queue');
    if (storedQueue) {
      this.syncQueue = JSON.parse(storedQueue);
    }

    // Start sync loop
    this.startSyncLoop();

    // Listen for online/offline events
    window.addEventListener('online', () => this.onNetworkStatusChange(true));
    window.addEventListener('offline', () => this.onNetworkStatusChange(false));
  }

  private async startSyncLoop(): Promise<void> {
    setInterval(async () => {
      if (navigator.onLine && !this.isSyncing && this.syncQueue.length > 0) {
        await this.processSyncQueue();
      }
    }, this.SYNC_INTERVAL);
  }

  private async onNetworkStatusChange(isOnline: boolean): Promise<void> {
    if (isOnline) {
      await this.processSyncQueue();
    }
  }

  public async queueFormAnalysis(formAnalysis: FormAnalysisResult): Promise<void> {
    const queueItem: SyncQueueItem = {
      id: crypto.randomUUID(),
      type: 'form_analysis',
      data: formAnalysis,
      timestamp: Date.now(),
      retryCount: 0
    };

    this.syncQueue.push(queueItem);
    await this.saveQueue();

    if (navigator.onLine) {
      await this.processSyncQueue();
    }
  }

  public async queueWorkout(workoutData: any): Promise<void> {
    const queueItem: SyncQueueItem = {
      id: crypto.randomUUID(),
      type: 'workout',
      data: workoutData,
      timestamp: Date.now(),
      retryCount: 0
    };

    this.syncQueue.push(queueItem);
    await this.saveQueue();

    if (navigator.onLine) {
      await this.processSyncQueue();
    }
  }

  private async processSyncQueue(): Promise<void> {
    if (this.isSyncing || this.syncQueue.length === 0) return;

    this.isSyncing = true;

    try {
      const itemsToSync = [...this.syncQueue];
      for (const item of itemsToSync) {
        try {
          await this.syncItem(item);
          // Remove successfully synced item
          this.syncQueue = this.syncQueue.filter(i => i.id !== item.id);
          await this.saveQueue();
        } catch (error) {
          console.error(`Failed to sync item ${item.id}:`, error);
          item.retryCount++;
          
          if (item.retryCount >= this.MAX_RETRIES) {
            // Remove failed item after max retries
            this.syncQueue = this.syncQueue.filter(i => i.id !== item.id);
            await this.saveQueue();
            
            // Store failed item separately for manual resolution
            await this.storeFailedSync(item);
          }
        }
      }
    } finally {
      this.isSyncing = false;
    }
  }

  private async syncItem(item: SyncQueueItem): Promise<void> {
    const request = {
      id: item.id,
      url: this.getUrlForType(item.type),
      method: 'POST',
      body: item.data,
      headers: { 'Content-Type': 'application/json' },
      timestamp: Date.now(),
      retryCount: item.retryCount
    };

    await this.networkRecovery.queueRequest(request);
  }

  private getUrlForType(type: SyncQueueItem['type']): string {
    switch (type) {
      case 'form_analysis':
        return '/api/form-analysis';
      case 'workout':
        return '/api/workouts';
      default:
        throw new Error(`Unknown sync item type: ${type}`);
    }
  }

  private async saveQueue(): Promise<void> {
    await this.storage.set('sync_queue', JSON.stringify(this.syncQueue));
  }

  private async storeFailedSync(item: SyncQueueItem): Promise<void> {
    const failedSyncs = JSON.parse(await this.storage.get('failed_syncs') || '[]');
    failedSyncs.push({
      ...item,
      failedAt: Date.now()
    });
    await this.storage.set('failed_syncs', JSON.stringify(failedSyncs));
  }

  public async getFailedSyncs(): Promise<SyncQueueItem[]> {
    return JSON.parse(await this.storage.get('failed_syncs') || '[]');
  }

  public async retryFailedSync(id: string): Promise<boolean> {
    const failedSyncs = await this.getFailedSyncs();
    const itemToRetry = failedSyncs.find(item => item.id === id);
    
    if (!itemToRetry) return false;

    // Reset retry count and add back to sync queue
    itemToRetry.retryCount = 0;
    this.syncQueue.push(itemToRetry);
    await this.saveQueue();

    // Remove from failed syncs
    await this.storage.set(
      'failed_syncs',
      JSON.stringify(failedSyncs.filter(item => item.id !== id))
    );

    if (navigator.onLine) {
      await this.processSyncQueue();
    }

    return true;
  }
}

export const syncService = SyncService.getInstance(); 