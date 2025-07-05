import { Capacitor } from '@capacitor/core';
import { mobileService } from './mobileService';

export interface NotificationPayload {
  title: string;
  body: string;
  data?: Record<string, any>;
  badge?: number;
  sound?: string;
  icon?: string;
  image?: string;
  tag?: string;
  actions?: NotificationAction[];
}

export interface NotificationAction {
  action: string;
  title: string;
  icon?: string;
}

export interface NotificationPermissionStatus {
  receive: 'granted' | 'denied' | 'prompt';
}

export interface ScheduledNotification {
  id: number;
  title: string;
  body: string;
  schedule: {
    at?: Date;
    repeats?: boolean;
    every?: 'minute' | 'hour' | 'day' | 'week' | 'month' | 'year';
    count?: number;
    on?: {
      weekday?: number; // 1-7, Sunday = 1
      hour?: number;    // 0-23
      minute?: number;  // 0-59
    };
  };
  extra?: Record<string, any>;
}

/**
 * Enhanced push notification service for mobile platforms
 */
export class PushNotificationService {
  private static instance: PushNotificationService;
  private isInitialized = false;
  private permissionStatus: NotificationPermissionStatus | null = null;
  private notificationQueue: NotificationPayload[] = [];

  private constructor() {}

  public static getInstance(): PushNotificationService {
    if (!PushNotificationService.instance) {
      PushNotificationService.instance = new PushNotificationService();
    }
    return PushNotificationService.instance;
  }

  /**
   * Initialize push notification service
   */
  public async initialize(): Promise<boolean> {
    if (this.isInitialized) return true;

    try {
      if (Capacitor.isNativePlatform()) {
        await this.initializeNative();
      } else {
        await this.initializeWeb();
      }

      this.isInitialized = true;
      return true;
    } catch (error) {
      console.error('Failed to initialize push notifications:', error);
      return false;
    }
  }

  /**
   * Initialize native push notifications
   */
  private async initializeNative(): Promise<void> {
    try {
      // This would use @capacitor/push-notifications plugin
      // For now, we'll set up the basic structure
      console.log('Initializing native push notifications');
      
      // Register for push notifications
      // await PushNotifications.register();

      // Setup listeners
      this.setupNativeListeners();
      
    } catch (error) {
      console.error('Native push notification initialization failed:', error);
    }
  }

  /**
   * Initialize web push notifications
   */
  private async initializeWeb(): Promise<void> {
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
      throw new Error('Push notifications not supported');
    }

