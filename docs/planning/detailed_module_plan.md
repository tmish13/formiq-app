# FormIQ Module Integration Plan from OpenSaaS Documentation

This document outlines a plan to integrate relevant modules and concepts from the OpenSaaS documentation into the FormIQ application (React + FastAPI).

## Core Modules for FormIQ MVP

### 1. User Authentication & Profiles ✅

*   **OpenSaaS Equivalent:** "Auth" (Email verified login, Social login like Google, GitHub)
*   **Why it's useful for FormIQ:**
    *   Essential for users to create accounts, upload and manage their workout videos, track their progress over time, and personalize their experience.
    *   Provides a secure way to associate data (videos, analysis results) with specific users.
*   **Integration Steps for FormIQ (React + FastAPI):**
    *   **Backend (FastAPI):**
        1.  **Authentication Strategy:** Implement token-based authentication (JWT - JSON Web Tokens).
        2.  **User Model:** Define a `User` model (e.g., using SQLAlchemy) with fields for hashed passwords, email, profile information (e.g., name, fitness goals), and timestamps.
        3.  **API Endpoints:**
            *   `/auth/register`: For new user sign-ups. Hash passwords.
            *   `/auth/login`: To authenticate users and issue JWTs.
            *   `/auth/logout`: (Client-side token removal, potentially blacklist token on server).
            *   `/users/me`: To get the authenticated user's profile.
            *   `/users/me`: To update the authenticated user's profile.
            *   `/auth/request-password-reset`: Initiates password reset.
            *   `/auth/reset-password`: Completes password reset with a token.
        4.  **Email Verification:** Integrate an email sending service (see Module 4) to send verification links.
        5.  **(Optional Post-MVP) Social Logins:** Implement OAuth2 for Google/other providers using libraries like `Authlib`.
        6.  **Security Note:** Implement HttpOnly cookies with CSRF protection for storing JWTs, rather than localStorage. This prevents token theft via XSS attacks, while CSRF protection prevents attacks against the cookies themselves.
    *   **Frontend (React):**
        1.  **UI Components:** Create forms for Sign Up, Login, Password Reset request, Password Reset confirm, and a Profile Management page.
        2.  **State Management:** Use React Context/Redux/Zustand for auth state (user, token, loading states).
        3.  **API Service:** Create a dedicated service/module for making API calls to FastAPI auth endpoints.
        4.  **Token Storage:** Store JWTs securely (e.g., `HttpOnly` cookies managed by the backend are preferred; if using `localStorage`, be aware of XSS).
        5.  **Protected Routes:** Implement route guards to restrict access based on authentication status.

### 2. File Uploads (Workout Videos)

*   **OpenSaaS Equivalent:** "File Uploading" (using AWS S3 with presigned URLs)
*   **Why it's useful for FormIQ:**
    *   Workout videos are large; S3 offers scalable, durable, and cost-effective storage.
    *   Presigned URLs enable direct client-to-S3 uploads, reducing server load and enhancing security.
*   **Integration Steps for FormIQ (React + FastAPI):**
    *   **Backend (FastAPI):**
        1.  **AWS SDK:** Install `boto3`.
        2.  **Configuration:** Securely store AWS credentials (Access Key, Secret Key), S3 bucket name, and region (environment variables).
        3.  **Presigned URL Endpoint:** `/videos/upload/signed-url`
            *   Accepts filename, content type.
            *   Generates a presigned S3 PUT URL via `boto3`.
            *   Returns the URL to the client.
        4.  **Video Metadata Model:** Create a `Video` model (SQLAlchemy) linked to the `User` model, storing S3 object key, upload timestamp, original filename, processing status (e.g., "uploaded", "processing", "completed", "failed"), and analysis results foreign key.
        5.  **Confirmation Endpoint (Optional):** `/videos/upload/confirm` - Client calls this after successful S3 upload, or use S3 event notifications (e.g., Lambda trigger) to update video status in the database.
    *   **Frontend (React):**
        1.  **File Input Component:** Allow users to select video files.
        2.  **Request Presigned URL:** Call the FastAPI endpoint to get the S3 presigned URL.
        3.  **Direct S3 Upload:** Perform a PUT request to the S3 URL with the video file.
        4.  **Progress Indicator:** Display upload progress.
        5.  **Confirmation:** Notify the backend or update UI based on S3 upload success.

### 3. Background Jobs (AI Pose Detection & Feedback)

