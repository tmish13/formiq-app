// Import and re-export from serviceMocks
export {
  createMockKeypoints,
  createMockJointAngles,
  createMockAnalysisResult,
  createMockPoseAnalysisService,
  setupMediaDevicesMock,
} from './serviceMocks';

// Re-export types with export type
export type {
  JointAngle,
  JointAngles,
  PoseAlignment,
  MovementMetrics,
  PoseAnalysisResult,
} from './serviceMocks';

// Import and re-export from formCheckMocks
export {
  FormCheckStatus,
  createMockFormCheck,
  createMockFormChecks,
  createMockFeedbackItems,
  createMockFormCheckService,
} from './formCheckMocks';

// Re-export types with export type
export type {
  FormCheck,
  // Rename FormFeedbackItem to avoid conflict
  FormFeedbackItem as FormCheckFeedbackItem,
} from './formCheckMocks';

// Re-export types with export type
export type {
  // Rename FormFeedbackItem to avoid conflict
  FormFeedbackItem as PoseFormFeedbackItem,
} from './serviceMocks';

// Import and re-export from canvasMocks
export {
  setupCanvasMock,
  createMockFile,
} from './canvasMocks';

// Import and re-export from axiosMocks
export {
  createAxiosError,
  createNetworkError,
  createTimeoutError,
  createUnauthorizedError,
  createForbiddenError,
  createNotFoundError,
  createCsrfError,
  createValidationError,
  createServerError,
} from './axiosMocks'; 