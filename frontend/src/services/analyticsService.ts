import apiService from './apiService';
import { formCheckService } from './formCheckService';
import { videoService } from './videoService';
import { FormCheck, ExerciseType } from '../types/formCheck';

export interface AnalyticsOverview {
  totalSessions: number;
  averageScore: number;
  bestExercise: ExerciseType | null;
  weeklyProgress: number;
  improvementRate: number;
  consistency: number;
  weakestArea: 'posture' | 'stability' | 'depth' | null;
}

export interface ExerciseStatistics {
  exercise_type: ExerciseType;
  count: number;
  avg_score: number;
  best_score: number;
  improvement: number;
  trend: 'up' | 'down' | 'stable';
  last_session: string;
  consistency_score: number;
}

export interface TimeSeriesPoint {
  date: string;
  overall_score: number;
  posture_score: number;
  stability_score: number;
  depth_score: number;
  session_count: number;
  video_uploads?: number;
  weekly_average?: number;
}

export interface VideoStatistics {
  totalVideos: number;
  processedVideos: number;
  failedVideos: number;
  processingVideos: number;
  averageProcessingTime: number;
  totalStorageUsed: number;
  uploadsByExerciseType: Record<string, number>;
  dailyUploads: Array<{ date: string; count: number }>;
  successRate: number;
}

export interface VideoMetrics {
  processingMetrics: {
    averageProcessingTime: number;
    processingSuccess: number;
    processingFailure: number;
    queueLength: number;
    processedToday: number;
    processingErrors: Array<{ error: string; count: number }>;
    processingTimeByExercise: Record<string, number>;
  };
  conversionMetrics: {
    videosUploaded: number;
    formChecksCreated: number;
    conversionRate: number;
    averageTimeToCompletion: number;
    successfulAnalyses: number;
    failedAnalyses: number;
  };
  qualityMetrics: {
    averageFileSize: number;
    averageDuration: number;
    resolutionDistribution: Record<string, number>;
    formatDistribution: Record<string, number>;
    qualityScores: Array<{ quality: string; count: number }>;
    compressionRates: Array<{ original: number; compressed: number; ratio: number }>;
  };
}

export interface AnalyticsFilters {
  timeRange?: '7d' | '30d' | '90d' | '1y' | 'all';
  exerciseTypes?: ExerciseType[];
  minScore?: number;
  maxScore?: number;
  dateFrom?: string;
  dateTo?: string;
}

/**
 * Analytics Service for comprehensive workout data analysis
 * Provides enhanced analytics with backend integration and client-side fallbacks
 */
export class AnalyticsService {
  private static instance: AnalyticsService | null = null;

  private constructor() {}

  public static getInstance(): AnalyticsService {
    if (!AnalyticsService.instance) {
      AnalyticsService.instance = new AnalyticsService();
    }
    return AnalyticsService.instance;
  }

  /**
   * Get comprehensive analytics overview
   */
  async getOverview(filters?: AnalyticsFilters): Promise<AnalyticsOverview> {
    try {
      // Try backend analytics first. The API returns only 5 fields; normalize to the
      // full AnalyticsOverview shape with safe defaults for the two frontend-computed
      // fields (consistency, weakestArea) that the backend does not provide.
      const raw = await apiService.getAnalyticsOverview(filters?.timeRange);
      return {
        totalSessions: raw.totalSessions,
        averageScore: raw.averageScore,
        bestExercise: raw.bestExercise as ExerciseType | null,
        weeklyProgress: raw.weeklyProgress,
        improvementRate: raw.improvementRate,
        consistency: 0,
        weakestArea: null,
      };
    } catch (error) {
      console.warn('Backend analytics unavailable, using client-side calculation');
      return await this.calculateOverviewFromFormChecks(filters);
    }
  }

