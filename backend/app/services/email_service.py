from typing import Optional, Dict, Any
from app.core.config import settings
from app.core.exceptions import EmailError
from app.core.logging import get_logger

logger = get_logger(__name__)

class EmailService:
    """Service for handling email operations."""

    @staticmethod
    async def send_email(
        to_email: str,
        subject: str,
        body: str,
        template_name: Optional[str] = None,
        template_vars: Optional[Dict[str, Any]] = None
    ) -> None:
        """Send an email."""
        try:
            # TODO: Implement actual email sending logic
            logger.info(f"Sending email to {to_email}: {subject}")
            if settings.TESTING:
                # In test mode, just log the email
                logger.debug(f"Email body: {body}")
                return
            
            # Mock successful email sending for now
            pass
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            raise EmailError(
                message=f"Failed to send email to {to_email}",
                details={"error": str(e)}
            )

    @staticmethod
    async def send_verification_email(email: str, token: str) -> None:
        """Send email verification link."""
        verification_url = f"{settings.SERVER_HOST}/verify-email?token={token}"
        subject = "Verify your email address"
        body = f"Please click the following link to verify your email address: {verification_url}"
        
        await EmailService.send_email(
            to_email=email,
            subject=subject,
            body=body,
            template_name="email_verification",
            template_vars={"verification_url": verification_url}
        )

    @staticmethod
    async def send_password_reset_email(email: str, token: str) -> None:
        """Send password reset link."""
        reset_url = f"{settings.SERVER_HOST}/reset-password?token={token}"
        subject = "Reset your password"
        body = f"Please click the following link to reset your password: {reset_url}"
        
        await EmailService.send_email(
            to_email=email,
            subject=subject,
            body=body,
            template_name="password_reset",
            template_vars={"reset_url": reset_url}
        ) 