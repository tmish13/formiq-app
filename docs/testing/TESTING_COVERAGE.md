# FormIQ Application Testing Coverage

This document provides an overview of the test coverage for the FormIQ application. All tests have been consolidated into logical groups based on functionality to improve maintainability and clarity.

## Consolidated Test Files

| Test File | Coverage Areas | Key Components Tested |
|-----------|----------------|------------------------|
| ApiServices.consolidated.test.tsx | API services, network handling, data persistence | API integration, error handling, offline mode, storage services, network recovery |
| Authentication.consolidated.test.tsx | User authentication | Login, registration, password reset, auth context, auth slice |
| CameraUploadFlow.consolidated.test.tsx | Camera capture and upload | Camera integration, upload process, preview functionality |
| CustomHooks.consolidated.test.tsx | Custom React hooks | useApi, useAuth, useFormAnalysis, useFormBuilder, useFormCheck, useWorkout |
| EndToEndUserFlows.consolidated.test.tsx | Full user journeys | Authentication flow, camera capture flow, workout flow |
| FormAnalysis.consolidated.test.tsx | Form analysis features | Form builder, analysis results, validation, feedback |
| FormCheck.consolidated.test.tsx | Form checking functionality | Form feedback, validation, form check service, form check slice |
| PoseAnalysis.consolidated.test.tsx | Exercise and pose analysis | Pose visualization, exercise selector, pose analysis service, exercise library |
| ProfileManagement.consolidated.test.tsx | User profile | Profile components, user settings, profile management |
| Security.consolidated.test.tsx | Security features | CSP headers, security policies |
| SubscriptionManagement.consolidated.test.tsx | Subscription features | Subscription components, subscription slice |
| UploadFlow.consolidated.test.tsx | Video upload workflow | Upload behavior, upload pages |
| UploadGuidance.consolidated.test.tsx | Upload guidance | Instructions, validation, user guidance |
| UploadResultsIntegration.consolidated.test.tsx | Upload results | Results display, integration with analysis |
| VideoService.consolidated.test.tsx | Video functionality | Video player, video analyzer, camera service, video processing |

## Test Coverage by Feature Area

### User Authentication and Management
- User registration and login
- Password reset functionality
- Authentication persistence
- Session management
- User profile and settings

### Form Analysis and Checking
- Form building and customization
- Form validation rules
- Analysis algorithms
- Results presentation
- Feedback mechanisms

### Video and Camera Services
- Video capture and processing
- Camera integration
- Video analysis
- Playback controls

### Pose and Exercise Analysis
- Pose detection and tracking
- Exercise recognition
- Form correction guidance
- Exercise library management

### Upload Workflow
- File selection and validation
- Upload progress tracking
- Error handling during uploads
- Results processing and display
- User guidance during upload

### API and Network Services
- API request/response handling
- Error management
- Offline capabilities
- Data persistence
- Network recovery strategies

### End-to-End User Flows
- Complete user journeys
- Integration between features
- State persistence across flows

## Test Maintenance

All tests are maintained in the `tests/consolidated` directory. When adding new features:

1. Identify the appropriate consolidated test file
2. Add new test cases to the relevant file
3. Update this document if new coverage areas are added

### Snapshot Testing

Many components use Jest snapshot testing to verify UI consistency. When making intentional UI changes:

```bash
# Update all snapshots
npm test -- -u

# Update snapshots for a specific test file
npm test -- -u FormAnalysis.consolidated.test.tsx
```

### Type Checking & Linting

The codebase maintains strict TypeScript checking and ESLint rules to ensure code quality:

```bash
# Run the linter
npm run lint

# Run TypeScript type checking
npm run typecheck
```

These checks are integrated into the CI pipeline to maintain code quality standards.

For questions about testing coverage or to request changes to the testing structure, please contact the testing team lead. 