  /**
   * Get exercise-specific statistics
   */
  async getExerciseStatistics(filters?: AnalyticsFilters): Promise<ExerciseStatistics[]> {
    try {
      // Backend returns 6 fields; normalize to full ExerciseStatistics shape with
      // safe defaults for last_session and consistency_score which the backend omits.
      const raw = await apiService.getExerciseStats(filters?.timeRange);
      return raw.map(item => ({
        exercise_type: item.exercise_type as ExerciseType,
        count: item.count,
        avg_score: item.avg_score,
        best_score: item.best_score,
        improvement: item.improvement,
        trend: item.trend,
        last_session: '',
        consistency_score: 0,
      }));
    } catch (error) {
      console.warn('Backend exercise stats unavailable, using client-side calculation');
      return await this.calculateExerciseStatsFromFormChecks(filters);
    }
  }

  /**
   * Get time series data for charts
   */
  async getTimeSeriesData(filters?: AnalyticsFilters): Promise<TimeSeriesPoint[]> {
    try {
      // Try backend analytics first
      return await apiService.getTimeSeriesData(filters?.timeRange);
    } catch (error) {
      console.warn('Backend time series unavailable, using client-side calculation');
      return await this.calculateTimeSeriesFromFormChecks(filters);
    }
  }

  /**
   * Export analytics data in various formats
   */
  async exportData(format: 'csv' | 'json' | 'pdf', filters?: AnalyticsFilters): Promise<Blob> {
    try {
      return await apiService.exportAnalyticsData(format, filters?.timeRange);
    } catch (error) {
      console.warn('Backend export unavailable, generating client-side export');
      return await this.generateClientExport(format, filters);
    }
  }

  /**
   * Get video statistics
   */
  async getVideoStatistics(filters?: AnalyticsFilters): Promise<VideoStatistics> {
    return await videoService.getVideoStatistics(filters?.timeRange);
  }

  /**
   * Get comprehensive video metrics
   */
  async getVideoMetrics(filters?: AnalyticsFilters): Promise<VideoMetrics> {
    const [processingMetrics, conversionMetrics, qualityMetrics] = await Promise.all([
      videoService.getProcessingMetrics(),
      videoService.getConversionMetrics(filters?.timeRange),
      videoService.getQualityMetrics()
    ]);

    return {
      processingMetrics,
      conversionMetrics,
      qualityMetrics
    };
  }

  /**
   * Get combined analytics including video and form check data
   */
  async getCombinedAnalytics(filters?: AnalyticsFilters): Promise<{
    overview: AnalyticsOverview;
    exerciseStats: ExerciseStatistics[];
    videoStats: VideoStatistics;
    videoMetrics: VideoMetrics;
    timeSeries: TimeSeriesPoint[];
  }> {
    const [overview, exerciseStats, videoStats, videoMetrics, timeSeries] = await Promise.all([
      this.getOverview(filters),
      this.getExerciseStatistics(filters),
      this.getVideoStatistics(filters),
      this.getVideoMetrics(filters),
      this.getTimeSeriesData(filters)
    ]);

    return {
      overview,
      exerciseStats,
      videoStats,
      videoMetrics,
      timeSeries
    };
  }

