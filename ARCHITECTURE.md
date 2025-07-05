# FormIQ Application Architecture

## Frontend Build System & Entry Points

### Build Configuration Files
- **`package.json`** - Defines dependencies, scripts, and build commands
- **`tsconfig.json`** - TypeScript configuration
- **`config-overrides.js`** - react-app-rewired customizations
- **`postcss.config.js`** - PostCSS configuration for Tailwind
- **`tailwind.config.js`** - Tailwind CSS configuration
- **`public/index.html`** - HTML template entry point

### Main Application Entry
- **`src/index.tsx`** - Application bootstrap
- **`src/App.tsx`** - Root component with providers
- **`src/styles/globals.css`** - Global styles and Tailwind imports

## Frontend Routing & Pages

### Route Configuration
- **`src/routes/routes.tsx`** - Central route definitions
- **`src/routes/AppRoutes.tsx`** - Route rendering logic
- **`src/routes/index.tsx`** - Route exports

### Current Active Pages (Modern UI)
```
/auth → ModernAuthPage
/dashboard → ModernDashboard  
/progress → ModernProgress
/exercise-library → ModernExerciseLibrary
/profile → ModernProfile
/form-analysis → ModernRecordPage
/processing/:videoId → ModernProcessingPage
/form-check/results/:videoId → ModernResultsPage
```

## Frontend State Management & Services

### Redux Store
- **`src/store/index.ts`** - Store configuration
- **`src/store/slices/authSlice.ts`** - Authentication state
- **`src/store/slices/formCheckSlice.ts`** - Form analysis state
- **`src/store/slices/progressSlice.ts`** - User progress state

### API Services
- **`src/services/apiService.ts`** - Main API client with axios
- **`src/services/formCheckService.ts`** - Video upload & analysis
- **`src/services/authService.ts`** - Authentication endpoints
- **`src/services/progressService.ts`** - Progress tracking
- **`src/services/exerciseConfigService.ts`** - Exercise configurations
- **`src/services/workoutService.ts`** - Workout management

## Backend API Structure

### Main Backend Entry Points
- **`backend/app/main.py`** - FastAPI application setup
- **`backend/app/core/config.py`** - Environment configuration
- **`backend/app/core/database.py`** - Database connection

### API Routes (All prefixed with `/api/v1`)

#### Authentication (`/auth`)
- **`backend/app/api/v1/endpoints/auth.py`**
  - `POST /auth/register` - User registration
  - `POST /auth/login` - User login
  - `POST /auth/logout` - User logout
  - `POST /auth/refresh` - Refresh JWT token
  - `GET /auth/me` - Get current user
  - `POST /auth/forgot-password` - Request password reset
  - `POST /auth/reset-password` - Confirm password reset

#### Form Check Analysis (`/form-check`)
- **`backend/app/api/v1/endpoints/form_check.py`**
  - `POST /form-check/upload` - Get presigned S3 URL
  - `POST /form-check/submit` - Submit video for analysis
  - `GET /form-check/{video_id}/status` - Check analysis status
  - `GET /form-check/{video_id}/results` - Get analysis results
  - `GET /form-check/history` - User's analysis history

#### Exercises (`/exercises`)
- **`backend/app/api/v1/endpoints/exercises.py`**
  - `GET /exercises` - List all exercises
  - `GET /exercises/{exercise_id}` - Get exercise details
  - `GET /exercises/{exercise_id}/config` - Get exercise configuration

#### Progress (`/progress`)
- **`backend/app/api/v1/endpoints/progress.py`**
  - `GET /progress/summary` - Overall progress summary
  - `GET /progress/exercises` - Progress by exercise
  - `GET /progress/timeline` - Progress timeline

#### User Profile (`/users`)
- **`backend/app/api/v1/endpoints/users.py`**
  - `GET /users/profile` - Get user profile
  - `PUT /users/profile` - Update profile
  - `DELETE /users/account` - Delete account

## Backend Services & Processing

### Core Services
- **`backend/app/services/video_service.py`** - Video upload handling
- **`backend/app/services/storage_service.py`** - S3 storage operations
- **`backend/app/services/ai_service.py`** - AI/ML pose detection
- **`backend/app/services/form_analysis_service.py`** - Analysis orchestration
- **`backend/app/services/feedback_service.py`** - Feedback generation

### Async Processing (Celery)
- **`backend/app/tasks/video_processing.py`** - Video processing tasks
- **`backend/app/tasks/ai_analysis.py`** - AI analysis tasks
- **`backend/app/core/celery_app.py`** - Celery configuration

### Database Models
- **`backend/app/models/user.py`** - User model
- **`backend/app/models/form_check.py`** - Form analysis model
- **`backend/app/models/exercise.py`** - Exercise model
- **`backend/app/models/progress.py`** - Progress tracking model

## Frontend-Backend Data Flow

### 1. Video Upload & Analysis Flow
```
Frontend                          Backend
--------                          -------
VideoUpload component
    ↓
formCheckService.requestUploadUrl() → POST /form-check/upload
    ↓                                   ↓
Upload to S3 directly              Return presigned URL
    ↓
formCheckService.submitForAnalysis() → POST /form-check/submit
    ↓                                   ↓
Poll for status                    Celery task processing
    ↓                                   ↓
formCheckService.getResults()      → GET /form-check/{id}/results
    ↓                                   ↓
Display results                    Return analysis data
```

### 2. Authentication Flow
```
Frontend                          Backend
--------                          -------
Login form
    ↓
apiService.login()               → POST /auth/login
    ↓                                ↓
Store JWT in Redux               Return JWT + user data
    ↓                                ↓
axios interceptor                All subsequent requests
adds Authorization header        validate JWT
```

### 3. Real-time Updates (WebSocket)
- **Frontend**: `src/services/websocketService.ts`
- **Backend**: `backend/app/api/v1/websocket.py`
- Used for live form analysis feedback during recording

## Key Configuration Files

### Frontend Environment
- **`.env`** - Environment variables (REACT_APP_API_URL, etc.)

### Backend Environment
- **`backend/.env`** - Backend config (DATABASE_URL, AWS credentials, etc.)

### Deployment
- **`docker-compose.yml`** - Container orchestration
- **`Dockerfile`** - Container build instructions

## Component Architecture

### UI Components (to be replaced)
Currently using shadcn/ui components from:
- `src/components/ui/*` - Base UI components
- `src/components/molecules/*` - Composite components
- `src/components/organisms/*` - Page sections

### Context Providers
- **`src/contexts/ModernThemeContext.tsx`** - Theme management
- **`src/contexts/NetworkStatusProvider.tsx`** - Offline support

### Custom Hooks
- **`src/hooks/useAuth.ts`** - Authentication logic
- **`src/hooks/useApi.ts`** - API call wrapper
- **`src/hooks/useWebSocket.ts`** - WebSocket connection

## Important Notes

This architecture ensures clean separation between frontend and backend, with the API serving as the contract between them. The frontend can be completely replaced as long as it adheres to the API contract defined by the backend routes.