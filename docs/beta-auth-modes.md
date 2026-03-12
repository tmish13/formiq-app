# FormIQ Beta Auth Modes

Two clearly defined operating modes prevent the "verification required but emails can't send" deadlock.

---

## Switching Modes

```bash
# Mode A — Local beta (no email required):
cp backend/.env.beta-local backend/.env
# Restart backend (see below)

# Mode B — Real email verification (requires SMTP):
cp backend/.env.beta-email backend/.env
# Fill in real MAIL_* values in backend/.env
# Verify SMTP works before inviting testers (see Mode B checklist below)
# Restart backend
```

### Restart the backend

`--reload` does NOT re-read `.env`. You must kill and restart:

```bash
# Find the PID:
lsof -i :8000 | grep LISTEN

# Kill and restart:
kill -9 <PID>
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Confirm which mode you're in

```bash
curl http://localhost:8000/api/v1/health/health/auth-config | python3 -m json.tool
```

| Response | Meaning |
|----------|---------|
| `{"beta_allow_unverified": true, "smtp_configured": false, "deadlock": false}` | Mode A — local beta, working |
| `{"beta_allow_unverified": false, "smtp_configured": true, "deadlock": false}` | Mode B — email verification, working |
| `{"deadlock": true}` | **BROKEN** — fix before inviting anyone |

---

## Mode A — Local Beta (no SMTP required)

**Config file:** `.env.beta-local` → `BETA_ALLOW_UNVERIFIED=true`

### Smoke test checklist

- [ ] `curl http://localhost:8000/api/v1/health/health/auth-config` returns `"beta_allow_unverified": true, "deadlock": false`
- [ ] Open `http://localhost:3000` → tap **Sign Up**
- [ ] Register with a real (or made-up) email + strong password (e.g. `MyPass1!`)
- [ ] Confirm you are **immediately** redirected to login / onboarding — no "check your inbox" required
- [ ] Log in → dashboard loads
- [ ] Amber banner visible: **"Beta mode — your email isn't verified yet"** with a Resend button
- [ ] Complete onboarding (goal + exercises)
- [ ] Record a squat video (2–7 seconds, full body in frame)
- [ ] Analysis results page loads with score, tabs, breakdown
- [ ] History page shows the new card
- [ ] Progress page shows trend (needs 2+ sessions for chart)
- [ ] No 403 errors in browser DevTools

---

## Mode B — Real Email Verification

**Config file:** `.env.beta-email` → `BETA_ALLOW_UNVERIFIED=false` + real SMTP

### Pre-tester SMTP checklist (do this FIRST)

1. Copy and fill in credentials:
   ```bash
   cp backend/.env.beta-email backend/.env
   # Edit backend/.env — replace YOUR_REAL_GMAIL, YOUR_REAL_APP_PASSWORD
   ```

2. Restart the backend (see above).

3. Verify SMTP works:
   ```bash
   curl -s -X POST http://localhost:8000/api/v1/debug/email-test \
     -H "Content-Type: application/json" \
     -d '{"to": "your.real.email@gmail.com"}' | python3 -m json.tool
   ```
   **Expected:** `{"sent": true, "smtp_server": "smtp.gmail.com:587", "smtp_username": "...", "error": null}`

   If `sent: false` — check the `error` field and backend logs. Common causes:
   - Wrong password (Gmail requires an App Password, not your login password)
   - 2FA not enabled on the Google account
   - `MAIL_USERNAME` doesn't match `MAIL_FROM_EMAIL`

4. Confirm auth-config:
   ```bash
   curl http://localhost:8000/api/v1/health/health/auth-config
   # Expected: {"beta_allow_unverified": false, "smtp_configured": true, "deadlock": false}
   ```

### Smoke test checklist

- [ ] `auth-config` shows `"deadlock": false`
- [ ] `/debug/email-test` returns `"sent": true`
- [ ] Register with a **real** email address you can access
- [ ] Confirm you are **blocked** from logging in immediately — app shows "check your inbox"
- [ ] Check inbox — verification email arrives within 60 seconds
- [ ] Click the verification link → redirected to "Email Verified" screen → tap "Continue to Login"
- [ ] Log in → succeeds, `is_verified=true` in DB
- [ ] **No amber banner** visible on dashboard (user is verified)
- [ ] Resend flow: on login page, click "Resend verification email" → new email arrives → original link still works (idempotent)
- [ ] Attempt to log in **before** verifying → 403 response, app shows "check your inbox" screen with Resend CTA

---

## What to Check Before Inviting a Beta Tester

| Check | Command | Expected |
|-------|---------|----------|
| Backend alive | `curl http://localhost:8000/api/v1/health/health/auth-config` | 200, no deadlock |
| Mode A: any user can log in | register + login | immediate access, amber banner |
| Mode B: SMTP works | `/debug/email-test` | `"sent": true` |
| Mode B: verification required | register + try to log in | blocked until email clicked |
| Frontend alive | open `http://localhost:3000` | login page loads |

---

## Deadlock Prevention

At startup, the backend logs a **CRITICAL** warning if `BETA_ALLOW_UNVERIFIED=false` AND SMTP is not configured:

```
CONFIGURATION DEADLOCK: BETA_ALLOW_UNVERIFIED=false but SMTP is not configured.
New users cannot verify their email, so NO ONE can log in.
Fix: set BETA_ALLOW_UNVERIFIED=true in .env (use .env.beta-local) or
configure real MAIL_* credentials (use .env.beta-email) and restart.
```

The `/health/auth-config` endpoint also exposes `"deadlock": true` for automated monitoring.
