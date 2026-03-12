import apiService from './apiService';

export interface AnalyticsSession {
  id: string;
  date: string;
  posture_score: number | null;
  named_scores: Record<string, number | null> | null;
  score_band: string | null;
  decision: string | null;
}

export interface AnalyticsResponse {
  sessions: AnalyticsSession[];
  trend: 'Improving' | 'Plateau' | 'Declining';
  best_score_ever: number | null;
  avg_last_5: number | null;
  improvement_since_first: number | null;
  session_count: number;
  weight_trend?: Array<{ date: string; weight_kg: number }>;
  best_weight?: number | null;
}

export interface ProgressData {
  id: string;
  userId: string;
  exerciseType: string;
  score: number;
  feedback: string[];
  riskLevel: 'low' | 'medium' | 'high';
  createdAt: string;
  videoUrl?: string;
}

export interface ProgressStats {
  averageScore: number;
  improvementRate: number;
  totalAnalyses: number;
  exerciseTypeBreakdown: Record<string, number>;
  recentTrend: 'improving' | 'stable' | 'declining';
  currentStreak: number;
}

export interface ProgressFilter {
  exerciseType?: string;
  startDate?: string;
  endDate?: string;
  limit?: number;
  offset?: number;
}

class ProgressService {
  private cache: Map<string, { data: any; timestamp: number }> = new Map();
  private readonly CACHE_DURATION = 5 * 60 * 1000; // 5 minutes

  /**
   * Get progress history with optional filtering
   */
  async getProgressHistory(filter?: ProgressFilter): Promise<ProgressData[]> {
    const cacheKey = `history-${JSON.stringify(filter)}`;

    // Check cache first
    const cached = this.getFromCache(cacheKey);
    if (cached) return cached;

    try {
      const params: Record<string, any> = {};
      if (filter?.exerciseType) params.exercise_type = filter.exerciseType;
      if (filter?.startDate) params.start_date = filter.startDate;
      if (filter?.endDate) params.end_date = filter.endDate;
      if (filter?.limit !== undefined) params.limit = filter.limit;
      if (filter?.offset !== undefined) params.offset = filter.offset;

      const response = await apiService.get<ProgressData[]>('/progress/history', { params });
      const data = response.data;
      this.setCache(cacheKey, data);
      return data;
    } catch (error) {
      console.error('Error fetching progress history:', error);
      throw error;
    }
  }

  /**
   * Get progress statistics
   */
  async getProgressStats(timeRange?: string): Promise<ProgressStats> {
    const cacheKey = `stats-${timeRange ?? 'all'}`;

    // Check cache first
    const cached = this.getFromCache(cacheKey);
    if (cached) return cached;

    try {
      const params: Record<string, any> = {};
      if (timeRange) params.time_range = timeRange;

      const response = await apiService.get<ProgressStats>('/progress/stats', { params });
      const data = response.data;
      this.setCache(cacheKey, data);
      return data;
    } catch (error) {
      console.error('Error fetching progress stats:', error);
      throw error;
    }
  }

  /**
   * Save new progress data
   */
  async saveProgress(data: Omit<ProgressData, 'id' | 'userId' | 'createdAt'>): Promise<ProgressData> {
    try {
      const response = await apiService.post<ProgressData>('/progress/save', data);
      const savedData = response.data;
      this.invalidateCache();
      return savedData;
    } catch (error) {
      console.error('Error saving progress:', error);
      throw error;
    }
  }

  /**
   * Get analytics data: last N sessions with trend via linear regression
   */
  async getAnalytics(exerciseType: string = 'squat', limit = 10): Promise<AnalyticsResponse> {
    const params = new URLSearchParams({ limit: String(limit) });
    // Always filter by exercise type — default to squat (the only supported exercise in V1)
    params.set('exercise_type', exerciseType);
    try {
      const response = await apiService.get<AnalyticsResponse>(`/progress/analytics?${params}`);
      return response.data;
    } catch (error) {
      console.error('Error fetching progress analytics:', error);
      throw error;
    }
  }

  /**
   * Get progress for a specific exercise type
   */
  async getExerciseProgress(exerciseType: string): Promise<ProgressData[]> {
    return this.getProgressHistory({ exerciseType });
  }

  /**
   * Get progress trends over time
   */
  async getProgressTrends(days: number = 30): Promise<Record<string, number[]>> {
    const cacheKey = `trends-${days}`;

    // Check cache first
    const cached = this.getFromCache(cacheKey);
    if (cached) return cached;

    try {
      const response = await apiService.get<Record<string, number[]>>('/progress/trends', { params: { days } });
      const data = response.data;
      this.setCache(cacheKey, data);
      return data;
    } catch (error) {
      console.error('Error fetching progress trends:', error);
      throw error;
    }
  }

  /**
   * Get overview data for dashboard
   */
  async getProgressOverview(): Promise<{
    currentStreak: number;
    averageScore: number;
    totalSessions: number;
    weeklyImprovement: number;
  }> {
    const cacheKey = 'overview';
    
    // Check cache first
    const cached = this.getFromCache(cacheKey);
    if (cached) return cached;
    
    try {
      // Try to get from backend first
      const response = await apiService.get<{
        currentStreak: number;
        averageScore: number;
        totalSessions: number;
        weeklyImprovement: number;
      }>('/progress/overview');
      const data = response.data;
      this.setCache(cacheKey, data);
      return data;
    } catch (error) {
      console.warn('Backend progress overview not available, calculating from stats');
      
      // Fallback: calculate from existing data
      try {
        const stats = await this.getProgressStats();
        const history = await this.getProgressHistory({ limit: 50 });
        
        const overview = {
          currentStreak: this.calculateStreak(history),
          averageScore: stats.averageScore,
          totalSessions: stats.totalAnalyses,
          weeklyImprovement: stats.improvementRate
        };
        
        this.setCache(cacheKey, overview);
        return overview;
      } catch (fallbackError) {
        console.error('Error calculating progress overview:', fallbackError);
        // Return default values
        return {
          currentStreak: 0,
          averageScore: 0,
          totalSessions: 0,
          weeklyImprovement: 0
        };
      }
    }
  }

  /**
   * Calculate current streak from progress history
   */
  private calculateStreak(history: ProgressData[]): number {
    if (history.length === 0) return 0;
    
    // Sort by date, most recent first
    const sortedHistory = history.sort((a, b) => 
      new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
    );
    
    let streak = 0;
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    
    for (const session of sortedHistory) {
      const sessionDate = new Date(session.createdAt);
      sessionDate.setHours(0, 0, 0, 0);
      
      const daysDiff = Math.floor((today.getTime() - sessionDate.getTime()) / (1000 * 60 * 60 * 24));
      
      if (daysDiff === streak) {
        streak++;
      } else if (daysDiff > streak) {
        break;
      }
    }
    
    return streak;
  }

  /**
   * Cache management methods
   */
  private getFromCache(key: string): any | null {
    const cached = this.cache.get(key);
    if (!cached) return null;
    
    // Check if cache is expired
    if (Date.now() - cached.timestamp > this.CACHE_DURATION) {
      this.cache.delete(key);
      return null;
    }
    
    return cached.data;
  }

  private setCache(key: string, data: any): void {
    this.cache.set(key, {
      data,
      timestamp: Date.now()
    });
  }

  private invalidateCache(): void {
    this.cache.clear();
  }

  /**
   * Clear all cached progress/analytics data.
   * Call this immediately after a successful video analysis so that the next
   * ProgressPage visit fetches fresh results instead of serving stale cache.
   */
  clearCache(): void {
    this.cache.clear();
  }
}

export const progressService = new ProgressService(); 