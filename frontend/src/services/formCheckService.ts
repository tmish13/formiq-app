import apiService, { endpoints } from './apiService';
import { FormCheck, ExerciseType, FormCheckStatus } from '../types/formCheck';

export class FormCheckService {
  private static instance: FormCheckService | null = null;
  private baseUrl = '/form-checks';

  private constructor() {}

  public static getInstance(): FormCheckService {
    if (!FormCheckService.instance) {
      FormCheckService.instance = new FormCheckService();
    }
    return FormCheckService.instance;
  }

  async getFormChecks(): Promise<FormCheck[]> {
    const response = await apiService.get<FormCheck[]>(this.baseUrl);
    return response.data;
  }

  async getFormCheck(id: string): Promise<FormCheck> {
    const response = await apiService.get<FormCheck>(`${this.baseUrl}/${id}`);
    return response.data;
  }

  async createFormCheck(formCheckData: Partial<FormCheck>): Promise<FormCheck> {
    const response = await apiService.post<FormCheck>(this.baseUrl, formCheckData);
    return response.data;
  }

  async updateFormCheck(id: string, formCheckData: Partial<FormCheck>): Promise<FormCheck> {
    const response = await apiService.put<FormCheck>(`${this.baseUrl}/${id}`, formCheckData);
    return response.data;
  }

  async deleteFormCheck(id: number | string): Promise<void> {
    await apiService.delete(`${this.baseUrl}/${id}`);
  }

  async getFormChecksByExerciseType(exerciseType: ExerciseType): Promise<FormCheck[]> {
    const response = await apiService.get<FormCheck[]>(`${this.baseUrl}/exercise/${exerciseType}`);
    return response.data;
  }

  async getLatestFormChecks(limit: number = 5): Promise<FormCheck[]> {
    const response = await apiService.get<FormCheck[]>(`${this.baseUrl}/latest`, {
      params: { limit }
    });
    return response.data;
  }

  async updateFormCheckStatus(id: string, status: FormCheckStatus): Promise<FormCheck> {
    const response = await apiService.patch<FormCheck>(`${this.baseUrl}/${id}/status`, { status });
    return response.data;
  }

