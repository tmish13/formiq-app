"""
Email utility module for sending various types of emails.
This module provides functions to send verification, password reset,
and other notification emails using SMTP.
"""

import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import secrets
import string
from app.core.config import settings

def generate_verification_token(length=32):
    """Generate a random token for email verification"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def send_verification_email(email: str, token: str) -> bool:
    """
    Send an email verification link to a user.
    
    Args:
        email: Recipient's email address
        token: Verification token
        
    Returns:
        bool: True if email was sent successfully, False otherwise
        
    Raises:
        None: Errors are caught and returned as False
    """
    try:
        msg = MIMEMultipart()
        msg['Subject'] = 'Verify your email'
        msg['From'] = settings.SMTP_SENDER
        msg['To'] = email
        
        # Create verification link
        verification_link = f"{settings.FRONTEND_URL}/verify-email?token={token}"
        
        # Create email body
        body = f"""
        Please verify your email by clicking the link below:
        {verification_link}
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Send email
        with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.send_message(msg)
            
        return True
        
    except Exception as exc:
        print(f"Error sending verification email: {exc}")
        return False

def send_password_reset_email(email: str, token: str) -> bool:
    """
    Send a password reset link to a user.
    
    Args:
        email: Recipient's email address
        token: Password reset token
        
    Returns:
        bool: True if email was sent successfully, False otherwise
        
    Raises:
        None: Errors are caught and returned as False
    """
    try:
        msg = MIMEMultipart()
        msg['From'] = settings.SMTP_SENDER
        msg['To'] = email
        msg['Subject'] = "Reset your FormIQ password"
        
        body = f"""
        You requested to reset your FormIQ password.
        
        Please click the following link to reset your password:
        {settings.FRONTEND_URL}/reset-password?token={token}
        
        If you didn't request a password reset, you can safely ignore this email.
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.send_message(msg)
            
        return True
        
    except Exception as exc:
        print(f"Error sending password reset email: {exc}")
        return False 