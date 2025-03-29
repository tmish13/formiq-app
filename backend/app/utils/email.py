from typing import List, Optional
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings
from app.core.logging import get_logger

# Initialize logger
logger = get_logger(__name__)

class EmailService:
    def __init__(self):
        self.smtp_server = settings.SMTP_SERVER
        self.smtp_port = settings.SMTP_PORT
        self.smtp_username = settings.SMTP_USERNAME
        self.smtp_password = settings.SMTP_PASSWORD
        self.from_email = settings.FROM_EMAIL

    async def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        html: Optional[str] = None
    ) -> bool:
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.from_email
            msg['To'] = to_email

            # Attach plain text version
            msg.attach(MIMEText(body, 'plain'))

            # Attach HTML version if provided
            if html:
                msg.attach(MIMEText(html, 'html'))

            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)

            logger.info(f"Email sent successfully to {to_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False

    async def send_verification_email(self, to_email: str, token: str) -> bool:
        subject = "Verify your email address"
        verification_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"
        
        body = f"""
        Please verify your email address by clicking the link below:
        
        {verification_url}
        
        If you did not create an account, please ignore this email.
        """
        
        html = f"""
        <html>
            <body>
                <h1>Verify your email address</h1>
                <p>Please verify your email address by clicking the link below:</p>
                <p><a href="{verification_url}">Verify Email</a></p>
                <p>If you did not create an account, please ignore this email.</p>
            </body>
        </html>
        """
        
        return await self.send_email(to_email, subject, body, html)

    async def send_password_reset_email(self, to_email: str, token: str) -> bool:
        subject = "Reset your password"
        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"
        
        body = f"""
        You have requested to reset your password. Click the link below to proceed:
        
        {reset_url}
        
        If you did not request a password reset, please ignore this email.
        """
        
        html = f"""
        <html>
            <body>
                <h1>Reset your password</h1>
                <p>You have requested to reset your password. Click the link below to proceed:</p>
                <p><a href="{reset_url}">Reset Password</a></p>
                <p>If you did not request a password reset, please ignore this email.</p>
            </body>
        </html>
        """
        
        return await self.send_email(to_email, subject, body, html) 