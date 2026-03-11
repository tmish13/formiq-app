"""Debug endpoints — only active in non-production environments."""
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr

from app.core.config import settings
from app.core.logging import logger
from app.services.email_service import EmailService

router = APIRouter()

# ---------------------------------------------------------------------------
# Beta feedback  (accessible in all environments — no production guard)
# ---------------------------------------------------------------------------

beta_router = APIRouter()


class BetaFeedbackRequest(BaseModel):
    user_id: Optional[str] = None
    category: Optional[str] = None
    message: str
    score: Optional[float] = None
    exercise: Optional[str] = None
    timestamp: Optional[str] = None


class BetaFeedbackResponse(BaseModel):
    received: bool


@beta_router.post(
    "/beta-feedback",
    response_model=BetaFeedbackResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit beta tester feedback",
    tags=["beta"],
)
async def submit_beta_feedback(body: BetaFeedbackRequest) -> BetaFeedbackResponse:
    """
    Accepts beta-tester feedback submitted from the ProfilePage.
    Logs the payload and returns 200 immediately.
    No database write — feedback is captured in structured logs for now.
    """
    logger.info(
        "Beta feedback received",
        extra={
            "user_id": body.user_id,
            "category": body.category or "General",
            "score": body.score,
            "exercise": body.exercise,
            "timestamp": body.timestamp,
            # message is intentionally last so it's easy to filter in logs
            "message": body.message[:500],  # truncate very long messages
        },
    )
    return BetaFeedbackResponse(received=True)


def _require_non_production() -> None:
    """Raise 404 in production so these endpoints are invisible to the outside world."""
    if str(settings.ENVIRONMENT).lower() == "production":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


class EmailTestRequest(BaseModel):
    to: EmailStr


class EmailTestResponse(BaseModel):
    sent: bool
    smtp_server: str
    smtp_username: str
    error: str | None = None


@router.post(
    "/email-test",
    response_model=EmailTestResponse,
    summary="Send a test email (non-production only)",
    description=(
        "Attempts to send a test email using the current SMTP config. "
        "Always returns 200 — check 'sent' and 'error' fields for the result. "
        "Returns 404 in production environments. "
        "Use this to verify your MAIL_* env vars are correct before enabling verification emails."
    ),
    tags=["debug"],
)
async def test_email(body: EmailTestRequest) -> Any:
    _require_non_production()

    smtp_server = f"{settings.MAIL_SERVER}:{settings.MAIL_PORT}"
    smtp_username = settings.MAIL_USERNAME or "(not set)"

    logger.info(
        "Debug email test requested",
        extra={"to": str(body.to), "smtp_server": smtp_server, "smtp_username": smtp_username},
    )

    # Gate: check placeholder / missing config before attempting SMTP
    if not settings.emails_enabled:
        logger.warning(
            "Debug email test: skipped — emails_enabled=False. "
            "SMTP credentials are missing or still contain placeholder values.",
            extra={"smtp_username": smtp_username, "smtp_server": smtp_server},
        )
        return EmailTestResponse(
            sent=False,
            smtp_server=smtp_server,
            smtp_username=smtp_username,
            error=(
                "Email is disabled — SMTP credentials are missing or still contain placeholder "
                "values. Set real MAIL_USERNAME, MAIL_PASSWORD, and MAIL_FROM_EMAIL in "
                "backend/.env, then restart the server."
            ),
        )

    try:
        sent = await EmailService.send_email(
            recipients=[str(body.to)],
            subject="FormIQ — Test Email",
            html_template_name="email_test.html",
            text_template_name="email_test.txt",
            template_data={
                "smtp_server": smtp_server,
                "smtp_username": smtp_username,
                "environment": str(settings.ENVIRONMENT),
            },
        )
    except Exception as exc:
        logger.exception("Debug email test raised an unexpected exception.")
        return EmailTestResponse(
            sent=False,
            smtp_server=smtp_server,
            smtp_username=smtp_username,
            error=f"Unexpected error: {type(exc).__name__}. Check backend logs for details.",
        )

    if not sent:
        return EmailTestResponse(
            sent=False,
            smtp_server=smtp_server,
            smtp_username=smtp_username,
            error=(
                "SMTP send failed. Check backend logs for the specific error. "
                "Common causes: wrong MAIL_PASSWORD (Gmail requires an App Password, not your "
                "login password), MAIL_USERNAME mismatch, or SMTP port blocked by firewall."
            ),
        )

    logger.info(
        "Debug email test succeeded.",
        extra={"to": str(body.to), "smtp_server": smtp_server},
    )
    return EmailTestResponse(
        sent=True,
        smtp_server=smtp_server,
        smtp_username=smtp_username,
    )
