/**
 * Client for POST /training-sessions/ and GET /training-sessions/.
 *
 * sync() is fire-and-forget: failures are silently swallowed so the workout
 * UI never blocks or crashes due to a network error.  localStorage remains
 * the immediate source of truth; this service makes it durable.
 */
import apiService from './apiService';
import type { WorkoutSession, SetLog } from '../features/training/types';

// Shape sent to POST /training-sessions/
interface TrainingSessionPayload {
  id: string;
  started_at: string;
  goal: string;
  sets_json: SetLog[];
}

// Shape returned by GET /training-sessions/
export interface TrainingSessionRecord extends TrainingSessionPayload {
  user_id: string;
  created_at: string;
}

class TrainingSessionService {
  private readonly baseUrl = '/training-sessions';

  /**
   * Persist a completed workout session to the backend.
   * Fire-and-forget: awaiting is optional; errors are silently ignored.
   * Idempotent: re-posting the same session id returns the existing row.
   */
  async sync(session: WorkoutSession, sets: SetLog[]): Promise<void> {
    const payload: TrainingSessionPayload = {
      id: session.id,
      started_at: session.startedAt,
      goal: session.goal,
      sets_json: sets,
    };
    await apiService.post(this.baseUrl + '/', payload).catch(() => {
      // Network error or server unavailable — localStorage fallback still intact.
    });
  }

  async list(limit = 200): Promise<TrainingSessionRecord[]> {
    const response = await apiService.get<TrainingSessionRecord[]>(
      `${this.baseUrl}/?limit=${limit}`,
    );
    return response.data;
  }
}

export const trainingSessionService = new TrainingSessionService();
