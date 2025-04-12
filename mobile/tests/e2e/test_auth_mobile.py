"""Mobile-specific end-to-end tests for authentication functionality."""
import pytest
from appium import webdriver
from appium.webdriver.common.mobileby import MobileBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from app.core.config import settings

@pytest.fixture
def driver():
    """Create a new Appium WebDriver instance for each test."""
    desired_caps = {
        'platformName': 'Android',
        'platformVersion': '11.0',
        'deviceName': 'Android Emulator',
        'automationName': 'UiAutomator2',
        'app': settings.MOBILE_APP_PATH,
        'noReset': False
    }
    driver = webdriver.Remote('http://localhost:4723/wd/hub', desired_caps)
    yield driver
    driver.quit()

@pytest.fixture
def wait(driver):
    """Create a WebDriverWait instance."""
    return WebDriverWait(driver, 10)

def test_mobile_registration_flow(driver, wait):
    """Test the mobile registration flow."""
    # Navigate to registration screen
    register_button = wait.until(
        EC.presence_of_element_located((MobileBy.ID, "register_button"))
    )
    register_button.click()
    
    # Fill registration form
    email_input = wait.until(
        EC.presence_of_element_located((MobileBy.ID, "email_input"))
    )
    email_input.send_keys("mobileuser@example.com")
    
    password_input = driver.find_element(MobileBy.ID, "password_input")
    password_input.send_keys("MobilePass123!")
    
    confirm_password_input = driver.find_element(MobileBy.ID, "confirm_password_input")
    confirm_password_input.send_keys("MobilePass123!")
    
    full_name_input = driver.find_element(MobileBy.ID, "full_name_input")
    full_name_input.send_keys("Mobile User")
    
    # Submit registration
    submit_button = driver.find_element(MobileBy.ID, "submit_button")
    submit_button.click()
    
    # Wait for success message
    success_message = wait.until(
        EC.presence_of_element_located((MobileBy.ID, "success_message"))
    )
    assert "Registration successful" in success_message.text

def test_mobile_login_flow(driver, wait):
    """Test the mobile login flow."""
    # Fill login form
    email_input = wait.until(
        EC.presence_of_element_located((MobileBy.ID, "email_input"))
    )
    email_input.send_keys("mobileuser@example.com")
    
    password_input = driver.find_element(MobileBy.ID, "password_input")
    password_input.send_keys("MobilePass123!")
    
    # Submit login
    submit_button = driver.find_element(MobileBy.ID, "submit_button")
    submit_button.click()
    
    # Wait for successful login
    dashboard = wait.until(
        EC.presence_of_element_located((MobileBy.ID, "dashboard"))
    )
    assert "Welcome" in dashboard.text

def test_mobile_password_reset_flow(driver, wait):
    """Test the mobile password reset flow."""
    # Click forgot password link
    forgot_password_link = wait.until(
        EC.presence_of_element_located((MobileBy.ID, "forgot_password_link"))
    )
    forgot_password_link.click()
    
    # Fill email for password reset
    email_input = wait.until(
        EC.presence_of_element_located((MobileBy.ID, "email_input"))
    )
    email_input.send_keys("mobileuser@example.com")
    
    # Submit password reset request
    submit_button = driver.find_element(MobileBy.ID, "submit_button")
    submit_button.click()
    
    # Wait for success message
    success_message = wait.until(
        EC.presence_of_element_located((MobileBy.ID, "success_message"))
    )
    assert "Password reset email sent" in success_message.text
    
    # Navigate to password reset confirmation screen with token
    # In a real test, we would get the token from the email
    reset_token = "test_reset_token"  # This would be a real token in production
    driver.get(f"{settings.MOBILE_APP_URL}/reset-password/{reset_token}")
    
    # Fill new password
    new_password_input = wait.until(
        EC.presence_of_element_located((MobileBy.ID, "new_password_input"))
    )
    new_password_input.send_keys("NewMobilePass123!")
    
    confirm_password_input = driver.find_element(MobileBy.ID, "confirm_password_input")
    confirm_password_input.send_keys("NewMobilePass123!")
    
    # Submit new password
    submit_button = driver.find_element(MobileBy.ID, "submit_button")
    submit_button.click()
    
    # Wait for success message
    success_message = wait.until(
        EC.presence_of_element_located((MobileBy.ID, "success_message"))
    )
    assert "Password successfully reset" in success_message.text

