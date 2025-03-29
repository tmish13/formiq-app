from typing import List, Optional
from app.core.exceptions import ServiceError
from app.core.config import settings

class EmailError(ServiceError):
    """Exception raised for email-related errors."""
    pass

class EmailService:
    def __init__(self):
        self.sender_email = settings.EMAIL_SENDER
        self.smtp_server = settings.SMTP_SERVER
        self.smtp_port = settings.SMTP_PORT
        self.smtp_username = settings.SMTP_USERNAME
        self.smtp_password = settings.SMTP_PASSWORD

    async def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        html_body: Optional[str] = None
    ) -> None:
        """Send an email."""
        try:
            # Implementation for sending email
            pass
        except Exception as e:
            raise EmailError(f"Failed to send email: {str(e)}")

    async def send_welcome_email(self, to_email: str, username: str) -> None:
        """Send a welcome email to a new user."""
        try:
            subject = "Welcome to FormIQ!"
            body = f"Hi {username},\n\nWelcome to FormIQ! We're excited to have you on board."
            html_body = f"<h1>Welcome to FormIQ!</h1><p>Hi {username},</p><p>Welcome to FormIQ! We're excited to have you on board.</p>"
            await self.send_email(to_email, subject, body, html_body)
        except Exception as e:
            raise EmailError(f"Failed to send welcome email: {str(e)}")

    async def send_password_reset_email(self, to_email: str, reset_token: str) -> None:
        """Send a password reset email."""
        try:
            subject = "Password Reset Request"
            reset_url = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
            body = f"Click the following link to reset your password: {reset_url}"
            html_body = f"<p>Click the following link to reset your password: <a href='{reset_url}'>{reset_url}</a></p>"
            await self.send_email(to_email, subject, body, html_body)
        except Exception as e:
            raise EmailError(f"Failed to send password reset email: {str(e)}")

    async def send_verification_email(self, to_email: str, verification_token: str) -> None:
        """Send an email verification email."""
        try:
            subject = "Verify Your Email"
            verification_url = f"{settings.FRONTEND_URL}/verify-email?token={verification_token}"
            body = f"Click the following link to verify your email: {verification_url}"
            html_body = f"<p>Click the following link to verify your email: <a href='{verification_url}'>{verification_url}</a></p>"
            await self.send_email(to_email, subject, body, html_body)
        except Exception as e:
            raise EmailError(f"Failed to send verification email: {str(e)}")

    async def send_workout_reminder(self, to_email: str, username: str, workout_name: str) -> None:
        """Send a workout reminder email."""
        try:
            subject = "Workout Reminder"
            body = f"Hi {username},\n\nThis is a reminder that you have a workout scheduled: {workout_name}"
            html_body = f"<h1>Workout Reminder</h1><p>Hi {username},</p><p>This is a reminder that you have a workout scheduled: {workout_name}</p>"
            await self.send_email(to_email, subject, body, html_body)
        except Exception as e:
            raise EmailError(f"Failed to send workout reminder: {str(e)}")

    async def send_subscription_receipt(self, to_email: str, amount: float, plan_name: str) -> None:
        """Send a subscription receipt email."""
        try:
            subject = "Subscription Receipt"
            body = f"Thank you for your subscription to {plan_name}. Amount charged: ${amount:.2f}"
            html_body = f"<h1>Subscription Receipt</h1><p>Thank you for your subscription to {plan_name}. Amount charged: ${amount:.2f}</p>"
            await self.send_email(to_email, subject, body, html_body)
        except Exception as e:
            raise EmailError(f"Failed to send subscription receipt: {str(e)}") 