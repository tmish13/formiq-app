import { useState, useEffect, useCallback, useRef } from 'react';
import { websocketService, WebSocketEvents, ConnectionStatus } from '../services/websocketService';
import { useAuth } from './useAuth';

// Hook return type
export interface UseWebSocketReturn {
  isConnected: boolean;
  status: ConnectionStatus;
  error: Error | null;
  connect: () => Promise<void>;
  disconnect: () => void;
  subscribe: <K extends keyof WebSocketEvents>(
    event: K,
    callback: WebSocketEvents[K]
  ) => () => void;
  joinVideoRoom: (videoId: string) => void;
  leaveVideoRoom: (videoId: string) => void;
  joinAnalysisSession: (sessionId: string) => void;
  leaveAnalysisSession: (sessionId: string) => void;
  sendPoseData: (sessionId: string, poseData: any) => void;
}

// Configuration options
export interface UseWebSocketOptions {
  autoConnect?: boolean;
  reconnectOnAuth?: boolean;
  maxRetries?: number;
}

/**
 * React hook for WebSocket management
 * Provides connection state, event subscription, and automatic lifecycle management
 */
export const useWebSocket = (options: UseWebSocketOptions = {}): UseWebSocketReturn => {
  const {
    autoConnect = true,
    reconnectOnAuth = true,
    maxRetries = 3,
  } = options;

  const { token, isAuthenticated } = useAuth();
  const [status, setStatus] = useState<ConnectionStatus>('disconnected');
  const [error, setError] = useState<Error | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  
  const retryCount = useRef(0);
  const subscriptions = useRef<Set<() => void>>(new Set());

  /**
   * Connect to WebSocket server
   */
  const connect = useCallback(async (): Promise<void> => {
    if (!token) {
      console.warn('Cannot connect to WebSocket: No auth token available');
      return;
    }

    try {
      setError(null);
      await websocketService.connect(token);
      retryCount.current = 0;
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Connection failed');
      setError(error);
      
      // Retry logic
      if (retryCount.current < maxRetries) {
        retryCount.current++;
        const delay = Math.pow(2, retryCount.current) * 1000; // Exponential backoff
        
        setTimeout(() => {
          connect();
        }, delay);
      }
      
      throw error;
    }
  }, [token, maxRetries]);

  /**
   * Disconnect from WebSocket server
   */
  const disconnect = useCallback((): void => {
    websocketService.disconnect();
    retryCount.current = 0;
  }, []);

  /**
   * Subscribe to WebSocket events
   */
  const subscribe = useCallback(<K extends keyof WebSocketEvents>(
    event: K,
    callback: WebSocketEvents[K]
  ): (() => void) => {
    const unsubscribe = websocketService.subscribe(event, callback);
    subscriptions.current.add(unsubscribe);
    
    // Return enhanced unsubscribe that also cleans up from our local set
    return () => {
      unsubscribe();
      subscriptions.current.delete(unsubscribe);
    };
  }, []);

  /**
   * Join video processing room
   */
  const joinVideoRoom = useCallback((videoId: string): void => {
    websocketService.joinVideoRoom(videoId);
  }, []);

  /**
   * Leave video processing room
   */
  const leaveVideoRoom = useCallback((videoId: string): void => {
    websocketService.leaveVideoRoom(videoId);
  }, []);

  /**
   * Join real-time analysis session
   */
  const joinAnalysisSession = useCallback((sessionId: string): void => {
    websocketService.joinAnalysisSession(sessionId);
  }, []);

  /**
   * Leave real-time analysis session
   */
  const leaveAnalysisSession = useCallback((sessionId: string): void => {
    websocketService.leaveAnalysisSession(sessionId);
  }, []);

  /**
   * Send pose data for real-time analysis
   */
  const sendPoseData = useCallback((sessionId: string, poseData: any): void => {
    websocketService.sendPoseData(sessionId, poseData);
  }, []);

  // Setup status monitoring
  useEffect(() => {
    const unsubscribeStatus = websocketService.subscribe('status_change', (newStatus) => {
      setStatus(newStatus);
      setIsConnected(newStatus === 'connected' && websocketService.isConnected());
    });

    const unsubscribeError = websocketService.subscribe('error', (error) => {
      setError(error);
    });

    const unsubscribeConnect = websocketService.subscribe('connect', () => {
      setIsConnected(true);
      setError(null);
    });

    const unsubscribeDisconnect = websocketService.subscribe('disconnect', () => {
      setIsConnected(false);
    });

    // Set initial status
    setStatus(websocketService.getStatus());
    setIsConnected(websocketService.isConnected());

    return () => {
      unsubscribeStatus();
      unsubscribeError();
      unsubscribeConnect();
      unsubscribeDisconnect();
    };
  }, []);

  // Auto-connect on authentication
  useEffect(() => {
    if (autoConnect && isAuthenticated && token && !isConnected) {
      connect().catch(console.error);
    }
  }, [autoConnect, isAuthenticated, token, isConnected, connect]);

  // Reconnect when auth token changes
  useEffect(() => {
    if (reconnectOnAuth && token && isConnected) {
      websocketService.updateAuthToken(token);
    }
  }, [reconnectOnAuth, token, isConnected]);

  // Auto-disconnect when auth is lost
  useEffect(() => {
    if (!isAuthenticated && isConnected) {
      disconnect();
    }
  }, [isAuthenticated, isConnected, disconnect]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      // Clean up all subscriptions
      subscriptions.current.forEach(unsubscribe => unsubscribe());
      subscriptions.current.clear();
    };
  }, []);

  return {
    isConnected,
    status,
    error,
    connect,
    disconnect,
    subscribe,
    joinVideoRoom,
    leaveVideoRoom,
    joinAnalysisSession,
    leaveAnalysisSession,
    sendPoseData,
  };
};

