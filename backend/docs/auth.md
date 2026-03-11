# FormIQ Auth — Configuration & Testing Guide

## Overview

FormIQ supports three auth methods:
- **Email + password** — register, login, logout, forgot-password, reset-password
- **Google Sign-In** — OAuth2 implicit flow via `@react-oauth/google` (web)
- **Apple Sign-In** — Apple JS SDK popup flow (web, HTTPS + registered domain required)

---

## Environment Variables

### Backend (`backend/.env` or environment)

| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | **yes** | ≥32-char secret for signing/misc crypto |
| `JWT_SECRET` | **yes** | ≥32-char secret for JWT tokens |
| `POSTGRES_SERVER` / `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | **yes** | PostgreSQL connection |
| `REDIS_HOST` / `REDIS_PORT` | **yes** | Redis (Celery broker + login-attempt tracking) |
| `GOOGLE_CLIENT_ID` | optional | Google OAuth2 Web Client ID. Empty → Google Sign-In endpoint accepts requests but `verify_google_token()` will fail with `AuthenticationException`. |
| `GOOGLE_CLIENT_SECRET` | optional | Not used in the current implicit-flow; reserved for server-side flows. |
| `APPLE_CLIENT_ID` | optional | Apple Service ID (e.g. `com.yourcompany.formiq`). Empty → `/auth/social/apple` returns 400 "not configured". |
| `APPLE_TEAM_ID` / `APPLE_KEY_ID` / `APPLE_PRIVATE_KEY` | optional | Reserved for server-generated Apple client secrets (not yet used in the JWKS verification path). |
| `MAIL_SERVER` / `MAIL_PORT` / `MAIL_USERNAME` / `MAIL_PASSWORD` / `MAIL_FROM_EMAIL` | optional | SMTP settings for verification + password-reset emails. Incomplete → emails silently fail; auth still works. |

> **Production warning**: On startup, `Settings.validate_settings()` logs a `WARNING` for each unconfigured social auth key when `ENVIRONMENT=production`.  The app continues to start; only the affected button is disabled on the frontend.

### Frontend (`frontend/.env.local`)

Copy `frontend/.env.local.example` to `frontend/.env.local` and fill in:

```bash
REACT_APP_API_URL=http://localhost:8000
REACT_APP_GOOGLE_CLIENT_ID=   # empty → Google button disabled, no SDK loaded
REACT_APP_APPLE_CLIENT_ID=    # empty → Apple button disabled, no SDK loaded
```

**Behavior when a client ID is empty:**
- The corresponding button is rendered with `opacity-40 cursor-not-allowed` and `title="… is not configured"`.
- No SDK script is loaded.
- No runtime errors occur.

---

## Auth Flows

### Email + Password

```
POST /api/v1/auth/register       → 201 {user}
POST /api/v1/auth/login          → 200 {access_token, refresh_token, user}
POST /api/v1/auth/logout         → 200
POST /api/v1/auth/refresh        → 200 {access_token}
POST /api/v1/auth/reset-password/request  → 200 (sends email)
POST /api/v1/auth/reset-password/confirm  → 200
POST /api/v1/auth/complete-onboarding     → 200 (sets has_completed_onboarding=true)
```

Password rules (backend + frontend must match):
- Min 8, max 100 characters
- At least one digit (0–9)
- At least one special character: `!@#$%^&*()_-+=[]{}|;:'",.<>/?`~`
- No uppercase/lowercase requirement

### Google Sign-In

**Prerequisites:**
- Google Cloud Console → APIs & Services → Credentials → OAuth 2.0 Client ID (Web application)
- Add `http://localhost:3000` to **Authorized JavaScript origins** (for local dev)
- Set `REACT_APP_GOOGLE_CLIENT_ID` in `frontend/.env.local`
- Set `GOOGLE_CLIENT_ID` in `backend/.env`

**Flow:**
1. User clicks Google button → `useGoogleLogin` (implicit flow) opens popup
2. Google returns `access_token`
3. Frontend calls `POST /api/v1/auth/social/google` with the access token
4. Backend calls `GET https://www.googleapis.com/oauth2/v2/userinfo` (Bearer)
5. Verifies `verified_email == true`
6. Looks up or creates user (3-step: provider-id → email fallback → create)
7. Returns `{access_token, refresh_token, user: {..., has_completed_onboarding}}`
8. Frontend routes: `has_completed_onboarding=false` → `/onboarding`; `true` → `/dashboard`

**First sign-in:** new user created, `has_completed_onboarding=false` → goes to onboarding.
**Repeat sign-in:** existing user found by `(social_provider, social_id)` → routed by onboarding flag.
**Deactivated account:** service raises `AuthenticationException("deactivated")` → HTTP 400.

### Apple Sign-In

