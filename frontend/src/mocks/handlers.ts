import { rest } from 'msw';
import { DefaultBodyType, PathParams, ResponseComposition, RestContext, RestRequest } from 'msw';
import { ExerciseType, FormCheck, User } from '../types';

const BASE_URL = process.env.REACT_APP_API_URL || '/api';

const mockUser: User = {
  id: 1,
  email: 'test@example.com',
  username: 'testuser',
  subscription_tier: 'basic',
  subscription_end_date: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString(),
  is_email_verified: true,
};

const mockFormChecks: FormCheck[] = [
  {
    id: 1,
    user_id: 1,
    exercise_type: 'squat' as ExerciseType,
    video_url: 'https://example.com/video1.mp4',
    score: 85,
    overall_feedback: 'Good form overall, minor adjustments needed',
    issues: ['Knees caving in slightly', 'Could go deeper'],
    created_at: new Date().toISOString(),
  },
  {
    id: 2,
    user_id: 1,
    exercise_type: 'deadlift' as ExerciseType,
    video_url: 'https://example.com/video2.mp4',
    score: 92,
    overall_feedback: 'Excellent form',
    issues: ['Slight rounding in lower back'],
    created_at: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
  },
];

export const handlers = [
  // Auth endpoints
  rest.post(
    `${BASE_URL}/auth/login`,
    async (req: RestRequest<DefaultBodyType, PathParams>, res: ResponseComposition, ctx: RestContext) => {
      return res(
        ctx.status(200),
        ctx.json({
          access_token: 'mock_token',
          token_type: 'bearer',
          user: mockUser,
        })
      );
    }
  ),

  rest.get(
    `${BASE_URL}/auth/me`,
    async (req: RestRequest, res: ResponseComposition, ctx: RestContext) => {
      return res(ctx.status(200), ctx.json(mockUser));
    }
  ),

  // Form checks endpoints
  rest.get(
    `${BASE_URL}/form-checks`,
    async (req: RestRequest, res: ResponseComposition, ctx: RestContext) => {
      return res(ctx.status(200), ctx.json(mockFormChecks));
    }
  ),

  rest.get(
    `${BASE_URL}/form-checks/:id`,
    async (req: RestRequest<DefaultBodyType, { id: string }>, res: ResponseComposition, ctx: RestContext) => {
      const { id } = req.params;
      const formCheck = mockFormChecks.find(check => check.id === Number(id));
      
      if (!formCheck) {
        return res(
          ctx.status(404),
          ctx.json({ detail: 'Form check not found' })
        );
      }

      return res(ctx.status(200), ctx.json(formCheck));
    }
  ),

  rest.post(
    `${BASE_URL}/form-checks`,
    async (req: RestRequest, res: ResponseComposition, ctx: RestContext) => {
      const formData = await req.json();
      
      const newFormCheck: FormCheck = {
        id: mockFormChecks.length + 1,
        user_id: mockUser.id,
        exercise_type: formData.exercise_type || 'squat',
        video_url: 'https://example.com/video-new.mp4',
        score: Math.floor(Math.random() * 30) + 70, // Random score between 70-100
        overall_feedback: 'New form check analysis',
        issues: ['Sample issue 1', 'Sample issue 2'],
        created_at: new Date().toISOString(),
      };

      return res(
        ctx.delay(1000), // Simulate network delay
        ctx.status(201),
        ctx.json(newFormCheck)
      );
    }
  ),
]; 