/**
 * Hook for video processing real-time updates
 */
export const useVideoProcessing = (videoId: string | null) => {
  const { isConnected, subscribe, joinVideoRoom, leaveVideoRoom } = useWebSocket();
  const [processingStatus, setProcessingStatus] = useState<any>(null);
  const [analysisProgress, setAnalysisProgress] = useState<any>(null);
  const [processingComplete, setProcessingComplete] = useState<any>(null);
  const [processingError, setProcessingError] = useState<any>(null);

  useEffect(() => {
    if (!videoId || !isConnected) return;

    // Join the video room
    joinVideoRoom(videoId);

    // Subscribe to processing events
    const unsubscribeStatus = subscribe('processing_status', (data) => {
      if (data.videoId === videoId) {
        setProcessingStatus(data);
      }
    });

    const unsubscribeProgress = subscribe('analysis_progress', (data) => {
      if (data.videoId === videoId) {
        setAnalysisProgress(data);
      }
    });

    const unsubscribeComplete = subscribe('processing_complete', (data) => {
      if (data.videoId === videoId) {
        setProcessingComplete(data);
      }
    });

    const unsubscribeError = subscribe('processing_error', (data) => {
      if (data.videoId === videoId) {
        setProcessingError(data);
      }
    });

    return () => {
      leaveVideoRoom(videoId);
      unsubscribeStatus();
      unsubscribeProgress();
      unsubscribeComplete();
      unsubscribeError();
    };
  }, [videoId, isConnected, subscribe, joinVideoRoom, leaveVideoRoom]);

  return {
    processingStatus,
    analysisProgress,
    processingComplete,
    processingError,
    isConnected,
  };
};

/**
 * Hook for real-time form analysis
 */
export const useRealTimeAnalysis = (sessionId?: string | null) => {
  const { 
    isConnected, 
    subscribe, 
    joinAnalysisSession, 
    leaveAnalysisSession, 
    sendPoseData 
  } = useWebSocket();
  
  const [formFeedback, setFormFeedback] = useState<any[]>([]);
  const [currentPose, setCurrentPose] = useState<any>(null);
  const [mlScores, setMlScores] = useState<any>(null);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(sessionId || null);

  const startSession = useCallback((newSessionId?: string) => {
    const sessionToUse = newSessionId || `session_${Date.now()}`;
    setCurrentSessionId(sessionToUse);
    if (isConnected) {
      joinAnalysisSession(sessionToUse);
    }
  }, [isConnected, joinAnalysisSession]);

  const stopSession = useCallback(() => {
    if (currentSessionId && isConnected) {
      leaveAnalysisSession(currentSessionId);
    }
    setCurrentSessionId(null);
    setFormFeedback([]);
    setCurrentPose(null);
    setMlScores(null);
  }, [currentSessionId, isConnected, leaveAnalysisSession]);

  useEffect(() => {
    if (!currentSessionId || !isConnected) return;

    // Join the analysis session
    joinAnalysisSession(currentSessionId);

    // Subscribe to real-time events
    const unsubscribeFeedback = subscribe('form_feedback', (data) => {
      if (data.sessionId === currentSessionId) {
        setFormFeedback(prev => [...prev, data.feedback]);
      }
    });

    const unsubscribePose = subscribe('pose_detection', (data) => {
      if (data.sessionId === currentSessionId) {
        setCurrentPose(data);
      }
    });

    const unsubscribeScores = subscribe('ml_scores_update', (data) => {
      if (data.sessionId === currentSessionId) {
        setMlScores(data.scores);
      }
    });

    return () => {
      unsubscribeFeedback();
      unsubscribePose();
      unsubscribeScores();
    };
  }, [currentSessionId, isConnected, subscribe, joinAnalysisSession]);

  const submitPoseData = useCallback((poseData: any) => {
    if (currentSessionId && isConnected) {
      sendPoseData(currentSessionId, poseData);
    }
  }, [currentSessionId, isConnected, sendPoseData]);

  const clearFeedback = useCallback(() => {
    setFormFeedback([]);
  }, []);

  return {
    // Original properties
    formFeedback,
    currentPose,
    mlScores,
    isConnected,
    submitPoseData,
    clearFeedback,
    // Expected properties for component compatibility
    scores: mlScores,
    feedback: formFeedback,
    startSession,
    stopSession,
  };
};

export default useWebSocket;