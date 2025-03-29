# API Documentation

## Overview

The Formiq API is built using FastAPI and provides a comprehensive set of endpoints for managing workouts, form checks, subscriptions, and user authentication.

## Base URL

```
http://localhost:8000/api/v1
```

## Authentication

All API endpoints except `/auth/register` and `/auth/login` require authentication using a Bearer token.

```http
Authorization: Bearer <your_access_token>
```

## Endpoints

### Authentication

#### Register User
```http
POST /auth/register
```

Request body:
```json
{
    "email": "user@example.com",
    "password": "securepassword",
    "full_name": "John Doe"
}
```

Response:
```json
{
    "id": "uuid",
    "email": "user@example.com",
    "full_name": "John Doe",
    "is_active": true,
    "is_verified": false
}
```

#### Login
```http
POST /auth/login
```

Request body:
```json
{
    "email": "user@example.com",
    "password": "securepassword"
}
```

Response:
```json
{
    "access_token": "jwt_token",
    "token_type": "bearer",
    "user": {
        "id": "uuid",
        "email": "user@example.com",
        "full_name": "John Doe",
        "is_active": true,
        "is_verified": true
    }
}
```

### Form Checks

#### Submit Form Check
```http
POST /form-checks
```

Request body:
```json
{
    "exercise_type": "squat",
    "video_url": "https://example.com/video.mp4",
    "notes": "Optional notes about the form"
}
```

Response:
```json
{
    "id": "uuid",
    "user_id": "uuid",
    "exercise_type": "squat",
    "video_url": "https://example.com/video.mp4",
    "status": "pending",
    "score": null,
    "feedback": null,
    "created_at": "2024-03-29T12:00:00Z"
}
```

#### Get Form Checks
```http
GET /form-checks
```

Query Parameters:
- `status`: Filter by status (pending, analyzing, completed)
- `exercise_type`: Filter by exercise type
- `skip`: Number of records to skip (pagination)
- `limit`: Number of records to return (pagination)

Response:
```json
{
    "items": [
        {
            "id": "uuid",
            "user_id": "uuid",
            "exercise_type": "squat",
            "video_url": "https://example.com/video.mp4",
            "status": "completed",
            "score": 85,
            "feedback": "Good form overall...",
            "created_at": "2024-03-29T12:00:00Z"
        }
    ],
    "total": 1,
    "skip": 0,
    "limit": 10
}
```

### Workouts

#### Create Workout
```http
POST /workouts
```

Request body:
```json
{
    "name": "Leg Day",
    "description": "Focus on lower body exercises",
    "exercises": [
        {
            "name": "Squat",
            "sets": 3,
            "reps": 12,
            "weight": 100
        }
    ]
}
```

Response:
```json
{
    "id": "uuid",
    "user_id": "uuid",
    "name": "Leg Day",
    "description": "Focus on lower body exercises",
    "exercises": [
        {
            "id": "uuid",
            "name": "Squat",
            "sets": 3,
            "reps": 12,
            "weight": 100
        }
    ],
    "created_at": "2024-03-29T12:00:00Z"
}
```

#### Get Workouts
```http
GET /workouts
```

Query Parameters:
- `skip`: Number of records to skip (pagination)
- `limit`: Number of records to return (pagination)

Response:
```json
{
    "items": [
        {
            "id": "uuid",
            "user_id": "uuid",
            "name": "Leg Day",
            "description": "Focus on lower body exercises",
            "exercises": [...],
            "created_at": "2024-03-29T12:00:00Z"
        }
    ],
    "total": 1,
    "skip": 0,
    "limit": 10
}
```

### Subscriptions

#### Create Subscription
```http
POST /subscriptions
```

Request body:
```json
{
    "tier": "PRO",
    "payment_method_id": "pm_xxx"
}
```

Response:
```json
{
    "id": "uuid",
    "user_id": "uuid",
    "tier": "PRO",
    "status": "active",
    "current_period_start": "2024-03-29T12:00:00Z",
    "current_period_end": "2024-04-29T12:00:00Z"
}
```

#### Get Current Subscription
```http
GET /subscriptions/current
```

Response:
```json
{
    "id": "uuid",
    "user_id": "uuid",
    "tier": "PRO",
    "status": "active",
    "current_period_start": "2024-03-29T12:00:00Z",
    "current_period_end": "2024-04-29T12:00:00Z"
}
```

## Error Responses

All endpoints may return the following error responses:

### 400 Bad Request
```json
{
    "detail": "Invalid input data"
}
```

### 401 Unauthorized
```json
{
    "detail": "Not authenticated"
}
```

### 403 Forbidden
```json
{
    "detail": "Not enough permissions"
}
```

### 404 Not Found
```json
{
    "detail": "Resource not found"
}
```

### 422 Validation Error
```json
{
    "detail": [
        {
            "loc": ["body", "email"],
            "msg": "field required",
            "type": "value_error.missing"
        }
    ]
}
```

## Rate Limiting

The API implements rate limiting based on subscription tiers:

- Free: 50 requests per minute
- Pro: 200 requests per minute
- Enterprise: 1000 requests per minute

Rate limit headers are included in all responses:

```http
X-RateLimit-Limit: 200
X-RateLimit-Remaining: 199
X-RateLimit-Reset: 1616789012
``` 