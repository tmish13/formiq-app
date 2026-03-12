"""Email service for sending app emails."""
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pydantic import EmailStr
from app.core.config import settings, Environment as AppEnvironment, get_settings
from app.models.user import User
from app.models.video import Video
from app.core.monitoring import track_email_sent
from functools import lru_cache
from app.core.celery_app import celery_app

# Set up logging
logger = logging.getLogger(__name__)

# Initialize settings to ensure ENVIRONMENT is correctly loaded for SUPPRESS_SEND
settings = get_settings()

# Configure Jinja2 for email templates
email_templates_dir = Path(settings.EMAIL_TEMPLATES_DIR)
jinja_env = Environment(
    loader=FileSystemLoader(email_templates_dir),
    autoescape=select_autoescape(['html', 'xml'])
)

# Configure FastMail
mail_config = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD.get_secret_value() if settings.MAIL_PASSWORD else "",
    MAIL_FROM=settings.MAIL_FROM_EMAIL,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_FROM_NAME=settings.MAIL_FROM_NAME,
    MAIL_STARTTLS=settings.MAIL_STARTTLS,
    MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
    USE_CREDENTIALS=settings.MAIL_USE_CREDENTIALS,
    VALIDATE_CERTS=settings.MAIL_VALIDATE_CERTS,
    TEMPLATE_FOLDER=str(settings.EMAIL_TEMPLATES_DIR),
    SUPPRESS_SEND= 1 if settings.ENVIRONMENT == AppEnvironment.TEST else 0
)

# Initialize FastMail
fast_mail = FastMail(mail_config)

class EmailService:
    """Email service for sending app emails."""
    
    @staticmethod
    async def send_email(
        recipients: List[EmailStr],
        subject: str,
        html_template_name: str,
        text_template_name: str,
        template_data: Dict[str, Any]
    ) -> bool:
        """
        Send an email with both HTML and text versions.
        
        Args:
            recipients: List of email addresses to send to
            subject: Email subject
            html_template_name: Name of HTML template file
            text_template_name: Name of text template file
            template_data: Data to render templates with
            
        Returns:
            bool: True if email sent successfully
        """
        try:
            # Add current year to template data for copyright
            if 'year' not in template_data:
                template_data['year'] = datetime.now().year
                
            # Render HTML template
            html_template = jinja_env.get_template(html_template_name)
            html_content = html_template.render(**template_data)
            
            # Render text template
            text_template = jinja_env.get_template(text_template_name)
            text_content = text_template.render(**template_data)
            
            # Create message
            message = MessageSchema(
                subject=subject,
                recipients=recipients,
                body=html_content,
                subtype=MessageType.html,
                alternative_body=text_content
            )
            
            # Log the attempt before hitting the network so any failure is traceable.
            # Never log MAIL_PASSWORD.
            logger.info(
                "Attempting SMTP send via %s as %s",
                f"{settings.MAIL_SERVER}:{settings.MAIL_PORT}",
                settings.MAIL_USERNAME or "(not set)",
                extra={"recipients": recipients, "subject": subject},
            )

            # Send email
            await fast_mail.send_message(message)

            # Track email sent
            track_email_sent("outbound")

            logger.info(
                "Email sent successfully.",
                extra={"recipients": recipients, "subject": subject},
            )
            return True

        except Exception:
            # logger.exception captures the full traceback without needing to pass the error.
            # Never log MAIL_PASSWORD.
            logger.exception(
                "SMTP send failed.",
                extra={
                    "smtp_server": f"{settings.MAIL_SERVER}:{settings.MAIL_PORT}",
                    "smtp_username": settings.MAIL_USERNAME or "(not set)",
                    "recipients": recipients,
                    "subject": subject,
                },
            )
            return False
    
    @staticmethod
    async def send_verification_email(user: User, verification_url: str, verification_code: str) -> bool:
        """
        Send email verification email.
        
        Args:
            user: User to send email to
            verification_url: URL for email verification
            verification_code: Verification code
            
        Returns:
            bool: True if email sent successfully
        """
        subject = "Verify Your FormIQ Account"
        recipients = [str(user.email)]
        
        template_data = {
            "user": user,
            "verification_url": verification_url,
            "verification_code": verification_code
        }
        
        return await EmailService.send_email(
            recipients=recipients,
            subject=subject,
            html_template_name="email_verification.html",
            text_template_name="email_verification.txt",
            template_data=template_data
        )
    
    @staticmethod
    async def send_password_reset_email(user: User, reset_url: str, reset_code: str, expire_hours: int = 24) -> bool:
        """
        Send password reset email.
        
        Args:
            user: User to send email to
            reset_url: URL for password reset
            reset_code: Reset code
            expire_hours: Hours until reset link expires
            
        Returns:
            bool: True if email sent successfully
        """
        subject = "Reset Your FormIQ Password"
        recipients = [str(user.email)]
        
        template_data = {
            "user": user,
            "reset_url": reset_url,
            "reset_code": reset_code,
            "expire_hours": expire_hours
        }
        
        return await EmailService.send_email(
            recipients=recipients,
            subject=subject,
            html_template_name="password_reset.html",
            text_template_name="password_reset.txt",
            template_data=template_data
        )
    
    @staticmethod
    async def send_welcome_email(user: User) -> bool:
        """
        Send welcome email to new users after verification.
        
        Args:
            user: User to send email to
            
        Returns:
            bool: True if email sent successfully
        """
        subject = "Welcome to FormIQ!"
        recipients = [str(user.email)]
        
        template_data = {
            "user": user,
            "login_url": f"{settings.FRONTEND_URL}/login"
        }
        
        return await EmailService.send_email(
            recipients=recipients,
            subject=subject,
            html_template_name="welcome.html",
            text_template_name="welcome.txt",
            template_data=template_data
        )
    
    @staticmethod
    async def send_analysis_complete_notification(user: User, video: Video) -> bool:
        """
        Send notification when video analysis is complete.
        
        Args:
            user: User to send email to
            video: The analyzed video
            
        Returns:
            bool: True if email sent successfully
        """
        subject = "Your Video Analysis is Complete"
        recipients = [str(user.email)]
        
        view_url = f"{settings.FRONTEND_URL}/videos/{video.id}"
        
        template_data = {
            "user": user,
            "video": video,
            "view_url": view_url,
            "score": video.score if hasattr(video, 'score') else None,
            "feedback_points": video.feedback if hasattr(video, 'feedback') else [],
            "app_name": "FormIQ"
        }
        
        return await EmailService.send_email(
            recipients=recipients,
            subject=subject,
            html_template_name="analysis_complete.html",
            text_template_name="analysis_complete.txt",
            template_data=template_data
        )
        
    @staticmethod
    async def get_email_rate_limit(email: str) -> Dict[str, Any]:
        """
        Get rate limit information for an email address.
        Used to enforce rate limits on email sending.
        
        Args:
            email: Email address to check
            
        Returns:
            Dict with rate limit information
        """
        from app.core.rate_limit import get_rate_limit_info
        
        # Get rate limit info for different email types
        rate_limits = {
            "verification": await get_rate_limit_info(f"email:verification:{email}"),
            "password_reset": await get_rate_limit_info(f"email:password_reset:{email}"),
            "notification": await get_rate_limit_info(f"email:notification:{email}")
        }
        
        return {
            "email": email,
            "rate_limits": rate_limits,
            "can_send_verification": rate_limits["verification"]["remaining"] > 0,
            "can_send_password_reset": rate_limits["password_reset"]["remaining"] > 0,
            "can_send_notification": rate_limits["notification"]["remaining"] > 0,
        } 