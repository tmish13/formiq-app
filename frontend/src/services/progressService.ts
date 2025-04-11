import { apiService } from './apiService';
import { ApiResponse } from './apiService';

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
      const response = await apiService.formAnalysis.getHistory();
      const data = (response.data as ApiResponse<ProgressData[]>).data;
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
  async getProgressStats(): Promise<ProgressStats> {
    const cacheKey = 'stats';
    
    // Check cache first
    const cached = this.getFromCache(cacheKey);
    if (cached) return cached;
    
    try {
      const response = await apiService.formAnalysis.getStats();
      const data = (response.data as ApiResponse<ProgressStats>).data;
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
      const response = await apiService.formAnalysis.saveProgress(data);
      const savedData = (response.data as ApiResponse<ProgressData>).data;
      // Invalidate cache
      this.invalidateCache();
      return savedData;
    } catch (error) {
      console.error('Error saving progress:', error);
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
      const response = await apiService.formAnalysis.getTrends(days);
      const data = (response.data as ApiResponse<Record<string, number[]>>).data;
      this.setCache(cacheKey, data);
      return data;
    } catch (error) {
      console.error('Error fetching progress trends:', error);
      throw error;
    }
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
}

export const progressService = new ProgressService(); 