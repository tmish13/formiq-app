import apiService from './apiService';
import { SquatTrainingSession } from '../types/formCheck';

// Backend snake_case shape returned by GET /squat-sessions/
interface SquatSessionPayload {
  id: string;
  user_id: string;
  form_check_id: string | null;
  date: string;
  working_weight_lb: number;
  overall_score: number;
  torso_stability: number;
  knee_symmetry: number;
  bottom_control: number;
  forward_lean: number;
  primary_limiter: string;
  notes?: string | null;
  sets_json: Array<{ setIndex: number; reps: number; formScore?: number; primaryLimiter?: string }>;
  created_at: string;
}

function toPayload(session: SquatTrainingSession, formCheckId?: string): Record<string, unknown> {
  return {
    form_check_id: formCheckId ?? null,
    date: session.date,
    working_weight_lb: session.workingWeight,
    overall_score: session.overallScore,
    torso_stability: session.components.torsoStability,
    knee_symmetry: session.components.kneeSymmetry,
    bottom_control: session.components.bottomControl,
    forward_lean: session.components.forwardLean,
    primary_limiter: session.primaryLimiter,
    notes: session.notes ?? null,
    sets_json: session.sets,
  };
}

function fromPayload(p: SquatSessionPayload): SquatTrainingSession {
  return {
    id: p.id,
    exercise: 'squat',
    date: p.date,
    workingWeight: p.working_weight_lb,
    overallScore: p.overall_score,
    components: {
      torsoStability: p.torso_stability,
      kneeSymmetry: p.knee_symmetry,
      bottomControl: p.bottom_control,
      forwardLean: p.forward_lean,
    },
    primaryLimiter: p.primary_limiter,
    notes: p.notes ?? undefined,
    sets: p.sets_json ?? [],
  };
}

class SquatSessionService {
  private readonly baseUrl = '/squat-sessions';

  async create(session: SquatTrainingSession, formCheckId?: string): Promise<void> {
    await apiService.post(this.baseUrl + '/', toPayload(session, formCheckId));
  }

  async list(limit = 200): Promise<SquatTrainingSession[]> {
    const response = await apiService.get<SquatSessionPayload[]>(
      `${this.baseUrl}/?limit=${limit}`,
    );
    return response.data.map(fromPayload);
  }
}

export const squatSessionService = new SquatSessionService();
