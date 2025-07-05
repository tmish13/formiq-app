import { io, Socket } from 'socket.io-client';
import { EventEmitter } from 'events';

// WebSocket event types
export interface WebSocketEvents {
  // Connection events
  connect: () => void;
  disconnect: (reason: string) => void;
  reconnect: (attemptNumber: number) => void;
  reconnect_failed: () => void;
  
  // Video processing events
  processing_status: (data: ProcessingStatusData) => void;
  analysis_progress: (data: AnalysisProgressData) => void;
  processing_complete: (data: ProcessingCompleteData) => void;
  processing_error: (data: ProcessingErrorData) => void;
  
  // Real-time form feedback events
  form_feedback: (data: FormFeedbackData) => void;
  pose_detection: (data: PoseDetectionData) => void;
  ml_scores_update: (data: MLScoresUpdateData) => void;
  
  // General events
  error: (error: Error) => void;
  status_change: (status: ConnectionStatus) => void;
}

// Data interfaces
export interface ProcessingStatusData {
  videoId: string;
  status: 'uploading' | 'processing' | 'analyzing' | 'completed' | 'failed';
  progress: number;
  message: string;
  estimatedTimeRemaining?: number;
}

export interface AnalysisProgressData {
  videoId: string;
  stage: 'pose_detection' | 'ml_analysis' | 'feedback_generation';
  progress: number;
  frameCount: number;
  processedFrames: number;
  currentFrame?: number;
}

export interface ProcessingCompleteData {
  videoId: string;
  analysisId: string;
  overallScore: number;
  mlScores: {
    posture_score: number;
    stability_score: number;
    depth_score: number;
    confidence: number;
  };
  feedbackItems: Array<{
    id: string;
    type: 'error' | 'warning' | 'success' | 'info';
    title: string;
    description: string;
    timestamp: number;
  }>;
}

export interface ProcessingErrorData {
  videoId: string;
  error: string;
  code: string;
  recoverable: boolean;
  retryAfter?: number;
}

export interface FormFeedbackData {
  sessionId: string;
  timestamp: number;
  feedback: {
    type: 'posture' | 'stability' | 'depth' | 'general';
    severity: 'info' | 'warning' | 'error';
    message: string;
    suggestion: string;
    position?: {
      x: number;
      y: number;
    };
  };
}

export interface PoseDetectionData {
  sessionId: string;
  timestamp: number;
  keypoints: Array<{
    x: number;
    y: number;
    z?: number;
    visibility: number;
    name: string;
  }>;
  confidence: number;
  boundingBox?: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
}

export interface MLScoresUpdateData {
  sessionId: string;
  timestamp: number;
  scores: {
    posture_score: number;
    stability_score: number;
    depth_score: number;
    overall_score: number;
    confidence: number;
  };
  trends: {
    improving: boolean;
    stability: 'stable' | 'improving' | 'declining';
  };
}

export type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'reconnecting' | 'error';

interface WebSocketConfig {
  url: string;
  options?: {
    transports?: string[];
    timeout?: number;
    forceNew?: boolean;
    autoConnect?: boolean;
  };
}

/**
 * WebSocket service for real-time communication with the FormIQ backend
 * Handles authentication, reconnection, and event management
 */
class WebSocketService extends EventEmitter {
  private socket: Socket | null = null;
  private config: WebSocketConfig;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private status: ConnectionStatus = 'disconnected';
  private authToken: string | null = null;
  private subscriptions = new Map<string, Set<Function>>();
  private heartbeatInterval: NodeJS.Timeout | null = null;
  private isAuthenticated = false;

  constructor(config: WebSocketConfig) {
    super();
    this.config = {
      url: config.url,
      options: {
        transports: ['websocket', 'polling'],
        timeout: 20000,
        forceNew: false,
        autoConnect: false,
        ...config.options,
      },
    };
  }