def test_mobile_email_verification_flow(driver, wait):
    """Test the mobile email verification flow."""
    # First login
    email_input = wait.until(
        EC.presence_of_element_located((MobileBy.ID, "email_input"))
    )
    email_input.send_keys("mobileuser@example.com")
    
    password_input = driver.find_element(MobileBy.ID, "password_input")
    password_input.send_keys("MobilePass123!")
    
    submit_button = driver.find_element(MobileBy.ID, "submit_button")
    submit_button.click()
    
    # Wait for dashboard
    dashboard = wait.until(
        EC.presence_of_element_located((MobileBy.ID, "dashboard"))
    )
    
    # Click resend verification email
    resend_verification_link = driver.find_element(MobileBy.ID, "resend_verification_link")
    resend_verification_link.click()
    
    # Wait for success message
    success_message = wait.until(
        EC.presence_of_element_located((MobileBy.ID, "success_message"))
    )
    assert "Verification email sent" in success_message.text
    
    # Navigate to verification screen with token
    # In a real test, we would get the token from the email
    verification_token = "test_verification_token"  # This would be a real token in production
    driver.get(f"{settings.MOBILE_APP_URL}/verify-email/{verification_token}")
    
    # Wait for success message
    success_message = wait.until(
        EC.presence_of_element_located((MobileBy.ID, "success_message"))
    )
    assert "Email successfully verified" in success_message.text

def test_mobile_offline_auth_flow(driver, wait):
    """Test authentication flow when device is offline."""
    # Enable airplane mode to simulate offline state
    driver.set_network_connection(1)  # 1 = airplane mode
    
    # Try to login
    email_input = wait.until(
        EC.presence_of_element_located((MobileBy.ID, "email_input"))
    )
    email_input.send_keys("mobileuser@example.com")
    
    password_input = driver.find_element(MobileBy.ID, "password_input")
    password_input.send_keys("MobilePass123!")
    
    submit_button = driver.find_element(MobileBy.ID, "submit_button")
    submit_button.click()
    
    # Wait for offline message
    offline_message = wait.until(
        EC.presence_of_element_located((MobileBy.ID, "offline_message"))
    )
    assert "You are offline" in offline_message.text
    
    # Disable airplane mode
    driver.set_network_connection(6)  # 6 = all network connections enabled
    
    # Retry login
    submit_button = driver.find_element(MobileBy.ID, "submit_button")
    submit_button.click()
    
    # Wait for successful login
    dashboard = wait.until(
        EC.presence_of_element_located((MobileBy.ID, "dashboard"))
    )
    assert "Welcome" in dashboard.text

def test_mobile_biometric_auth_flow(driver, wait):
    """Test biometric authentication flow."""
    # Enable biometric authentication
    settings_button = wait.until(
        EC.presence_of_element_located((MobileBy.ID, "settings_button"))
    )
    settings_button.click()
    
    biometric_toggle = wait.until(
        EC.presence_of_element_located((MobileBy.ID, "biometric_toggle"))
    )
    biometric_toggle.click()
    
    # Logout
    logout_button = driver.find_element(MobileBy.ID, "logout_button")
    logout_button.click()
    
    # Try to login with biometric
    biometric_button = wait.until(
        EC.presence_of_element_located((MobileBy.ID, "biometric_button"))
    )
    biometric_button.click()
    
    # Simulate biometric authentication
    # In a real test, this would trigger the device's biometric prompt
    driver.execute_script('mobile: shell', {
        'command': 'input keyevent 66'  # Simulate fingerprint authentication
    })
    
    # Wait for successful login
    dashboard = wait.until(
        EC.presence_of_element_located((MobileBy.ID, "dashboard"))
    )
    assert "Welcome" in dashboard.text 