# G-16: log redaction — 2026-09-24

## Finding

structlog had no scrubbing processor and the stdlib handlers no filter; the only masking anywhere was
the Redis URL. Measured on the API's own log before the change (`docker compose logs app --since 12h`,
1,222 lines): 4 lines carried a user's e-mail address in clear (`register` and the SMTP warning),
0 carried a bearer token, and the validation handler logged `exc.errors()` whole — pydantic's error
objects include `input`, the submitted body, which on `/auth/register` and `/auth/login` is the
password. (Confirmed: the stored validation lines had keys `input, loc, msg, type, url`.)

## Change (`audit/g16-log-redaction`)

- `app/core/redaction.py`: one rule set — credential-named keys (`authorization`, `password`,
  `password_hash`, `secret`, `token`, `access_token`, `refresh_token`, `api_key`, `cookie`, …) masked
  whole; inside any string, JWT-shaped tokens, `Bearer <token>`, `password=<value>`-style fragments and
  the local part of e-mail addresses masked (`***@example.com`: the domain stays, it is what delivery
  debugging needs). Two hooks: `redact_event` (structlog processor, placed before `JSONRenderer` in
  `app/core/logging.py`) and `RedactingFilter` (stdlib `logging.Filter` on the console, file and
  error-file handlers, scrubbing the fully formatted message so templates and args are covered alike;
  `%s` placeholders are left intact).
- `app/core/exception_handlers.py`: the validation handler logs the errors without `input`.
- Tests: `tests/unit/test_log_redaction.py` (7: e-mail, JWT/Bearer, key=value vs placeholders,
  nested keys, processor, stdlib filter, the app config carries both hooks) and
  `tests/api/test_exception_handlers.py::test_a_validation_failure_on_register_does_not_log_the_submitted_password`
  (a real 422 on `/auth/register`; the handler's logger observed directly because the `app` loggers
  do not propagate to root). 11 passed in the worker image.

## Evidence on the running API

```bash
docker compose -f backend/deployment/docker-compose.yml restart app     # bind-mounted code
# then: register (201) -> login (200, JWT of 264 chars) -> an invalid register body (422) -> one upload (202)
docker compose -f backend/deployment/docker-compose.yml logs app --since <the run>
```

| in the new log segment (269 lines) | before the change | after |
|---|---|---|
| lines with an e-mail local part in clear | 4 per 1,222 lines over 12 h | **0** |
| lines with the e-mail masked (`***@example.com`) | — | 2 |
| lines containing the password value | (the 422 path logged it inside `input`) | **0** |
| lines containing the JWT | 0 | **0** |
| validation-error lines carrying an `input` key | all of them | **0** (1 validation line, without `input`) |

```
[WARNING] [app] {"extra": {"email": "***@example.com"}, "event": "Verification email was NOT delivered ..."}
[INFO]    [app] {"extra": {"user_id": "UUID('4644...')", "email": "***@example.com", "ip": "172.20.0.1", ...}}
```

## Not covered, on purpose

- `user_id` UUIDs and client IPs stay in the log: they are what an incident needs and are not
  credentials. Whether an IP is personal data for this deployment is a policy call, not a code one.
- Uvicorn's access log is configured separately (`logging.py` `uvicorn.access`); it logs paths and
  status codes, not bodies or headers.
