// Create a type definition for a basic API service that matches our needs for this file
interface ApiService {
  formAnalysis: {
    analyze: (data: any) => Promise<any>;
    save: (data: any) => Promise<any>;
  };
  uploads: {
    uploadVideo: (formData: FormData, progressCallback?: (progress: number) => void) => Promise<any>;
  };
}

// Import the API service and specify its type
import apiService from './apiService';
const api = apiService as unknown as ApiService;

import { EventEmitter } from 'events';

// Queue item types
export type QueueItemType = 'UPLOAD_VIDEO' | 'ANALYZE_FORM' | 'SAVE_ANALYSIS';

// Queue item priority
export type QueueItemPriority = 'high' | 'medium' | 'low';

// Queue item interface
export interface QueueItem {
  id: string;
  type: QueueItemType;
  payload: any;
  priority: QueueItemPriority;
  timestamp: number;
  retries: number;
}

/**
 * Service to handle offline operations by queueing them for later execution.
 */
class OfflineQueueService extends EventEmitter {
  private queue: QueueItem[] = [];
  private processing = false;
  private autoSyncEnabled = false;
  private onlineHandler: () => void;
  private storageKey = 'formiq_offline_queue';
  
  constructor() {
    super();
    this.loadQueueFromStorage();
    
    // Create bound handler for online event
    this.onlineHandler = this.handleOnline.bind(this);
  }
  
  /**
   * Enables automatic syncing when the device comes online.
   */
  enableAutoSync(): void {
    if (!this.autoSyncEnabled) {
      window.addEventListener('online', this.onlineHandler);
      this.autoSyncEnabled = true;
    }
  }
  
  /**
   * Disables automatic syncing.
   */
  disableAutoSync(): void {
    if (this.autoSyncEnabled) {
      window.removeEventListener('online', this.onlineHandler);
      this.autoSyncEnabled = false;
    }
  }
  
  /**
   * Handles the online event by processing the queue.
   */
  private handleOnline(): void {
    this.processQueue().catch(error => {
      console.error('Error processing queue after coming online:', error);
    });
  }
  
