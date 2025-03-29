"""Service for handling email operations."""
from typing import List, Dict, Any, Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
import os
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

class EmailError(Exception):
    """Custom exception for email service errors."""
    pass

class EmailService:
    """Service for handling email operations."""
    
    def __init__(self):
        """Initialize email service with SMTP settings."""
        self.smtp_host = os.environ.get('SMTP_HOST', settings.SMTP_HOST)
        self.smtp_port = int(os.environ.get('SMTP_PORT', settings.SMTP_PORT))
        self.smtp_username = os.environ.get('SMTP_USERNAME', settings.SMTP_USERNAME)
        self.smtp_password = os.environ.get('SMTP_PASSWORD', settings.SMTP_PASSWORD)
        self.email_from = os.environ.get('EMAIL_FROM', settings.EMAIL_FROM)

    def _create_smtp_server(self) -> smtplib.SMTP:
        """Create and configure SMTP server connection."""
        try:
            server = smtplib.SMTP(self.smtp_host, self.smtp_port)
            server.starttls()
            server.login(self.smtp_username, self.smtp_password)
            return server
        except Exception as e:
            logger.error(f"Failed to create SMTP server: {str(e)}")
            raise EmailError(f"Failed to create SMTP server: {str(e)}")

    def send_email(self, to_email: str, subject: str, body: str, is_html: bool = False) -> None:
        """Send an email to the specified recipient."""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_from
            msg['To'] = to_email
            msg['Subject'] = subject

            content_type = 'html' if is_html else 'plain'
            msg.attach(MIMEText(body, content_type))

            server = self._create_smtp_server()
            server.send_message(msg)
            server.quit()
            
            logger.info(f"Email sent successfully to {to_email}")
        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}")
            raise EmailError(f"Failed to send email: {str(e)}")

    def send_welcome_email(self, to_email: str, username: str) -> None:
        """Send welcome email to new users."""
        subject = "Welcome to FormIQ!"
        body = f"""
        <html>
            <body>
                <h2>Welcome to FormIQ, {username}!</h2>
                <p>Thank you for joining our platform. We're excited to help you improve your exercise form.</p>
                <p>Get started by:</p>
                <ul>
                    <li>Creating your first workout</li>
                    <li>Recording your exercise form</li>
                    <li>Getting AI-powered feedback</li>
                </ul>
                <p>If you have any questions, feel free to reach out to our support team.</p>
                <p>Best regards,<br>The FormIQ Team</p>
            </body>
        </html>
        """
        self.send_email(to_email, subject, body, is_html=True)

    def send_form_analysis_email(self, to_email: str, analysis_results: Dict[str, Any]) -> None:
        """Send email with form analysis results."""
        subject = "Your Exercise Form Analysis Results"
        body = f"""
        <html>
            <body>
                <h2>Exercise Form Analysis Results</h2>
                <p>Score: {analysis_results.get('score', 'N/A')}/100</p>
                <h3>Feedback:</h3>
                <ul>
                    {''.join([f'<li>{feedback}</li>' for feedback in analysis_results.get('feedback', [])])}
                </ul>
                <h3>Suggestions for Improvement:</h3>
                <ul>
                    {''.join([f'<li>{suggestion}</li>' for suggestion in analysis_results.get('suggestions', [])])}
                </ul>
                <p>Keep up the great work!</p>
                <p>Best regards,<br>The FormIQ Team</p>
            </body>
        </html>
        """
        self.send_email(to_email, subject, body, is_html=True) 