*   **OpenSaaS Equivalent:** "Jobs" (Wasp's cron jobs/queues)
*   **Why it's useful for FormIQ:**
    *   AI analysis is computationally intensive. Asynchronous processing is crucial for good UX.
*   **Integration Steps for FormIQ (React + FastAPI):**
    *   **Backend (FastAPI):**
        1.  **Task Queue:** Implement Celery with Redis or RabbitMQ as the broker.
        2.  **AI Task Definition:** Create Celery tasks for:
            *   Downloading video from S3.
            *   Running pose detection models.
            *   Generating feedback based on pose data.
            *   Storing analysis results.
        3.  **Task Enqueueing:** When a video upload is confirmed and metadata stored, enqueue the AI analysis task with the video ID or S3 key.
        4.  **Results Storage:** Define an `AnalysisResult` model (SQLAlchemy) linked to the `Video` model to store pose data, feedback text, scores, etc.
        5.  **Status Updates:** Update the `Video` model's processing status field as the task progresses.
    *   **Frontend (React):**
        1.  **Processing Indication:** Inform the user their video is being analyzed.
        2.  **Status Polling/WebSockets:**
            *   Periodically poll a FastAPI endpoint (e.g., `/videos/{video_id}/status`) for processing status.
            *   (Post-MVP) Implement WebSockets for real-time status updates.
        3.  **Display Results:** Fetch and render analysis results when processing is complete.

### 4. Email Sending

*   **OpenSaaS Equivalent:** "Email Sending" (SendGrid, MailGun, SMTP)
*   **Why it's useful for FormIQ:**
    *   User email verification.
    *   Password reset functionality.
    *   Notifications (e.g., video analysis complete).
*   **Integration Steps for FormIQ (React + FastAPI):**
    *   **Backend (FastAPI):**
        1.  **Provider/Library:** Use a service like SendGrid (with `sendgrid-python`) or AWS SES (with `boto3`). `fastapi-mail` is also a good option.
        2.  **Configuration:** Store API keys and sender email securely.
        3.  **Utility Functions:** Create helpers like `send_verification_email(to_email, token)`, `send_password_reset_email(to_email, token)`, `send_analysis_complete_notification(to_email, video_name)`.
        4.  **Integration Points:** Call these from user registration, password reset flows, and Celery tasks (on analysis completion).
        5.  **Rate Limiting:** Implement rate limiting on email-sending endpoints (e.g., 5 requests per hour per IP or user) to prevent abuse of password reset/resend verification endpoints. Use Redis to track request counts or a library like `slowapi`.
    *   **Frontend (React):**
        1.  **UI for Actions:** Buttons/links for "Resend verification," "Forgot password."
        2.  **Feedback:** Inform users to check email.
        3.  **Rate Limit Feedback:** Display appropriate messages when rate limits are reached.

## Post-MVP / Future Enhancements

### 5. Subscription Payments

*   **OpenSaaS Equivalent:** "Subscription Payments with Stripe or Lemon Squeezy"
*   **Why it's useful for FormIQ:**
    *   Monetization through premium features (more storage, advanced analytics, higher processing priority).
*   **Integration Steps for FormIQ (React + FastAPI):**
    *   **Backend (FastAPI):**
        1.  **Provider SDK:** Use `stripe` (Python).
        2.  **Product Setup:** Define plans in Stripe dashboard.
        3.  **API Endpoints:**
            *   `/payments/create-checkout-session`: Initiates Stripe Checkout.
            *   `/payments/webhook`: Handles events from Stripe (e.g., `checkout.session.completed`, `invoice.paid`, `customer.subscription.updated`) to update user subscription status in DB. Secure with webhook signing.
        4.  **User Model Update:** Add fields like `stripe_customer_id`, `subscription_plan`, `subscription_status` to the `User` model.
    *   **Frontend (React):**
        1.  **Pricing Page:** Display plans.
        2.  **Checkout Flow:** Redirect to Stripe Checkout.
        3.  **Subscription Management:** Link to Stripe Customer Portal.

### 6. Admin Dashboard

*   **OpenSaaS Equivalent:** "Analytics and Admin Dashboard"
*   **Why it's useful for FormIQ:**
    *   User management, application monitoring, content moderation.
*   **Integration Steps for FormIQ (React + FastAPI):**
    *   **Backend (FastAPI):**
        1.  **Admin Authorization:** Add `is_admin` field to `User` model. Protect admin APIs.
        2.  **Admin API Endpoints:** Endpoints for `/admin/users`, `/admin/videos`, `/admin/stats`.
    *   **Frontend (React):**
        1.  **Admin UI:** Separate section/app for admins.
        2.  **Data Display & Actions:** Tables, charts, user management tools.

---

This plan prioritizes core functionality for an MVP and outlines future enhancements. Each step requires careful implementation and testing. 