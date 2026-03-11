import apiService, { endpoints } from './apiService';
import { FormCheck, ExerciseType, FormCheckStatus, MLAnalysisResponse } from '../types/formCheck';

export class FormCheckService {
  private static instance: FormCheckService | null = null;
  private baseUrl = '/form-checks';

  // Per-call fallback cache: shared across analytics methods so a single
  // backend outage triggers only one getFormChecks() fetch, not three.
  // Cleared after each top-level call chain by resetting to null.
  private _fallbackChecksCache: FormCheck[] | null = null;

  private constructor() {}

  public static getInstance(): FormCheckService {
    if (!FormCheckService.instance) {
      FormCheckService.instance = new FormCheckService();
    }
    return FormCheckService.instance;
  }

  async getFormChecks(): Promise<FormCheck[]> {
    // Backend has no bare GET /form-checks — use the history endpoint instead
    const response = await apiService.get<FormCheck[]>(`${this.baseUrl}/history`);
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

  /**
   * Submit a video file directly for form-check analysis.
   * Calls POST /form-checks/submit (multipart) — bypasses the S3 presigned-URL flow.
   */
  async submitFormCheck(
    video: File,
    exerciseName: string,
    notes?: string,
    posture_v1_mode?: 'active' | 'shadow',
    weightKg?: number,
    reps?: number,
  ): Promise<FormCheck> {
    const params = new URLSearchParams({ exercise_name: exerciseName });
    if (notes) params.append('notes', notes);
    if (posture_v1_mode) params.append('posture_v1_mode', posture_v1_mode);
    if (weightKg != null) params.append('weight_kg', String(weightKg));
    if (reps != null) params.append('reps', String(reps));

    const formData = new FormData();
    formData.append('video_upload', video);

    const response = await apiService.post<FormCheck>(
      `${this.baseUrl}/submit?${params.toString()}`,
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' }, timeout: 120000 }
    );
    return response.data;
  }

  async analyze(id: string): Promise<FormCheck> {
    const response = await apiService.post<FormCheck>(`${this.baseUrl}/${id}/analyze`);
    return response.data;
  }

  async getHistory(): Promise<FormCheck[]> {
    const response = await apiService.get<FormCheck[]>(`${this.baseUrl}/history?limit=100`);
    return response.data;
  }

  // ML-specific methods

  async getMLAnalysis(id: string): Promise<MLAnalysisResponse> {
    const response = await apiService.get<MLAnalysisResponse>(`${this.baseUrl}/${id}/ml-analysis`);
    return response.data;
  }

  async getReferencePose(exerciseType: ExerciseType): Promise<any> {
    const response = await apiService.get(endpoints.exercises.referencePose(exerciseType));
    return response.data;
  }

  async exportAnalysisFrame(id: string, frameIndex: number): Promise<Blob> {
    const response = await apiService.get<Blob>(`${this.baseUrl}/${id}/export-frame/${frameIndex}`, {
      responseType: 'blob'
    });
    return response.data;
  }

  async getFormCheckComparison(currentId: string, previousId: string): Promise<{
    current: { id: string; score: number; created_at: string; exercise_type: string | null };
    previous: { id: string; score: number; created_at: string; exercise_type: string | null };
    improvements: {
      posture_improvement: number | null;
      stability_improvement: number | null;
      depth_improvement: number | null;
      overall_improvement: number;
    };
  }> {
    const response = await apiService.get<{
      current: { id: string; score: number; created_at: string; exercise_type: string | null };
      previous: { id: string; score: number; created_at: string; exercise_type: string | null };
      improvements: {
        posture_improvement: number | null;
        stability_improvement: number | null;
        depth_improvement: number | null;
        overall_improvement: number;
      };
    }>(`${this.baseUrl}/compare/${currentId}/${previousId}`);
    return response.data;
  }

  async getMLModelInfo(): Promise<{
    version: string;
    supported_exercises: string[];
    confidence_threshold: number;
    last_updated: string;
  }> {
    const response = await apiService.get<{
      version: string;
      supported_exercises: string[];
      confidence_threshold: number;
      last_updated: string;
    }>(endpoints.ml.modelInfo);
    return response.data;
  }

  async requestMLReanalysis(id: string): Promise<FormCheck> {
    const response = await apiService.post<FormCheck>(`${this.baseUrl}/${id}/reanalyze`);
    return response.data;
  }

  // ------------------------------------------------------------------
  // Shared fallback: one getFormChecks() call is shared across all three
  // analytics methods so a backend outage causes only one extra fetch.
  // ------------------------------------------------------------------

  private async _getFallbackChecks(): Promise<FormCheck[]> {
    if (!this._fallbackChecksCache) {
      this._fallbackChecksCache = await this.getFormChecks();
    }
    return this._fallbackChecksCache;
  }

  private _clearFallbackCache(): void {
    this._fallbackChecksCache = null;
  }

  // Analytics methods that utilize apiService for enhanced analytics
  async getAnalyticsOverview(timeRange?: string): Promise<{
    totalSessions: number;
    averageScore: number;
    bestExercise: string | null;
    weeklyProgress: number;
    improvementRate: number;
  }> {
    this._clearFallbackCache(); // reset at the start of a fresh analytics request
    try {
      return await apiService.getAnalyticsOverview(timeRange);
    } catch (error) {
      // Fallback: reuse the same fetch across all three analytics methods
      console.warn('Backend analytics not available, using fallback calculation');
      const formChecks = await this._getFallbackChecks();
      return this.calculateAnalyticsOverview(formChecks, timeRange);
    }
  }

  async getExerciseStatistics(timeRange?: string) {
    try {
      return await apiService.getExerciseStats(timeRange);
    } catch (error) {
      console.warn('Backend exercise stats not available, using fallback calculation');
      const formChecks = await this._getFallbackChecks();
      return this.calculateExerciseStats(formChecks, timeRange);
    }
  }

  async getTimeSeriesAnalytics(timeRange?: string) {
    try {
      return await apiService.getTimeSeriesData(timeRange);
    } catch (error) {
      console.warn('Backend time series data not available, using fallback calculation');
      const formChecks = await this._getFallbackChecks();
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
      const key = fc.exercise_type || fc.classified_exercise_slug;
      if (!key) return;
      if (!exerciseAvgs[key]) exerciseAvgs[key] = { total: 0, count: 0 };
      exerciseAvgs[key].total += fc.score || 0;
      exerciseAvgs[key].count += 1;
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
      const key = fc.exercise_type || fc.classified_exercise_slug;
      if (!key) return;
      if (!exerciseGroups[key]) exerciseGroups[key] = [];
      exerciseGroups[key].push(fc);
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

      // Only count valid sessions (with a real score) — uncertain sessions are excluded.
      if (fc.score) {
        dayData.session_count += 1;
        dayData.scores.push(fc.score);
      }
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