**Prerequisites:**
- Apple Developer account with a **Service ID** (separate from App ID)
- Sign-In with Apple enabled on the Service ID
- Redirect domain registered: must be **HTTPS** — Apple does **not** work on plain `http://localhost`
- Set `REACT_APP_APPLE_CLIENT_ID` in `frontend/.env.local`
- Set `APPLE_CLIENT_ID` in `backend/.env`

**Flow:**
1. User clicks Apple button → Apple JS SDK (`appleid.auth.js`) loaded lazily on first click
2. `AppleID.auth.signIn()` opens Apple popup → returns `authorization.id_token` (JWT)
3. Frontend calls `POST /api/v1/auth/social/apple` with the `id_token`
4. Backend fetches Apple JWKS from `https://appleid.apple.com/auth/keys`
5. Verifies `iss`, `aud` (== `APPLE_CLIENT_ID`), signature, `exp`
6. Uses `sub` as stable identifier; `email` may be absent on repeat sign-ins
7. Same 3-step lookup as Google; returns same response shape

**Local dev limitation:** Apple Sign-In web requires HTTPS and a registered domain.
On `http://localhost`, the Apple button remains disabled (no `REACT_APP_APPLE_CLIENT_ID`).
To test locally, use a tunnel (ngrok with HTTPS) and register its domain in the Apple Developer portal.

**User cancellation:** `popup_closed_by_user` error is silently swallowed — no scary message.
**Deactivated account:** 400 with clear detail.
**Repeat sign-in without email:** resolved by `sub` lookup; only fails if the account was never created.

---

## How to Run Auth Tests

### Unit gate

```bash
cd backend
make test-unit
# or: pytest -q -m "not integration and not e2e and not slow"
```

Relevant unit test files:
- `tests/unit/test_password_validator.py` — 43 tests for password rules
- `tests/unit/test_social_auth_service.py` — service-layer tests (new/repeat login, backfill, active guard, verify_google_token, verify_apple_token JWKS flow)
- `tests/unit/test_social_auth_endpoints.py` — HTTP contract tests for /auth/social/google and /auth/social/apple
- `tests/unit/test_auth_lockout.py` — Redis-based login-attempt lockout

### Integration gate

Requires Docker (PostgreSQL on port 5434):

```bash
docker compose -f tests/docker-compose.test.yml up -d
cd backend
make test-integration
# or: pytest -q -m integration tests/integration/form_checks/ tests/integration/videos/ \
#       --override-ini="addopts=-q --asyncio-mode=auto --no-cov"
```

Relevant integration test files:
- `tests/integration/form_checks/test_auth_registration.py` — register → login → /users/me full flow
  - `test_register_returns_201`
  - `test_register_then_login_then_me` (verifies `has_completed_onboarding=false`)
  - `test_duplicate_email_returns_400`
  - `test_weak_password_returns_422`

### Manual E2E checklist

```bash
# Start backend + deps
docker compose -f infrastructure/docker/docker-compose.yml up -d db redis
cd backend && uvicorn app.main:app --reload &

# Start frontend
cd frontend && npm start
# Open http://localhost:3000
```

1. **Email signup**: Create account → auto-routed to `/onboarding` → complete → `/dashboard` → refresh → still on dashboard
2. **Email login** (returning user): Sign out → sign in → goes straight to `/dashboard` (no onboarding)
3. **Forgot password**: Click "Forgot password?" → enter email → "check email" message; click emailed link → `/reset-password?token=…` → set new password → redirect to login → sign in with new password ✓
4. **Google Sign-In** (needs `REACT_APP_GOOGLE_CLIENT_ID`): Click → popup → new user → `/onboarding`; returning user → `/dashboard`
5. **Apple Sign-In** (needs `REACT_APP_APPLE_CLIENT_ID` + HTTPS domain): Click → Apple popup → new user → `/onboarding`; returning user → `/dashboard`
6. **Apple Sign-In unconfigured**: Button is greyed out with tooltip "Apple Sign-In is not configured" — no errors
7. **Onboarding replay**: Profile page → "Replay Onboarding" → `/onboarding?replay=true` → stays logged in

---

## Limitations

| Item | Notes |
|---|---|
| Apple Sign-In on localhost | Not supported — Apple requires HTTPS + registered domain. Use a tunnel (e.g. ngrok) for integration testing. |
| Google Sign-In in TestClient | Unit tests mock `handle_social_login` — no real Google HTTP calls. Use the E2E checklist for real Google flows. |
| SMTP email delivery | Emails for verify/reset only work if `MAIL_SERVER` + credentials are configured. Missing config logs a warning but does not block auth. |
| Onboarding replay | Available at `/onboarding?replay=true`; `has_completed_onboarding` is **not** reset — user can re-enter preferences but won't be forced through onboarding on next login. |