  /**
   * Get performance insights and recommendations
   */
  async getInsights(filters?: AnalyticsFilters): Promise<{
    strengths: string[];
    improvements: string[];
    recommendations: string[];
    goals: string[];
    videoInsights?: {
      uploadPatterns: string[];
      processingHealth: string[];
      storageRecommendations: string[];
    };
  }> {
    const [overview, exerciseStats, videoStats] = await Promise.all([
      this.getOverview(filters),
      this.getExerciseStatistics(filters),
      this.getVideoStatistics(filters)
    ]);
    
    const insights = {
      strengths: [] as string[],
      improvements: [] as string[],
      recommendations: [] as string[],
      goals: [] as string[],
      videoInsights: {
        uploadPatterns: [] as string[],
        processingHealth: [] as string[],
        storageRecommendations: [] as string[]
      }
    };

    // Analyze strengths
    if (overview.averageScore >= 80) {
      insights.strengths.push('Excellent overall form quality');
    }
    if (overview.consistency >= 80) {
      insights.strengths.push('High workout consistency');
    }
    if (videoStats.successRate >= 90) {
      insights.strengths.push('High video processing success rate');
    }

    // Analyze improvements needed
    if (overview.averageScore < 70) {
      insights.improvements.push('Focus on improving overall form quality');
    }
    if (overview.weakestArea) {
      insights.improvements.push(`Work on ${overview.weakestArea} technique`);
    }
    if (videoStats.successRate < 80) {
      insights.improvements.push('Video processing success rate could be improved');
    }

    // Generate recommendations
    const lowScoreExercises = exerciseStats.filter(stat => stat.avg_score < 70);
    if (lowScoreExercises.length > 0) {
      insights.recommendations.push(
        `Practice ${lowScoreExercises[0].exercise_type} technique with lighter weights`
      );
    }

    // Video-specific insights
    if (videoStats.dailyUploads.length > 0) {
      const avgUploadsPerDay = videoStats.totalVideos / videoStats.dailyUploads.length;
      if (avgUploadsPerDay > 2) {
        insights.videoInsights.uploadPatterns.push('High upload frequency - great consistency!');
      } else if (avgUploadsPerDay < 0.5) {
        insights.videoInsights.uploadPatterns.push('Consider uploading more regularly for better progress tracking');
      }
    }

    if (videoStats.averageProcessingTime > 60) {
      insights.videoInsights.processingHealth.push('Processing times are longer than average - consider smaller file sizes');
    }

    const storageGB = videoStats.totalStorageUsed / (1024 * 1024 * 1024);
    if (storageGB > 5) {
      insights.videoInsights.storageRecommendations.push('Consider archiving older videos to save storage space');
    }

    // Set goals
    if (overview.averageScore < 85) {
      insights.goals.push(`Achieve ${Math.ceil(overview.averageScore / 5) * 5 + 5}% average score`);
    }
    if (videoStats.successRate < 95) {
      insights.goals.push('Achieve 95%+ video processing success rate');
    }
    
    return insights;
  }

  // Private methods for client-side calculations

  private async calculateOverviewFromFormChecks(filters?: AnalyticsFilters): Promise<AnalyticsOverview> {
    const formChecks = await formCheckService.getFormChecks();
    const filteredChecks = this.applyFilters(formChecks, filters);
    const completedChecks = filteredChecks.filter(fc => fc.status === 'completed' && fc.score);

    const totalSessions = completedChecks.length;
    const averageScore = totalSessions > 0
      ? completedChecks.reduce((sum, fc) => sum + (fc.score || 0), 0) / totalSessions
      : 0;

    // Calculate best exercise
    const exerciseAvgs = this.groupByExercise(completedChecks);
    let bestExercise: ExerciseType | null = null;
    let bestAvg = 0;

    Object.entries(exerciseAvgs).forEach(([exercise, stats]) => {
      if (stats.avgScore > bestAvg) {
        bestAvg = stats.avgScore;
        bestExercise = exercise as ExerciseType;
      }
    });

    // Calculate weakest area from ML scores
    const weakestArea = this.calculateWeakestArea(completedChecks);

    return {
      totalSessions,
      averageScore,
      bestExercise,
      weeklyProgress: this.calculateWeeklyProgress(filteredChecks),
      improvementRate: this.calculateImprovementRate(filteredChecks),
      consistency: this.calculateConsistency(filteredChecks),
      weakestArea
    };
  }