  // Add the missing methods needed by the useFormCheck hook
  async uploadVideo(
    video: File, 
    exerciseType: ExerciseType, 
    onProgress?: (progress: number) => void
  ): Promise<FormCheck> {
    const formData = new FormData();
    formData.append('video', video);
    formData.append('exerciseType', exerciseType);

    const response = await apiService.post<FormCheck>(`${this.baseUrl}/upload`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress(progress);
        }
      }
    });
    
    return response.data;
  }

  async analyze(id: string): Promise<FormCheck> {
    const response = await apiService.post<FormCheck>(`${this.baseUrl}/${id}/analyze`);
    return response.data;
  }

  async getHistory(): Promise<FormCheck[]> {
    const response = await apiService.get<FormCheck[]>(`${this.baseUrl}/history`);
    return response.data;
  }

  // ML-specific methods

  async getMLAnalysis(id: string): Promise<{
    ml_scores?: {
      posture_score: number;
      stability_score: number;
      depth_score: number;
      confidence?: number;
    };
    pose_data?: any[];
    detected_issues?: any[];
  }> {
    const response = await apiService.get(`${this.baseUrl}/${id}/ml-analysis`);
    return response.data;
  }

  async getReferencePose(exerciseType: ExerciseType): Promise<any> {
    const response = await apiService.get(endpoints.exercises.referencePose(exerciseType));
    return response.data;
  }

  async exportAnalysisFrame(id: string, frameIndex: number): Promise<Blob> {
    const response = await apiService.get(`${this.baseUrl}/${id}/export-frame/${frameIndex}`, {
      responseType: 'blob'
    });
    return response.data;
  }

  async getFormCheckComparison(currentId: string, previousId: string): Promise<{
    current: FormCheck;
    previous: FormCheck;
    improvements: {
      posture_improvement: number;
      stability_improvement: number;
      depth_improvement: number;
      overall_improvement: number;
    };
  }> {
    const response = await apiService.get(`${this.baseUrl}/compare/${currentId}/${previousId}`);
    return response.data;
  }

  async getMLModelInfo(): Promise<{
    version: string;
    supported_exercises: string[];
    confidence_threshold: number;
    last_updated: string;
  }> {
    const response = await apiService.get(endpoints.ml.modelInfo);
    return response.data;
  }

  async requestMLReanalysis(id: string): Promise<FormCheck> {
    const response = await apiService.post<FormCheck>(`${this.baseUrl}/${id}/reanalyze`);
    return response.data;
  }

  // Analytics methods that utilize apiService for enhanced analytics
  async getAnalyticsOverview(timeRange?: string): Promise<{
    totalSessions: number;
    averageScore: number;
    bestExercise: string | null;
    weeklyProgress: number;
    improvementRate: number;
  }> {
    try {
      return await apiService.getAnalyticsOverview(timeRange);
    } catch (error) {
      // Fallback to calculating from form checks if backend analytics not available
      console.warn('Backend analytics not available, using fallback calculation');
      const formChecks = await this.getFormChecks();
      return this.calculateAnalyticsOverview(formChecks, timeRange);
    }
  }

  async getExerciseStatistics(timeRange?: string) {
    try {
      return await apiService.getExerciseStats(timeRange);
    } catch (error) {
      console.warn('Backend exercise stats not available, using fallback calculation');
      const formChecks = await this.getFormChecks();
      return this.calculateExerciseStats(formChecks, timeRange);
    }
  }

  async getTimeSeriesAnalytics(timeRange?: string) {
    try {
      return await apiService.getTimeSeriesData(timeRange);
    } catch (error) {
      console.warn('Backend time series data not available, using fallback calculation');
      const formChecks = await this.getFormChecks();
      return this.calculateTimeSeriesData(formChecks, timeRange);
    }
  }

  async exportAnalytics(format: 'csv' | 'json' | 'pdf', timeRange?: string): Promise<Blob> {
    try {
      return await apiService.exportAnalyticsData(format, timeRange);
    } catch (error) {
      console.warn('Backend export not available, generating client-side export');
      const formChecks = await this.getFormChecks();
      return this.generateClientSideExport(formChecks, format, timeRange);
    }
  }

  // Fallback calculation methods for when backend analytics are not available
  private calculateAnalyticsOverview(formChecks: FormCheck[], timeRange?: string): {
    totalSessions: number;
    averageScore: number;
    bestExercise: string | null;
    weeklyProgress: number;
    improvementRate: number;
  } {
    const filteredChecks = this.filterByTimeRange(formChecks, timeRange);
    const completedChecks = filteredChecks.filter(fc => fc.status === 'completed' && fc.score);

    const totalSessions = completedChecks.length;
    const averageScore = totalSessions > 0 
      ? completedChecks.reduce((sum, fc) => sum + (fc.score || 0), 0) / totalSessions 
      : 0;

    // Calculate best exercise
    const exerciseAvgs: Record<string, { total: number; count: number }> = {};
    completedChecks.forEach(fc => {
      if (!exerciseAvgs[fc.exercise_type]) {
        exerciseAvgs[fc.exercise_type] = { total: 0, count: 0 };
      }
      exerciseAvgs[fc.exercise_type].total += fc.score || 0;
      exerciseAvgs[fc.exercise_type].count += 1;
    });

    let bestExercise: string | null = null;
    let bestAvg = 0;
    Object.entries(exerciseAvgs).forEach(([exercise, { total, count }]) => {
      const avg = total / count;
      if (avg > bestAvg) {
        bestAvg = avg;
        bestExercise = exercise;
      }
    });

    return {
      totalSessions,
      averageScore,
      bestExercise,
      weeklyProgress: this.calculateWeeklyProgress(formChecks),
      improvementRate: this.calculateImprovementRate(formChecks)
    };
  }

  private calculateExerciseStats(formChecks: FormCheck[], timeRange?: string) {
    const filteredChecks = this.filterByTimeRange(formChecks, timeRange);
    const exerciseGroups: Record<string, FormCheck[]> = {};

    filteredChecks.forEach(fc => {
      if (!exerciseGroups[fc.exercise_type]) {
        exerciseGroups[fc.exercise_type] = [];
      }
      exerciseGroups[fc.exercise_type].push(fc);
    });

    return Object.entries(exerciseGroups).map(([exerciseType, checks]) => {
      const completedChecks = checks.filter(fc => fc.status === 'completed' && fc.score);
      const scores = completedChecks.map(fc => fc.score || 0);

      const improvement = this.calculateExerciseImprovement(completedChecks);
      const trend = this.calculateExerciseTrend(improvement);
      
      return {
        exercise_type: exerciseType,
        count: completedChecks.length,
        avg_score: scores.length > 0 ? scores.reduce((sum, s) => sum + s, 0) / scores.length : 0,
        best_score: scores.length > 0 ? Math.max(...scores) : 0,
        improvement,
        trend
      };
    });
  }

  private calculateTimeSeriesData(formChecks: FormCheck[], timeRange?: string) {
    const filteredChecks = this.filterByTimeRange(formChecks, timeRange);
    const dailyData: Record<string, {
      date: string;
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
          date,
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

    return Object.values(dailyData).map(day => ({
      date: day.date,
      overall_score: day.scores.length > 0 ? day.scores.reduce((sum, s) => sum + s, 0) / day.scores.length : 0,
      posture_score: day.posture_scores.length > 0 ? day.posture_scores.reduce((sum, s) => sum + s, 0) / day.posture_scores.length : 0,
      stability_score: day.stability_scores.length > 0 ? day.stability_scores.reduce((sum, s) => sum + s, 0) / day.stability_scores.length : 0,
      depth_score: day.depth_scores.length > 0 ? day.depth_scores.reduce((sum, s) => sum + s, 0) / day.depth_scores.length : 0,
      session_count: day.session_count
    })).sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());
  }

  private filterByTimeRange(formChecks: FormCheck[], timeRange?: string): FormCheck[] {
    if (!timeRange) return formChecks;

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

  private async generateClientSideExport(formChecks: FormCheck[], format: 'csv' | 'json' | 'pdf', timeRange?: string): Promise<Blob> {
    const filteredChecks = this.filterByTimeRange(formChecks, timeRange);

    switch (format) {
      case 'json':
        const jsonData = JSON.stringify(filteredChecks, null, 2);
        return new Blob([jsonData], { type: 'application/json' });
      
      case 'csv':
        const csvHeader = 'Date,Exercise Type,Score,Posture Score,Stability Score,Depth Score,Status\n';
        const csvRows = filteredChecks.map(fc => 
          `${fc.created_at},${fc.exercise_type},${fc.score || ''},${fc.posture_score || ''},${fc.stability_score || ''},${fc.depth_score || ''},${fc.status}`
        ).join('\n');
        return new Blob([csvHeader + csvRows], { type: 'text/csv' });
      
      case 'pdf':
        // For PDF, we'll just return a text blob for now since PDF generation requires additional dependencies
        const textData = `FormIQ Analytics Report\n\nTotal Sessions: ${filteredChecks.length}\n\n` +
          filteredChecks.map(fc => 
            `${fc.created_at} - ${fc.exercise_type} - Score: ${fc.score || 'N/A'}`
          ).join('\n');
        return new Blob([textData], { type: 'text/plain' });
      
      default:
        throw new Error(`Unsupported export format: ${format}`);
    }
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

  private average(numbers: number[]): number {
    return numbers.length > 0 ? numbers.reduce((sum, n) => sum + n, 0) / numbers.length : 0;
  }
}

export const formCheckService = FormCheckService.getInstance(); 