  /**
   * Initialize and connect to the WebSocket server
   */
  async connect(authToken?: string): Promise<void> {
    if (authToken) {
      this.authToken = authToken;
    }

    if (this.socket && this.socket.connected) {
      console.warn('WebSocket already connected');
      return;
    }

    this.setStatus('connecting');

    try {
      // Create socket instance with authentication
      this.socket = io(this.config.url, {
        ...this.config.options,
        auth: {
          token: this.authToken,
        },
        extraHeaders: this.authToken ? {
          Authorization: `Bearer ${this.authToken}`,
        } : undefined,
      });

      this.setupEventListeners();
      this.socket.connect();

      // Wait for connection with timeout
      await this.waitForConnection(10000);

    } catch (error) {
      console.error('Failed to connect to WebSocket:', error);
      this.setStatus('error');
      this.emit('error', new Error(`Connection failed: ${error}`));
      throw error;
    }
  }

  /**
   * Disconnect from the WebSocket server
   */
  disconnect(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }

    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }

    this.isAuthenticated = false;
    this.setStatus('disconnected');
    this.subscriptions.clear();
  }

  /**
   * Check if WebSocket is connected and authenticated
   */
  isConnected(): boolean {
    return this.socket?.connected === true && this.isAuthenticated;
  }

  /**
   * Get current connection status
   */
  getStatus(): ConnectionStatus {
    return this.status;
  }

  /**
   * Subscribe to a specific event
   */
  subscribe<K extends keyof WebSocketEvents>(
    event: K,
    callback: WebSocketEvents[K]
  ): () => void {
    if (!this.subscriptions.has(event)) {
      this.subscriptions.set(event, new Set());
    }
    
    this.subscriptions.get(event)!.add(callback);
    this.on(event, callback as any);

    // Return unsubscribe function
    return () => {
      const callbacks = this.subscriptions.get(event);
      if (callbacks) {
        callbacks.delete(callback);
        if (callbacks.size === 0) {
          this.subscriptions.delete(event);
        }
      }
      this.off(event, callback as any);
    };
  }

  /**
   * Join a video processing room for real-time updates
   */
  joinVideoRoom(videoId: string): void {
    if (!this.isConnected()) {
      console.warn('Cannot join video room: WebSocket not connected');
      return;
    }
    
    this.socket!.emit('join_video_room', { videoId });
  }

  /**
   * Leave a video processing room
   */
  leaveVideoRoom(videoId: string): void {
    if (!this.isConnected()) {
      return;
    }
    
    this.socket!.emit('leave_video_room', { videoId });
  }

  /**
   * Join a real-time analysis session
   */
  joinAnalysisSession(sessionId: string): void {
    if (!this.isConnected()) {
      console.warn('Cannot join analysis session: WebSocket not connected');
      return;
    }
    
    this.socket!.emit('join_analysis_session', { sessionId });
  }

  /**
   * Leave a real-time analysis session
   */
  leaveAnalysisSession(sessionId: string): void {
    if (!this.isConnected()) {
      return;
    }
    
    this.socket!.emit('leave_analysis_session', { sessionId });
  }

  /**
   * Send pose data for real-time analysis
   */
  sendPoseData(sessionId: string, poseData: Omit<PoseDetectionData, 'sessionId'>): void {
    if (!this.isConnected()) {
      console.warn('Cannot send pose data: WebSocket not connected');
      return;
    }
    
    this.socket!.emit('pose_data', {
      sessionId,
      ...poseData,
    });
  }

  /**
   * Update authentication token
   */
  updateAuthToken(newToken: string): void {
    this.authToken = newToken;
    
    if (this.socket && this.socket.connected) {
      this.socket.auth = { token: newToken };
      this.socket.emit('update_auth', { token: newToken });
    }
  }

  /**
   * Setup socket event listeners
   */
  private setupEventListeners(): void {
    if (!this.socket) return;

    // Connection events
    this.socket.on('connect', () => {
      console.log('WebSocket connected');
      this.reconnectAttempts = 0;
      this.setStatus('connected');
      this.startHeartbeat();
      this.emit('connect');
    });

    this.socket.on('disconnect', (reason: string) => {
      console.log('WebSocket disconnected:', reason);
      this.isAuthenticated = false;
      this.setStatus('disconnected');
      this.stopHeartbeat();
      this.emit('disconnect', reason);
      
      // Attempt reconnection for non-intentional disconnects
      if (reason !== 'io client disconnect') {
        this.handleReconnection();
      }
    });

    this.socket.on('reconnect', (attemptNumber: number) => {
      console.log('WebSocket reconnected after', attemptNumber, 'attempts');
      this.setStatus('connected');
      this.emit('reconnect', attemptNumber);
    });

    this.socket.on('reconnect_failed', () => {
      console.error('WebSocket reconnection failed');
      this.setStatus('error');
      this.emit('reconnect_failed');
    });

    // Authentication events
    this.socket.on('authenticated', () => {
      console.log('WebSocket authenticated successfully');
      this.isAuthenticated = true;
    });

    this.socket.on('unauthorized', (error: any) => {
      console.error('WebSocket authentication failed:', error);
      this.isAuthenticated = false;
      this.emit('error', new Error(`Authentication failed: ${error.message}`));
    });

    // Processing events
    this.socket.on('processing_status', (data: ProcessingStatusData) => {
      this.emit('processing_status', data);
    });

    this.socket.on('analysis_progress', (data: AnalysisProgressData) => {
      this.emit('analysis_progress', data);
    });

    this.socket.on('processing_complete', (data: ProcessingCompleteData) => {
      this.emit('processing_complete', data);
    });

    this.socket.on('processing_error', (data: ProcessingErrorData) => {
      this.emit('processing_error', data);
    });

    // Real-time feedback events
    this.socket.on('form_feedback', (data: FormFeedbackData) => {
      this.emit('form_feedback', data);
    });

    this.socket.on('pose_detection', (data: PoseDetectionData) => {
      this.emit('pose_detection', data);
    });

    this.socket.on('ml_scores_update', (data: MLScoresUpdateData) => {
      this.emit('ml_scores_update', data);
    });

    // Error handling
    this.socket.on('error', (error: any) => {
      console.error('WebSocket error:', error);
      this.emit('error', new Error(error.message || 'WebSocket error'));
    });

    // Heartbeat response
    this.socket.on('pong', () => {
      // Heartbeat acknowledged
    });
  }

  /**
   * Handle reconnection logic
   */
  private handleReconnection(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached');
      this.setStatus('error');
      return;
    }

    this.reconnectAttempts++;
    this.setStatus('reconnecting');
    
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
    
    setTimeout(() => {
      if (this.status === 'reconnecting') {
        this.connect(this.authToken || undefined);
      }
    }, delay);
  }

  /**
   * Wait for connection to be established
   */
  private waitForConnection(timeout: number): Promise<void> {
    return new Promise((resolve, reject) => {
      if (this.socket?.connected) {
        resolve();
        return;
      }

      const timer = setTimeout(() => {
        reject(new Error('Connection timeout'));
      }, timeout);

      const onConnect = () => {
        clearTimeout(timer);
        this.socket?.off('connect', onConnect);
        this.socket?.off('connect_error', onError);
        resolve();
      };

      const onError = (error: any) => {
        clearTimeout(timer);
        this.socket?.off('connect', onConnect);
        this.socket?.off('connect_error', onError);
        reject(error);
      };

      this.socket?.on('connect', onConnect);
      this.socket?.on('connect_error', onError);
    });
  }

  /**
   * Set connection status and emit event
   */
  private setStatus(status: ConnectionStatus): void {
    if (this.status !== status) {
      this.status = status;
      this.emit('status_change', status);
    }
  }

  /**
   * Start heartbeat to keep connection alive
   */
  private startHeartbeat(): void {
    this.stopHeartbeat();
    
    this.heartbeatInterval = setInterval(() => {
      if (this.socket?.connected) {
        this.socket.emit('ping');
      }
    }, 30000); // 30 seconds
  }

  /**
   * Stop heartbeat
   */
  private stopHeartbeat(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }
}

// Create and export singleton instance
const getWebSocketUrl = (): string => {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = process.env.REACT_APP_WS_HOST || window.location.hostname;
  const port = process.env.REACT_APP_WS_PORT || (window.location.protocol === 'https:' ? '443' : '8080');
  
  return `${protocol}//${host}:${port}`;
};

export const websocketService = new WebSocketService({
  url: getWebSocketUrl(),
  options: {
    transports: ['websocket', 'polling'],
    timeout: 20000,
    autoConnect: false,
  },
});

export default websocketService;