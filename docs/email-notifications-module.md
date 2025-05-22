# Email Notifications Module

## Overview

The Email Notifications Module provides a centralized system for sending transactional and informational emails to users. It includes rate limiting, templating, and monitoring capabilities to ensure reliable delivery of important communications.

## Architecture

The module follows a layered architecture:

```
┌─────────────────┐      ┌───────────────┐      ┌─────────────────┐      ┌──────────────┐
│ API Controllers │─────▶│ Auth Service  │─────▶│  Email Service  │─────▶│ SMTP Server  │
└─────────────────┘      └───────────────┘      └─────────────────┘      └──────────────┘
        │                       │                       │                        │
        │                       │                       │                        │
        ▼                       ▼                       ▼                        ▼
┌─────────────────┐      ┌───────────────┐      ┌─────────────────┐      ┌──────────────┐
│ Task Workers    │─────▶│ Video Service │─────▶│  Templates      │─────▶│ Rate Limiter │
└─────────────────┘      └───────────────┘      └─────────────────┘      └──────────────┘
```

## Key Components

### EmailService

The core service responsible for composing and sending emails. It supports:

- Multiple email types (verification, password reset, notifications)
- HTML and plain text templates
- Email tracking and metrics

### Email Templates

- `password_reset.html/txt`: For password reset requests
- `email_verification.html/txt`: For email verification requests
- `analysis_complete.html/txt`: For notifying users when video analysis is complete

### Rate Limiting

The module includes a robust rate limiting system to prevent abuse:

- Verification emails: 3 per hour per email address
- Password reset emails: 3 per hour per email address  
- Notification emails: 10 per hour per email address

Rate limits are implemented using Redis for distributed counting with TTL expiration.

## Email Types

### Authentication Emails

- **Email Verification**: Sent when users register or request verification
- **Password Reset**: Sent when users request to reset their password

### Notification Emails

- **Video Analysis Complete**: Sent when the system completes analyzing a user's video
- Future types can be easily added to the system

## API Endpoints

### Authentication-related

- `POST /auth/reset-password/request`: Request a password reset email
- `POST /auth/reset-password/confirm`: Confirm password reset with token
- `POST /auth/verify-email/request`: Request email verification
- `POST /auth/verify-email/confirm`: Confirm email with token

## Configuration

### Environment Variables

```
# SMTP Configuration
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=noreply@formiq.com
SMTP_PASSWORD=your-secure-password
SMTP_FROM_EMAIL=noreply@formiq.com
SMTP_FROM_NAME=FormIQ

# Rate Limiting
REDIS_URL=redis://localhost:6379/0
EMAIL_RATE_LIMIT_VERIFICATION=3
EMAIL_RATE_LIMIT_PASSWORD_RESET=3
EMAIL_RATE_LIMIT_NOTIFICATION=10
```

## Frontend Components

The module includes frontend components for handling email-related user flows:

- `ResetPasswordForm`: Form for requesting a password reset
- `ConfirmPasswordResetForm`: Form for confirming a password reset with token
- `RequestEmailVerificationForm`: Form for requesting email verification
- `ConfirmEmailVerification`: Component for confirming email verification

## Security Considerations

- All tokens are cryptographically secure and expire after a set period
- Password reset: 30 minutes
- Email verification: 24 hours
- Rate limiting prevents enumeration and abuse
- Sensitive links use HTTPS and have embedded signatures

## Monitoring and Metrics

The module tracks:

- Email send attempts
- Successful deliveries
- Failures by type
- Rate limit hits
- Token usage and expiration

## Future Enhancements

- Email delivery status tracking
- Click and open tracking
- User notification preferences
- Scheduled and batch email sending
- Integration with marketing automation tools
- Support for localization/internationalization