  /**
   * Adds an item to the queue.
   * @param item The queue item to add
   * @returns The queue item ID
   */
  async addToQueue({
    type,
    payload,
    priority = 'medium'
  }: {
    type: QueueItemType;
    payload: any;
    priority?: QueueItemPriority;
  }): Promise<string> {
    const id = `queue_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    
    const queueItem: QueueItem = {
      id,
      type,
      payload,
      priority,
      timestamp: Date.now(),
      retries: 0
    };
    
    this.queue.push(queueItem);
    this.saveQueueToStorage();
    
    this.emit('itemAdded', queueItem);
    
    // If we're online, try to process the queue immediately
    if (navigator.onLine && !this.processing) {
      this.processQueue().catch(console.error);
    }
    
    return id;
  }
  
  /**
   * Returns the current queue length.
   */
  getQueueLength(): number {
    return this.queue.length;
  }
  
  /**
   * Gets all items in the queue.
   */
  getQueueItems(): QueueItem[] {
    return [...this.queue];
  }
  
  /**
   * Removes an item from the queue by ID.
   * @param id The ID of the item to remove
   * @returns True if the item was found and removed
   */
  removeItem(id: string): boolean {
    const initialLength = this.queue.length;
    this.queue = this.queue.filter(item => item.id !== id);
    
    if (this.queue.length !== initialLength) {
      this.saveQueueToStorage();
      this.emit('itemRemoved', id);
      return true;
    }
    
    return false;
  }
  
  /**
   * Processes all items in the queue.
   */
  async processQueue(): Promise<void> {
    if (this.processing || this.queue.length === 0 || !navigator.onLine) {
      return;
    }
    
    this.processing = true;
    this.emit('syncStart', { queueLength: this.queue.length });
    
    try {
      // Sort queue by priority and timestamp
      const sortedQueue = [...this.queue].sort((a, b) => {
        const priorityValues: Record<QueueItemPriority, number> = {
          high: 3,
          medium: 2,
          low: 1
        };
        
        // First sort by priority (high to low)
        const priorityDiff = priorityValues[b.priority] - priorityValues[a.priority];
        if (priorityDiff !== 0) return priorityDiff;
        
        // Then by timestamp (oldest first)
        return a.timestamp - b.timestamp;
      });
      
      const successfulIds: string[] = [];
      const failedItems: QueueItem[] = [];
      
      // Process each item
      for (const item of sortedQueue) {
        try {
          await this.processItem(item);
          successfulIds.push(item.id);
        } catch (error) {
          console.error(`Error processing queue item ${item.id}:`, error);
          
          // Increment retry count
          item.retries += 1;
          
          if (item.retries < 3) {
            // Keep in queue for retry
            failedItems.push(item);
          } else {
            // Too many retries, emit error event but remove from queue
            this.emit('itemFailed', { item, error });
            successfulIds.push(item.id);
          }
        }
      }
      
      // Remove successful items
      successfulIds.forEach(id => this.removeItem(id));
      
      // Update queue with failed items (already included since we didn't remove them)
      this.saveQueueToStorage();
      
      if (failedItems.length > 0) {
        this.emit('syncError', { failedItems });
      } else {
        this.emit('syncComplete', { processedCount: successfulIds.length });
      }
    } catch (error) {
      console.error('Error processing queue:', error);
      this.emit('syncError', { error });
    } finally {
      this.processing = false;
    }
  }
  
  /**
   * Processes a single queue item.
   * @param item The queue item to process
   */
  private async processItem(item: QueueItem): Promise<void> {
    switch (item.type) {
      case 'UPLOAD_VIDEO':
        await this.processVideoUpload(item.payload);
        break;
      case 'ANALYZE_FORM':
        await this.processFormAnalysis(item.payload);
        break;
      case 'SAVE_ANALYSIS':
        await this.processSaveAnalysis(item.payload);
        break;
      default:
        throw new Error(`Unknown queue item type: ${(item as any).type}`);
    }
  }
  
  /**
   * Processes a video upload queue item.
   */
  private async processVideoUpload(payload: any): Promise<void> {
    const { file, exerciseType } = payload;
    
    // Create form data for the upload
    const formData = new FormData();
    formData.append('file', file);
    formData.append('exerciseType', exerciseType);
    
    // Upload the video
    const response = await apiService.uploads.uploadVideo(formData, (progress: number) => {
      this.emit('uploadProgress', { progress, exerciseType });
    });
    
    return response.data;
  }
  
  /**
   * Processes a form analysis queue item.
   */
  private async processFormAnalysis(payload: any): Promise<void> {
    const response = await apiService.formAnalysis.analyze(payload);
    return response.data;
  }
  
  /**
   * Processes a save analysis queue item.
   */
  private async processSaveAnalysis(payload: any): Promise<void> {
    const response = await apiService.formAnalysis.save(payload);
    return response.data;
  }
  
  /**
   * Loads the queue from local storage.
   */
  private loadQueueFromStorage(): void {
    try {
      const storedQueue = localStorage.getItem(this.storageKey);
      if (storedQueue) {
        this.queue = JSON.parse(storedQueue);
      }
    } catch (error) {
      console.error('Error loading offline queue from storage:', error);
      this.queue = [];
    }
  }
  
  /**
   * Saves the queue to local storage.
   */
  private saveQueueToStorage(): void {
    try {
      localStorage.setItem(this.storageKey, JSON.stringify(this.queue));
    } catch (error) {
      console.error('Error saving offline queue to storage:', error);
    }
  }
  
  /**
   * Clears the entire queue.
   */
  clearQueue(): void {
    this.queue = [];
    this.saveQueueToStorage();
    this.emit('queueCleared');
  }
}

// Create singleton instance
export const offlineQueueService = new OfflineQueueService(); 