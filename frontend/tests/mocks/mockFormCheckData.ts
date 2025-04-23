export const mockFormCheck = {
  id: '1',
  exercise_type: 'squat',
  score: 95,
  created_at: '2024-01-15T10:00:00Z',
  video_url: 'https://example.com/videos/squat1.mp4',
  feedback: {
    overall: 'Great form overall',
    issues: ['Slight knee valgus at bottom position'],
    suggestions: ['Focus on pushing knees outward during descent']
  }
};

export const mockFormChecks = [
  mockFormCheck,
  {
    id: '2',
    exercise_type: 'deadlift',
    score: 88,
    created_at: '2024-01-14T15:30:00Z',
    video_url: 'https://example.com/videos/deadlift1.mp4',
    feedback: {
      overall: 'Good form overall',
      issues: ['Slight rounding in lower back'],
      suggestions: ['Engage core before lifting']
    }
  },
  {
    id: '3',
    exercise_type: 'bench_press',
    score: 92,
    created_at: '2024-01-13T09:15:00Z',
    video_url: 'https://example.com/videos/bench1.mp4',
    feedback: {
      overall: 'Excellent form',
      issues: ['Minor wrist angle variation'],
      suggestions: ['Keep wrists straight throughout the movement']
    }
  }
];

export const mockFormCheckError = {
  message: 'Error loading form check',
  code: 'FORM_CHECK_ERROR'
};

export const mockFormCheckNotFound = {
  message: 'Form check not found',
  code: 'NOT_FOUND'
}; 