    try {
      // Register service worker
      const registration = await navigator.serviceWorker.register('/sw.js');
      console.log('Service worker registered:', registration);

      // Setup web push
      this.setupWebListeners();
      
    } catch (error) {
      console.error('Web push notification initialization failed:', error);
    }
  }

  /**
   * Setup native push notification listeners
   */
  private setupNativeListeners(): void {
    // This would set up listeners for the @capacitor/push-notifications plugin
    /*
    PushNotifications.addListener('registration', (token) => {
      console.log('Push registration success, token: ' + token.value);
      this.onTokenReceived(token.value);
    });

    PushNotifications.addListener('registrationError', (error) => {
      console.error('Error on registration: ' + JSON.stringify(error));
    });

    PushNotifications.addListener('pushNotificationReceived', (notification) => {
      console.log('Push received: ' + JSON.stringify(notification));
      this.onNotificationReceived(notification);
    });

    PushNotifications.addListener('pushNotificationActionPerformed', (action) => {
      console.log('Push action performed: ' + JSON.stringify(action));
      this.onNotificationAction(action);
    });
    */
  }

  /**
   * Setup web push notification listeners
   */
  private setupWebListeners(): void {
    // Listen for messages from service worker
    navigator.serviceWorker.addEventListener('message', (event) => {
      if (event.data && event.data.type === 'NOTIFICATION_CLICKED') {
        this.onNotificationAction(event.data.payload);
      }
    });
  }

  /**
   * Request notification permissions
   */
  public async requestPermissions(): Promise<NotificationPermissionStatus> {
    try {
      if (Capacitor.isNativePlatform()) {
        // Use native permissions
        return await this.requestNativePermissions();
      } else {
        // Use web permissions
        return await this.requestWebPermissions();
      }
    } catch (error) {
      console.error('Failed to request notification permissions:', error);
      return { receive: 'denied' };
    }
  }

  /**
   * Request native notification permissions
   */
  private async requestNativePermissions(): Promise<NotificationPermissionStatus> {
    try {
      // This would use the native plugin
      /*
      const status = await PushNotifications.checkPermissions();
      
      if (status.receive === 'prompt') {
        const result = await PushNotifications.requestPermissions();
        this.permissionStatus = { receive: result.receive };
      } else {
        this.permissionStatus = { receive: status.receive };
      }
      */
      
      // Mock response for now
      this.permissionStatus = { receive: 'granted' };
      return this.permissionStatus;
    } catch (error) {
      console.error('Native permission request failed:', error);
      return { receive: 'denied' };
    }
  }

  /**
   * Request web notification permissions
   */
  private async requestWebPermissions(): Promise<NotificationPermissionStatus> {
    try {
      const permission = await Notification.requestPermission();
      this.permissionStatus = { 
        receive: permission as 'granted' | 'denied' | 'prompt' 
      };
      return this.permissionStatus;
    } catch (error) {
      console.error('Web permission request failed:', error);
      return { receive: 'denied' };
    }
  }

  /**
   * Check current permission status
   */
  public async checkPermissions(): Promise<NotificationPermissionStatus> {
    if (this.permissionStatus) {
      return this.permissionStatus;
    }

    try {
      if (Capacitor.isNativePlatform()) {
        // Check native permissions
        // const status = await PushNotifications.checkPermissions();
        // this.permissionStatus = { receive: status.receive };
        this.permissionStatus = { receive: 'granted' }; // Mock
      } else {
        // Check web permissions
        this.permissionStatus = { 
          receive: Notification.permission as 'granted' | 'denied' | 'prompt'
        };
      }

      return this.permissionStatus;
    } catch (error) {
      console.error('Permission check failed:', error);
      return { receive: 'denied' };
    }
  }

  /**
   * Send local notification
   */
  public async sendLocalNotification(payload: NotificationPayload): Promise<boolean> {
    const permissions = await this.checkPermissions();
    
    if (permissions.receive !== 'granted') {
      console.warn('Notification permissions not granted');
      return false;
    }

    try {
      if (Capacitor.isNativePlatform()) {
        return await this.sendNativeNotification(payload);
      } else {
        return await this.sendWebNotification(payload);
      }
    } catch (error) {
      console.error('Failed to send notification:', error);
      return false;
    }
  }

  /**
   * Send native notification
   */
  private async sendNativeNotification(payload: NotificationPayload): Promise<boolean> {
    try {
      // This would use the native plugin
      /*
      await LocalNotifications.schedule({
        notifications: [{
          title: payload.title,
          body: payload.body,
          id: Date.now(),
          extra: payload.data,
          iconColor: '#667eea',
          sound: payload.sound,
          largeIcon: payload.icon,
          largeBody: payload.body,
          summaryText: payload.title
        }]
      });
      */
      
      console.log('Native notification sent:', payload.title);
      return true;
    } catch (error) {
      console.error('Native notification failed:', error);
      return false;
    }
  }

  /**
   * Send web notification
   */
  private async sendWebNotification(payload: NotificationPayload): Promise<boolean> {
    try {
      const notification = new Notification(payload.title, {
        body: payload.body,
        icon: payload.icon || '/icon-192.png',
        image: payload.image,
        badge: '/icon-badge.png',
        data: payload.data,
        tag: payload.tag,
        requireInteraction: true,
        actions: payload.actions
      });

      // Auto-close after 5 seconds if not interacted with
      setTimeout(() => notification.close(), 5000);

      notification.onclick = () => {
        this.onNotificationAction({ notification: payload, action: 'tap' });
        notification.close();
      };

      return true;
    } catch (error) {
      console.error('Web notification failed:', error);
      return false;
    }
  }

  /**
   * Schedule notification
   */
  public async scheduleNotification(notification: ScheduledNotification): Promise<boolean> {
    try {
      if (Capacitor.isNativePlatform()) {
        return await this.scheduleNativeNotification(notification);
      } else {
        return await this.scheduleWebNotification(notification);
      }
    } catch (error) {
      console.error('Failed to schedule notification:', error);
      return false;
    }
  }

  /**
   * Schedule native notification
   */
  private async scheduleNativeNotification(notification: ScheduledNotification): Promise<boolean> {
    try {
      // This would use the LocalNotifications plugin
      console.log('Scheduling native notification:', notification.title);
      return true;
    } catch (error) {
      console.error('Native notification scheduling failed:', error);
      return false;
    }
  }

  /**
   * Schedule web notification
   */
  private async scheduleWebNotification(notification: ScheduledNotification): Promise<boolean> {
    try {
      // Use setTimeout for simple scheduling
      if (notification.schedule.at) {
        const delay = notification.schedule.at.getTime() - Date.now();
        if (delay > 0) {
          setTimeout(() => {
            this.sendLocalNotification({
              title: notification.title,
              body: notification.body,
              data: notification.extra
            });
          }, delay);
          return true;
        }
      }
      
      return false;
    } catch (error) {
      console.error('Web notification scheduling failed:', error);
      return false;
    }
  }

  /**
   * Cancel scheduled notification
   */
  public async cancelNotification(id: number): Promise<boolean> {
    try {
      if (Capacitor.isNativePlatform()) {
        // Cancel native notification
        console.log('Canceling native notification:', id);
      } else {
        // Cancel web notification (limited functionality)
        console.log('Canceling web notification:', id);
      }
      return true;
    } catch (error) {
      console.error('Failed to cancel notification:', error);
      return false;
    }
  }

  /**
   * Get pending notifications
   */
  public async getPendingNotifications(): Promise<ScheduledNotification[]> {
    try {
      if (Capacitor.isNativePlatform()) {
        // Get native pending notifications
        return [];
      } else {
        // Web has limited support for this
        return [];
      }
    } catch (error) {
      console.error('Failed to get pending notifications:', error);
      return [];
    }
  }

  /**
   * Handle notification received
   */
  private onNotificationReceived(notification: any): void {
    console.log('Notification received:', notification);
    
    // Trigger haptic feedback
    mobileService.hapticFeedback('light');
    
    // Emit event for app to handle
    window.dispatchEvent(new CustomEvent('notificationReceived', {
      detail: notification
    }));
  }

  /**
   * Handle notification action
   */
  private onNotificationAction(action: any): void {
    console.log('Notification action:', action);
    
    // Trigger haptic feedback
    mobileService.hapticFeedback('medium');
    
    // Emit event for app to handle
    window.dispatchEvent(new CustomEvent('notificationAction', {
      detail: action
    }));
  }

  /**
   * Handle push token received
   */
  private onTokenReceived(token: string): void {
    console.log('Push token received:', token);
    
    // Send token to backend
    this.sendTokenToBackend(token);
  }

  /**
   * Send push token to backend
   */
  private async sendTokenToBackend(token: string): Promise<void> {
    try {
      // This would send the token to your backend
      const response = await fetch('/api/push-tokens', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ token })
      });
      
      if (response.ok) {
        console.log('Push token registered with backend');
      }
    } catch (error) {
      console.error('Failed to register push token:', error);
    }
  }

  /**
   * Create workout reminder notifications
   */
  public async scheduleWorkoutReminders(): Promise<void> {
    const reminders = [
      {
        id: 1,
        title: 'Time for your workout! 💪',
        body: 'Don\'t forget to check your form with FormIQ',
        schedule: {
          repeats: true,
          every: 'day' as const,
          on: { hour: 18, minute: 0 } // 6 PM daily
        }
      },
      {
        id: 2,
        title: 'Weekly Progress Check 📊',
        body: 'See how your form has improved this week!',
        schedule: {
          repeats: true,
          every: 'week' as const,
          on: { weekday: 1, hour: 10, minute: 0 } // Sunday 10 AM
        }
      }
    ];

    for (const reminder of reminders) {
      await this.scheduleNotification(reminder);
    }
  }
}

export const pushNotificationService = PushNotificationService.getInstance();
export default pushNotificationService;