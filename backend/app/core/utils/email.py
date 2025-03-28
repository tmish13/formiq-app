"""
Email utility module for sending various types of emails.
This module provides functions for sending verification and password reset emails.
"""

import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import secrets
import string
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

def generate_verification_token() -> str:
    """Generate a verification token."""
    return secrets.token_urlsafe(32)

def send_email(
    email_to: str,
    subject: str,
    html_content: str,
) -> bool:
    """Send an email."""
    try:
        msg = MIMEMultipart()
        msg["Subject"] = subject
        msg["From"] = f"{settings.EMAILS_FROM_NAME} <{settings.EMAILS_FROM_EMAIL}>"
        msg["To"] = email_to
        
        msg.attach(MIMEText(html_content, "html"))
        
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            if settings.SMTP_TLS:
                server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
        
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {str(e)}")
        return False

def send_verification_email(email_to: str, token: str) -> bool:
    """Send verification email."""
    subject = "Verify your email"
    verification_url = f"http://localhost:3000/verify-email?token={token}"
    html_content = f"""
        <p>Hi,</p>
        <p>Please verify your email by clicking the link below:</p>
        <p><a href="{verification_url}">Verify Email</a></p>
        <p>If you did not create an account, you can safely ignore this email.</p>
    """
    return send_email(email_to, subject, html_content)

def send_password_reset_email(email_to: str, token: str) -> bool:
    """Send password reset email."""
    subject = "Reset your password"
    reset_url = f"http://localhost:3000/reset-password?token={token}"
    html_content = f"""
        <p>Hi,</p>
        <p>You have requested to reset your password. Click the link below to proceed:</p>
        <p><a href="{reset_url}">Reset Password</a></p>
        <p>If you did not request a password reset, you can safely ignore this email.</p>
    """
    return send_email(email_to, subject, html_content) 