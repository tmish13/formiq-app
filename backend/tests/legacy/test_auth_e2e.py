"""End-to-end tests for authentication functionality."""
import pytest
from datetime import datetime, timedelta
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from app.core.config import settings
from app.models.user import User
from app.core.security import get_password_hash

@pytest.fixture
def driver():
    """Create a new WebDriver instance for each test."""
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # Run in headless mode
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=options)
    yield driver
    driver.quit()

@pytest.fixture
def wait(driver):
    """Create a WebDriverWait instance."""
    return WebDriverWait(driver, 10)

def test_complete_auth_flow(driver, wait):
    """Test the complete authentication flow from registration to logout."""
    # Navigate to registration page
    driver.get(f"{settings.FRONTEND_URL}/register")
    
    # Fill registration form
    email_input = wait.until(EC.presence_of_element_located((By.NAME, "email")))
    email_input.send_keys("testuser@example.com")
    
    password_input = driver.find_element(By.NAME, "password")
    password_input.send_keys("TestPassword123!")
    
    confirm_password_input = driver.find_element(By.NAME, "confirm_password")
    confirm_password_input.send_keys("TestPassword123!")
    
    full_name_input = driver.find_element(By.NAME, "full_name")
    full_name_input.send_keys("Test User")
    
    # Submit registration
    submit_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
    submit_button.click()
    
    # Wait for success message
    success_message = wait.until(
        EC.presence_of_element_located((By.CLASS_NAME, "success-message"))
    )
    assert "Registration successful" in success_message.text
    
    # Navigate to login page
    driver.get(f"{settings.FRONTEND_URL}/login")
    
    # Fill login form
    email_input = wait.until(EC.presence_of_element_located((By.NAME, "email")))
    email_input.send_keys("testuser@example.com")
    
    password_input = driver.find_element(By.NAME, "password")
    password_input.send_keys("TestPassword123!")
    
    # Submit login
    submit_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
    submit_button.click()
    
    # Wait for successful login
    dashboard = wait.until(
        EC.presence_of_element_located((By.CLASS_NAME, "dashboard"))
    )
    assert "Welcome" in dashboard.text
    
    # Test password reset flow
    # Click forgot password link
    forgot_password_link = driver.find_element(By.LINK_TEXT, "Forgot Password?")
    forgot_password_link.click()
    
    # Fill email for password reset
    email_input = wait.until(EC.presence_of_element_located((By.NAME, "email")))
    email_input.send_keys("testuser@example.com")
    
    # Submit password reset request
    submit_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
    submit_button.click()
    
    # Wait for success message
    success_message = wait.until(
        EC.presence_of_element_located((By.CLASS_NAME, "success-message"))
    )
    assert "Password reset email sent" in success_message.text
    
    # Test email verification flow
    # Click resend verification email
    resend_verification_link = driver.find_element(By.LINK_TEXT, "Resend Verification Email")
    resend_verification_link.click()
    
    # Wait for success message
    success_message = wait.until(
        EC.presence_of_element_located((By.CLASS_NAME, "success-message"))
    )
    assert "Verification email sent" in success_message.text
    
    # Test logout
    # Click logout button
    logout_button = driver.find_element(By.LINK_TEXT, "Logout")
    logout_button.click()
    
    # Wait for redirect to login page
    login_form = wait.until(
        EC.presence_of_element_located((By.CLASS_NAME, "login-form"))
    )
    assert "Login" in login_form.text

def test_invalid_login_attempts(driver, wait):
    """Test handling of invalid login attempts."""
    # Navigate to login page
    driver.get(f"{settings.FRONTEND_URL}/login")
    
    # Try invalid credentials multiple times
    for _ in range(5):
        email_input = wait.until(EC.presence_of_element_located((By.NAME, "email")))
        email_input.send_keys("testuser@example.com")
        
        password_input = driver.find_element(By.NAME, "password")
        password_input.send_keys("WrongPassword123!")
        
        submit_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        submit_button.click()
        
        # Wait for error message
        error_message = wait.until(
            EC.presence_of_element_located((By.CLASS_NAME, "error-message"))
        )
        assert "Incorrect email or password" in error_message.text
        
        # Clear fields for next attempt
        email_input.clear()
        password_input.clear()
    
    # Verify account is temporarily locked
    email_input = wait.until(EC.presence_of_element_located((By.NAME, "email")))
    email_input.send_keys("testuser@example.com")
    
    password_input = driver.find_element(By.NAME, "password")
    password_input.send_keys("TestPassword123!")
    
    submit_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
    submit_button.click()
    
    # Wait for account locked message
    error_message = wait.until(
        EC.presence_of_element_located((By.CLASS_NAME, "error-message"))
    )
    assert "Account temporarily locked" in error_message.text

