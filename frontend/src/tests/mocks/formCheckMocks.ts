// Define types as needed 
export enum FormCheckStatus {
  Pending = 'pending',
  Processing = 'processing',
  Completed = 'completed',
  Failed = 'failed'
}

export interface FormFeedbackItem {
  id: string;
  severity: 'low' | 'medium' | 'high';
  type: 'form' | 'posture' | 'movement';
  message: string;
  timestamp: number;
  details: string;
}

export interface FormCheck {
  id: string;
  user_id: string;
  exercise_type: string;
  video_url: string;
  status: FormCheckStatus;
  feedback_items: FormFeedbackItem[];
  created_at: string;
  updated_at: string;
}

// Helper to create a mock form check
export const createMockFormCheck = (
  overrides: Partial<FormCheck> = {}
): FormCheck => ({
  id: 'mock-form-check-id',
  user_id: 'user-123',
  exercise_type: 'squat',
  video_url: 'https://example.com/video.mp4',
  status: FormCheckStatus.Completed,
  feedback_items: [
    {
      id: 'feedback-1',
      severity: 'medium',
      type: 'form',
      message: 'Keep your knees aligned with your toes',
      timestamp: 1000,
      details: 'Your knees are moving inward during the squat'
    },
    {
      id: 'feedback-2',
      severity: 'high',
      type: 'posture',
      message: 'Maintain a neutral spine',
      timestamp: 2000,
      details: 'Your back is rounding at the bottom of the squat'
    }
  ],
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
  ...overrides
});

// Helper to create an array of mock form checks
export const createMockFormChecks = (
  count: number,
  overridesFn?: (index: number) => Partial<FormCheck>
): FormCheck[] => {
  return Array.from({ length: count }, (_, index) => {
    const overrides = overridesFn ? overridesFn(index) : {};
    return createMockFormCheck({
      id: `mock-form-check-id-${index}`,
      ...overrides
    });
  });
};

// Helper to create mock feedback items
export const createMockFeedbackItems = (
  count: number,
  overridesFn?: (index: number) => Partial<FormFeedbackItem>
): FormFeedbackItem[] => {
  return Array.from({ length: count }, (_, index) => ({
    id: `feedback-${index}`,
    severity: index % 3 === 0 ? 'high' : index % 2 === 0 ? 'medium' : 'low',
    type: index % 2 === 0 ? 'form' : 'posture',
    message: `Mock feedback item ${index}`,
    timestamp: index * 1000,
    details: `Details for feedback item ${index}`,
    ...(overridesFn ? overridesFn(index) : {})
  }));
};

// Mock form check service
export const createMockFormCheckService = () => {
  const mockFormChecks = createMockFormChecks(3);
  
  return {
    getFormChecks: jest.fn().mockResolvedValue(mockFormChecks),
    getFormCheck: jest.fn().mockImplementation((id: string) => {
      const formCheck = mockFormChecks.find(fc => fc.id === id);
      return Promise.resolve(formCheck || null);
    }),
    createFormCheck: jest.fn().mockImplementation((data: Partial<FormCheck>) => {
      const newFormCheck = createMockFormCheck({
        id: `new-form-check-${Date.now()}`,
        ...data
      });
      return Promise.resolve(newFormCheck);
    }),
    updateFormCheck: jest.fn().mockImplementation((id: string, data: Partial<FormCheck>) => {
      const formCheck = mockFormChecks.find(fc => fc.id === id);
      if (!formCheck) return Promise.resolve(null);
      
      const updatedFormCheck = {
        ...formCheck,
        ...data,
        updated_at: new Date().toISOString()
      };
      return Promise.resolve(updatedFormCheck);
    }),
    deleteFormCheck: jest.fn().mockImplementation((id: string) => {
      return Promise.resolve({ success: true });
    }),
    uploadVideo: jest.fn().mockImplementation((file: File, exerciseType: string) => {
      return Promise.resolve({
        url: 'https://example.com/uploads/video.mp4',
        id: `upload-${Date.now()}`
      });
    }),
    analyzeVideo: jest.fn().mockImplementation((formCheckId: string) => {
      return Promise.resolve({
        success: true,
        message: 'Analysis started'
      });
    })
  };
}; 