  private async calculateExerciseStatsFromFormChecks(filters?: AnalyticsFilters): Promise<ExerciseStatistics[]> {
    const formChecks = await formCheckService.getFormChecks();
    const filteredChecks = this.applyFilters(formChecks, filters);
    const exerciseGroups = this.groupByExerciseType(filteredChecks);

    return Object.entries(exerciseGroups).map(([exerciseType, checks]) => {
      const completedChecks = checks.filter(fc => fc.status === 'completed' && fc.score);
      const scores = completedChecks.map(fc => fc.score || 0);
      const lastSession = checks.length > 0 ? checks[checks.length - 1].created_at : '';

      const improvement = this.calculateExerciseImprovement(completedChecks);
      const trend = this.calculateExerciseTrend(improvement);
      
      return {
        exercise_type: exerciseType as ExerciseType,
        count: completedChecks.length,
        avg_score: scores.length > 0 ? scores.reduce((sum, s) => sum + s, 0) / scores.length : 0,
        best_score: scores.length > 0 ? Math.max(...scores) : 0,
        improvement,
        trend,
        last_session: lastSession,
        consistency_score: this.calculateExerciseConsistency(checks)
      };
    });
  }

  private async calculateTimeSeriesFromFormChecks(filters?: AnalyticsFilters): Promise<TimeSeriesPoint[]> {
    const formChecks = await formCheckService.getFormChecks();
    const filteredChecks = this.applyFilters(formChecks, filters);
    
    const dailyData: Record<string, {
      scores: number[];
      posture_scores: number[];
      stability_scores: number[];
      depth_scores: number[];
      session_count: number;
    }> = {};

    filteredChecks.forEach(fc => {
      const date = new Date(fc.created_at).toLocaleDateString();
      if (!dailyData[date]) {
        dailyData[date] = {
          scores: [],
          posture_scores: [],
          stability_scores: [],
          depth_scores: [],
          session_count: 0
        };
      }

      const dayData = dailyData[date];
      dayData.session_count += 1;

      if (fc.score) dayData.scores.push(fc.score);
      if (fc.posture_score) dayData.posture_scores.push(fc.posture_score);
      if (fc.stability_score) dayData.stability_scores.push(fc.stability_score);
      if (fc.depth_score) dayData.depth_scores.push(fc.depth_score);
    });

    return Object.entries(dailyData).map(([date, data]) => ({
      date,
      overall_score: this.average(data.scores),
      posture_score: this.average(data.posture_scores),
      stability_score: this.average(data.stability_scores),
      depth_score: this.average(data.depth_scores),
      session_count: data.session_count
    })).sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());
  }

  private async generateClientExport(format: 'csv' | 'json' | 'pdf', filters?: AnalyticsFilters): Promise<Blob> {
    const formChecks = await formCheckService.getFormChecks();
    const filteredChecks = this.applyFilters(formChecks, filters);

    switch (format) {
      case 'json':
        const jsonData = JSON.stringify({
          overview: await this.calculateOverviewFromFormChecks(filters),
          exerciseStats: await this.calculateExerciseStatsFromFormChecks(filters),
          timeSeries: await this.calculateTimeSeriesFromFormChecks(filters),
          rawData: filteredChecks
        }, null, 2);
        return new Blob([jsonData], { type: 'application/json' });

      case 'csv':
        const csvHeader = 'Date,Exercise Type,Score,Posture Score,Stability Score,Depth Score,Status,Duration\n';
        const csvRows = filteredChecks.map(fc =>
          `${fc.created_at},${fc.exercise_type},${fc.score || ''},${fc.posture_score || ''},${fc.stability_score || ''},${fc.depth_score || ''},${fc.status},${fc.processing_time || ''}`
        ).join('\n');
        return new Blob([csvHeader + csvRows], { type: 'text/csv' });

      default:
        throw new Error(`Unsupported export format: ${format}`);
    }
  }

  // Utility methods

  private applyFilters(formChecks: FormCheck[], filters?: AnalyticsFilters): FormCheck[] {
    if (!filters) return formChecks;

    let filtered = formChecks;

    // Time range filter
    if (filters.timeRange) {
      filtered = this.filterByTimeRange(filtered, filters.timeRange);
    }

    // Exercise type filter
    if (filters.exerciseTypes && filters.exerciseTypes.length > 0) {
      filtered = filtered.filter(fc => filters.exerciseTypes!.includes(fc.exercise_type));
    }

    // Score filters
    if (filters.minScore !== undefined) {
      filtered = filtered.filter(fc => (fc.score || 0) >= filters.minScore!);
    }
    if (filters.maxScore !== undefined) {
      filtered = filtered.filter(fc => (fc.score || 0) <= filters.maxScore!);
    }

    // Date range filters
    if (filters.dateFrom) {
      filtered = filtered.filter(fc => new Date(fc.created_at) >= new Date(filters.dateFrom!));
    }
    if (filters.dateTo) {
      filtered = filtered.filter(fc => new Date(fc.created_at) <= new Date(filters.dateTo!));
    }

    return filtered;
  }

  private filterByTimeRange(formChecks: FormCheck[], timeRange: string): FormCheck[] {
    const now = new Date();
    let cutoffDate: Date;

    switch (timeRange) {
      case '7d':
        cutoffDate = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
        break;
      case '30d':
        cutoffDate = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
        break;
      case '90d':
        cutoffDate = new Date(now.getTime() - 90 * 24 * 60 * 60 * 1000);
        break;
      case '1y':
        cutoffDate = new Date(now.getTime() - 365 * 24 * 60 * 60 * 1000);
        break;
      default:
        return formChecks;
    }

    return formChecks.filter(fc => new Date(fc.created_at) >= cutoffDate);
  }

  private groupByExercise(formChecks: FormCheck[]): Record<string, { avgScore: number; count: number }> {
    const groups: Record<string, { total: number; count: number }> = {};
    
    formChecks.forEach(fc => {
      if (fc.score) {
        if (!groups[fc.exercise_type]) {
          groups[fc.exercise_type] = { total: 0, count: 0 };
        }
        groups[fc.exercise_type].total += fc.score;
        groups[fc.exercise_type].count += 1;
      }
    });

    return Object.fromEntries(
      Object.entries(groups).map(([exercise, { total, count }]) => [
        exercise,
        { avgScore: total / count, count }
      ])
    );
  }

  private groupByExerciseType(formChecks: FormCheck[]): Record<string, FormCheck[]> {
    return formChecks.reduce((groups, fc) => {
      if (!groups[fc.exercise_type]) {
        groups[fc.exercise_type] = [];
      }
      groups[fc.exercise_type].push(fc);
      return groups;
    }, {} as Record<string, FormCheck[]>);
  }

  private calculateWeakestArea(formChecks: FormCheck[]): 'posture' | 'stability' | 'depth' | null {
    const mlScores = formChecks.filter(fc => fc.posture_score && fc.stability_score && fc.depth_score);
    if (mlScores.length === 0) return null;

    const avgPosture = this.average(mlScores.map(fc => fc.posture_score!));
    const avgStability = this.average(mlScores.map(fc => fc.stability_score!));
    const avgDepth = this.average(mlScores.map(fc => fc.depth_score!));

    const areas = { posture: avgPosture, stability: avgStability, depth: avgDepth };
    return Object.entries(areas).reduce((min, [area, score]) =>
      score < areas[min] ? area as 'posture' | 'stability' | 'depth' : min,
      'posture' as 'posture' | 'stability' | 'depth'
    );
  }

  private calculateConsistency(formChecks: FormCheck[]): number {
    if (formChecks.length < 2) return 0;

    // Calculate consistency based on regular session frequency
    const dates = formChecks.map(fc => new Date(fc.created_at).getTime()).sort();
    const intervals = [];
    for (let i = 1; i < dates.length; i++) {
      intervals.push(dates[i] - dates[i - 1]);
    }

    if (intervals.length === 0) return 0;

    const avgInterval = this.average(intervals);
    const stdDev = this.standardDeviation(intervals);
    
    // Lower standard deviation relative to average = higher consistency
    const consistencyScore = Math.max(0, 100 - (stdDev / avgInterval) * 100);
    return Math.min(100, consistencyScore);
  }

  private calculateExerciseConsistency(checks: FormCheck[]): number {
    if (checks.length < 2) return 0;
    
    const scores = checks.filter(fc => fc.score).map(fc => fc.score!);
    if (scores.length < 2) return 0;

    const avgScore = this.average(scores);
    const stdDev = this.standardDeviation(scores);
    
    // Lower coefficient of variation = higher consistency
    const coefficientOfVariation = stdDev / avgScore;
    return Math.max(0, 100 - coefficientOfVariation * 100);
  }

  private average(numbers: number[]): number {
    return numbers.length > 0 ? numbers.reduce((sum, n) => sum + n, 0) / numbers.length : 0;
  }

  private standardDeviation(numbers: number[]): number {
    if (numbers.length < 2) return 0;
    const avg = this.average(numbers);
    const squaredDiffs = numbers.map(n => Math.pow(n - avg, 2));
    return Math.sqrt(this.average(squaredDiffs));
  }

  private calculateWeeklyProgress(formChecks: FormCheck[]): number {
    if (formChecks.length < 2) return 0;

    const now = new Date();
    const oneWeekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
    const twoWeeksAgo = new Date(now.getTime() - 14 * 24 * 60 * 60 * 1000);

    const thisWeekChecks = formChecks.filter(fc => 
      fc.status === 'completed' && 
      fc.score && 
      new Date(fc.created_at) >= oneWeekAgo
    );
    
    const lastWeekChecks = formChecks.filter(fc => 
      fc.status === 'completed' && 
      fc.score && 
      new Date(fc.created_at) >= twoWeeksAgo && 
      new Date(fc.created_at) < oneWeekAgo
    );

    if (thisWeekChecks.length === 0 || lastWeekChecks.length === 0) return 0;

    const thisWeekAvg = this.average(thisWeekChecks.map(fc => fc.score!));
    const lastWeekAvg = this.average(lastWeekChecks.map(fc => fc.score!));

    if (lastWeekAvg === 0) return 0;
    
    return ((thisWeekAvg - lastWeekAvg) / lastWeekAvg) * 100;
  }

  private calculateImprovementRate(formChecks: FormCheck[]): number {
    if (formChecks.length < 5) return 0;

    const completedChecks = formChecks
      .filter(fc => fc.status === 'completed' && fc.score)
      .sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime());

    if (completedChecks.length < 5) return 0;

    const recentChecks = completedChecks.slice(-5);
    const earlyChecks = completedChecks.slice(0, Math.min(5, completedChecks.length - 5));

    if (earlyChecks.length === 0) return 0;

    const recentAvg = this.average(recentChecks.map(fc => fc.score!));
    const earlyAvg = this.average(earlyChecks.map(fc => fc.score!));

    if (earlyAvg === 0) return 0;

    return ((recentAvg - earlyAvg) / earlyAvg) * 100;
  }

  private calculateExerciseImprovement(checks: FormCheck[]): number {
    if (checks.length < 3) return 0;

    const sortedChecks = checks
      .filter(fc => fc.score)
      .sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime());

    if (sortedChecks.length < 3) return 0;

    const firstThird = sortedChecks.slice(0, Math.ceil(sortedChecks.length / 3));
    const lastThird = sortedChecks.slice(-Math.ceil(sortedChecks.length / 3));

    const firstAvg = this.average(firstThird.map(fc => fc.score!));
    const lastAvg = this.average(lastThird.map(fc => fc.score!));

    if (firstAvg === 0) return 0;

    return ((lastAvg - firstAvg) / firstAvg) * 100;
  }

  private calculateExerciseTrend(improvement: number): 'up' | 'down' | 'stable' {
    if (improvement > 5) return 'up';
    if (improvement < -5) return 'down';
    return 'stable';
  }
}

export const analyticsService = AnalyticsService.getInstance();
export default analyticsService;