def test_password_reset_flow(driver, wait):
    """Test the complete password reset flow."""
    # Navigate to password reset page
    driver.get(f"{settings.FRONTEND_URL}/reset-password")
    
    # Fill email for password reset
    email_input = wait.until(EC.presence_of_element_located((By.NAME, "email")))
    email_input.send_keys("testuser@example.com")
    
    # Submit password reset request
    submit_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
    submit_button.click()
    
    # Wait for success message
    success_message = wait.until(
        EC.presence_of_element_located((By.CLASS_NAME, "success-message"))
    )
    assert "Password reset email sent" in success_message.text
    
    # Navigate to password reset confirmation page with token
    # In a real test, we would get the token from the email
    reset_token = "test_reset_token"  # This would be a real token in production
    driver.get(f"{settings.FRONTEND_URL}/reset-password/{reset_token}")
    
    # Fill new password
    new_password_input = wait.until(EC.presence_of_element_located((By.NAME, "new_password")))
    new_password_input.send_keys("NewPassword123!")
    
    confirm_password_input = driver.find_element(By.NAME, "confirm_password")
    confirm_password_input.send_keys("NewPassword123!")
    
    # Submit new password
    submit_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
    submit_button.click()
    
    # Wait for success message
    success_message = wait.until(
        EC.presence_of_element_located((By.CLASS_NAME, "success-message"))
    )
    assert "Password successfully reset" in success_message.text
    
    # Verify can login with new password
    driver.get(f"{settings.FRONTEND_URL}/login")
    
    email_input = wait.until(EC.presence_of_element_located((By.NAME, "email")))
    email_input.send_keys("testuser@example.com")
    
    password_input = driver.find_element(By.NAME, "password")
    password_input.send_keys("NewPassword123!")
    
    submit_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
    submit_button.click()
    
    # Wait for successful login
    dashboard = wait.until(
        EC.presence_of_element_located((By.CLASS_NAME, "dashboard"))
    )
    assert "Welcome" in dashboard.text

def test_email_verification_flow(driver, wait):
    """Test the email verification flow."""
    # First login
    driver.get(f"{settings.FRONTEND_URL}/login")
    
    email_input = wait.until(EC.presence_of_element_located((By.NAME, "email")))
    email_input.send_keys("testuser@example.com")
    
    password_input = driver.find_element(By.NAME, "password")
    password_input.send_keys("TestPassword123!")
    
    submit_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
    submit_button.click()
    
    # Wait for dashboard
    dashboard = wait.until(
        EC.presence_of_element_located((By.CLASS_NAME, "dashboard"))
    )
    
    # Click resend verification email
    resend_verification_link = driver.find_element(By.LINK_TEXT, "Resend Verification Email")
    resend_verification_link.click()
    
    # Wait for success message
    success_message = wait.until(
        EC.presence_of_element_located((By.CLASS_NAME, "success-message"))
    )
    assert "Verification email sent" in success_message.text
    
    # Navigate to verification page with token
    # In a real test, we would get the token from the email
    verification_token = "test_verification_token"  # This would be a real token in production
    driver.get(f"{settings.FRONTEND_URL}/verify-email/{verification_token}")
    
    # Wait for success message
    success_message = wait.until(
        EC.presence_of_element_located((By.CLASS_NAME, "success-message"))
    )
    assert "Email successfully verified" in success_message.text
    
    # Verify user is now marked as verified
    profile_link = driver.find_element(By.LINK_TEXT, "Profile")
    profile_link.click()
    
    verification_status = wait.until(
        EC.presence_of_element_located((By.CLASS_NAME, "verification-status"))
    )
    assert "Verified" in verification_status.text 