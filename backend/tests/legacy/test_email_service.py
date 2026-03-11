import pytest
from unittest.mock import Mock, patch
from app.services.email import EmailService, EmailError
from app.core.config import settings
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

@pytest.fixture
def mock_smtp():
    """Mock SMTP server"""
    with patch('smtplib.SMTP') as mock_smtp:
        server = mock_smtp.return_value
        server.starttls = Mock()
        server.login = Mock()
        server.send_message = Mock()
        server.quit = Mock()
        yield server

@pytest.fixture
def email_service(mock_smtp):
    """Create an email service instance"""
    with patch.dict(os.environ, {
        'SMTP_HOST': 'smtp.test.com',
        'SMTP_PORT': '587',
        'SMTP_USERNAME': 'test@test.com',
        'SMTP_PASSWORD': 'test_password',
        'EMAIL_FROM': 'noreply@test.com'
    }):
        service = EmailService()
        return service

def test_send_welcome_email(email_service, mock_smtp):
    """Test sending welcome email"""
    email_service.send_welcome_email(
        to_email="user@example.com",
        username="testuser"
    )
    
    mock_smtp.send_message.assert_called_once()
    message = mock_smtp.send_message.call_args[0][0]
    assert isinstance(message, MIMEMultipart)
    assert message['To'] == "user@example.com"
    assert "Welcome" in message['Subject']

def test_send_password_reset_email(email_service, mock_smtp):
    """Test sending password reset email"""
    reset_token = "test_token_123"
    email_service.send_password_reset_email(
        to_email="user@example.com",
        reset_token=reset_token
    )
    
    mock_smtp.send_message.assert_called_once()
    message = mock_smtp.send_message.call_args[0][0]
    assert isinstance(message, MIMEMultipart)
    assert message['To'] == "user@example.com"
    assert "Password Reset" in message['Subject']

def test_send_subscription_confirmation_email(email_service, mock_smtp):
    """Test sending subscription confirmation email"""
    email_service.send_subscription_confirmation_email(
        to_email="user@example.com",
        subscription_tier="PRO",
        amount=29.99
    )
    
    mock_smtp.send_message.assert_called_once()
    message = mock_smtp.send_message.call_args[0][0]
    assert isinstance(message, MIMEMultipart)
    assert message['To'] == "user@example.com"
    assert "Subscription Confirmed" in message['Subject']

def test_send_subscription_cancellation_email(email_service, mock_smtp):
    """Test sending subscription cancellation email"""
    email_service.send_subscription_cancellation_email(
        to_email="user@example.com",
        subscription_tier="PRO"
    )
    
    mock_smtp.send_message.assert_called_once()
    message = mock_smtp.send_message.call_args[0][0]
    assert isinstance(message, MIMEMultipart)
    assert message['To'] == "user@example.com"
    assert "Subscription Cancelled" in message['Subject']

def test_send_form_check_complete_email(email_service, mock_smtp):
    """Test sending form check completion email"""
    email_service.send_form_check_complete_email(
        to_email="user@example.com",
        form_check_id=123,
        score=8.5
    )
    
    mock_smtp.send_message.assert_called_once()
    message = mock_smtp.send_message.call_args[0][0]
    assert isinstance(message, MIMEMultipart)
    assert message['To'] == "user@example.com"
    assert "Form Check Complete" in message['Subject']

def test_send_subscription_expiry_notification(email_service, mock_smtp):
    """Test sending subscription expiry notification"""
    email_service.send_subscription_expiry_notification(
        to_email="user@example.com",
        days_remaining=7
    )
    
    mock_smtp.send_message.assert_called_once()
    message = mock_smtp.send_message.call_args[0][0]
    assert isinstance(message, MIMEMultipart)
    assert message['To'] == "user@example.com"
    assert "Subscription Expiring" in message['Subject']

def test_send_email_validation_error(email_service, mock_smtp):
    """Test sending email with invalid email address"""
    with pytest.raises(EmailError):
        email_service.send_welcome_email(
            to_email="invalid_email",
            username="testuser"
        )

def test_send_email_smtp_error(email_service, mock_smtp):
    """Test handling SMTP server errors"""
    mock_smtp.send_message.side_effect = smtplib.SMTPException("Connection refused")
    
    with pytest.raises(EmailError):
        email_service.send_welcome_email(
            to_email="user@example.com",
            username="testuser"
        )

def test_send_email_authentication_error(email_service, mock_smtp):
    """Test handling SMTP authentication errors"""
    mock_smtp.login.side_effect = smtplib.SMTPAuthenticationError(535, "Invalid credentials")
    
    with pytest.raises(EmailError):
        email_service.send_welcome_email(
            to_email="user@example.com",
            username="testuser"
        )

def test_send_email_with_attachments(email_service, mock_smtp):
    """Test sending email with attachments"""
    attachments = [
        ("test.pdf", b"test content", "application/pdf"),
        ("image.jpg", b"image content", "image/jpeg")
    ]
    
    email_service.send_email_with_attachments(
        to_email="user@example.com",
        subject="Test Email with Attachments",
        body="Test body",
        attachments=attachments
    )
    
    mock_smtp.send_message.assert_called_once()
    message = mock_smtp.send_message.call_args[0][0]
    assert len(message.get_payload()) == 3  # Text part + 2 attachments

def test_send_bulk_emails(email_service, mock_smtp):
    """Test sending bulk emails"""
    recipients = [
        "user1@example.com",
        "user2@example.com",
        "user3@example.com"
    ]
    
    email_service.send_bulk_emails(
        recipients=recipients,
        subject="Bulk Test Email",
        body="Test body"
    )
    
    assert mock_smtp.send_message.call_count == 3
    for call in mock_smtp.send_message.call_args_list:
        message = call[0][0]
        assert message['To'] in recipients

def test_send_email_with_template(email_service, mock_smtp):
    """Test sending email using HTML template"""
    template_data = {
        "username": "testuser",
        "action_url": "https://test.com/action",
        "expiry_hours": 24
    }
    
    email_service.send_email_with_template(
        to_email="user@example.com",
        template_name="action_required",
        template_data=template_data
    )
    
    mock_smtp.send_message.assert_called_once()
    message = mock_smtp.send_message.call_args[0][0]
    assert isinstance(message, MIMEMultipart)
    assert "text/html" in str(message)

def test_send_email_rate_limiting(email_service, mock_smtp):
    """Test email rate limiting"""
    # Send multiple emails in quick succession
    for _ in range(5):
        email_service.send_welcome_email(
            to_email="user@example.com",
            username="testuser"
        )
    
    # Verify rate limiting
    assert mock_smtp.send_message.call_count <= 3  # Assuming rate limit of 3 emails per minute

def test_send_email_with_priority(email_service, mock_smtp):
    """Test sending high priority email"""
    email_service.send_email_with_priority(
        to_email="user@example.com",
        subject="High Priority Test",
        body="Test body",
        priority="high"
    )
    
    mock_smtp.send_message.assert_called_once()
    message = mock_smtp.send_message.call_args[0][0]
    assert message['X-Priority'] == '1'
    assert message['X-MSMail-Priority'] == 'High' 