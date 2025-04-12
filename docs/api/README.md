# FormIQ API Documentation

## Overview

FormIQ provides a RESTful API for form analysis and exercise tracking. This documentation covers all available endpoints, authentication methods, and common use cases.

## Authentication

All API requests require authentication using JWT tokens.

### Obtaining a Token

```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123"
}
```

Response:
```json
{
  "tokens": {
    "accessToken": "eyJhbG...",
    "refreshToken": "eyJhbG..."
  },
  "user": {
    "id": "123",
    "email": "user@example.com"
  }
}
```

### Using the Token

Include the token in the Authorization header:
```http
Authorization: Bearer eyJhbG...
```

## Form Analysis Endpoints

### Submit Form Analysis

```http
POST /api/v1/form-analysis/analyze
Content-Type: multipart/form-data

Parameters:
- video: Video file (required)
- exerciseType: string (optional)
```

Response:
```json
{
  "id": "analysis_123",
  "status": "completed",
  "confidence": 0.95,
  "poses": [...],
  "recommendations": [...]
}
```

### Get Analysis History

```http
GET /api/v1/form-analysis/history
```

Response:
```json
{
  "analyses": [
    {
      "id": "analysis_123",
      "createdAt": "2024-03-15T10:00:00Z",
      "status": "completed",
      "exerciseType": "squat"
    }
  ]
}
```

## Error Handling

The API uses standard HTTP status codes:

- 200: Success
- 400: Bad Request
- 401: Unauthorized
- 403: Forbidden
- 404: Not Found
- 429: Too Many Requests
- 500: Internal Server Error

Error Response Format:
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input parameters",
    "details": {...}
  }
}
```

## Rate Limiting

- Global: 100 requests per 15 minutes
- Auth endpoints: 5 attempts per hour
- API endpoints: 50 requests per 15 minutes

## Security

### CSRF Protection

All POST/PUT/DELETE requests require a CSRF token:
```http
X-XSRF-TOKEN: token_from_cookie
```

### Content Security Policy

The API enforces strict CSP headers. See security documentation for details.

## Monitoring

### Health Check

```http
GET /api/health
```

Response:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2024-03-15T10:00:00Z"
}
```

## WebSocket API

### Real-time Form Analysis

Connect to:
```
ws://api.formiq.com/ws
```

Message format:
```json
{
  "type": "form_analysis",
  "data": {
    "timestamp": 1234567890,
    "keypoints": [...]
  }
}
```

## Development

### Local Setup

1. Clone the repository
2. Install dependencies:
   ```bash
   npm install
   ```
3. Set up environment variables:
   ```bash
   cp .env.example .env
   ```
4. Start development server:
   ```bash
   npm run dev
   ```

### Testing

Run tests:
```bash
npm test
```

Run specific test suite:
```bash
npm test -- --grep "Form Analysis"
```

## Deployment

See [deployment.md](../deployment/deployment.md) for detailed deployment instructions. 