import { Platform } from '@capacitor/core';
import { Health } from '@capacitor-community/health';
import { StorageService } from './storageService';

export interface HealthData {
  steps: number;
  calories: number;
  distance: number;
  heartRate: number[];
  workoutMinutes: number;
}

export class HealthService {
  private static instance: HealthService;
  private storage: StorageService;
  private health: typeof Health;

  private constructor() {
    this.storage = new StorageService();
    this.health = Health;
  }

  public static getInstance(): HealthService {
    if (!HealthService.instance) {
      HealthService.instance = new HealthService();
    }
    return HealthService.instance;
  }

  public async initialize(): Promise<boolean> {
    try {
      const isAvailable = await this.health.isAvailable();
      if (!isAvailable) {
        console.warn('Health tracking is not available on this device');
        return false;
      }

      const hasPermissions = await this.health.requestAuthorization({
        read: [
          'steps',
          'distance',
          'calories',
          'heart_rate',
          'workout'
        ],
        write: ['workout']
      });

      return hasPermissions;
    } catch (error) {
      console.error('Failed to initialize health tracking:', error);
      return false;
    }
  }

  public async getHealthData(startDate: Date, endDate: Date): Promise<HealthData> {
    try {
      const [steps, calories, distance, heartRate, workouts] = await Promise.all([
        this.getSteps(startDate, endDate),
        this.getCalories(startDate, endDate),
        this.getDistance(startDate, endDate),
        this.getHeartRate(startDate, endDate),
        this.getWorkoutMinutes(startDate, endDate)
      ]);

      return {
        steps,
        calories,
        distance,
        heartRate,
        workoutMinutes: workouts
      };
    } catch (error) {
      console.error('Failed to fetch health data:', error);
      throw error;
    }
  }

  private async getSteps(startDate: Date, endDate: Date): Promise<number> {
    const result = await this.health.queryAggregated({
      startDate,
      endDate,
      dataType: 'steps'
    });
    return result.value || 0;
  }

  private async getCalories(startDate: Date, endDate: Date): Promise<number> {
    const result = await this.health.queryAggregated({
      startDate,
      endDate,
      dataType: 'calories'
    });
    return result.value || 0;
  }

  private async getDistance(startDate: Date, endDate: Date): Promise<number> {
    const result = await this.health.queryAggregated({
      startDate,
      endDate,
      dataType: 'distance'
    });
    return result.value || 0;
  }

  private async getHeartRate(startDate: Date, endDate: Date): Promise<number[]> {
    const result = await this.health.query({
      startDate,
      endDate,
      dataType: 'heart_rate'
    });
    return result.map(entry => entry.value);
  }

  private async getWorkoutMinutes(startDate: Date, endDate: Date): Promise<number> {
    const result = await this.health.queryAggregated({
      startDate,
      endDate,
      dataType: 'workout'
    });
    return result.value || 0;
  }

  public async saveWorkout(
    startTime: Date,
    endTime: Date,
    type: string,
    calories: number
  ): Promise<void> {
    try {
      await this.health.store({
        dataType: 'workout',
        startDate: startTime,
        endDate: endTime,
        value: calories,
        sourceName: 'FormIQ',
        sourceBundleId: 'com.formiq.app',
        metadata: {
          type: type
        }
      });
    } catch (error) {
      console.error('Failed to save workout:', error);
      throw error;
    }
  }
}

export const healthService = HealthService.getInstance(); 